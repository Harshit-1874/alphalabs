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
from datetime import datetime, date, timezone
from typing import Dict, Optional, Union, List
from uuid import UUID

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
        agent: Optional[Agent] = None,
        agent_id: Optional[UUID] = None,
        asset: str = "",
        timeframe: str = "",
        start_date: Optional[Union[datetime, date]] = None,
        end_date: Optional[Union[datetime, date]] = None,
        starting_capital: float = 0.0,
        safety_mode: bool = True,
        allow_leverage: bool = False,
        playback_speed: str = "normal",
        decision_mode: str = "every_candle",
        decision_interval_candles: int = 1,
        indicator_readiness_threshold: float = 80.0,
        user_id: str = "",
        council_mode: bool = False,
        council_models: Optional[List[str]] = None,
        council_chairman_model: Optional[str] = None,
    ) -> None:
        """
        Start a backtest session.
        
        Validates parameters, loads historical data, initializes services,
        and begins processing candles. Runs in background task.
        
        Args:
            session_id: Unique session identifier
            agent: Agent configuration object (optional, will be reloaded if expired)
            agent_id: Agent ID (preferred for background tasks to avoid lazy loading)
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
        if start_date is None or end_date is None:
            raise ValidationError("start_date and end_date are required")
        start_dt = self._coerce_to_datetime(start_date, "start_date")
        end_dt = self._coerce_to_datetime(end_date, "end_date")
        
        start_date_str = start_dt.date()
        end_date_str = end_dt.date()
        
        # Extract agent_id - prefer passed agent_id, otherwise try to get from agent object
        # The agent object may be expired in background tasks, so we reload it below
        resolved_agent_id: Optional[UUID] = None
        if agent_id:
            resolved_agent_id = agent_id
        elif agent:
            # Try to get ID without triggering lazy load
            try:
                # Use getattr to avoid triggering lazy load if possible
                resolved_agent_id = getattr(agent, 'id', None)
                if resolved_agent_id is None:
                    # Fallback: try direct access (may fail in background tasks)
                    resolved_agent_id = agent.id
            except Exception:
                # Agent object is expired, we'll reload it below using session_id lookup
                pass
        
        if not resolved_agent_id:
            raise ValidationError("Agent ID could not be determined. Please provide agent_id parameter.")
        
        logger.info(
            f"Starting backtest: session_id={session_id}, "
            f"agent_id={resolved_agent_id}, asset={asset}, timeframe={timeframe}, "
            f"start={start_date_str}, end={end_date_str}"
        )
        
        try:
            # Create a new session for initialization
            async with self.session_factory() as db:
                # Reload agent with api_key relationship to avoid lazy loading issues
                # This ensures we have fresh data in the proper async context
                # IMPORTANT: Always reload agent from DB in background tasks to avoid expired objects
                
                # Use a fresh query to ensure we get the latest data from the database
                # This is critical if the agent was just updated
                from sqlalchemy.orm import joinedload
                agent_result = await db.execute(
                    select(Agent)
                    .options(joinedload(Agent.api_key))
                    .where(Agent.id == resolved_agent_id)
                )
                agent = agent_result.scalar_one_or_none()
                if not agent:
                    raise ValidationError(f"Agent not found: {resolved_agent_id}")
                
                # Log for debugging
                logger.info(
                    f"Loaded agent '{agent.name}' (id={agent.id}): "
                    f"api_key_id={agent.api_key_id}, "
                    f"has_api_key_relationship={agent.api_key is not None}, "
                    f"has_encrypted_key={agent.api_key.encrypted_key is not None if agent.api_key else False}"
                )
                
                # Validate API key early - before starting any processing
                if not agent.api_key_id:
                    raise ValidationError(
                        f"Agent '{agent.name}' does not have an API key configured (api_key_id is None). "
                        f"Please add an API key to this agent before starting a backtest."
                    )
                if not agent.api_key:
                    raise ValidationError(
                        f"Agent '{agent.name}' has api_key_id={agent.api_key_id} but the API key relationship could not be loaded. "
                        f"This might indicate the API key was deleted. Please update the agent with a valid API key."
                    )
                if not agent.api_key.encrypted_key:
                    raise ValidationError(
                        f"Agent '{agent.name}' has an API key reference but the encrypted_key is missing or invalid. "
                        f"Please update the API key for this agent."
                    )
                
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
            # API key was already validated above, but double-check here for safety
            # (in case something changed between validation and this point)
            if not agent.api_key or not agent.api_key.encrypted_key:
                raise ValidationError(
                    f"Agent '{agent.name}' does not have a valid API key. "
                    f"This should have been caught earlier - please report this issue."
                )
            
            # Decrypt API key
            from core.encryption import decrypt_api_key
            try:
                api_key = decrypt_api_key(agent.api_key.encrypted_key)
            except Exception as e:
                logger.error(f"Failed to decrypt API key for agent {agent.name}: {e}")
                raise ValidationError(
                    f"Failed to decrypt API key for agent '{agent.name}'. "
                    f"The API key may be corrupted. Please update it."
                ) from e
            
            # Initialize AI trader (council mode or standard)
            if council_mode:
                from services.ai_council_trader import AICouncilTrader
                from services.llm_council.config import CouncilConfig
                
                # IMPORTANT: Bot's model is ALWAYS the first council member
                # Additional models are provided via council_models parameter
                
                # If no additional models provided, use defaults
                if not council_models:
                    # Get 2 default additional models (bot's model will be added as #1)
                    default_config = CouncilConfig.create_default(api_key, num_models=2)
                    additional_models = default_config.council_models[:2]
                else:
                    additional_models = council_models
                
                # Build final council: Bot's model + additional models
                final_council_models = [agent.model] + additional_models
                
                # Chairman defaults to bot's model if not specified
                chairman = council_chairman_model or agent.model
                
                logger.info(
                    f"Initializing Council Mode with {len(final_council_models)} models: "
                    f"Lead={agent.model} (bot), Additional={additional_models}, Chairman={chairman}"
                )
                
                ai_trader = AICouncilTrader(
                    api_key=api_key,
                    council_models=final_council_models,
                    chairman_model=chairman,
                    strategy_prompt=agent.strategy_prompt,
                    mode=agent.mode,
                    model_timeout=30.0,
                    total_timeout=60.0
                )
            else:
                from services.ai_trader import AITrader
                
                ai_trader = AITrader(
                    api_key=api_key,
                    model=agent.model,
                    strategy_prompt=agent.strategy_prompt,
                    mode=agent.mode
                )
            
            # Eagerly initialize model metadata to avoid fetching during trading decisions
            await ai_trader.initialize()
            
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
            council_config_dict = None
            if council_mode:
                council_config_dict = {
                    "models": council_models,
                    "chairman": council_chairman_model
                }
            
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
                council_mode=council_mode,
                council_config=council_config_dict,
                user_id=user_id,
                asset=asset,
                timeframe=timeframe,
            )
            
            # Store session state
            self.active_sessions[session_id] = session_state
            
            # Update session status to running
            async with self.session_factory() as db:
                started_at = datetime.now(timezone.utc)
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
        Ensure incoming values are datetime objects with timezone awareness (UTC).
        """
        if isinstance(value, datetime):
            # Ensure timezone-aware (UTC)
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
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
        
        if start_date > datetime.now(timezone.utc):
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
        
        Optimized to pre-determine LLM call points and fast-forward through
        non-decision candles. Only processes candles where decisions are needed
        or where positions need attention.
        
        Args:
            session_id: Session identifier
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            logger.error(f"Session state not found: {session_id}")
            return
        
        logger.info(f"Starting backtest processing: session_id={session_id}")
        
        try:
            # Pre-compute all LLM call points based on decision mode
            llm_call_points = self.processor.precompute_llm_call_points(
                session_state,
                len(session_state.candles)
            )
            
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
                    candle_index = session_state.current_index
                    
                    # Check if we have an open position (need to check for force conditions)
                    has_position = session_state.position_manager.has_open_position()
                    
                    # Determine if this candle needs full processing
                    is_llm_call_point = candle_index in llm_call_points
                    
                    # Check for force conditions if we have a position
                    # (force conditions can't be pre-determined, so we check dynamically)
                    force_decision = False
                    if has_position:
                        force_decision, _ = self.processor._should_force_llm_call(
                            session_state, candle_index, 
                            session_state.position_manager.get_position(), candle
                        )
                    
                    # If this is a decision point or force condition, do full processing
                    if is_llm_call_point or force_decision:
                        # Full processing with LLM call
                        await self.processor.process_candle(db, session_id, session_state, candle)
                    else:
                        # Fast-forward: only update positions and pending orders
                        await self.processor.fast_forward_candle(
                            db, session_id, session_state, candle, candle_index
                        )
                        
                        # Update stats (in-memory only during fast-forward)
                        stats = session_state.position_manager.get_stats()
                        self.processor._record_equity_point(
                            session_state, candle.timestamp, stats["current_equity"]
                        )
                        
                        # Broadcast EVERY candle during fast-forward for smooth visual progression
                        # Skip indicator calculation during fast-forward for maximum speed
                        # (indicators are pre-calculated but lookup still has overhead)
                        # Use empty dict - frontend doesn't need indicators for non-decision candles
                        empty_indicators = {}
                        await self.broadcaster.broadcast_candle(
                            session_id, candle, 
                            empty_indicators,  # Skip indicator lookup for speed
                            candle_index
                        )
                        
                        # Batch database updates during fast-forward (every 20 candles) for maximum performance
                        # This reduces database I/O significantly while still keeping data reasonably fresh
                        if candle_index % 20 == 0:
                            await self.database_manager.update_session_runtime_stats(
                                db=db,
                                session_id=session_id,
                                current_equity=stats["current_equity"],
                                current_pnl_pct=stats["equity_change_pct"],
                                max_drawdown_pct=session_state.max_drawdown_pct,
                                elapsed_seconds=self.processor._compute_elapsed_seconds(session_state),
                                open_position=self.processor._serialize_position(
                                    session_state.position_manager.get_position()
                                ),
                                current_candle=candle_index + 1,
                            )
                            # Include progress information in stats update
                            stats_with_progress = {
                                **stats,
                                "current_candle": candle_index + 1,
                                "total_candles": len(session_state.candles),
                            }
                            await self.broadcaster.broadcast_stats_update(session_id, stats_with_progress)
                        
                        # NO DELAY during fast-forward - go as fast as possible!
                        # The chart will update as fast as WebSocket can handle it
                        # Browser will naturally throttle if it can't keep up
                    
                    # Move to next candle
                    session_state.current_index += 1
                    
                    # Update session current_candle in database
                    await self.database_manager.update_session_current_candle(
                        db, session_id, session_state.current_index
                    )
                    
                    # Apply playback speed delay only for decision candles (or instant mode)
                    # This makes fast-forward truly fast
                    if (is_llm_call_point or force_decision) and session_state.playback_speed != "instant":
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
            await self.database_manager.update_session_paused_at(db, session_id, datetime.now(timezone.utc))
        
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
        
        # If not in active sessions, check database to see if it exists
        # (might have completed or been cleaned up from memory)
        if not session_state:
            async with self.session_factory() as db:
                from sqlalchemy import select
                from models.arena import TestSession
                result = await db.execute(
                    select(TestSession).where(TestSession.id == session_id)
                )
                db_session = result.scalar_one_or_none()
                
                if not db_session:
                    raise ValidationError(f"Session not found: {session_id}")
                
                # If session is already completed, return its result_id if available
                if db_session.status == "completed":
                    from models.result import TestResult
                    result_query = await db.execute(
                        select(TestResult).where(TestResult.session_id == session_id)
                        .order_by(TestResult.created_at.desc())
                        .limit(1)
                    )
                    test_result = result_query.scalar_one_or_none()
                    if test_result:
                        logger.info(
                            f"Session {session_id} already completed, returning existing result_id: {test_result.id}"
                        )
                        return str(test_result.id)
                    else:
                        raise ValidationError(
                            f"Session {session_id} is already completed but no result found. "
                            f"Please check the results page."
                        )
                
                # If session exists in DB but not in memory, it might have errored or been cleaned up
                # Try to generate result from database state (similar to cleanup endpoint behavior)
                logger.warning(
                    f"Session {session_id} not in active_sessions but exists in database "
                    f"with status {db_session.status}. Attempting to generate result from DB state."
                )
                
                # Check if result already exists
                from models.result import TestResult
                from models.arena import Trade
                result_query = await db.execute(
                    select(TestResult).where(TestResult.session_id == session_id)
                    .order_by(TestResult.created_at.desc())
                    .limit(1)
                )
                existing_result = result_query.scalar_one_or_none()
                if existing_result:
                    logger.info(
                        f"Session {session_id} already has result, marking as completed: {existing_result.id}"
                    )
                    # Mark session as completed
                    await self.database_manager.update_session_status(db, session_id, "completed")
                    await self.database_manager.update_session_completed_at(
                        db, session_id, datetime.now(timezone.utc)
                    )
                    await db.commit()
                    return str(existing_result.id)
                
                # Calculate stats from database trades
                trades_result = await db.execute(
                    select(Trade).where(Trade.session_id == session_id).order_by(Trade.trade_number)
                )
                trades = trades_result.scalars().all()
                
                # Calculate stats from trades (similar to PositionManager.get_stats())
                total_trades = len(trades)
                if total_trades == 0:
                    stats = {
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "win_rate": 0.0,
                        "total_pnl": 0.0,
                        "total_pnl_pct": 0.0,
                        "current_equity": float(db_session.current_equity or db_session.starting_capital),
                        "equity_change_pct": float(db_session.current_pnl_pct or 0.0)
                    }
                else:
                    winning_trades = [t for t in trades if t.pnl_amount and t.pnl_amount > 0]
                    losing_trades = [t for t in trades if t.pnl_amount and (t.pnl_amount <= 0)]
                    total_pnl = sum(float(t.pnl_amount or 0) for t in trades)
                    total_pnl_pct = (total_pnl / float(db_session.starting_capital)) * 100 if db_session.starting_capital else 0.0
                    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
                    
                    stats = {
                        "total_trades": total_trades,
                        "winning_trades": len(winning_trades),
                        "losing_trades": len(losing_trades),
                        "win_rate": win_rate,
                        "total_pnl": total_pnl,
                        "total_pnl_pct": total_pnl_pct,
                        "current_equity": float(db_session.current_equity or db_session.starting_capital),
                        "equity_change_pct": float(db_session.current_pnl_pct or 0.0)
                    }
                
                # Mark session as completed
                await self.database_manager.update_session_status(db, session_id, "completed")
                await self.database_manager.update_session_completed_at(
                    db, session_id, datetime.now(timezone.utc)
                )
                
                # Generate result from database state
                result_service = ResultService(db)
                result_id = await result_service.create_from_session(
                    session_id=session_id,
                    stats=stats,
                    equity_curve=None,  # Can't reconstruct equity curve from DB
                    forced_stop=True
                )
                
                # Broadcast session completed event
                await self.broadcaster.broadcast_session_completed(
                    session_id=session_id,
                    result_id=str(result_id),
                    final_equity=stats["current_equity"],
                    total_pnl=stats["total_pnl"],
                    total_pnl_pct=stats["total_pnl_pct"],
                    total_trades=stats["total_trades"],
                    win_rate=stats["win_rate"],
                    forced_stop=True
                )
                
                logger.info(
                    f"Backtest stopped from DB state: session_id={session_id}, result_id={result_id}"
                )
                
                # Defensively remove from active_sessions if it exists (shouldn't happen, but cleanup just in case)
                if session_id in self.active_sessions:
                    logger.warning(
                        f"Session {session_id} was in active_sessions but handled from DB state. Removing from memory."
                    )
                    del self.active_sessions[session_id]
                
                return result_id
        
        # Session is in memory - use normal stop flow
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
    
    async def send_historical_candles_to_connection(
        self,
        session_id: str,
        connection_id: str
    ) -> None:
        """
        Send all processed candles to a reconnecting WebSocket connection.
        
        This ensures reconnecting clients receive the full chart history
        up to the current point in the backtest.
        
        Args:
            session_id: Session identifier
            connection_id: WebSocket connection identifier
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            logger.debug(f"Session {session_id} not found or not yet started - no historical candles to send")
            return
        
        # If we haven't processed any candles yet, nothing to send
        if session_state.current_index == 0:
            logger.debug(f"No historical candles to send for session {session_id} - backtest just started")
            return
        
        # Calculate how many candles have been processed (excluding the current one)
        processed_count = session_state.current_index
        
        if processed_count == 0:
            logger.debug(f"No candles processed yet for session {session_id}")
            return
        
        logger.info(
            f"Sending {processed_count} historical candles "
            f"to connection {connection_id} for session {session_id}"
        )
        
        # Send all processed candles with their indicators in batches
        batch_size = 50  # Send in batches to prevent overwhelming the WebSocket
        for batch_start in range(0, processed_count, batch_size):
            batch_end = min(batch_start + batch_size, processed_count)
            
            for candle_idx in range(batch_start, batch_end):
                candle = session_state.candles[candle_idx]
                indicators = session_state.indicator_calculator.calculate_all(candle_idx)
                
                # Send each candle to the specific connection
                await self.broadcaster.send_candle_to_connection(
                    connection_id,
                    candle,
                    indicators,
                    candle_idx
                )
            
            # Small delay between batches to prevent overwhelming the connection
            await asyncio.sleep(0.01)
        
        logger.info(f"Finished sending historical candles to connection {connection_id}")
    
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
        await self.database_manager.update_session_completed_at(db, session_id, datetime.now(timezone.utc))
        
        # Get final stats
        stats = session_state.position_manager.get_stats()
        
        await self.database_manager.save_ai_thoughts(db, session_id, session_state.ai_thoughts)
        await self.database_manager.update_session_runtime_stats(
            db,
            session_id,
            current_equity=stats["current_equity"],
            current_pnl_pct=stats["equity_change_pct"],
            max_drawdown_pct=session_state.max_drawdown_pct,
            elapsed_seconds=int((datetime.now(timezone.utc) - session_state.started_at).total_seconds()) if session_state.started_at else None,
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
