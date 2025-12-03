"""
Result Service for AlphaLab Trading Platform.

Purpose:
    Aggregate completed session performance and persist `TestResult`
    records with full trading analytics, equity curves, notifications,
    and agent/session stat updates.

Usage:
    service = ResultService(db_session)
    result = await service.create_result_from_session(session_id, stats, equity_points)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from statistics import pstdev
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent
from models.arena import TestSession, Trade
from models.result import TestResult
from models.activity import ActivityLog, Notification
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class ResultService:
    """
    Aggregates final stats for a completed `TestSession`.

    Responsibilities:
        - Derive metrics (PnL, drawdown, sharpe, profit factor, holding time)
        - Persist `TestResult` row
        - Update session runtime fields (elapsed time, open position)
        - Increment agent stats
        - Emit activity + notification rows
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_session(
        self,
        session_id: str,
        stats: Dict[str, Any],
        equity_curve: Optional[List[Dict[str, float]]] = None,
        ai_summary: Optional[str] = None,
        forced_stop: bool = False,
    ) -> UUID:
        """
        Build and persist a `TestResult` for a completed `TestSession`.

        Args:
            session_id: Finished test session identifier.
            stats: Aggregated stats from PositionManager.
            equity_curve: Optional per-candle equity samples.
            ai_summary: Optional AI-generated post mortem.
            forced_stop: Whether user stopped the run early.

        Returns:
            UUID of the newly created `TestResult`.
        """
        result = await self._calculate_and_persist(session_id, stats, equity_curve, ai_summary, forced_stop)
        await self.db.commit()
        logger.info("Created TestResult %s for session %s", result.id, session_id)
        return result.id

    async def _calculate_and_persist(
        self,
        session_id: str,
        stats: Dict[str, Any],
        equity_curve: Optional[List[Dict[str, float]]],
        ai_summary: Optional[str],
        forced_stop: bool,
    ) -> TestResult:
        session: TestSession = await self._get_session(session_id)
        trades: Sequence[Trade] = await self._get_trades(session_id)

        duration_seconds, duration_display = self._compute_duration(session)
        pnl_amount = Decimal(str(stats.get("total_pnl", 0.0)))
        pnl_pct = Decimal(str(stats.get("total_pnl_pct", 0.0)))
        current_equity = Decimal(str(stats.get("current_equity", float(session.starting_capital))))

        drawdown_pct, equity_points = self._derive_drawdown(equity_curve, float(session.starting_capital))
        sharpe_ratio = self._compute_sharpe(equity_points)
        profit_factor = self._compute_profit_factor(trades)
        holding_avg_seconds, holding_display = self._compute_average_holding(trades)
        best_trade, worst_trade = self._compute_best_worst_trade(trades)

        result = TestResult(
            session_id=session.id,
            user_id=session.user_id,
            agent_id=session.agent_id,
            type=session.type,
            asset=session.asset,
            mode=session.agent.mode if session.agent else "monk",
            timeframe=session.timeframe,
            start_date=datetime.combine(session.start_date, datetime.min.time(), tzinfo=timezone.utc)
            if session.start_date
            else session.started_at,
            end_date=datetime.combine(session.end_date, datetime.min.time(), tzinfo=timezone.utc)
            if session.end_date
            else session.completed_at,
            duration_seconds=duration_seconds,
            duration_display=duration_display,
            starting_capital=Decimal(str(session.starting_capital)),
            ending_capital=current_equity,
            total_pnl_amount=pnl_amount,
            total_pnl_pct=pnl_pct,
            total_trades=len(trades),
            winning_trades=sum(1 for t in trades if t.pnl_amount and t.pnl_amount > 0),
            losing_trades=sum(1 for t in trades if t.pnl_amount and t.pnl_amount <= 0),
            win_rate=Decimal(str(stats.get("win_rate", 0.0))),
            max_drawdown_pct=Decimal(str(drawdown_pct)) if drawdown_pct is not None else None,
            sharpe_ratio=Decimal(str(sharpe_ratio)) if sharpe_ratio is not None else None,
            profit_factor=Decimal(str(profit_factor)) if profit_factor is not None else None,
            avg_trade_pnl=(pnl_pct / len(trades)) if trades else None,
            best_trade_pnl=Decimal(str(best_trade)) if best_trade is not None else None,
            worst_trade_pnl=Decimal(str(worst_trade)) if worst_trade is not None else None,
            avg_holding_time_seconds=holding_avg_seconds,
            avg_holding_time_display=holding_display,
            equity_curve=self._truncate_equity_curve(equity_points),
            ai_summary=ai_summary,
        )

        self.db.add(result)
        await self._update_session_runtime(session.id, current_equity, pnl_pct)
        await self._update_agent_stats(session.agent_id, result)
        await self._log_completion(session, result, forced_stop)
        return result

    async def _get_session(self, session_id: str) -> TestSession:
        session = await self.db.scalar(
            select(TestSession)
            .where(TestSession.id == session_id)
            .options(selectinload(TestSession.agent))
        )
        if not session:
            raise ValueError(f"Session {session_id} not found for result aggregation")
        return session

    async def _get_trades(self, session_id: str) -> Sequence[Trade]:
        result = await self.db.execute(
            select(Trade).where(Trade.session_id == session_id).order_by(Trade.trade_number)
        )
        return result.scalars().all()

    async def _update_session_runtime(
        self,
        session_id: UUID,
        current_equity: Decimal,
        current_pnl_pct: Decimal,
    ) -> None:
        await self.db.execute(
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(
                current_equity=current_equity,
                current_pnl_pct=current_pnl_pct,
                status="completed",
                open_position=None,
            )
        )

    async def _update_agent_stats(self, agent_id: UUID, result: TestResult) -> None:
        if not agent_id:
            return
        await self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(
                tests_run=Agent.tests_run + 1,
                total_profitable_tests=Agent.total_profitable_tests + (1 if result.total_pnl_pct >= 0 else 0),
                best_pnl=func.greatest(Agent.best_pnl, result.total_pnl_pct),
                avg_drawdown=result.max_drawdown_pct
                if result.max_drawdown_pct is not None
                else Agent.avg_drawdown,
            )
        )

    async def _log_completion(
        self,
        session: TestSession,
        result: TestResult,
        forced_stop: bool,
    ) -> None:
        description = (
            f"{session.asset} {session.type} {'stopped early' if forced_stop else 'completed'} "
            f"with {result.total_pnl_pct}%"
        )
        activity = ActivityLog(
            user_id=session.user_id,
            agent_id=session.agent_id,
            session_id=session.id,
            result_id=result.id,
            activity_type="test_completed",
            description=description,
            activity_metadata={
                "asset": session.asset,
                "timeframe": session.timeframe,
                "pnl_pct": float(result.total_pnl_pct),
                "trades": result.total_trades,
            },
        )

        notification = Notification(
            user_id=session.user_id,
            session_id=session.id,
            result_id=result.id,
            type="test_completed",
            title=f"{session.asset} {session.type.title()} complete",
            message=description,
        )
        self.db.add_all([activity, notification])

    def _compute_duration(self, session: TestSession) -> Tuple[int, str]:
        if session.started_at and session.completed_at:
            diff = session.completed_at - session.started_at
        elif session.start_date and session.end_date:
            diff = datetime.combine(session.end_date, datetime.min.time()) - datetime.combine(
                session.start_date, datetime.min.time()
            )
        else:
            diff = session.updated_at - session.created_at
        seconds = max(int(diff.total_seconds()), 0)
        if seconds < 60:
            display = f"{seconds}s"
        elif seconds < 3600:
            display = f"{seconds // 60}m"
        else:
            display = f"{seconds // 3600}h"
        return seconds, display

    def _derive_drawdown(
        self,
        curve: Optional[List[Dict[str, float]]],
        starting_capital: float,
    ) -> Tuple[Optional[float], List[Dict[str, float]]]:
        if not curve:
            return None, []
        peak = starting_capital
        max_dd = 0.0
        computed = []
        for point in curve:
            equity = point.get("value") or starting_capital
            peak = max(peak, equity)
            dd = (equity - peak) / peak * 100 if peak > 0 else 0
            max_dd = min(max_dd, dd)
            computed.append(
                {
                    "time": point.get("time"),
                    "value": equity,
                    "drawdown": dd,
                }
            )
        return max_dd, computed

    def _truncate_equity_curve(self, curve: List[Dict[str, float]]) -> Optional[List[Dict[str, float]]]:
        if not curve:
            return None
        if len(curve) <= 500:
            return curve
        step = max(len(curve) // 500, 1)
        return curve[::step]

    def _compute_sharpe(self, curve: List[Dict[str, float]]) -> Optional[float]:
        if len(curve) < 2:
            return None
        returns = []
        for prev, curr in zip(curve[:-1], curve[1:]):
            prev_val = prev["value"]
            curr_val = curr["value"]
            if prev_val <= 0:
                continue
            returns.append((curr_val - prev_val) / prev_val)
        if not returns:
            return None
        mean_return = sum(returns) / len(returns)
        std_dev = pstdev(returns)
        if std_dev == 0:
            return None
        sharpe = (mean_return / std_dev) * (len(returns) ** 0.5)
        return round(sharpe, 3)

    def _compute_profit_factor(self, trades: Sequence[Trade]) -> Optional[float]:
        if not trades:
            return None
        gross_profit = sum(float(t.pnl_amount) for t in trades if t.pnl_amount and t.pnl_amount > 0)
        gross_loss = -sum(float(t.pnl_amount) for t in trades if t.pnl_amount and t.pnl_amount < 0)
        if gross_loss == 0:
            return None
        return round(gross_profit / gross_loss, 3)

    def _compute_average_holding(self, trades: Sequence[Trade]) -> Tuple[Optional[int], Optional[str]]:
        durations = [
            int((t.exit_time - t.entry_time).total_seconds())
            for t in trades
            if t.exit_time and t.entry_time
        ]
        if not durations:
            return None, None
        avg_seconds = sum(durations) // len(durations)
        if avg_seconds < 60:
            display = f"{avg_seconds}s"
        elif avg_seconds < 3600:
            display = f"{avg_seconds // 60}m"
        else:
            display = f"{avg_seconds // 3600}h"
        return avg_seconds, display

    def _compute_best_worst_trade(self, trades: Sequence[Trade]) -> Tuple[Optional[float], Optional[float]]:
        pnl_values = [float(t.pnl_pct) for t in trades if t.pnl_pct is not None]
        if not pnl_values:
            return None, None
        return max(pnl_values), min(pnl_values)

