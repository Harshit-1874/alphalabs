"""
Candle processing and decision execution for forward test engine.

Purpose:
    Handle candle processing logic including indicator calculation,
    AI decision making, and decision execution for forward tests.

Features:
    - Candle processing with indicator calculation
    - AI decision integration
    - Position management based on AI decisions
    - WebSocket event broadcasting
    - Email notification triggering

Usage:
    processor = CandleProcessor(
        broadcaster,
        position_handler,
        database_manager,
        auto_stop_manager
    )
    await processor.process_candle(
        db=db,
        session_id="uuid",
        session_state=session_state,
        candle=candle,
        email_notifications=True
    )
"""

import logging
from typing import Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from services.market_data_service import Candle
from services.trading.indicator_calculator import IndicatorCalculator
from services.ai_trader import AIDecision
from websocket.manager import WebSocketManager
from services.trading.position_manager import Position

logger = logging.getLogger(__name__)

# Constants for indicator readiness thresholds
INITIAL_READINESS_THRESHOLD = 0.8  # 80% for initial decision_start_index calculation
RUNTIME_READINESS_THRESHOLD = 0.7  # 70% for runtime indicator readiness checks


class CandleProcessor:
    """
    Processes candles and executes AI trading decisions for forward tests.
    
    Handles the complete candle processing workflow:
    1. Calculate indicators for current candle
    2. Broadcast candle event
    3. Update open positions
    4. Get AI decision
    5. Execute AI decision
    6. Broadcast stats update
    """
    
    def __init__(
        self,
        broadcaster: Any,
        position_handler: Any,
        database_manager: Any,
        auto_stop_manager: Any
    ):
        """
        Initialize candle processor.
        
        Args:
            broadcaster: Event broadcaster for WebSocket events
            position_handler: Position handler for position lifecycle
            database_manager: Database manager for persistence
            auto_stop_manager: Auto-stop manager for condition monitoring
        """
        self.broadcaster = broadcaster
        self.position_handler = position_handler
        self.database_manager = database_manager
        self.auto_stop_manager = auto_stop_manager
        self.logger = logging.getLogger(__name__)
    
    async def process_candle(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,
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
        # Add new candle to processed list first
        session_state.candles_processed.append(candle)
        candle_number = len(session_state.candles_processed) - 1  # 0-indexed for indicator calculator
        
        self.logger.info(
            f"Processing candle {candle_number}: "
            f"timestamp={candle.timestamp}, close={candle.close}"
        )
        
        # Initialize indicator calculator if not already done (fallback for when historical fetch failed)
        if session_state.indicator_calculator is None:
            self.logger.warning(
                f"Indicator calculator not initialized, creating with {len(session_state.candles_processed)} candles"
            )
            session_state.indicator_calculator = IndicatorCalculator(
                candles=session_state.candles_processed,
                enabled_indicators=session_state.agent.indicators,
                mode=session_state.agent.mode,
                custom_indicators=session_state.agent.custom_indicators,
            )
            
            # Calculate decision_start_index if not already set
            if session_state.decision_start_index == 0:
                session_state.decision_start_index = session_state.indicator_calculator.find_first_ready_index(
                    min_ready_percentage=INITIAL_READINESS_THRESHOLD
                )
                self.logger.info(
                    f"Decision start index calculated: {session_state.decision_start_index} "
                    f"(threshold: {INITIAL_READINESS_THRESHOLD * 100}%)"
                )
        else:
            # Update indicator calculator with new candle
            # Recreate calculator with all candles (including the new one)
            # This ensures indicators are calculated correctly with full history
            session_state.indicator_calculator = IndicatorCalculator(
                candles=session_state.candles_processed,
                enabled_indicators=session_state.agent.indicators,
                mode=session_state.agent.mode,
                custom_indicators=session_state.agent.custom_indicators,
            )
        
        # Calculate indicators for the latest candle
        indicators = session_state.indicator_calculator.calculate_all(candle_number)
        
        # Check indicator readiness at runtime
        indicators_ready = session_state.indicator_calculator.check_indicator_readiness(
            candle_number,
            min_ready_percentage=RUNTIME_READINESS_THRESHOLD
        )
        
        # Log indicator readiness status
        ready_count = sum(1 for v in indicators.values() if v is not None)
        total_count = len(indicators)
        ready_pct = (ready_count / total_count * 100) if total_count > 0 else 0
        self.logger.info(
            f"Indicator readiness: {ready_count}/{total_count} ({ready_pct:.1f}%) "
            f"ready, threshold: {RUNTIME_READINESS_THRESHOLD * 100}%"
        )
        
        # Broadcast indicator readiness event
        await self.broadcaster.broadcast_indicator_readiness(
            session_id,
            ready_count,
            total_count,
            ready_pct,
            indicators_ready
        )
        
        # Broadcast candle event with indicators
        await self.broadcaster.broadcast_candle(session_id, candle, indicators, candle_number)
        
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
                    candle_number,
                    candle.timestamp,
                    email_notifications
                )
        
        # Get AI decision
        position_state = session_state.position_manager.get_position()
        equity = session_state.position_manager.get_total_equity()
        
        # Determine if we should run AI decision based on readiness and cadence
        is_decision_candle = self._is_decision_candle(session_state, candle_number)
        past_start_index = candle_number >= session_state.decision_start_index
        
        should_run_ai = (
            past_start_index
            and indicators_ready
            and is_decision_candle
        )
        
        # Log detailed LLM intervention decision criteria
        self.logger.info(
            f"LLM Intervention Decision for candle {candle_number}:\n"
            f"  - candle_number >= decision_start_index: {past_start_index} "
            f"(candle_number={candle_number}, decision_start_index={session_state.decision_start_index})\n"
            f"  - indicators_ready: {indicators_ready} "
            f"({ready_count}/{total_count} ready, threshold={RUNTIME_READINESS_THRESHOLD * 100}%)\n"
            f"  - is_decision_candle: {is_decision_candle} "
            f"(mode={getattr(session_state, 'decision_mode', 'every_candle')}, "
            f"interval={getattr(session_state, 'decision_interval_candles', 1)})\n"
            f"  - SHOULD_RUN_AI: {should_run_ai}"
        )
        
        if should_run_ai:
            # Broadcast AI thinking event
            await self.broadcaster.broadcast_ai_thinking(session_id)
            
            decision = await session_state.ai_trader.get_decision(
                candle=candle,
                indicators=indicators,
                position_state=position_state,
                equity=equity
            )
        else:
            # Build skip reasoning
            if candle_number < session_state.decision_start_index:
                reasoning = (
                    f"Skipping AI decision for candle {candle_number} because "
                    f"indicators are still warming up (decision_start_index="
                    f"{session_state.decision_start_index})."
                )
            elif not indicators_ready:
                reasoning = (
                    f"Skipping AI decision for candle {candle_number} because "
                    f"insufficient indicators are ready ({ready_count}/{total_count} ready, "
                    f"need {RUNTIME_READINESS_THRESHOLD * 100}%)."
                )
            else:
                reasoning = (
                    f"Decision cadence ({session_state.decision_mode}) skipped candle {candle_number}"
                )
            
            decision = AIDecision(
                action="HOLD",
                reasoning=reasoning,
                size_percentage=0.0,
                leverage=1,
            )
        
        # Store AI thought
        # Extract council deliberation (if present in decision context)
        council_deliberation = None
        if decision.decision_context and isinstance(decision.decision_context, dict):
            council_deliberation = decision.decision_context.get("council_deliberation")

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
            } if decision.action in ["LONG", "SHORT"] else None,
            # Council deliberation details for persistence
            "council_stage1": council_deliberation.get("stage1") if council_deliberation else None,
            "council_stage2": council_deliberation.get("stage2") if council_deliberation else None,
            "council_metadata": {
                "aggregate_rankings": council_deliberation.get("aggregate_rankings"),
                "label_to_model": council_deliberation.get("label_to_model"),
                "stage3": council_deliberation.get("stage3"),
            } if council_deliberation else None,
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
            candle_number,
            email_notifications
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
        )
    
    async def execute_decision(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,
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
                    await self.position_handler.handle_position_closed(
                        db,
                        session_id,
                        session_state,
                        closed_trade,
                        candle_number,
                        candle.timestamp,
                        email_notifications
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
            
            # Open position
            success = await session_state.position_manager.open_position(
                action=action.lower(),
                entry_price=candle.close,
                size_percentage=decision.size_percentage,
                stop_loss=decision.stop_loss_price,
                take_profit=decision.take_profit_price,
                leverage=leverage
            )
            
            if success:
                position = session_state.position_manager.get_position()
                await self.position_handler.handle_position_opened(
                    db,
                    session_id,
                    session_state,
                    position,
                    candle_number,
                    candle.timestamp,
                    decision.reasoning,
                    email_notifications
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

    def _compute_elapsed_seconds(self, session_state: Any) -> int:
        if not session_state.started_at:
            return 0
        # Ensure both datetimes are timezone-aware
        from datetime import timezone
        now = datetime.now(timezone.utc)
        started = session_state.started_at
        # If started_at is naive, make it aware (shouldn't happen, but safety check)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return int((now - started).total_seconds())
    
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
    
    async def process_initial_ai_decision(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,
        email_notifications: bool
    ) -> None:
        """
        Process an initial AI decision based on historical data when forward test starts.
        
        This gives users immediate AI analysis without waiting for the first live candle.
        Uses the last historical candle which is already in candles_processed.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object
            email_notifications: Whether to send email notifications
        """
        if not session_state.candles_processed:
            self.logger.warning(
                f"No historical candles available for initial AI decision: session_id={session_id}"
            )
            return
        
        if session_state.indicator_calculator is None:
            self.logger.warning(
                f"Indicator calculator not initialized for initial AI decision: session_id={session_id}"
            )
            return
        
        # Use the last historical candle (already in candles_processed)
        last_idx = len(session_state.candles_processed) - 1
        
        # Check if we have enough data for AI decisions
        if last_idx < session_state.decision_start_index:
            self.logger.info(
                f"Skipping initial AI decision: not enough historical data "
                f"(last_idx={last_idx}, decision_start_index={session_state.decision_start_index})"
            )
            return
        
        last_candle = session_state.candles_processed[-1]
        
        self.logger.info(
            f"Processing initial AI decision on historical data: "
            f"session_id={session_id}, candle_idx={last_idx}, timestamp={last_candle.timestamp}"
        )
        
        # Calculate indicators for the last candle
        indicators = session_state.indicator_calculator.calculate_all(last_idx)
        
        # For the *initial* decision we only log readiness, we don't block on it.
        # This guarantees one immediate AI call on forward start as long as we're
        # past decision_start_index.
        ready_count = sum(1 for v in indicators.values() if v is not None)
        total_count = len(indicators)
        ready_pct = (ready_count / total_count * 100) if total_count > 0 else 0
        
        self.logger.info(
            f"Initial AI decision indicator readiness: {ready_count}/{total_count} ({ready_pct:.1f}%)"
        )

        # Broadcast AI thinking event
        await self.broadcaster.broadcast_ai_thinking(session_id)
        
        # Get position state and equity for AI decision
        position_state = session_state.position_manager.get_position()
        equity = session_state.position_manager.get_total_equity()
        
        # Get AI decision
        decision = await session_state.ai_trader.get_decision(
            candle=last_candle,
            indicators=indicators,
            position_state=position_state,
            equity=equity
        )
        
        self.logger.info(
            f"Initial AI decision received: action={decision.action}, reasoning={decision.reasoning[:100]}..."
        )
        
        # Store AI thought
        council_deliberation = None
        if decision.decision_context and isinstance(decision.decision_context, dict):
            council_deliberation = decision.decision_context.get("council_deliberation")
        
        ai_thought = {
            "candle_number": last_idx,
            "timestamp": last_candle.timestamp,
            "candle_data": {
                "open": last_candle.open,
                "high": last_candle.high,
                "low": last_candle.low,
                "close": last_candle.close,
                "volume": last_candle.volume
            },
            "indicator_values": indicators,
            "reasoning": decision.reasoning,
            "decision": decision.action,
            "order_data": {
                "stop_loss_price": decision.stop_loss_price,
                "take_profit_price": decision.take_profit_price,
                "size_percentage": decision.size_percentage,
                "leverage": decision.leverage
            } if decision.action in ["LONG", "SHORT"] else None,
            "council_stage1": council_deliberation.get("stage1") if council_deliberation else None,
            "council_stage2": council_deliberation.get("stage2") if council_deliberation else None,
            "council_metadata": {
                "aggregate_rankings": council_deliberation.get("aggregate_rankings"),
                "label_to_model": council_deliberation.get("label_to_model"),
                "stage3": council_deliberation.get("stage3"),
            } if council_deliberation else None,
            "is_initial": True,  # Mark this as the initial analysis
        }
        session_state.ai_thoughts.append(ai_thought)
        
        # Broadcast AI decision event
        await self.broadcaster.broadcast_ai_decision(session_id, decision)
        
        # Execute AI decision (can open positions based on initial analysis)
        await self.execute_decision(
            db,
            session_id,
            session_state,
            decision,
            last_candle,
            last_idx,
            email_notifications
        )
        
        # Broadcast stats update
        stats = session_state.position_manager.get_stats()
        self._record_equity_point(session_state, last_candle.timestamp, stats["current_equity"])
        await self.broadcaster.broadcast_stats_update(session_id, stats)
        await self.database_manager.update_session_runtime_stats(
            db=db,
            session_id=session_id,
            current_equity=stats["current_equity"],
            current_pnl_pct=stats["equity_change_pct"],
            max_drawdown_pct=session_state.max_drawdown_pct,
            elapsed_seconds=self._compute_elapsed_seconds(session_state),
            open_position=self._serialize_position(session_state.position_manager.get_position()),
        )
        
        self.logger.info(
            f"Initial AI decision processed successfully: session_id={session_id}"
        )