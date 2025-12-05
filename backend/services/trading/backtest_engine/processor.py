"""
Candle processing for backtest engine.

Purpose:
    Handle candle processing logic including indicator calculation,
    AI decision making, and decision execution for backtest sessions.

Features:
    - Sequential candle processing
    - Indicator calculation integration
    - AI decision integration
    - Position management coordination
    - Real-time event broadcasting
    - Trade execution logic

Usage:
    processor = CandleProcessor(
        broadcaster=broadcaster,
        position_handler=position_handler,
        database_manager=database_manager
    )
    await processor.process_candle(
        db=db,
        session_id="uuid",
        session_state=session_state,
        candle=candle_data
    )
"""

import logging
from datetime import datetime
from typing import Any, Optional, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from services.market_data_service import Candle
from services.ai_trader import AIDecision
from services.trading.position_manager import Position
from services.trading.backtest_engine.broadcaster import EventBroadcaster
from services.trading.backtest_engine.position_handler import PositionHandler
from services.trading.backtest_engine.database import DatabaseManager

logger = logging.getLogger(__name__)


HISTORY_WINDOW = 20
MIN_HISTORY_WINDOW = 10  # Reduced history when no position and market is stable

# Constants for LLM triggering logic
INITIAL_READINESS_THRESHOLD = 0.8  # 80% for initial decision_start_index calculation
RUNTIME_READINESS_THRESHOLD = 0.7  # 70% for runtime indicator readiness checks

# Position-aware forcing thresholds
FORCE_DECISION_SL_TP_PROXIMITY_PCT = 1.0  # Force if within 1% of stop-loss or take-profit
FORCE_DECISION_SIGNIFICANT_PNL_PCT = 2.0  # Force if unrealized PnL > 2% of position size
FORCE_DECISION_EXTENDED_PERIOD = 50  # Force if position open for 50+ candles without review

# Volatility-based skipping thresholds
LOW_VOLATILITY_THRESHOLD = 0.5  # Skip if current volatility < 50% of recent average


