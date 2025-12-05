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
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.agent import Agent
from services.market_data_service import MarketDataService
from services.trading.position_manager import PositionManager
from services.trading.indicator_calculator import IndicatorCalculator
from services.ai_trader import AITrader
from websocket.manager import WebSocketManager
from websocket.events import Event, EventType
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
    
    @staticmethod
    def _calculate_required_historical_candles(
        enabled_indicators: List[str],
        timeframe: str
    ) -> int:
        """
        Calculate the required number of historical candles based on enabled indicators.
        
        Strategy:
        1. Find the maximum lookback period needed by any enabled indicator
        2. Add a safety buffer (50-100 candles) for indicator stability
        3. Apply timeframe-specific minimums/maximums
        4. Ensure we have enough data for chart context
        
        Args:
            enabled_indicators: List of enabled indicator names
            timeframe: Trading timeframe (e.g., '15m', '1h', '4h', '1d')
            
        Returns:
            Number of historical candles to fetch
        """
        # Get maximum lookback period from enabled indicators
        max_lookback = 0
        for indicator in enabled_indicators:
            # Normalize indicator name (handle aliases)
            normalized = indicator.lower().strip()
            if normalized in IndicatorCalculator.INDICATOR_MIN_HISTORY:
                lookback = IndicatorCalculator.INDICATOR_MIN_HISTORY[normalized]
                max_lookback = max(max_lookback, lookback)
        
        # If no indicators found or max_lookback is 0, use default
        if max_lookback == 0:
            max_lookback = 200  # Default to SMA_200 requirement
        
        # Add safety buffer: 50% more candles for stability
        # This ensures indicators are fully warmed up and stable
        buffer_multiplier = 1.5
        required_candles = int(max_lookback * buffer_multiplier)
        
        # Apply timeframe-specific adjustments
        # Longer timeframes (1d) need more historical context for meaningful analysis
        # Shorter timeframes (15m) can work with less
        timeframe_adjustments = {
            '15m': {'min': 250, 'max': 1000, 'multiplier': 1.0},   # 15min: 250-1000 candles (~2.6-10.4 days)
            '1h': {'min': 300, 'max': 1000, 'multiplier': 1.2},   # 1h: 300-1000 candles (~12.5-41.7 days)
            '4h': {'min': 300, 'max': 1000, 'multiplier': 1.3},   # 4h: 300-1000 candles (~50-167 days)
            '1d': {'min': 400, 'max': 1000, 'multiplier': 1.5},   # 1d: 400-1000 candles (~1.1-2.7 years)
        }
        
        adjustment = timeframe_adjustments.get(timeframe.lower(), {'min': 250, 'max': 1000, 'multiplier': 1.0})
        
        # Apply timeframe multiplier
        required_candles = int(required_candles * adjustment['multiplier'])
        
        # Apply min/max bounds
        required_candles = max(adjustment['min'], min(required_candles, adjustment['max']))
        
        logger.info(
            f"Calculated required historical candles: {required_candles} "
            f"(max_lookback={max_lookback}, timeframe={timeframe}, enabled_indicators={len(enabled_indicators)})"
        )
        
        return required_candles
    
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
        decision_mode: str = "every_candle",
        decision_interval_candles: int = 1,
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
        # Extract agent_id first (primary key access is safe, but avoid accessing other attributes)
        # The agent object may be expired in background tasks, so we reload it below
        try:
            agent_id = agent.id
        except Exception:
            raise ValidationError("Agent ID could not be determined from agent object")
        
        logger.info(
            f"Starting forward test: session_id={session_id}, "
            f"agent_id={agent_id}, asset={asset}, timeframe={timeframe}"
        )
        
        try:
            # Create a new session for initialization
            async with self.session_factory() as db:
                # Reload agent with api_key relationship to avoid lazy loading issues
                # This ensures we have fresh data in the proper async context
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
                
                # Eagerly initialize model metadata to avoid fetching during trading decisions
                await ai_trader.initialize()
                
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
                    decision_mode=decision_mode,
                    decision_interval_candles=decision_interval_candles,
                )
                
                # Store session state
                self.active_sessions[session_id] = session_state
                
                # Update session status to running
                await self.database_manager.update_session_status(db, session_id, "running")
                started_at = datetime.now(timezone.utc)
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
                
                # Fetch historical candles to show chart context
                # AND initialize indicator calculator with historical data
                # Use the same method as backtest for consistency
                historical_candles = []
                try:
                    logger.info(f"Fetching historical data for {session_state.asset} {session_state.timeframe}")
                    
                    # Calculate required historical candles based on enabled indicators and timeframe
                    required_candles = self._calculate_required_historical_candles(
                        enabled_indicators=session_state.agent.indicators or [],
                        timeframe=session_state.timeframe
                    )
                    
                    logger.info(
                        f"Fetching {required_candles} historical candles for {session_state.asset} "
                        f"{session_state.timeframe} (based on {len(session_state.agent.indicators or [])} enabled indicators)"
                    )
                    
                    # Calculate start_date based on required candles
                    # Use the SAME approach as backtest: get_historical_data with date range
                    from datetime import timedelta
                    end_date = datetime.now(timezone.utc)
                    
                    # Calculate how far back we need to go based on timeframe
                    if session_state.timeframe == '15m':
                        days_back = (required_candles * 15) // (24 * 60) + 1
                    elif session_state.timeframe == '1h':
                        days_back = (required_candles // 24) + 1
                    elif session_state.timeframe == '4h':
                        days_back = (required_candles // 6) + 1
                    elif session_state.timeframe == '1d':
                        days_back = required_candles
                    else:
                        days_back = 30  # Default
                    
                    start_date = end_date - timedelta(days=days_back)
                    
                    logger.info(
                        f"Fetching historical data from {start_date.date()} to {end_date.date()} "
                        f"({days_back} days) for {session_state.asset} {session_state.timeframe}"
                    )
                    
                    # Use the SAME method as backtest (works reliably with yfinance)
                    historical_candles = await market_data_service.get_historical_data(
                        asset=session_state.asset,
                        timeframe=session_state.timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if historical_candles and len(historical_candles) > 0:
                        logger.info(f"Fetched {len(historical_candles)} historical candles")
                        
                        # Initialize indicator calculator with historical candles
                        # This is critical - it warms up indicators so they're ready when first real candle arrives
                        logger.info(
                            f"Initializing indicator calculator with {len(historical_candles)} historical candles: "
                            f"session_id={session_id}"
                        )
                        session_state.indicator_calculator = IndicatorCalculator(
                            candles=historical_candles,
                            enabled_indicators=session_state.agent.indicators,
                            mode=session_state.agent.mode,
                            custom_indicators=session_state.agent.custom_indicators,
                        )
                        
                        # Calculate decision_start_index upfront (like backtest does)
                        # Use 80% threshold for initial readiness check
                        INITIAL_READINESS_THRESHOLD = 0.8
                        session_state.decision_start_index = session_state.indicator_calculator.find_first_ready_index(
                            min_ready_percentage=INITIAL_READINESS_THRESHOLD
                        )
                        
                        logger.info(
                            f"Indicator calculator initialized and decision_start_index calculated: "
                            f"{session_state.decision_start_index} (threshold: {INITIAL_READINESS_THRESHOLD * 100}%)"
                        )
                        
                        # Store historical candles in session state for context (except the last one)
                        # We'll process the last one separately to get initial AI analysis
                        # The last candle will be added by the processor
                        if len(historical_candles) > 0:
                            session_state.candles_processed = historical_candles[:-1].copy()
                            last_historical_candle = historical_candles[-1]
                        else:
                            session_state.candles_processed = []
                            last_historical_candle = None
                        
                        # Broadcast all historical candles to frontend for chart display
                        # Now we can calculate indicators for them too!
                        logger.info(f"Broadcasting {len(historical_candles)} historical candles with indicators...")
                        batch_size = 50
                        for batch_start in range(0, len(historical_candles), batch_size):
                            batch = historical_candles[batch_start:batch_start + batch_size]
                            for idx, candle in enumerate(batch):
                                candle_idx = batch_start + idx
                                # Calculate indicators for this historical candle
                                indicators = session_state.indicator_calculator.calculate_all(candle_idx)
                                await self.broadcaster.broadcast_candle(
                                    session_id,
                                    candle,
                                    indicators,  # Now with indicators!
                                    -(len(historical_candles) - candle_idx)  # Negative numbers for historical
                                )
                            # Small delay between batches to avoid overwhelming
                            await asyncio.sleep(0.1)
                        
                        logger.info(
                            f"Successfully broadcasted {len(historical_candles)} historical candles with indicators: "
                            f"session_id={session_id}"
                        )
                        
                        # Process the last historical candle through AI to get initial analysis
                        # This gives the agent an immediate assessment of current market state
                        # before waiting for the first new candle to close
                        if last_historical_candle:
                            last_historical_idx = len(historical_candles) - 1
                            if last_historical_idx >= session_state.decision_start_index:
                                logger.info(
                                    f"Processing last historical candle (index {last_historical_idx}) through AI "
                                    f"for initial market analysis: session_id={session_id}"
                                )
                                
                                # Process the last historical candle to get initial AI decision
                                # This will add it to candles_processed and trigger AI analysis
                                await self.processor.process_candle(
                                    db,
                                    session_id,
                                    session_state,
                                    last_historical_candle,
                                    email_notifications
                                )
                                
                                logger.info(
                                    f"Initial AI analysis completed for historical candle: "
                                    f"session_id={session_id}, timestamp={last_historical_candle.timestamp}"
                                )
                            else:
                                logger.info(
                                    f"Skipping initial AI analysis: indicators not ready yet "
                                    f"(decision_start_index={session_state.decision_start_index}, "
                                    f"last_historical_idx={last_historical_idx}). "
                                    f"Will process when first new candle arrives."
                                )
                                # Still add the last candle to processed list even if we skip AI
                                session_state.candles_processed.append(last_historical_candle)
                    else:
                        logger.warning(f"No historical candles fetched for {session_state.asset}")
                except Exception as e:
                    logger.error(f"Could not fetch historical candles: {e}", exc_info=True)
                    # If historical fetch fails, we'll initialize calculator lazily when first candle arrives
                    # This is a fallback to ensure forward test can still start
                
                # Fetch and display the current (unclosed) candle immediately
                # This gives users something to see right away instead of waiting
                # We display it but DON'T process it - it's not closed yet
                try:
                    current_candle = await market_data_service.get_latest_candle(
                        session_state.asset,
                        session_state.timeframe
                    )
                    if current_candle:
                        # Broadcast it immediately for display (but don't add to processed list)
                        # This is just for visual feedback - the candle will be processed when it closes
                        await self.broadcaster.broadcast_candle(
                            session_id,
                            current_candle,
                            {},  # No indicators yet - candle isn't closed
                            0  # Candle number 0 (preview)
                        )
                        logger.info(
                            f"Displayed current candle immediately: session_id={session_id}, "
                            f"timestamp={current_candle.timestamp.isoformat()}"
                        )
                except Exception as e:
                    logger.warning(f"Could not fetch current candle for display: {e}")
                
                # Start real-time price streaming task
                asyncio.create_task(
                    self._stream_real_time_prices(
                        session_id,
                        session_state,
                        market_data_service
                    )
                )
                
                # Main processing loop
                while not session_state.is_stopped:
                    # Wait for resume if paused
                    await session_state.pause_event.wait()
                    if session_state.is_stopped:
                        break

                    # Wait for next candle close
                    candle = await self.timing_manager.wait_for_candle_close(
                        session_id,
                        session_state,
                        market_data_service
                    )
                    
                    if candle is None:
                        # Stopped during wait
                        break
                    
                    if session_state.is_paused or session_state.is_stopped:
                        continue
                    
                    # Process this candle (it will be added to processed list inside processor)
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
        session_state.is_paused = False
        session_state.pause_event.set()
        
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

    async def pause_forward_test(self, session_id: str) -> None:
        """
        Pause an active forward test.
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        if session_state.is_paused:
            return

        session_state.is_paused = True
        session_state.pause_event.clear()
        await self.broadcaster.broadcast_session_paused(session_id)

    async def resume_forward_test(self, session_id: str) -> None:
        """
        Resume a paused forward test.
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            raise ValidationError(f"Session not found: {session_id}")
        if not session_state.is_paused:
            return

        session_state.is_paused = False
        session_state.pause_event.set()
        await self.broadcaster.broadcast_session_resumed(session_id)
    
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
    
    async def send_historical_candles_to_connection(
        self,
        session_id: str,
        connection_id: str
    ) -> None:
        """
        Send all historical/processed candles to a new WebSocket connection.
        
        This ensures new connections receive the full chart history.
        
        Args:
            session_id: Session identifier
            connection_id: WebSocket connection identifier
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            logger.warning(f"Cannot send historical candles: session {session_id} not found")
            return
        
        if not session_state.candles_processed or len(session_state.candles_processed) == 0:
            logger.debug(f"No historical candles to send for session {session_id}")
            return
        
        if not session_state.indicator_calculator:
            logger.warning(f"Cannot send historical candles: indicator calculator not initialized for session {session_id}")
            return
        
        logger.info(
            f"Sending {len(session_state.candles_processed)} historical candles "
            f"to connection {connection_id} for session {session_id}"
        )
        
        # Send all processed candles with their indicators in smaller batches
        # This prevents UI overload and allows progressive loading
        batch_size = 25  # Smaller batches for smoother UI
        for batch_start in range(0, len(session_state.candles_processed), batch_size):
            batch = session_state.candles_processed[batch_start:batch_start + batch_size]
            for idx, candle in enumerate(batch):
                candle_idx = batch_start + idx
                # Calculate indicators - now with full history available
                indicators = session_state.indicator_calculator.calculate_all(candle_idx)
                # Use negative numbers for historical candles (before candle 0)
                candle_number = candle_idx - len(session_state.candles_processed)
                await self.broadcaster.send_candle_to_connection(
                    connection_id,
                    candle,
                    indicators,
                    candle_number
                )
            # Delay between batches to allow UI to catch up
            if batch_start + batch_size < len(session_state.candles_processed):
                await asyncio.sleep(0.1)  # Longer delay between batches
        
        logger.info(
            f"Successfully sent {len(session_state.candles_processed)} historical candles "
            f"to connection {connection_id}"
        )
        
        # Send historical AI thoughts after candles are loaded (staggered loading)
        # Wait a bit for candles to render first
        await asyncio.sleep(0.5)
        
        if session_state.ai_thoughts and len(session_state.ai_thoughts) > 0:
            logger.info(
                f"Sending {len(session_state.ai_thoughts)} historical AI thoughts "
                f"to connection {connection_id}"
            )
            
            # Send AI thoughts in reverse order (newest first) with delays
            for thought in reversed(session_state.ai_thoughts):
                # Reconstruct AIDecision from stored thought
                from services.ai_trader import AIDecision
                decision = AIDecision(
                    action=thought.get("decision", "HOLD"),
                    reasoning=thought.get("reasoning", ""),
                    stop_loss_price=thought.get("order_data", {}).get("stop_loss_price") if thought.get("order_data") else None,
                    take_profit_price=thought.get("order_data", {}).get("take_profit_price") if thought.get("order_data") else None,
                    size_percentage=thought.get("order_data", {}).get("size_percentage", 0.0) if thought.get("order_data") else 0.0,
                    leverage=thought.get("order_data", {}).get("leverage", 1) if thought.get("order_data") else 1,
                )
                
                # Add candle_number to decision data for frontend
                event = Event(
                    type=EventType.AI_DECISION,
                    data={
                        "candle_number": thought.get("candle_number", 0),
                        "action": decision.action,
                        "reasoning": decision.reasoning,
                        "stop_loss_price": decision.stop_loss_price,
                        "take_profit_price": decision.take_profit_price,
                        "size_percentage": decision.size_percentage,
                        "leverage": decision.leverage
                    }
                )
                await self.broadcaster.websocket_manager.send_to_connection(connection_id, event)
                # Small delay between thoughts
                await asyncio.sleep(0.15)
            
            logger.info(
                f"Successfully sent {len(session_state.ai_thoughts)} historical AI thoughts "
                f"to connection {connection_id}"
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
    
    async def _stream_real_time_prices(
        self,
        session_id: str,
        session_state: SessionState,
        market_data_service: MarketDataService
    ) -> None:
        """
        Stream real-time price updates for the forward test session.
        
        Fetches current price every second from FreeCryptoAPI and broadcasts it via WebSocket
        for real-time chart updates.
        
        Args:
            session_id: Session identifier
            session_state: Session state object
            market_data_service: Market data service instance
        """
        logger.info(f"Starting real-time price stream: session_id={session_id}")
        
        while not session_state.is_stopped:
            try:
                # Wait for resume if paused
                await session_state.pause_event.wait()
                if session_state.is_stopped:
                    break
                
                # Get current price from CoinGecko
                price_data = await market_data_service.get_current_price(session_state.asset)
                if price_data:
                    await self.broadcaster.broadcast_price_update(
                        session_id,
                        price_data['price'],
                        datetime.now(timezone.utc)
                    )
                
                # Update every second for real-time updates
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in price streaming: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(5)
        
        logger.info(f"Stopped real-time price stream: session_id={session_id}")
