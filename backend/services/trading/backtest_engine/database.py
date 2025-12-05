"""
Database operations for backtest engine.

Purpose:
    Handle all database update operations for backtest sessions,
    including status updates, timestamps, statistics, and AI thoughts.

Features:
    - Session status management
    - Timestamp tracking
    - Statistics updates
    - AI thought persistence
    - Transaction management

Usage:
    db_manager = DatabaseManager(websocket_manager)
    await db_manager.update_session_status(db, session_id, "running")
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from models.arena import TestSession, AiThought
from websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database operations for backtest sessions.
    
    Handles all database updates including session status, timestamps,
    statistics, and AI thought persistence.
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        """
        Initialize database manager.
        
        Args:
            websocket_manager: WebSocket manager for real-time updates
        """
        self.websocket_manager = websocket_manager
        self.logger = logging.getLogger(__name__)
    
    async def update_session_status(
        self,
        db: AsyncSession,
        session_id: str,
        status: str
    ) -> None:
        """
        Update session status in database.
        
        Args:
            db: Database session
            session_id: Session identifier
            status: New status value
        """
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(status=status)
        )
        await db.execute(stmt)
        await db.commit()
        self.logger.debug(f"Updated session {session_id} status to {status}")
    
    async def update_session_started_at(
        self,
        db: AsyncSession,
        session_id: str,
        started_at: datetime
    ) -> None:
        """
        Update session started_at timestamp in database.
        
        Args:
            db: Database session
            session_id: Session identifier
            started_at: Start timestamp
        """
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(started_at=started_at)
        )
        await db.execute(stmt)
        await db.commit()
        self.logger.debug(f"Updated session {session_id} started_at to {started_at}")
    
    async def update_session_total_candles(
        self,
        db: AsyncSession,
        session_id: str,
        total_candles: int
    ) -> None:
        """
        Update session total_candles in database.
        
        Args:
            db: Database session
            session_id: Session identifier
            total_candles: Total number of candles
        """
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(total_candles=total_candles)
        )
        await db.execute(stmt)
        await db.commit()
        self.logger.debug(f"Updated session {session_id} total_candles to {total_candles}")
    
    async def update_session_current_candle(
        self,
        db: AsyncSession,
        session_id: str,
        current_candle: int
    ) -> None:
        """
        Update session current_candle in database.
        
        Args:
            db: Database session
            session_id: Session identifier
            current_candle: Current candle index
        """
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(current_candle=current_candle)
        )
        await db.execute(stmt)
        await db.commit()
        self.logger.debug(f"Updated session {session_id} current_candle to {current_candle}")
    
    async def update_session_runtime_stats(
        self,
        db: AsyncSession,
        session_id: str,
        *,
        current_equity: float,
        current_pnl_pct: float,
        max_drawdown_pct: Optional[float] = None,
        elapsed_seconds: Optional[int] = None,
        open_position: Optional[dict] = None,
        current_candle: Optional[int] = None,
    ) -> None:
        """
        Persist runtime statistics for an active session.
        """
        values = {
            "current_equity": Decimal(str(current_equity)),
            "current_pnl_pct": Decimal(str(current_pnl_pct)),
        }
        if max_drawdown_pct is not None:
            values["max_drawdown_pct"] = Decimal(str(max_drawdown_pct))
        if elapsed_seconds is not None:
            values["elapsed_seconds"] = elapsed_seconds
        if open_position is not None:
            values["open_position"] = open_position
        if current_candle is not None:
            values["current_candle"] = current_candle
        
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(**values)
        )
        await db.execute(stmt)
        await db.commit()
    
    async def update_session_paused_at(
        self,
        db: AsyncSession,
        session_id: str,
        paused_at: datetime
    ) -> None:
        """
        Update session paused_at timestamp in database.
        
        Args:
            db: Database session
            session_id: Session identifier
            paused_at: Pause timestamp
        """
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(paused_at=paused_at)
        )
        await db.execute(stmt)
        await db.commit()
        self.logger.debug(f"Updated session {session_id} paused_at to {paused_at}")
    
    async def update_session_completed_at(
        self,
        db: AsyncSession,
        session_id: str,
        completed_at: datetime
    ) -> None:
        """
        Update session completed_at timestamp in database.
        
        Args:
            db: Database session
            session_id: Session identifier
            completed_at: Completion timestamp
        """
        stmt = (
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(completed_at=completed_at)
        )
        await db.execute(stmt)
        await db.commit()
        self.logger.debug(f"Updated session {session_id} completed_at to {completed_at}")
    
    async def update_session_final_stats(
        self,
        db: AsyncSession,
        session_id: str,
        current_equity: float,
        current_pnl_pct: float
    ) -> None:
        """
        Update session with final equity and PnL.
        
        Args:
            db: Database session
            session_id: Session identifier
            current_equity: Final equity value
            current_pnl_pct: Final PnL percentage
        """
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
        self.logger.debug(
            f"Updated session {session_id} final stats: "
            f"equity={current_equity}, pnl_pct={current_pnl_pct}"
        )
    
    async def save_ai_thoughts(
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
        self.logger.info(f"Saving {len(ai_thoughts)} AI thoughts for session {session_id}")
        
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
                order_data=thought.get("order_data"),
                # Persist council deliberation if present
                council_stage1=thought.get("council_stage1"),
                council_stage2=thought.get("council_stage2"),
                council_metadata=thought.get("council_metadata"),
            )
            db.add(ai_thought)
        
        await db.commit()
        
        self.logger.info(f"Saved AI thoughts for session {session_id}")