class CandleProcessor:
    """
    Processes candles for backtest sessions.
    
    Handles the complete candle processing workflow:
    1. Calculate indicators
    2. Update open positions
    3. Get AI decision
    4. Execute decision
    5. Broadcast events
    """
    
    def __init__(
        self,
        broadcaster: EventBroadcaster,
        position_handler: PositionHandler,
        database_manager: DatabaseManager
    ):
        """
        Initialize candle processor.
        
        Args:
            broadcaster: Event broadcaster for WebSocket updates
            position_handler: Position handler for trade management
            database_manager: Database manager for persistence
        """
        self.broadcaster = broadcaster
        self.position_handler = position_handler
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)
    
    def precompute_llm_call_points(
        self,
        session_state: Any,
        total_candles: int
    ) -> set[int]:
        """
        Pre-compute all candle indices where LLM calls should be made.
        
        This allows us to fast-forward through non-decision candles.
        
        Args:
            session_state: Session state object
            total_candles: Total number of candles in backtest
            
        Returns:
            Set of candle indices where LLM calls should be made (based on normal cadence)
        """
        call_points = set()
        
        decision_start = session_state.decision_start_index
        decision_mode = getattr(session_state, "decision_mode", "every_candle")
        decision_interval = getattr(session_state, "decision_interval_candles", 1) or 1
        
        if decision_mode == "every_candle":
            # Every candle after decision_start_index
            for i in range(decision_start, total_candles):
                call_points.add(i)
        elif decision_mode == "every_n_candles":
            # Every N candles after decision_start_index
            for i in range(decision_start, total_candles):
                elapsed = i - decision_start
                if elapsed % decision_interval == 0:
                    call_points.add(i)
        
        self.logger.info(
            f"Pre-computed {len(call_points)} LLM call points "
            f"(mode={decision_mode}, interval={decision_interval}, "
            f"start_index={decision_start}, total_candles={total_candles})"
        )
        
        return call_points
    
    async def fast_forward_candle(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,
        candle: Candle,
        candle_index: int
    ) -> Optional[str]:
        """
        Fast-forward through a candle with minimal processing.
        
        Only updates positions (for SL/TP checks) and processes pending orders.
        Skips indicator calculation, broadcasting, and LLM calls.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            candle: Current candle to process
            candle_index: Current candle index
            
        Returns:
            Close reason if position was closed, None otherwise
        """
        # Update open position if exists (for SL/TP checks)
        if session_state.position_manager.has_open_position():
            close_reason = await session_state.position_manager.update_position(
                candle_high=candle.high,
                candle_low=candle.low,
                current_price=candle.close
            )
            
            # If position was closed by stop-loss or take-profit
            if close_reason:
                closed_trade = session_state.position_manager.get_closed_trades()[-1]
                await self.position_handler.handle_position_closed(
                    db,
                    session_id,
                    session_state,
                    closed_trade,
                    candle_index,
                    candle.timestamp
                )
                return close_reason
        
        # Process any pending order (limit-like entry)
        if session_state.pending_order and not session_state.position_manager.has_open_position():
            po = session_state.pending_order
            entry_price = po.get("entry_price")
            action = po.get("action")
            size_pct = po.get("size_percentage", 0.0)
            stop_loss = po.get("stop_loss_price")
            take_profit = po.get("take_profit_price")
            leverage = po.get("leverage", 1)

            if entry_price is not None:
                # Check if this candle's high/low touched the entry price
                if candle.low <= entry_price <= candle.high:
                    self.logger.info(
                        f"Filling pending {action} order at {entry_price} on candle {candle_index}"
                    )
                    success = await session_state.position_manager.open_position(
                        action=action.lower(),
                        entry_price=entry_price,
                        size_percentage=size_pct,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        leverage=leverage,
                    )
                    if success:
                        position = session_state.position_manager.get_position()
                        await self.position_handler.handle_position_opened(
                            db,
                            session_id,
                            session_state,
                            position,
                            candle_index,
                            candle.timestamp,
                            po.get("reasoning", "Pending order filled"),
                        )
                    # Clear the pending order after this candle
                    session_state.pending_order = None
        
        return None
    
    async def process_candle(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,  # SessionState type (avoiding circular import)
        candle: Candle
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
        """
        candle_index = session_state.current_index
        
        self.logger.debug(
            f"Processing candle {candle_index + 1}/{len(session_state.candles)}: "
            f"timestamp={candle.timestamp}, close={candle.close}"
        )
        
        # Calculate indicators for current candle
        indicators = session_state.indicator_calculator.calculate_all(candle_index)
        
        # Broadcast candle event with indicators
        await self.broadcaster.broadcast_candle(session_id, candle, indicators, candle_index)
        
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
                await self.position_handler.handle_position_closed(
                    db,
                    session_id,
                    session_state,
                    closed_trade,
                    candle_index,
                    candle.timestamp
                )
        
        # Process any pending order (limit-like entry) before asking the AI
        # for a new decision. This simulates placing an order at a prior
        # candle and having it fill only when price actually reaches the
        # requested entry level.
        if session_state.pending_order and not session_state.position_manager.has_open_position():
            po = session_state.pending_order
            entry_price = po.get("entry_price")
            action = po.get("action")
            size_pct = po.get("size_percentage", 0.0)
            stop_loss = po.get("stop_loss_price")
            take_profit = po.get("take_profit_price")
            leverage = po.get("leverage", 1)

            if entry_price is not None:
                # Check if this candle's high/low touched the entry price.
                if candle.low <= entry_price <= candle.high:
                    self.logger.info(
                        f"Filling pending {action} order at {entry_price} on candle {candle_index}"
                    )
                    success = await session_state.position_manager.open_position(
                        action=action.lower(),
                        entry_price=entry_price,
                        size_percentage=size_pct,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        leverage=leverage,
                    )
                    if success:
                        position = session_state.position_manager.get_position()
                        await self.position_handler.handle_position_opened(
                            db,
                            session_id,
                            session_state,
                            position,
                            candle_index,
                            candle.timestamp,
                            po.get("reasoning", "Pending order filled"),
                        )
                    # Either way, clear the pending order after this candle.
                    session_state.pending_order = None

        # Get AI decision
        position_state = session_state.position_manager.get_position()
        equity = session_state.position_manager.get_total_equity()

        # Check if indicators are actually ready at runtime (safety check)
        # This ensures we don't call the LLM with mostly None indicators
        indicators_ready = session_state.indicator_calculator.check_indicator_readiness(
            candle_index, 
            min_ready_percentage=RUNTIME_READINESS_THRESHOLD
        )

        # Priority-based LLM triggering logic
        # Priority 1: Force conditions (position needs attention)
        force_decision, force_reason = self._should_force_llm_call(
            session_state, candle_index, position_state, candle
        )
        
        # Initialize skip_reason for use in else block
        skip_reason: Optional[str] = None
        
        # Priority 2: Normal cadence check (if not forced)
        if not force_decision:
            # Check volatility-based skipping (only if no position)
            if not position_state:
                skip_volatility, volatility_reason = self._should_skip_due_to_low_volatility(
                    session_state, candle_index, indicators
                )
                if skip_volatility:
                    should_run_ai = False
                    skip_reason = f"SKIPPED (volatility): {volatility_reason}"
                else:
                    # Normal cadence check
                    should_run_ai = (
                        candle_index >= session_state.decision_start_index
                        and indicators_ready
                        and self._is_decision_candle(session_state, candle_index)
                    )
            else:
                # Normal cadence check when position exists
                should_run_ai = (
                    candle_index >= session_state.decision_start_index
                    and indicators_ready
                    and self._is_decision_candle(session_state, candle_index)
                )
                skip_reason = None
        else:
            # Force decision - override normal cadence
            should_run_ai = True
            skip_reason = None

        if should_run_ai:
            # Broadcast AI thinking event
            await self.broadcaster.broadcast_ai_thinking(session_id)

            # Use adaptive history window based on position state
            force_full_history = force_decision  # Always use full history when forced
            recent_candles, recent_indicators = self._build_decision_history(
                session_state, candle_index, force_full_history=force_full_history
            )
            
            decision_context = {
                "mode": session_state.decision_mode,
                "interval": session_state.decision_interval_candles,
                "candle_index": candle_index,
                "allow_leverage": session_state.allow_leverage,
                "max_leverage": 5 if session_state.allow_leverage else 1,
                "forced_decision": force_decision,
                "force_reason": force_reason if force_decision else None,
            }

            decision = await session_state.ai_trader.get_decision(
                candle=candle,
                indicators=indicators,
                position_state=position_state,
                equity=equity,
                recent_candles=recent_candles,
                recent_indicators=recent_indicators,
                decision_context=decision_context,
            )
            decision.candle_index = candle_index
        else:
            # Build skip reasoning
            if candle_index < session_state.decision_start_index:
                reasoning = (
                    f"Skipping AI decision for candle {candle_index} because "
                    f"indicators are still warming up (decision_start_index="
                    f"{session_state.decision_start_index})."
                )
            elif not indicators_ready:
                ready_count = sum(1 for v in indicators.values() if v is not None)
                total_count = len(indicators)
                reasoning = (
                    f"Skipping AI decision for candle {candle_index} because "
                    f"insufficient indicators are ready ({ready_count}/{total_count} ready)."
                )
            else:
                reasoning = skip_reason or (
                    f"Decision cadence ({session_state.decision_mode}) skipped candle {candle_index}"
                )
            decision = AIDecision(
                action="HOLD",
                reasoning=reasoning,
                size_percentage=0.0,
                leverage=1,
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
                "entry_price": decision.entry_price,
                "stop_loss_price": decision.stop_loss_price,
                "take_profit_price": decision.take_profit_price,
                "size_percentage": decision.size_percentage,
                "leverage": decision.leverage,
            }
            if decision.action in ["LONG", "SHORT"]
            else None
        }
        session_state.ai_thoughts.append(ai_thought)
        
        # Broadcast AI decision event
        await self.broadcaster.broadcast_ai_decision(session_id, decision)
        
        # Execute AI decision
        await self.execute_decision(
            db,
            session_id,
            session_state,
            decision,
            candle,
            candle_index
        )
        
        # Broadcast stats update
        stats = session_state.position_manager.get_stats()
        self._record_equity_point(session_state, candle.timestamp, stats["current_equity"])
        await self.broadcaster.broadcast_stats_update(session_id, stats)

        await self.database_manager.update_session_runtime_stats(
            db=db,
            session_id=session_id,
            current_equity=stats["current_equity"],
            current_pnl_pct=stats["equity_change_pct"],
            max_drawdown_pct=session_state.max_drawdown_pct,
            elapsed_seconds=self._compute_elapsed_seconds(session_state),
            open_position=self._serialize_position(session_state.position_manager.get_position()),
            current_candle=candle_index + 1,
        )
    
    async def execute_decision(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,  # SessionState type (avoiding circular import)
        decision: AIDecision,
        candle: Candle,
        candle_index: int
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
                    await self.position_handler.handle_position_closed(
                        db,
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
                self.logger.warning(
                    f"Cannot open {action} position: position already exists"
                )
                return
            
            leverage = decision.leverage or 1
            if not session_state.allow_leverage:
                leverage = 1
            leverage = max(1, min(int(leverage), 5))
            
            # If the AI provided an explicit entry_price, treat this as a
            # pending order that will be filled only when price reaches that
            # level on a future candle. Otherwise, enter immediately at the
            # current close.
            if decision.entry_price is not None:
                session_state.pending_order = {
                    "action": action,
                    "entry_price": float(decision.entry_price),
                    "size_percentage": decision.size_percentage,
                    "stop_loss_price": decision.stop_loss_price,
                    "take_profit_price": decision.take_profit_price,
                    "leverage": leverage,
                    "reasoning": decision.reasoning,
                    "decision_candle": decision.candle_index,
                    "decision_context": getattr(decision, "decision_context", None),
                }
                self.logger.info(
                    f"Registered pending {action} order at {decision.entry_price} "
                    f"for session {session_id} on candle {candle_index}"
                )
            else:
                # Open position at current close (market-at-close behavior)
                success = await session_state.position_manager.open_position(
                    action=action.lower(),
                    entry_price=candle.close,
                    size_percentage=decision.size_percentage,
                    stop_loss=decision.stop_loss_price,
                    take_profit=decision.take_profit_price,
                    leverage=leverage,
                )
                
                if success:
                    position = session_state.position_manager.get_position()
                    await self.position_handler.handle_position_opened(
                        db,
                        session_id,
                        session_state,
                        position,
                        candle_index,
                        candle.timestamp,
                        decision.reasoning,
                    )

    def _record_equity_point(self, session_state: Any, timestamp: datetime, equity: float) -> None:
        point = {"time": timestamp.isoformat(), "value": equity}
        if equity > session_state.peak_equity:
            session_state.peak_equity = equity
        drawdown = 0.0
        if session_state.peak_equity:
            drawdown = ((equity - session_state.peak_equity) / session_state.peak_equity) * 100
        session_state.max_drawdown_pct = min(session_state.max_drawdown_pct, drawdown)
        point["drawdown"] = drawdown
        session_state.equity_curve.append(point)

    def _serialize_position(self, position: Optional[Position]) -> Optional[dict]:
        if not position:
            return None
        return {
            "type": position.action,
            "entry_price": position.entry_price,
            "size": position.size,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "entry_time": position.entry_time.isoformat(),
            "leverage": position.leverage,
            "unrealized_pnl": position.unrealized_pnl,
        }

    def _is_decision_candle(self, session_state: Any, candle_index: int) -> bool:
        """
        Determine if this candle should trigger an AI decision based on cadence settings.
        
        For 'every_candle': Always returns True (after warm-up period).
        For 'every_n_candles': Returns True every N candles, counting from decision_start_index.
        
        Args:
            session_state: Session state object
            candle_index: Current candle index
            
        Returns:
            True if this candle should trigger a decision, False otherwise
        """
        mode = getattr(session_state, "decision_mode", "every_candle")
        if mode == "every_candle":
            return True
        if mode == "every_n_candles":
            interval = getattr(session_state, "decision_interval_candles", 1) or 1
            # Count from decision_start_index to avoid triggering during warm-up
            elapsed = max(0, candle_index - session_state.decision_start_index)
            return elapsed % interval == 0
        return True

    def _build_decision_history(
        self, 
        session_state: Any, 
        candle_index: int, 
        force_full_history: bool = False
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Build recent candle and indicator history for AI decision context.
        
        Uses adaptive window size:
        - Full window (HISTORY_WINDOW) when position exists or forced
        - Reduced window (MIN_HISTORY_WINDOW) when no position and not forced
        
        Args:
            session_state: Session state object
            candle_index: Current candle index
            force_full_history: If True, always use full history window
            
        Returns:
            Tuple of (recent_candles, recent_indicators) lists
        """
        # Adaptive window: use smaller window when no position and not forced
        has_position = session_state.position_manager.has_open_position()
        window_size = HISTORY_WINDOW if (force_full_history or has_position) else MIN_HISTORY_WINDOW
        
        window_start = max(0, candle_index - window_size + 1)
        selected_candles = session_state.candles[window_start:candle_index + 1]
        
        recent_candles = [
            {
                "timestamp": c.timestamp.isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in selected_candles
        ]

        recent_indicators = []
        for idx in range(window_start, candle_index + 1):
            values = session_state.indicator_calculator.calculate_all(idx)
            recent_indicators.append(
                {
                    "candle_index": idx,
                    "values": values,
                }
            )

        return recent_candles, recent_indicators

    def _should_force_llm_call(
        self, 
        session_state: Any, 
        candle_index: int, 
        position: Optional[Position], 
        candle: Candle
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if LLM call should be forced due to position conditions.
        
        Forces decision when:
        1. Position is near stop-loss or take-profit (within threshold)
        2. Position has significant unrealized PnL (> threshold % of position size)
        3. Position has been open for extended period without review
        
        Args:
            session_state: Session state object
            candle_index: Current candle index
            position: Current open position (None if no position)
            candle: Current candle data
            
        Returns:
            Tuple of (should_force, reason_string)
        """
        if not position:
            return False, None
        
        current_price = candle.close
        
        # Check 1: Position near stop-loss or take-profit
        if position.stop_loss:
            distance_to_sl_pct = abs(position.stop_loss - current_price) / current_price * 100
            if distance_to_sl_pct < FORCE_DECISION_SL_TP_PROXIMITY_PCT:
                return True, f"Position near stop-loss (within {FORCE_DECISION_SL_TP_PROXIMITY_PCT}%)"
        
        if position.take_profit:
            distance_to_tp_pct = abs(position.take_profit - current_price) / current_price * 100
            if distance_to_tp_pct < FORCE_DECISION_SL_TP_PROXIMITY_PCT:
                return True, f"Position near take-profit (within {FORCE_DECISION_SL_TP_PROXIMITY_PCT}%)"
        
        # Check 2: Significant unrealized PnL
        if position.size > 0:
            pnl_pct_of_position = abs(position.unrealized_pnl) / position.size * 100
            if pnl_pct_of_position > FORCE_DECISION_SIGNIFICANT_PNL_PCT:
                return True, f"Significant unrealized PnL ({pnl_pct_of_position:.2f}% of position size)"
        
        # Check 3: Position open for extended period
        # Find when position was opened by checking recent AI thoughts
        entry_candle_index = None
        for thought in reversed(session_state.ai_thoughts[-20:]):  # Check last 20 thoughts
            if thought.get("decision") in ["LONG", "SHORT"]:
                entry_candle_index = thought.get("candle_number")
                break
        
        if entry_candle_index is not None:
            candles_since_entry = candle_index - entry_candle_index
            if candles_since_entry > FORCE_DECISION_EXTENDED_PERIOD:
                return True, f"Position open for {candles_since_entry} candles without review"
        
        return False, None

    def _should_skip_due_to_low_volatility(
        self, 
        session_state: Any, 
        candle_index: int, 
        indicators: Dict[str, Optional[float]]
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if LLM call should be skipped due to low volatility.
        
        Skips when current volatility is significantly below recent average.
        Uses ATR if available, otherwise uses price range.
        
        Args:
            session_state: Session state object
            candle_index: Current candle index
            indicators: Current indicator values
            
        Returns:
            Tuple of (should_skip, reason_string)
        """
        # Need at least a few candles to compare volatility
        if candle_index < 5:
            return False, None
        
        # Method 1: Use ATR if available
        if 'atr' in indicators and indicators['atr'] is not None:
            current_atr = indicators['atr']
            # Get average ATR from recent candles
            recent_atrs = []
            for idx in range(max(0, candle_index - 5), candle_index):
                recent_indicators = session_state.indicator_calculator.calculate_all(idx)
                if 'atr' in recent_indicators and recent_indicators['atr'] is not None:
                    recent_atrs.append(recent_indicators['atr'])
            
            if len(recent_atrs) >= 3:
                avg_atr = sum(recent_atrs) / len(recent_atrs)
                if avg_atr > 0 and current_atr < avg_atr * LOW_VOLATILITY_THRESHOLD:
                    return True, f"Low volatility (ATR {current_atr:.2f} < {LOW_VOLATILITY_THRESHOLD*100}% of avg {avg_atr:.2f})"
        
        # Method 2: Use price range as fallback
        if candle_index >= 5:
            recent_candles = session_state.candles[max(0, candle_index - 5):candle_index + 1]
            price_ranges = [c.high - c.low for c in recent_candles]
            avg_range = sum(price_ranges[:-1]) / len(price_ranges[:-1]) if len(price_ranges) > 1 else price_ranges[0]
            current_range = price_ranges[-1]
            
            if avg_range > 0 and current_range < avg_range * LOW_VOLATILITY_THRESHOLD:
                return True, f"Low volatility (price range {current_range:.2f} < {LOW_VOLATILITY_THRESHOLD*100}% of avg {avg_range:.2f})"
        
        return False, None

    def _compute_elapsed_seconds(self, session_state: Any) -> int:
        if not session_state.started_at:
            return 0
        # Ensure both datetimes are timezone-aware
        from datetime import timezone
        now = datetime.now(timezone.utc)
        started = session_state.started_at
        # If started_at is naive, make it aware (backward compatibility)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return int((now - started).total_seconds())
