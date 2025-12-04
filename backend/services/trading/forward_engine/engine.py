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
from datetime import datetime
from typing import Dict, Optional, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.agent import Agent
from services.market_data_service import MarketDataService
from services.trading.position_manager import PositionManager
from services.ai_trader import AITrader
from websocket.manager import WebSocketManager
from exceptions import ValidationError

from .session_state import SessionState
from .broadcaster import EventBroadcaster
from .database import DatabaseManager
from .processor import CandleProcessor
from .position_handler import PositionHandler
from .timing import TimingManager
from .auto_stop import AutoStopManager
from .notifications import NotificationManager
from services.result_service import ResultService

logger = logging.getLogger(__name__)


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
    
    def __init__(self, session_factory, websocket_manager: WebSocketManager):
        """
        Initialize forward test engine.
        
        Args:
            session_factory: SQLAlchemy async session factory
            websocket_manager: WebSocket manager for real-time updates
        """
        self.session_factory = session_factory
        self.websocket_manager = websocket_manager
        
        # Initialize helper classes
        self.broadcaster = EventBroadcaster(websocket_manager)
        self.database_manager = DatabaseManager(websocket_manager)
        self.notification_manager = NotificationManager()
        self.timing_manager = TimingManager(websocket_manager)
        self.auto_stop_manager = AutoStopManager(websocket_manager)
        self.position_handler = PositionHandler(websocket_manager, self.notification_manager)
        self.processor = CandleProcessor(
            self.broadcaster,
            self.position_handler,
            self.database_manager,
            self.auto_stop_manager
        )
        
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
        email_notifications: bool = False,
        allow_leverage: bool = False,
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
                # Reload agent with api_key relationship to avoid lazy loading issues
                # This ensures we have fresh data in the proper async context
                agent_id = agent.id
                agent_result = await db.execute(
                    select(Agent)
                    .options(selectinload(Agent.api_key))
                    .where(Agent.id == agent_id)
                )
                agent = agent_result.scalar_one_or_none()
                if not agent:
                    raise ValidationError(f"Agent not found: {agent_id}")
                
                # Validate parameters
                self._validate_parameters(asset, timeframe, starting_capital)
                
                # Update session status to initializing
                await self.database_manager.update_session_status(db, session_id, "initializing")
                
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
                    auto_stop_config=auto_stop_config or {},
                    allow_leverage=allow_leverage,
                )
                
                # Store session state
                self.active_sessions[session_id] = session_state
                
                # Update session status to running
                await self.database_manager.update_session_status(db, session_id, "running")
                started_at = datetime.utcnow()
                session_state.started_at = started_at
                await self.database_manager.update_session_started_at(db, session_id, started_at)
                
                # Broadcast session initialized event
                await self.broadcaster.broadcast_session_initialized(
                    session_id,
                    agent.name,
                    agent.mode,
                    asset,
                    timeframe,
                    email_notifications
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
                await self.database_manager.update_session_status(db, session_id, "failed")
            await self.broadcaster.broadcast_error(session_id, str(e))
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
                    candle = await self.timing_manager.wait_for_candle_close(
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
                    await self.processor.process_candle(
                        db,
                        session_id,
                        session_state,
                        candle,
                        email_notifications
                    )
                    
                    # Check auto-stop conditions
                    should_stop = await self.auto_stop_manager.check_auto_stop_conditions(
                        session_id,
                        session_state
                    )
                    
                    if should_stop:
                        logger.info(f"Auto-stop triggered: session_id={session_id}")
                        await self.auto_stop_manager.handle_auto_stop(
                            db,
                            session_id,
                            session_state,
                            email_notifications
                        )
                        # Complete the forward test after auto-stop
                        await self._complete_forward_test(
                            db,
                            session_id,
                            session_state,
                            auto_stop=True
                        )
                        break
                
                # Forward test completed or stopped
                if not session_state.is_stopped:
                    logger.info(f"Forward test completed: session_id={session_id}")
                
        except Exception as e:
            logger.error(f"Error processing forward test: {e}", exc_info=True)
            async with self.session_factory() as db:
                await self.database_manager.update_session_status(db, session_id, "failed")
            await self.broadcaster.broadcast_error(session_id, str(e))
        finally:
            # Clean up session state
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def stop_forward_test(self, session_id: str, close_position: bool = True) -> Tuple[str, bool]:
        """
        Stop a forward test and generate results.
        
        Closes open position and generates final results.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of result_id and whether a position was closed
            
        Raises:
            ValidationError: If session not found
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        
        logger.info(f"Stopping forward test: session_id={session_id}")
        
        # Set stop flag
        session_state.is_stopped = True
        
        position_closed = False
        async with self.session_factory() as db:
            market_data_service = MarketDataService(db)
            
            # Close open position if exists
            if close_position and session_state.position_manager.has_open_position():
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
                    await self.position_handler.handle_position_closed(
                        db,
                        session_id,
                        session_state,
                        closed_trade,
                        len(session_state.candles_processed),
                        latest_candle.timestamp,
                        email_notifications=False
                    )
                    position_closed = True
            
            # Generate results
            result_id = await self._complete_forward_test(
                db,
                session_id,
                session_state,
                force_stop=True
            )
        
        logger.info(f"Forward test stopped: session_id={session_id}, result_id={result_id}")
        
        return result_id, position_closed
    
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
        await self.database_manager.update_session_status(db, session_id, "completed")
        await self.database_manager.update_session_completed_at(db, session_id, datetime.utcnow())
        
        # Get final stats
        stats = session_state.position_manager.get_stats()
        
        await self.database_manager.save_ai_thoughts(db, session_id, session_state.ai_thoughts)
        await self.database_manager.update_session_runtime_stats(
            db,
            session_id,
            current_equity=stats["current_equity"],
            current_pnl_pct=stats["equity_change_pct"],
            max_drawdown_pct=session_state.max_drawdown_pct,
            elapsed_seconds=int((datetime.utcnow() - session_state.started_at).total_seconds()) if session_state.started_at else None,
            open_position=None,
        )
        
        result_service = ResultService(db)
        result_id = await result_service.create_from_session(
            session_id=session_id,
            stats=stats,
            equity_curve=session_state.equity_curve,
            forced_stop=force_stop or auto_stop
        )
        
        # Broadcast session completed event
        await self.broadcaster.broadcast_session_completed(
            session_id,
            result_id,
            stats["current_equity"],
            stats["total_pnl"],
            stats["total_pnl_pct"],
            stats["total_trades"],
            stats["win_rate"],
            forced_stop=force_stop
        )
        
        logger.info(
            f"Forward test completed: session_id={session_id}, "
            f"final_equity={stats['current_equity']}, "
            f"pnl={stats['total_pnl_pct']}%"
        )
        
        return result_id
