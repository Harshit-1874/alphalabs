"""
Backtest Engine main class.

Purpose:
    Main orchestrator for backtest execution, managing the complete lifecycle
    of backtest sessions including initialization, processing, and completion.

Features:
    - Session lifecycle management
    - Historical data loading
    - Service initialization (indicators, AI, position manager)
    - Pause/resume/stop controls
    - Result generation
    - Real-time WebSocket updates

Usage:
    engine = BacktestEngine(session_factory, websocket_manager)
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
from datetime import datetime, date
from typing import Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.agent import Agent
from services.market_data_service import MarketDataService
from services.trading.indicator_calculator import IndicatorCalculator
from services.trading.position_manager import PositionManager
from services.ai_trader import AITrader
from websocket.manager import WebSocketManager
from exceptions import ValidationError
from services.trading.backtest_engine.session_state import SessionState
from services.trading.backtest_engine.broadcaster import EventBroadcaster
from services.trading.backtest_engine.position_handler import PositionHandler
from services.trading.backtest_engine.database import DatabaseManager
from services.trading.backtest_engine.processor import CandleProcessor
from services.result_service import ResultService

logger = logging.getLogger(__name__)


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
    
    def __init__(self, session_factory, websocket_manager: WebSocketManager):
        """
        Initialize backtest engine.
        
        Args:
            session_factory: SQLAlchemy async session factory
            websocket_manager: WebSocket manager for real-time updates
        """
        self.session_factory = session_factory
        self.websocket_manager = websocket_manager
        
        # Initialize helper classes
        self.broadcaster = EventBroadcaster(websocket_manager)
        self.position_handler = PositionHandler(websocket_manager)
        self.database_manager = DatabaseManager(websocket_manager)
        self.processor = CandleProcessor(
            broadcaster=self.broadcaster,
            position_handler=self.position_handler,
            database_manager=self.database_manager
        )
        
        # Store active session states
        self.active_sessions: Dict[str, SessionState] = {}
        
        logger.info("BacktestEngine initialized")
    
    async def start_backtest(
        self,
        session_id: str,
        agent: Agent,
        asset: str,
        timeframe: str,
        start_date: Union[datetime, date],
        end_date: Union[datetime, date],
        starting_capital: float,
        safety_mode: bool = True,
        allow_leverage: bool = False,
        playback_speed: str = "normal",
        decision_mode: str = "every_candle",
        decision_interval_candles: int = 1,
        indicator_readiness_threshold: float = 80.0,
        user_id: str = "",
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
        # Normalize to datetime objects (handles date inputs from API)
        start_dt = self._coerce_to_datetime(start_date, "start_date")
        end_dt = self._coerce_to_datetime(end_date, "end_date")
        
        start_date_str = start_dt.date()
        end_date_str = end_dt.date()
        
        logger.info(
            f"Starting backtest: session_id={session_id}, "
            f"agent={agent.name}, asset={asset}, timeframe={timeframe}, "
            f"start={start_date_str}, end={end_date_str}"
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
                self._validate_parameters(asset, timeframe, start_dt, end_dt, starting_capital)
                
                # Update session status to initializing
                await self.database_manager.update_session_status(db, session_id, "initializing")
                
                # Load historical candle data
                logger.info(f"Loading historical data for {asset} {timeframe}")
                market_data_service = MarketDataService(db)
                candles = await market_data_service.get_historical_data(
                    asset=asset,
                    timeframe=timeframe,
                    start_date=start_dt,
                    end_date=end_dt
                )
            
            if not candles:
                raise ValidationError(
                    f"No historical data available for {asset} {timeframe} "
                    f"from {start_date_str} to {end_date_str}"
                )
            
            logger.info(f"Loaded {len(candles)} candles for backtest")
            
            # Update session with total candles
            async with self.session_factory() as db:
                await self.database_manager.update_session_total_candles(db, session_id, len(candles))
            
            # Initialize indicator calculator
            indicator_calculator = IndicatorCalculator(
                candles=candles,
                enabled_indicators=agent.indicators,
                mode=agent.mode,
                custom_indicators=agent.custom_indicators,
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
            
            # Compute when it's safe to start asking the LLM for decisions.
            # Use dynamic indicator readiness check (user-configured percentage of indicators ready)
            # instead of waiting for ALL indicators (which could be 200+ candles
            # if SMA_200 or EMA_200 is enabled).
            # Convert percentage (0-100) to decimal (0.0-1.0)
            readiness_threshold_decimal = indicator_readiness_threshold / 100.0
            decision_start_index = indicator_calculator.find_first_ready_index(
                min_ready_percentage=readiness_threshold_decimal
            )
            
            logger.info(
                f"Decision start index: {decision_start_index} "
                f"(using dynamic indicator readiness check, {indicator_readiness_threshold}% threshold)"
            )
            
            # Create session state
            session_state = SessionState(
                session_id=session_id,
                agent=agent,
                candles=candles,
                current_index=0,
                position_manager=position_manager,
                indicator_calculator=indicator_calculator,
                ai_trader=ai_trader,
                 decision_start_index=decision_start_index,
                allow_leverage=allow_leverage,
                playback_speed=playback_speed,
                decision_mode=decision_mode,
                decision_interval_candles=decision_interval_candles,
                user_id=user_id,
                asset=asset,
                timeframe=timeframe,
            )
            
            # Store session state
            self.active_sessions[session_id] = session_state
            
            # Update session status to running
            async with self.session_factory() as db:
                started_at = datetime.utcnow()
                session_state.started_at = started_at
                await self.database_manager.update_session_status(db, session_id, "running")
                await self.database_manager.update_session_started_at(db, session_id, started_at)
            
            # Broadcast session initialized event
            await self.broadcaster.broadcast_session_initialized(
                session_id=session_id,
                agent_name=agent.name,
                agent_mode=agent.mode,
                asset=asset,
                timeframe=timeframe,
                total_candles=len(candles)
            )
            
            # Start processing candles in background
            asyncio.create_task(self._process_backtest(session_id))
            
            logger.info(f"Backtest started successfully: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error starting backtest: {e}", exc_info=True)
            # Create a new session for error reporting since the previous one might be broken or closed
            async with self.session_factory() as db:
                await self.database_manager.update_session_status(db, session_id, "failed")
            await self.broadcaster.broadcast_error(session_id, str(e))
            raise
    
    @staticmethod
    def _get_playback_delay(playback_speed: str) -> int:
        """
        Get delay in milliseconds for playback speed.
        
        Args:
            playback_speed: Speed setting ('slow', 'normal', 'fast', 'instant')
            
        Returns:
            Delay in milliseconds
        """
        speed_map = {
            "slow": 1000,      # 1 second per candle
            "normal": 500,     # 500ms per candle
            "fast": 200,       # 200ms per candle
            "instant": 0       # No delay
        }
        return speed_map.get(playback_speed, 500)  # Default to normal
    
    @staticmethod
    def _coerce_to_datetime(value: Union[datetime, date], field_name: str) -> datetime:
        """
        Ensure incoming values are datetime objects.
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        raise ValidationError(f"{field_name} must be a date or datetime, got {type(value).__name__}")
    
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
            # Create session for the backtest loop
            async with self.session_factory() as db:
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
                    
                    # Process this candle using processor
                    await self.processor.process_candle(db, session_id, session_state, candle)
                    
                    # Move to next candle
                    session_state.current_index += 1
                    
                    # Update session current_candle in database
                    await self.database_manager.update_session_current_candle(
                        db, session_id, session_state.current_index
                    )
                    
                    # Apply playback speed delay (except for instant)
                    if session_state.playback_speed != "instant":
                        delay_ms = self._get_playback_delay(session_state.playback_speed)
                        if delay_ms > 0:
                            await asyncio.sleep(delay_ms / 1000.0)
                
                # Backtest completed
                if not session_state.is_stopped:
                    logger.info(f"Backtest completed: session_id={session_id}")
                    await self._complete_backtest(db, session_id, session_state)
            
        except Exception as e:
            logger.error(f"Error processing backtest: {e}", exc_info=True)
            async with self.session_factory() as db:
                await self.database_manager.update_session_status(db, session_id, "failed")
            await self.broadcaster.broadcast_error(session_id, str(e))
        finally:
            # Clean up session state
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
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
        async with self.session_factory() as db:
            await self.database_manager.update_session_status(db, session_id, "paused")
            await self.database_manager.update_session_paused_at(db, session_id, datetime.utcnow())
        
        # Broadcast paused event
        await self.broadcaster.broadcast_session_paused(session_id, session_state.current_index)
        
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
        async with self.session_factory() as db:
            await self.database_manager.update_session_status(db, session_id, "running")
        
        # Broadcast resumed event
        await self.broadcaster.broadcast_session_resumed(session_id, session_state.current_index)
        
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
        
        async with self.session_factory() as db:
            # Close open position if requested
            if close_position and session_state.position_manager.has_open_position():
                current_candle = session_state.candles[session_state.current_index]
                closed_trade = await session_state.position_manager.close_position(
                    exit_price=current_candle.close,
                    reason="manual"
                )
                if closed_trade:
                    await self.position_handler.handle_position_closed(
                        db,
                        session_id,
                        session_state,
                        closed_trade,
                        session_state.current_index,
                        current_candle.timestamp
                    )
            
            # Generate results
            result_id = await self._complete_backtest(db, session_id, session_state, force_stop=True)
        
        logger.info(f"Backtest stopped: session_id={session_id}, result_id={result_id}")
        
        return result_id
    
    async def _complete_backtest(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: SessionState,
        force_stop: bool = False
    ) -> str:
        """
        Complete backtest and generate results.
        
        Saves final results, AI thoughts, and broadcasts completion event.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            force_stop: Whether this is a forced stop
            
        Returns:
            result_id: ID of generated result record
        """
        logger.info(f"Completing backtest: session_id={session_id}")
        
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
            current_candle=session_state.current_index,
        )
        
        result_service = ResultService(db)
        result_id = await result_service.create_from_session(
            session_id=session_id,
            stats=stats,
            equity_curve=session_state.equity_curve,
            forced_stop=force_stop
        )
        
        # Broadcast session completed event
        await self.broadcaster.broadcast_session_completed(
            session_id=session_id,
            # Cast to string so it can be JSON-serialized for WebSocket clients
            result_id=str(result_id),
            final_equity=stats["current_equity"],
            total_pnl=stats["total_pnl"],
            total_pnl_pct=stats["total_pnl_pct"],
            total_trades=stats["total_trades"],
            win_rate=stats["win_rate"],
            forced_stop=force_stop
        )
        
        logger.info(
            f"Backtest completed: session_id={session_id}, "
            f"final_equity={stats['current_equity']}, "
            f"pnl={stats['total_pnl_pct']}%"
        )
        
        return result_id
    
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
