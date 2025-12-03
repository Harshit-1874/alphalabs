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
        candle_number = len(session_state.candles_processed)
        
        self.logger.info(
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
        
        # Broadcast AI thinking event
        await self.broadcaster.broadcast_ai_thinking(session_id)
        
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
        return int((datetime.utcnow() - session_state.started_at).total_seconds())
