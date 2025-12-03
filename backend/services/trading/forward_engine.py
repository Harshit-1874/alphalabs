"""
Forward Test Engine for AlphaLab Trading Platform.

Purpose:
    Execute forward tests with live market data, waiting for candle closes
    and processing in real-time. Supports auto-stop conditions, email
    notifications, and real-time WebSocket updates.

Features:
    - Live data polling from market data service
    - Candle close detection and countdown updates
    - Auto-stop condition monitoring
    - Email notifications for key events
    - Real-time WebSocket broadcasting
    - Result generation on completion

Usage:
    engine = ForwardEngine(db_session, websocket_manager)
    await engine.start_forward_test(
        session_id="uuid",
        agent=agent_obj,
        asset="BTC/USDT",
        timeframe="1h",
        starting_capital=10000.0,
        safety_mode=True,
        auto_stop_config={
            "enabled": True,
            "loss_pct": 5.0
        }
    )
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models.agent import Agent
from models.arena import TestSession, Trade, AiThought
from services.market_data_service import MarketDataService, Candle
from services.trading.indicator_calculator import IndicatorCalculator
from services.trading.position_manager import PositionManager, Position as PositionData
from services.ai_trader import AITrader, AIDecision
from websocket.manager import WebSocketManager
from websocket.events import Event, EventType, create_countdown_update_event
from config import settings
from exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """
    Represents the runtime state of a forward test session.
    
    Attributes:
        session_id: Unique session identifier
        agent: Agent configuration
        asset: Trading asset
        timeframe: Candlestick timeframe
        position_manager: Position management instance
        ai_trader: AI decision making instance
        is_stopped: Whether session is stopped
        candles_processed: List of processed candles
        ai_thoughts: List of AI reasoning records
        next_candle_time: Expected time of next candle close
        auto_stop_config: Auto-stop configuration
    """
    session_id: str
    agent: Agent
    asset: str
    timeframe: str
    position_manager: PositionManager
    ai_trader: AITrader
    is_stopped: bool = False
    candles_processed: List[Candle] = None
    ai_thoughts: List[Dict[str, Any]] = None
    next_candle_time: Optional[datetime] = None
    auto_stop_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.candles_processed is None:
            self.candles_processed = []
        if self.ai_thoughts is None:
            self.ai_thoughts = []
        if self.auto_stop_config is None:
            self.auto_stop_config = {}


class ForwardEngine:
    """
    Forward test engine for executing live trading simulations.
    
    Manages the complete forward test lifecycle:
    1. Initialize services (indicators, AI, position manager)
    2. Poll for latest candle data
    3. Wait for candle close with countdown updates
    4. Process candles and get AI decisions
    5. Monitor auto-stop conditions
    6. Send email notifications
    7. Generate results on completion
    
    Supports manual stop and auto-stop based on loss thresholds.
    """
    
    # Timeframe to minutes mapping
    TIMEFRAME_MINUTES = {
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440,
    }
    
    def __init__(self, session_factory, websocket_manager: WebSocketManager):
        """
        Initialize forward test engine.
        
        Args:
            session_factory: SQLAlchemy async session factory
            websocket_manager: WebSocket manager for real-time updates
        """
        self.session_factory = session_factory
        self.websocket_manager = websocket_manager
        
        # Store active session states
        self.active_sessions: Dict[str, SessionState] = {}
        
        logger.info("ForwardEngine initialized")
    
    async def start_forward_test(
        self,
        session_id: str,
        agent: Agent,
        asset: str,
        timeframe: str,
        starting_capital: float,
        safety_mode: bool = True,
        auto_stop_config: Optional[Dict[str, Any]] = None,
        email_notifications: bool = False
    ) -> None:
        """
        Start a forward test session.
        
        Validates parameters, initializes services, and begins live data polling.
        Runs in background task.
        
        Args:
            session_id: Unique session identifier
            agent: Agent configuration object
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            starting_capital: Initial capital amount
            safety_mode: Whether to enforce safety mode (-2% stop loss)
            auto_stop_config: Auto-stop configuration dict
            email_notifications: Whether to send email notifications
            
        Raises:
            ValidationError: If parameters are invalid
            Exception: If initialization fails
        """
        logger.info(
            f"Starting forward test: session_id={session_id}, "
            f"agent={agent.name}, asset={asset}, timeframe={timeframe}"
        )
        
        try:
            # Create a new session for initialization
            async with self.session_factory() as db:
                # Validate parameters
                self._validate_parameters(asset, timeframe, starting_capital)
                
                # Update session status to initializing
                await self._update_session_status(db, session_id, "initializing")
                
                # Initialize position manager
                position_manager = PositionManager(
                    starting_capital=starting_capital,
                    safety_mode=safety_mode
                )
                
                # Initialize AI trader
                # Get API key from agent's api_key relationship
                if not agent.api_key or not agent.api_key.encrypted_key:
                    raise ValidationError(f"Agent {agent.name} does not have a valid API key")
                
                # Decrypt API key
                from core.encryption import decrypt_api_key
                api_key = decrypt_api_key(agent.api_key.encrypted_key)
                
                ai_trader = AITrader(
                    api_key=api_key,
                    model=agent.model,
                    strategy_prompt=agent.strategy_prompt,
                    mode=agent.mode
                )
                
                # Create session state
                session_state = SessionState(
                    session_id=session_id,
                    agent=agent,
                    asset=asset,
                    timeframe=timeframe,
                    position_manager=position_manager,
                    ai_trader=ai_trader,
                    auto_stop_config=auto_stop_config or {}
                )
                
                # Store session state
                self.active_sessions[session_id] = session_state
                
                # Update session status to running
                await self._update_session_status(db, session_id, "running")
                await self._update_session_started_at(db, session_id, datetime.utcnow())
                
                # Broadcast session initialized event
                await self._broadcast_session_initialized(
                    session_id, agent, asset, timeframe, email_notifications
                )
                
                # Start forward test processing in background
                asyncio.create_task(
                    self._process_forward_test(session_id, email_notifications)
                )
                
                logger.info(f"Forward test started successfully: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error starting forward test: {e}", exc_info=True)
            # Create a new session for error reporting
            async with self.session_factory() as db:
                await self._update_session_status(db, session_id, "failed")
            await self._broadcast_error(session_id, str(e))
            raise
    
    def _validate_parameters(
        self,
        asset: str,
        timeframe: str,
        starting_capital: float
    ) -> None:
        """
        Validate forward test parameters.
        
        Args:
            asset: Trading asset
            timeframe: Candlestick timeframe
            starting_capital: Initial capital
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        # Validate asset
        if asset not in MarketDataService.ASSET_TICKER_MAP:
            supported = ', '.join(MarketDataService.ASSET_TICKER_MAP.keys())
            raise ValidationError(
                f"Unsupported asset '{asset}'. Supported: {supported}"
            )
        
        # Validate timeframe
        if timeframe not in MarketDataService.TIMEFRAME_INTERVAL_MAP:
            supported = ', '.join(MarketDataService.TIMEFRAME_INTERVAL_MAP.keys())
            raise ValidationError(
                f"Unsupported timeframe '{timeframe}'. Supported: {supported}"
            )
        
        # Validate starting capital
        if starting_capital <= 0:
            raise ValidationError(
                f"starting_capital must be positive, got {starting_capital}"
            )
        
        if starting_capital < 100:
            raise ValidationError(
                f"starting_capital must be at least $100, got ${starting_capital}"
            )
    
    def _calculate_next_candle_close_time(
        self,
        current_time: datetime,
        timeframe: str
    ) -> datetime:
        """
        Calculate the next candle close time based on timeframe.
        
        Args:
            current_time: Current datetime
            timeframe: Candlestick timeframe
            
        Returns:
            datetime: Next candle close time
        """
        minutes = self.TIMEFRAME_MINUTES.get(timeframe, 60)
        
        # Round current time to the next candle boundary
        # For example, if it's 10:23 and timeframe is 1h, next close is 11:00
        current_minute = current_time.hour * 60 + current_time.minute
        
        # Calculate minutes until next boundary
        minutes_until_next = minutes - (current_minute % minutes)
        
        # Calculate next close time
        next_close = current_time + timedelta(minutes=minutes_until_next)
        
        # Round to exact minute (remove seconds and microseconds)
        next_close = next_close.replace(second=0, microsecond=0)
        
        return next_close
    
    async def _update_session_status(self, db: AsyncSession, session_id: str, status: str) -> None:
        """Update session status in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(status=status)
        )
        await db.execute(stmt)
        await db.commit()
    
    async def _update_session_started_at(self, db: AsyncSession, session_id: str, started_at: datetime) -> None:
        """Update session started_at timestamp in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(started_at=started_at)
        )
        await db.execute(stmt)
        await db.commit()
    
    async def _broadcast_session_initialized(
        self,
        session_id: str,
        agent: Agent,
        asset: str,
        timeframe: str,
        email_notifications: bool
    ) -> None:
        """Broadcast session initialized event to WebSocket clients."""
        event = Event(
            type=EventType.SESSION_INITIALIZED,
            data={
                "session_id": session_id,
                "agent_name": agent.name,
                "agent_mode": agent.mode,
                "asset": asset,
                "timeframe": timeframe,
                "email_notifications": email_notifications,
                "test_type": "forward"
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _broadcast_error(self, session_id: str, error_message: str) -> None:
        """Broadcast error event to WebSocket clients."""
        event = Event(
            type=EventType.ERROR,
            data={
                "message": error_message
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _process_forward_test(
        self,
        session_id: str,
        email_notifications: bool
    ) -> None:
        """
        Main forward test processing loop.
        
        Polls for latest candle, waits for candle close, processes candle,
        and monitors auto-stop conditions.
        
        Args:
            session_id: Session identifier
            email_notifications: Whether to send email notifications
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            logger.error(f"Session state not found: {session_id}")
            return
        
        logger.info(f"Starting forward test processing: session_id={session_id}")
        
        try:
            # Create session for the forward test loop
            async with self.session_factory() as db:
                market_data_service = MarketDataService(db)
                
                # Main processing loop
                while not session_state.is_stopped:
                    # Wait for next candle close
                    candle = await self._wait_for_candle_close(
                        session_id,
                        session_state,
                        market_data_service
                    )
                    
                    if candle is None:
                        # Stopped during wait
                        break
                    
                    # Add candle to processed list
                    session_state.candles_processed.append(candle)
                    
                    # Process this candle
                    await self._process_candle(
                        db,
                        session_id,
                        session_state,
                        candle,
                        email_notifications
                    )
                    
                    # Check auto-stop conditions
                    should_stop = await self._check_auto_stop_conditions(
                        session_id,
                        session_state
                    )
                    
                    if should_stop:
                        logger.info(f"Auto-stop triggered: session_id={session_id}")
                        await self._handle_auto_stop(
                            db,
                            session_id,
                            session_state,
                            email_notifications
                        )
                        break
                
                # Forward test completed or stopped
                if not session_state.is_stopped:
                    logger.info(f"Forward test completed: session_id={session_id}")
                
        except Exception as e:
            logger.error(f"Error processing forward test: {e}", exc_info=True)
            async with self.session_factory() as db:
                await self._update_session_status(db, session_id, "failed")
            await self._broadcast_error(session_id, str(e))
        finally:
            # Clean up session state
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def stop_forward_test(self, session_id: str) -> str:
        """
        Stop a forward test and generate results.
        
        Closes open position and generates final results.
        
        Args:
            session_id: Session identifier
            
        Returns:
            result_id: ID of generated result record
            
        Raises:
            ValidationError: If session not found
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        
        logger.info(f"Stopping forward test: session_id={session_id}")
        
        # Set stop flag
        session_state.is_stopped = True
        
        async with self.session_factory() as db:
            market_data_service = MarketDataService(db)
            
            # Close open position if exists
            if session_state.position_manager.has_open_position():
                # Get latest price
                latest_candle = await market_data_service.get_latest_candle(
                    session_state.asset,
                    session_state.timeframe
                )
                
                closed_trade = await session_state.position_manager.close_position(
                    exit_price=latest_candle.close,
                    reason="manual"
                )
                
                if closed_trade:
                    await self._handle_position_closed(
                        db,
                        session_id,
                        session_state,
                        closed_trade,
                        len(session_state.candles_processed),
                        latest_candle.timestamp
                    )
            
            # Generate results
            result_id = await self._complete_forward_test(
                db,
                session_id,
                session_state,
                force_stop=True
            )
        
        logger.info(f"Forward test stopped: session_id={session_id}, result_id={result_id}")
        
        return result_id
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """
        Get session state for a running forward test.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionState object or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def is_session_active(self, session_id: str) -> bool:
        """
        Check if a session is currently active.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session is active, False otherwise
        """
        return session_id in self.active_sessions

    
    async def _wait_for_candle_close(
        self,
        session_id: str,
        session_state: SessionState,
        market_data_service: MarketDataService
    ) -> Optional[Candle]:
        """
        Wait for the next candle to close, sending countdown updates.
        
        Polls market data service for latest candle and sends countdown
        updates every 30 seconds until candle closes.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            market_data_service: Market data service instance
            
        Returns:
            Candle: The newly closed candle, or None if stopped
        """
        # Get current time
        current_time = datetime.utcnow()
        
        # Calculate next candle close time
        next_close_time = self._calculate_next_candle_close_time(
            current_time,
            session_state.timeframe
        )
        session_state.next_candle_time = next_close_time
        
        logger.info(
            f"Waiting for candle close: session_id={session_id}, "
            f"next_close={next_close_time.isoformat()}"
        )
        
        # Get the last known candle timestamp to detect new candles
        last_candle_timestamp = None
        if session_state.candles_processed:
            last_candle_timestamp = session_state.candles_processed[-1].timestamp
        
        # Wait loop with countdown updates
        while not session_state.is_stopped:
            current_time = datetime.utcnow()
            
            # Calculate seconds remaining
            seconds_remaining = int((next_close_time - current_time).total_seconds())
            
            # Check if candle has closed
            if seconds_remaining <= 0:
                # Try to fetch the new candle
                try:
                    latest_candle = await market_data_service.get_latest_candle(
                        session_state.asset,
                        session_state.timeframe
                    )
                    
                    # Check if this is a new candle
                    if last_candle_timestamp is None or latest_candle.timestamp > last_candle_timestamp:
                        logger.info(
                            f"New candle detected: session_id={session_id}, "
                            f"timestamp={latest_candle.timestamp.isoformat()}"
                        )
                        return latest_candle
                    else:
                        # Candle not ready yet, wait a bit more
                        logger.debug(
                            f"Candle not ready yet: session_id={session_id}, "
                            f"waiting 10 more seconds"
                        )
                        await asyncio.sleep(10)
                        # Recalculate next close time
                        next_close_time = self._calculate_next_candle_close_time(
                            datetime.utcnow(),
                            session_state.timeframe
                        )
                        continue
                        
                except Exception as e:
                    logger.error(f"Error fetching latest candle: {e}")
                    # Wait and retry
                    await asyncio.sleep(10)
                    continue
            
            # Send countdown update
            await self._broadcast_countdown_update(
                session_id,
                seconds_remaining,
                next_close_time
            )
            
            # Wait 30 seconds before next update (or less if close to candle close)
            wait_time = min(30, max(1, seconds_remaining))
            await asyncio.sleep(wait_time)
        
        # Stopped during wait
        return None
    
    async def _broadcast_countdown_update(
        self,
        session_id: str,
        seconds_remaining: int,
        next_candle_time: datetime
    ) -> None:
        """Broadcast countdown update event."""
        event = create_countdown_update_event(
            seconds_remaining=seconds_remaining,
            next_candle_time=next_candle_time.isoformat()
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _process_candle(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        candle: Candle,
        email_notifications: bool
    ) -> None:
        """
        Process a single candle.
        
        Calculates indicators, gets AI decision, manages positions,
        and broadcasts events.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            candle: Current candle to process
            email_notifications: Whether to send email notifications
        """
        candle_number = len(session_state.candles_processed)
        
        logger.info(
            f"Processing candle {candle_number}: "
            f"timestamp={candle.timestamp}, close={candle.close}"
        )
        
        # Calculate indicators for current candle
        # We need to create an indicator calculator with all processed candles
        indicator_calculator = IndicatorCalculator(
            candles=session_state.candles_processed,
            enabled_indicators=session_state.agent.indicators,
            mode=session_state.agent.mode,
            custom_indicators=session_state.agent.custom_indicators
        )
        
        # Calculate indicators for the latest candle
        indicators = indicator_calculator.calculate_all(len(session_state.candles_processed) - 1)
        
        # Broadcast candle event with indicators
        await self._broadcast_candle(session_id, candle, indicators, candle_number)
        
        # Update open position if exists
        if session_state.position_manager.has_open_position():
            close_reason = await session_state.position_manager.update_position(
                candle_high=candle.high,
                candle_low=candle.low,
                current_price=candle.close
            )
            
            # If position was closed by stop-loss or take-profit
            if close_reason:
                closed_trade = session_state.position_manager.get_closed_trades()[-1]
                await self._handle_position_closed(
                    db,
                    session_id,
                    session_state,
                    closed_trade,
                    candle_number,
                    candle.timestamp
                )
                
                # Send email notification if enabled
                if email_notifications:
                    await self._send_position_closed_notification(
                        session_state,
                        closed_trade
                    )
        
        # Get AI decision
        position_state = session_state.position_manager.get_position()
        equity = session_state.position_manager.get_total_equity()
        
        # Broadcast AI thinking event
        await self._broadcast_ai_thinking(session_id)
        
        decision = await session_state.ai_trader.get_decision(
            candle=candle,
            indicators=indicators,
            position_state=position_state,
            equity=equity
        )
        
        # Store AI thought
        ai_thought = {
            "candle_number": candle_number,
            "timestamp": candle.timestamp,
            "candle_data": {
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume
            },
            "indicator_values": indicators,
            "reasoning": decision.reasoning,
            "decision": decision.action,
            "order_data": {
                "stop_loss_price": decision.stop_loss_price,
                "take_profit_price": decision.take_profit_price,
                "size_percentage": decision.size_percentage,
                "leverage": decision.leverage
            } if decision.action in ["LONG", "SHORT"] else None
        }
        session_state.ai_thoughts.append(ai_thought)
        
        # Broadcast AI decision event
        await self._broadcast_ai_decision(session_id, decision)
        
        # Execute AI decision
        await self._execute_decision(
            db,
            session_id,
            session_state,
            decision,
            candle,
            candle_number,
            email_notifications
        )
        
        # Broadcast stats update
        stats = session_state.position_manager.get_stats()
        await self._broadcast_stats_update(session_id, stats)
    
    async def _execute_decision(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        decision: AIDecision,
        candle: Candle,
        candle_number: int,
        email_notifications: bool
    ) -> None:
        """
        Execute AI trading decision.
        
        Opens, closes, or holds positions based on AI decision.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            decision: AI decision object
            candle: Current candle
            candle_number: Current candle number
            email_notifications: Whether to send email notifications
        """
        action = decision.action.upper()
        
        # Handle CLOSE action
        if action == "CLOSE":
            if session_state.position_manager.has_open_position():
                closed_trade = await session_state.position_manager.close_position(
                    exit_price=candle.close,
                    reason="ai_decision"
                )
                if closed_trade:
                    await self._handle_position_closed(
                        db,
                        session_id,
                        session_state,
                        closed_trade,
                        candle_number,
                        candle.timestamp
                    )
                    
                    # Send email notification if enabled
                    if email_notifications:
                        await self._send_position_closed_notification(
                            session_state,
                            closed_trade
                        )
            return
        
        # Handle HOLD action
        if action == "HOLD":
            return
        
        # Handle LONG/SHORT actions
        if action in ["LONG", "SHORT"]:
            # Can only open if no position exists
            if session_state.position_manager.has_open_position():
                logger.warning(
                    f"Cannot open {action} position: position already exists"
                )
                return
            
            # Open position
            success = await session_state.position_manager.open_position(
                action=action.lower(),
                entry_price=candle.close,
                size_percentage=decision.size_percentage,
                stop_loss=decision.stop_loss_price,
                take_profit=decision.take_profit_price,
                leverage=decision.leverage
            )
            
            if success:
                position = session_state.position_manager.get_position()
                await self._handle_position_opened(
                    db,
                    session_id,
                    session_state,
                    position,
                    candle_number,
                    candle.timestamp,
                    decision.reasoning
                )
                
                # Send email notification if enabled
                if email_notifications:
                    await self._send_position_opened_notification(
                        session_state,
                        position
                    )
    
    async def _handle_position_opened(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        position: PositionData,
        candle_number: int,
        timestamp: datetime,
        reasoning: str
    ) -> None:
        """
        Handle position opened event.
        
        Saves trade to database and broadcasts event.
        """
        logger.info(
            f"Position opened: session_id={session_id}, "
            f"action={position.action}, entry_price={position.entry_price}, "
            f"size={position.size}, leverage={position.leverage}"
        )
        
        # Create trade record in database
        trade_number = len(session_state.position_manager.get_closed_trades()) + 1
        trade = Trade(
            session_id=session_id,
            trade_number=trade_number,
            type=position.action,
            entry_price=Decimal(str(position.entry_price)),
            entry_time=timestamp,
            entry_candle=candle_number,
            entry_reasoning=reasoning,
            size=Decimal(str(position.size)),
            leverage=position.leverage,
            stop_loss=Decimal(str(position.stop_loss)) if position.stop_loss else None,
            take_profit=Decimal(str(position.take_profit)) if position.take_profit else None
        )
        db.add(trade)
        await db.commit()
        
        # Broadcast position opened event
        event = Event(
            type=EventType.POSITION_OPENED,
            data={
                "trade_number": trade_number,
                "action": position.action,
                "entry_price": position.entry_price,
                "size": position.size,
                "leverage": position.leverage,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit,
                "entry_time": timestamp.isoformat(),
                "reasoning": reasoning
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _handle_position_closed(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        trade: Any,  # Trade from position_manager
        candle_number: int,
        timestamp: datetime
    ) -> None:
        """
        Handle position closed event.
        
        Updates trade in database and broadcasts event.
        """
        logger.info(
            f"Position closed: session_id={session_id}, "
            f"action={trade.action}, exit_price={trade.exit_price}, "
            f"pnl={trade.pnl}, reason={trade.reason}"
        )
        
        # Update trade record in database
        trade_number = len(session_state.position_manager.get_closed_trades())
        stmt = (
            update(Trade)
            .where(Trade.session_id == session_id)
            .where(Trade.trade_number == trade_number)
            .values(
                exit_price=Decimal(str(trade.exit_price)),
                exit_time=timestamp,
                exit_candle=candle_number,
                exit_type=trade.reason,
                pnl_amount=Decimal(str(trade.pnl)),
                pnl_pct=Decimal(str(trade.pnl_pct))
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        # Broadcast position closed event
        event = Event(
            type=EventType.POSITION_CLOSED,
            data={
                "trade_number": trade_number,
                "action": trade.action,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "pnl_pct": trade.pnl_pct,
                "reason": trade.reason,
                "exit_time": timestamp.isoformat()
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _broadcast_candle(
        self,
        session_id: str,
        candle: Candle,
        indicators: Dict[str, float],
        candle_number: int
    ) -> None:
        """Broadcast candle event with indicators."""
        event = Event(
            type=EventType.CANDLE,
            data={
                "candle_number": candle_number,
                "timestamp": candle.timestamp.isoformat(),
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "indicators": indicators
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _broadcast_ai_thinking(self, session_id: str) -> None:
        """Broadcast AI thinking event."""
        event = Event(
            type=EventType.AI_THINKING,
            data={"status": "analyzing"}
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _broadcast_ai_decision(self, session_id: str, decision: AIDecision) -> None:
        """Broadcast AI decision event."""
        event = Event(
            type=EventType.AI_DECISION,
            data={
                "action": decision.action,
                "reasoning": decision.reasoning,
                "stop_loss_price": decision.stop_loss_price,
                "take_profit_price": decision.take_profit_price,
                "size_percentage": decision.size_percentage,
                "leverage": decision.leverage
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _broadcast_stats_update(self, session_id: str, stats: Dict[str, Any]) -> None:
        """Broadcast stats update event."""
        event = Event(
            type=EventType.STATS_UPDATE,
            data=stats
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
    
    async def _check_auto_stop_conditions(
        self,
        session_id: str,
        session_state: SessionState
    ) -> bool:
        """
        Check if auto-stop conditions are met.
        
        Monitors loss threshold and other auto-stop conditions.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            
        Returns:
            bool: True if auto-stop should trigger, False otherwise
        """
        # Check if auto-stop is enabled
        if not session_state.auto_stop_config.get("enabled", False):
            return False
        
        # Get current stats
        stats = session_state.position_manager.get_stats()
        
        # Check loss threshold
        loss_pct_threshold = session_state.auto_stop_config.get("loss_pct")
        if loss_pct_threshold is not None:
            current_pnl_pct = stats.get("total_pnl_pct", 0.0)
            
            if current_pnl_pct <= -abs(loss_pct_threshold):
                logger.warning(
                    f"Auto-stop triggered by loss threshold: "
                    f"session_id={session_id}, "
                    f"current_pnl={current_pnl_pct}%, "
                    f"threshold={-abs(loss_pct_threshold)}%"
                )
                return True
        
        # Add more auto-stop conditions here if needed
        # For example: max drawdown, time-based, etc.
        
        return False
    
    async def _handle_auto_stop(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        email_notifications: bool
    ) -> None:
        """
        Handle auto-stop trigger.
        
        Closes open position and generates results.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            email_notifications: Whether to send email notifications
        """
        logger.info(f"Handling auto-stop: session_id={session_id}")
        
        # Set stop flag
        session_state.is_stopped = True
        
        # Close open position if exists
        if session_state.position_manager.has_open_position():
            # Get latest candle for exit price
            if session_state.candles_processed:
                latest_candle = session_state.candles_processed[-1]
                
                closed_trade = await session_state.position_manager.close_position(
                    exit_price=latest_candle.close,
                    reason="auto_stop"
                )
                
                if closed_trade:
                    await self._handle_position_closed(
                        db,
                        session_id,
                        session_state,
                        closed_trade,
                        len(session_state.candles_processed),
                        latest_candle.timestamp
                    )
        
        # Send email notification if enabled
        if email_notifications:
            await self._send_auto_stop_notification(session_state)
        
        # Generate results
        await self._complete_forward_test(
            db,
            session_id,
            session_state,
            auto_stop=True
        )
    
    async def _send_position_opened_notification(
        self,
        session_state: SessionState,
        position: PositionData
    ) -> None:
        """
        Send email notification for position opened.
        
        Args:
            session_state: Session state object
            position: Opened position data
        """
        # TODO: Implement email notification
        # This would integrate with an email service (SendGrid, AWS SES, etc.)
        logger.info(
            f"Email notification: Position opened - "
            f"agent={session_state.agent.name}, "
            f"action={position.action}, "
            f"entry_price={position.entry_price}"
        )
    
    async def _send_position_closed_notification(
        self,
        session_state: SessionState,
        trade: Any
    ) -> None:
        """
        Send email notification for position closed.
        
        Args:
            session_state: Session state object
            trade: Closed trade data
        """
        # TODO: Implement email notification
        logger.info(
            f"Email notification: Position closed - "
            f"agent={session_state.agent.name}, "
            f"pnl={trade.pnl}, "
            f"reason={trade.reason}"
        )
    
    async def _send_auto_stop_notification(
        self,
        session_state: SessionState
    ) -> None:
        """
        Send email notification for auto-stop trigger.
        
        Args:
            session_state: Session state object
        """
        # TODO: Implement email notification
        stats = session_state.position_manager.get_stats()
        logger.info(
            f"Email notification: Auto-stop triggered - "
            f"agent={session_state.agent.name}, "
            f"final_pnl={stats.get('total_pnl_pct', 0.0)}%"
        )
    
    async def _complete_forward_test(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        force_stop: bool = False,
        auto_stop: bool = False
    ) -> str:
        """
        Complete forward test and generate results.
        
        Saves final results, AI thoughts, and broadcasts completion event.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            force_stop: Whether this is a forced stop
            auto_stop: Whether this is an auto-stop
            
        Returns:
            result_id: ID of generated result record
        """
        logger.info(f"Completing forward test: session_id={session_id}")
        
        # Update session status
        await self._update_session_status(db, session_id, "completed")
        await self._update_session_completed_at(db, session_id, datetime.utcnow())
        
        # Get final stats
        stats = session_state.position_manager.get_stats()
        
        # Update session with final equity and PnL
        await self._update_session_final_stats(
            db,
            session_id,
            stats["current_equity"],
            stats["equity_change_pct"]
        )
        
        # Save AI thoughts to database
        await self._save_ai_thoughts(db, session_id, session_state.ai_thoughts)
        
        # Generate result using ResultService (will be implemented in task 10)
        # For now, we'll create a placeholder result_id
        result_id = f"result_{session_id}"
        
        # Broadcast session completed event
        event = Event(
            type=EventType.SESSION_COMPLETED,
            data={
                "session_id": session_id,
                "result_id": result_id,
                "final_equity": stats["current_equity"],
                "total_pnl": stats["total_pnl"],
                "total_pnl_pct": stats["total_pnl_pct"],
                "total_trades": stats["total_trades"],
                "win_rate": stats["win_rate"],
                "forced_stop": force_stop,
                "auto_stop": auto_stop
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
        
        logger.info(
            f"Forward test completed: session_id={session_id}, "
            f"final_equity={stats['current_equity']}, "
            f"pnl={stats['total_pnl_pct']}%"
        )
        
        return result_id
    
    async def _update_session_completed_at(self, db: AsyncSession, session_id: str, completed_at: datetime) -> None:
        """Update session completed_at timestamp in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(completed_at=completed_at)
        )
        await db.execute(stmt)
        await db.commit()
    
    async def _update_session_final_stats(
        self,
        db: AsyncSession,
        session_id: str,
        current_equity: float,
        current_pnl_pct: float
    ) -> None:
        """Update session with final equity and PnL."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(
                current_equity=Decimal(str(current_equity)),
                current_pnl_pct=Decimal(str(current_pnl_pct))
            )
        )
        await db.execute(stmt)
        await db.commit()
    
    async def _save_ai_thoughts(
        self,
        db: AsyncSession,
        session_id: str,
        ai_thoughts: List[Dict[str, Any]]
    ) -> None:
        """
        Save AI thoughts to database.
        
        Args:
            db: Database session
            session_id: Session identifier
            ai_thoughts: List of AI thought records
        """
        logger.info(f"Saving {len(ai_thoughts)} AI thoughts for session {session_id}")
        
        for thought in ai_thoughts:
            ai_thought = AiThought(
                session_id=session_id,
                candle_number=thought["candle_number"],
                timestamp=thought["timestamp"],
                candle_data=thought["candle_data"],
                indicator_values=thought["indicator_values"],
                thought_type="decision",
                reasoning=thought["reasoning"],
                decision=thought["decision"].lower() if thought["decision"] else None,
                order_data=thought.get("order_data")
            )
            db.add(ai_thought)
        
        await db.commit()
        
        logger.info(f"Saved AI thoughts for session {session_id}")
