"""
Backtest Engine for AlphaLab Trading Platform.

Purpose:
    Execute backtests by processing historical candle data sequentially,
    calculating indicators, getting AI decisions, and managing positions.
    Supports pause/resume/stop functionality with real-time WebSocket updates.

Features:
    - Session state management
    - Sequential candle processing
    - Indicator calculation integration
    - AI decision integration
    - Position management
    - Real-time WebSocket broadcasting
    - Pause/resume/stop controls
    - Result generation on completion

Usage:
    engine = BacktestEngine(db_session, websocket_manager)
    await engine.start_backtest(
        session_id="uuid",
        agent=agent_obj,
        asset="BTC/USDT",
        timeframe="1h",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 31),
        starting_capital=10000.0
    )
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
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
from websocket.events import Event, EventType
from config import settings
from exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """
    Represents the runtime state of a backtest session.
    
    Attributes:
        session_id: Unique session identifier
        agent: Agent configuration
        candles: Historical candle data
        current_index: Current candle being processed
        position_manager: Position management instance
        indicator_calculator: Indicator calculation instance
        ai_trader: AI decision making instance
        is_paused: Whether session is paused
        is_stopped: Whether session is stopped
        pause_event: Asyncio event for pause coordination
        ai_thoughts: List of AI reasoning records
    """
    session_id: str
    agent: Agent
    candles: List[Candle]
    current_index: int
    position_manager: PositionManager
    indicator_calculator: IndicatorCalculator
    ai_trader: AITrader
    is_paused: bool = False
    is_stopped: bool = False
    pause_event: asyncio.Event = None
    ai_thoughts: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.pause_event is None:
            self.pause_event = asyncio.Event()
            self.pause_event.set()  # Start unpaused
        if self.ai_thoughts is None:
            self.ai_thoughts = []


class BacktestEngine:
    """
    Backtest engine for executing historical trading simulations.
    
    Manages the complete backtest lifecycle:
    1. Load historical data
    2. Initialize services (indicators, AI, position manager)
    3. Process candles sequentially
    4. Broadcast events via WebSocket
    5. Generate results on completion
    
    Supports pause/resume/stop controls for interactive testing.
    """
    
    def __init__(self, db: AsyncSession, websocket_manager: WebSocketManager):
        """
        Initialize backtest engine.
        
        Args:
            db: Database session for persistence
            websocket_manager: WebSocket manager for real-time updates
        """
        self.db = db
        self.websocket_manager = websocket_manager
        self.market_data_service = MarketDataService(db)
        
        # Store active session states
        self.active_sessions: Dict[str, SessionState] = {}
        
        logger.info("BacktestEngine initialized")
    
    async def start_backtest(
        self,
        session_id: str,
        agent: Agent,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        starting_capital: float,
        safety_mode: bool = True
    ) -> None:
        """
        Start a backtest session.
        
        Validates parameters, loads historical data, initializes services,
        and begins processing candles. Runs in background task.
        
        Args:
            session_id: Unique session identifier
            agent: Agent configuration object
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            start_date: Backtest start date
            end_date: Backtest end date
            starting_capital: Initial capital amount
            safety_mode: Whether to enforce safety mode (-2% stop loss)
            
        Raises:
            ValidationError: If parameters are invalid
            Exception: If data loading or initialization fails
        """
        logger.info(
            f"Starting backtest: session_id={session_id}, "
            f"agent={agent.name}, asset={asset}, timeframe={timeframe}, "
            f"start={start_date.date()}, end={end_date.date()}"
        )
        
        try:
            # Validate parameters
            self._validate_parameters(asset, timeframe, start_date, end_date, starting_capital)
            
            # Update session status to initializing
            await self._update_session_status(session_id, "initializing")
            
            # Load historical candle data
            logger.info(f"Loading historical data for {asset} {timeframe}")
            candles = await self.market_data_service.get_historical_data(
                asset=asset,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if not candles:
                raise ValidationError(
                    f"No historical data available for {asset} {timeframe} "
                    f"from {start_date.date()} to {end_date.date()}"
                )
            
            logger.info(f"Loaded {len(candles)} candles for backtest")
            
            # Update session with total candles
            await self._update_session_total_candles(session_id, len(candles))
            
            # Initialize indicator calculator
            indicator_calculator = IndicatorCalculator(
                candles=candles,
                enabled_indicators=agent.indicators,
                mode=agent.mode,
                custom_indicators=agent.custom_indicators
            )
            
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
                candles=candles,
                current_index=0,
                position_manager=position_manager,
                indicator_calculator=indicator_calculator,
                ai_trader=ai_trader
            )
            
            # Store session state
            self.active_sessions[session_id] = session_state
            
            # Update session status to running
            await self._update_session_status(session_id, "running")
            await self._update_session_started_at(session_id, datetime.utcnow())
            
            # Broadcast session initialized event
            await self._broadcast_session_initialized(session_id, agent, asset, timeframe, len(candles))
            
            # Start processing candles in background
            asyncio.create_task(self._process_backtest(session_id))
            
            logger.info(f"Backtest started successfully: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error starting backtest: {e}", exc_info=True)
            await self._update_session_status(session_id, "failed")
            await self._broadcast_error(session_id, str(e))
            raise
    
    def _validate_parameters(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        starting_capital: float
    ) -> None:
        """
        Validate backtest parameters.
        
        Args:
            asset: Trading asset
            timeframe: Candlestick timeframe
            start_date: Start date
            end_date: End date
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
        
        # Validate date range
        if start_date >= end_date:
            raise ValidationError(
                f"start_date ({start_date.date()}) must be before end_date ({end_date.date()})"
            )
        
        if start_date > datetime.now():
            raise ValidationError(
                f"start_date ({start_date.date()}) cannot be in the future"
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
    
    async def _update_session_status(self, session_id: str, status: str) -> None:
        """Update session status in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(status=status)
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _update_session_started_at(self, session_id: str, started_at: datetime) -> None:
        """Update session started_at timestamp in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(started_at=started_at)
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _update_session_total_candles(self, session_id: str, total_candles: int) -> None:
        """Update session total_candles in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(total_candles=total_candles)
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _broadcast_session_initialized(
        self,
        session_id: str,
        agent: Agent,
        asset: str,
        timeframe: str,
        total_candles: int
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
                "total_candles": total_candles
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

    async def _process_backtest(self, session_id: str) -> None:
        """
        Main backtest processing loop.
        
        Processes each candle sequentially, calculating indicators,
        getting AI decisions, managing positions, and broadcasting events.
        
        Args:
            session_id: Session identifier
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            logger.error(f"Session state not found: {session_id}")
            return
        
        logger.info(f"Starting backtest processing: session_id={session_id}")
        
        try:
            # Process each candle
            while session_state.current_index < len(session_state.candles):
                # Check if stopped
                if session_state.is_stopped:
                    logger.info(f"Backtest stopped: session_id={session_id}")
                    break
                
                # Wait if paused
                await session_state.pause_event.wait()
                
                # Get current candle
                candle = session_state.candles[session_state.current_index]
                
                # Process this candle
                await self._process_candle(session_id, session_state, candle)
                
                # Move to next candle
                session_state.current_index += 1
                
                # Update session current_candle in database
                await self._update_session_current_candle(session_id, session_state.current_index)
            
            # Backtest completed
            if not session_state.is_stopped:
                logger.info(f"Backtest completed: session_id={session_id}")
                await self._complete_backtest(session_id, session_state)
            
        except Exception as e:
            logger.error(f"Error processing backtest: {e}", exc_info=True)
            await self._update_session_status(session_id, "failed")
            await self._broadcast_error(session_id, str(e))
        finally:
            # Clean up session state
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def _process_candle(
        self,
        session_id: str,
        session_state: SessionState,
        candle: Candle
    ) -> None:
        """
        Process a single candle.
        
        Calculates indicators, gets AI decision, manages positions,
        and broadcasts events.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            candle: Current candle to process
        """
        candle_index = session_state.current_index
        
        logger.debug(
            f"Processing candle {candle_index + 1}/{len(session_state.candles)}: "
            f"timestamp={candle.timestamp}, close={candle.close}"
        )
        
        # Calculate indicators for current candle
        indicators = session_state.indicator_calculator.calculate_all(candle_index)
        
        # Broadcast candle event with indicators
        await self._broadcast_candle(session_id, candle, indicators, candle_index)
        
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
                    session_id,
                    session_state,
                    closed_trade,
                    candle_index,
                    candle.timestamp
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
            "candle_number": candle_index,
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
            session_id,
            session_state,
            decision,
            candle,
            candle_index
        )
        
        # Broadcast stats update
        stats = session_state.position_manager.get_stats()
        await self._broadcast_stats_update(session_id, stats)
    
    async def _execute_decision(
        self,
        session_id: str,
        session_state: SessionState,
        decision: AIDecision,
        candle: Candle,
        candle_index: int
    ) -> None:
        """
        Execute AI trading decision.
        
        Opens, closes, or holds positions based on AI decision.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            decision: AI decision object
            candle: Current candle
            candle_index: Current candle index
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
                        session_id,
                        session_state,
                        closed_trade,
                        candle_index,
                        candle.timestamp
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
                    session_id,
                    session_state,
                    position,
                    candle_index,
                    candle.timestamp,
                    decision.reasoning
                )
    
    async def _handle_position_opened(
        self,
        session_id: str,
        session_state: SessionState,
        position: PositionData,
        candle_index: int,
        timestamp: datetime,
        reasoning: str
    ) -> None:
        """
        Handle position opened event.
        
        Saves trade to database and broadcasts event.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            position: Opened position data
            candle_index: Candle index at entry
            timestamp: Entry timestamp
            reasoning: AI reasoning for entry
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
            entry_candle=candle_index,
            entry_reasoning=reasoning,
            size=Decimal(str(position.size)),
            leverage=position.leverage,
            stop_loss=Decimal(str(position.stop_loss)) if position.stop_loss else None,
            take_profit=Decimal(str(position.take_profit)) if position.take_profit else None
        )
        self.db.add(trade)
        await self.db.commit()
        
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
        session_id: str,
        session_state: SessionState,
        trade: Any,  # Trade from position_manager
        candle_index: int,
        timestamp: datetime
    ) -> None:
        """
        Handle position closed event.
        
        Updates trade in database and broadcasts event.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            trade: Closed trade data
            candle_index: Candle index at exit
            timestamp: Exit timestamp
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
                exit_candle=candle_index,
                exit_type=trade.reason,
                pnl_amount=Decimal(str(trade.pnl)),
                pnl_pct=Decimal(str(trade.pnl_pct))
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
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
        candle_index: int
    ) -> None:
        """Broadcast candle event with indicators."""
        event = Event(
            type=EventType.CANDLE,
            data={
                "candle_index": candle_index,
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
    
    async def _update_session_current_candle(self, session_id: str, current_candle: int) -> None:
        """Update session current_candle in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(current_candle=current_candle)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def pause_backtest(self, session_id: str) -> None:
        """
        Pause a running backtest.
        
        Halts candle processing until resume is called.
        
        Args:
            session_id: Session identifier
            
        Raises:
            ValidationError: If session not found or not running
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        
        if session_state.is_paused:
            logger.warning(f"Session already paused: {session_id}")
            return
        
        logger.info(f"Pausing backtest: session_id={session_id}")
        
        # Set pause flag and clear event
        session_state.is_paused = True
        session_state.pause_event.clear()
        
        # Update session status in database
        await self._update_session_status(session_id, "paused")
        await self._update_session_paused_at(session_id, datetime.utcnow())
        
        # Broadcast paused event
        event = Event(
            type=EventType.SESSION_PAUSED,
            data={
                "session_id": session_id,
                "current_candle": session_state.current_index
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
        
        logger.info(f"Backtest paused: session_id={session_id}")
    
    async def resume_backtest(self, session_id: str) -> None:
        """
        Resume a paused backtest.
        
        Continues candle processing from current index.
        
        Args:
            session_id: Session identifier
            
        Raises:
            ValidationError: If session not found or not paused
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        
        if not session_state.is_paused:
            logger.warning(f"Session not paused: {session_id}")
            return
        
        logger.info(f"Resuming backtest: session_id={session_id}")
        
        # Clear pause flag and set event
        session_state.is_paused = False
        session_state.pause_event.set()
        
        # Update session status in database
        await self._update_session_status(session_id, "running")
        
        # Broadcast resumed event
        event = Event(
            type=EventType.SESSION_RESUMED,
            data={
                "session_id": session_id,
                "current_candle": session_state.current_index
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
        
        logger.info(f"Backtest resumed: session_id={session_id}")
    
    async def stop_backtest(self, session_id: str, close_position: bool = True) -> str:
        """
        Stop a backtest and generate results.
        
        Forces backtest completion, optionally closes open position,
        and generates final results.
        
        Args:
            session_id: Session identifier
            close_position: Whether to close open position before stopping
            
        Returns:
            result_id: ID of generated result record
            
        Raises:
            ValidationError: If session not found
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        
        logger.info(
            f"Stopping backtest: session_id={session_id}, "
            f"close_position={close_position}"
        )
        
        # Set stop flag
        session_state.is_stopped = True
        
        # Resume if paused to allow cleanup
        if session_state.is_paused:
            session_state.pause_event.set()
        
        # Close open position if requested
        if close_position and session_state.position_manager.has_open_position():
            current_candle = session_state.candles[session_state.current_index]
            closed_trade = await session_state.position_manager.close_position(
                exit_price=current_candle.close,
                reason="manual"
            )
            if closed_trade:
                await self._handle_position_closed(
                    session_id,
                    session_state,
                    closed_trade,
                    session_state.current_index,
                    current_candle.timestamp
                )
        
        # Generate results
        result_id = await self._complete_backtest(session_state, force_stop=True)
        
        logger.info(f"Backtest stopped: session_id={session_id}, result_id={result_id}")
        
        return result_id
    
    async def _update_session_paused_at(self, session_id: str, paused_at: datetime) -> None:
        """Update session paused_at timestamp in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(paused_at=paused_at)
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _complete_backtest(
        self,
        session_state: SessionState,
        force_stop: bool = False
    ) -> str:
        """
        Complete backtest and generate results.
        
        Saves final results, AI thoughts, and broadcasts completion event.
        
        Args:
            session_state: Session state object
            force_stop: Whether this is a forced stop
            
        Returns:
            result_id: ID of generated result record
        """
        session_id = session_state.session_id
        
        logger.info(f"Completing backtest: session_id={session_id}")
        
        # Update session status
        await self._update_session_status(session_id, "completed")
        await self._update_session_completed_at(session_id, datetime.utcnow())
        
        # Get final stats
        stats = session_state.position_manager.get_stats()
        
        # Update session with final equity and PnL
        await self._update_session_final_stats(
            session_id,
            stats["current_equity"],
            stats["equity_change_pct"]
        )
        
        # Save AI thoughts to database
        await self._save_ai_thoughts(session_id, session_state.ai_thoughts)
        
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
                "forced_stop": force_stop
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
        
        logger.info(
            f"Backtest completed: session_id={session_id}, "
            f"final_equity={stats['current_equity']}, "
            f"pnl={stats['total_pnl_pct']}%"
        )
        
        return result_id
    
    async def _update_session_completed_at(self, session_id: str, completed_at: datetime) -> None:
        """Update session completed_at timestamp in database."""
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(completed_at=completed_at)
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _update_session_final_stats(
        self,
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
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _save_ai_thoughts(
        self,
        session_id: str,
        ai_thoughts: List[Dict[str, Any]]
    ) -> None:
        """
        Save AI thoughts to database.
        
        Args:
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
            self.db.add(ai_thought)
        
        await self.db.commit()
        
        logger.info(f"Saved AI thoughts for session {session_id}")
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """
        Get session state for a running backtest.
        
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
