"""
Position handling for backtest engine.

Purpose:
    Handle position lifecycle events including opening and closing positions.
    Manages database persistence and WebSocket broadcasting for position events.

Features:
    - Position opened event handling
    - Position closed event handling
    - Trade record persistence
    - Real-time WebSocket broadcasting
    - Integration with position manager

Usage:
    position_handler = PositionHandler(websocket_manager)
    await position_handler.handle_position_opened(
        db=db,
        session_id="uuid",
        session_state=session_state,
        position=position_data,
        candle_index=100,
        timestamp=datetime.utcnow(),
        reasoning="AI reasoning text"
    )
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from models.arena import Trade
from services.trading.position_manager import Position as PositionData
from websocket.manager import WebSocketManager
from websocket.events import Event, EventType
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class PositionHandler:
    """
    Manages position lifecycle events for backtest sessions.
    
    Handles the opening and closing of positions, including database
    persistence and WebSocket event broadcasting.
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        """
        Initialize position handler.
        
        Args:
            websocket_manager: WebSocket manager for real-time updates
        """
        self.websocket_manager = websocket_manager
        self.logger = logging.getLogger(__name__)
    
    async def handle_position_opened(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,  # SessionState type (avoiding circular import)
        position: PositionData,
        candle_index: int,
        timestamp: datetime,
        reasoning: str
    ) -> None:
        """
        Handle position opened event.
        
        Saves trade to database and broadcasts event via WebSocket.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object containing position manager
            position: Opened position data from position manager
            candle_index: Candle index at entry
            timestamp: Entry timestamp
            reasoning: AI reasoning for entry
        """
        self.logger.info(
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
        
        self.logger.debug(
            f"Position opened event broadcasted: session_id={session_id}, "
            f"trade_number={trade_number}"
        )
        
        try:
            notification_service = NotificationService(db)
            await notification_service.create_notification(
                user_id=UUID(session_state.user_id),
                type="trade_executed",
                title=f"Trade executed • {session_state.asset.upper()}",
                message=(
                    f"{session_state.agent.name} opened {position.action.upper()} "
                    f"at ${position.entry_price:.2f}"
                ),
                session_id=UUID(session_id),
            )
        except Exception as exc:
            self.logger.warning("Failed to send trade notification: %s", exc)
    
    async def handle_position_closed(
        self,
        db: AsyncSession,
        session_id: str,
        session_state: Any,  # SessionState type (avoiding circular import)
        trade: Any,  # Trade from position_manager
        candle_index: int,
        timestamp: datetime
    ) -> None:
        """
        Handle position closed event.
        
        Updates trade in database and broadcasts event via WebSocket.
        
        Args:
            db: Database session
            session_id: Session identifier
            session_state: Session state object containing position manager
            trade: Closed trade data from position manager
            candle_index: Candle index at exit
            timestamp: Exit timestamp
        """
        self.logger.info(
            f"Position closed: session_id={session_id}, "
            f"action={trade.action}, exit_price={trade.exit_price}, "
            f"pnl={trade.pnl}, reason={trade.reason}"
        )
        
        # Map position manager reason to database exit_type
        # Database allows: 'take_profit', 'stop_loss', 'manual', 'signal'
        # Position manager uses: 'take_profit', 'stop_loss', 'ai_decision', 'manual'
        exit_type_map = {
            "take_profit": "take_profit",
            "stop_loss": "stop_loss",
            "manual": "manual",
            "ai_decision": "signal"  # Map AI decision to signal
        }
        db_exit_type = exit_type_map.get(trade.reason, "signal")
        
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
                exit_type=db_exit_type,
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
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": timestamp.isoformat(),
                "size": trade.size,
                "pnl": trade.pnl,
                "pnl_pct": trade.pnl_pct,
                "reason": trade.reason,
                "leverage": trade.leverage
            }
        )
        await self.websocket_manager.broadcast_to_session(session_id, event)
        
        self.logger.debug(
            f"Position closed event broadcasted: session_id={session_id}, "
            f"trade_number={trade_number}, pnl={trade.pnl}"
        )
