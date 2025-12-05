
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple, Dict, List, Any, Set
from uuid import UUID
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, delete
from sqlalchemy.orm import selectinload

from database import get_db
from schemas.arena_schemas import (
    BacktestStartRequest, BacktestStartResponse, BacktestSessionResponse,
    BacktestStatusResponse, PauseResponse, ResumeResponse, StopRequest, StopResponse,
    OpenPosition, BacktestStatusWrapper,
    ForwardStartRequest, ForwardStartResponse, ForwardSessionResponse,
    ForwardActiveSession, ForwardActiveListResponse, ForwardStatusWrapper, ForwardStopResponse
)
from schemas.data_schemas import CandleSchema
from models.agent import Agent
from models.arena import TestSession, Trade
from models.result import TestResult
from services.trading.backtest_engine import BacktestEngine
from services.trading.forward_engine import ForwardEngine
from services.trading.engine_factory import get_backtest_engine, get_forward_engine
from services.market_data_service import MarketDataService
from services.notification_service import NotificationService
from config import settings
from api.users import get_current_user
from exceptions import ValidationError

router = APIRouter(prefix="/api/arena", tags=["arena"])
logger = logging.getLogger(__name__)


@router.post("/forward/{id}/stop", response_model=ForwardStopResponse)
async def stop_forward_test(
    id: UUID,
    request: StopRequest,
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine),
    db: AsyncSession = Depends(get_db)
):
    """Stop a forward test."""
    session_stmt = await db.execute(
        select(TestSession).where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    session = session_stmt.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        result_id, position_closed = await engine.stop_forward_test(str(id), close_position=request.close_position)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    final_pnl = None
    if result_id:
        result_stmt = await db.execute(
            select(TestResult).where(TestResult.id == result_id)
        )
        test_result = result_stmt.scalar_one_or_none()
        if test_result:
            final_pnl = float(test_result.total_pnl_pct)
    
    return {
        "session_id": id,
        "status": "completed",
        "result_id": result_id,
        "final_pnl": final_pnl,
        "position_closed": position_closed
    }


@router.post("/forward/{id}/pause", response_model=PauseResponse)
async def pause_forward_test(
    id: UUID,
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine),
    db: AsyncSession = Depends(get_db)
):
    """Pause a forward test."""
    session_stmt = await db.execute(
        select(TestSession).where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    session = session_stmt.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await engine.pause_forward_test(str(id))
    return PauseResponse(
        session_id=id,
        status="paused",
        paused_at=datetime.now(timezone.utc)
    )


@router.post("/forward/{id}/resume", response_model=ResumeResponse)
async def resume_forward_test(
    id: UUID,
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine),
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused forward test."""
    session_stmt = await db.execute(
        select(TestSession).where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    session = session_stmt.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await engine.resume_forward_test(str(id))
    return ResumeResponse(
        session_id=id,
        status="running"
    )

@router.post("/forward/{id}/pause", response_model=PauseResponse)
async def pause_forward_test(
    id: UUID,
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine),
    db: AsyncSession = Depends(get_db)
):
    """Pause a forward test."""
    session_stmt = await db.execute(
        select(TestSession).where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    session = session_stmt.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        await engine.pause_forward_test(str(id))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "session_id": id,
        "status": "paused",
        "paused_at": datetime.now(timezone.utc)
    }

@router.post("/forward/{id}/resume", response_model=ResumeResponse)
async def resume_forward_test(
    id: UUID,
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine),
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused forward test."""
    session_stmt = await db.execute(
        select(TestSession).where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    session = session_stmt.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        await engine.resume_forward_test(str(id))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "session_id": id,
        "status": "running"
    }
@router.get("/forward/active", response_model=ForwardActiveListResponse)
async def get_forward_active_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine),
    agent_id: Optional[UUID] = None,
    statuses: Optional[List[str]] = Query(
        None,
        description="Filter by status (running, paused, initializing)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of sessions to return"),
):
    """List active forward sessions - optimized with batched queries and stale session filtering."""
    sessions: List[ForwardActiveSession] = []
    seen_ids: Set[UUID] = set()
    now = datetime.now(timezone.utc)
    STALE_THRESHOLD_HOURS = 2  # Sessions running > 2 hours with 0 trades are considered stale
    
    # Collect in-memory sessions first (fast, no DB query) - these are definitely active
    for session_id_str, state in engine.active_sessions.items():
        if state.agent.user_id != current_user.id:
            continue
        if agent_id and state.agent.id != agent_id:
            continue
        session_uuid = UUID(session_id_str)
        stats = state.position_manager.get_stats()
        started_at = state.started_at or now
        elapsed_seconds = int((now - started_at).total_seconds())
        elapsed_hours = elapsed_seconds / 3600
        status_value = "running" if not state.is_paused else "paused"
        
        if statuses and status_value not in statuses:
            continue
        
        # Filter out stale in-memory sessions (running > 2h with 0 trades)
        if stats["total_trades"] == 0 and elapsed_hours > STALE_THRESHOLD_HOURS:
            continue
        
        sessions.append(
            ForwardActiveSession(
                id=session_uuid,
                agent_id=state.agent.id,
                agent_name=state.agent.name,
                asset=state.asset,
                status=status_value,
                started_at=started_at,
                duration_display=_format_duration(elapsed_seconds),
                current_pnl_pct=stats["equity_change_pct"],
                trades_count=stats["total_trades"],
                win_rate=stats["win_rate"]
            )
        )
        seen_ids.add(session_uuid)
    
    # Build optimized DB query - single query with join instead of multiple
    # Filter out sessions that are too old and have no trades
    base_query = (
        select(TestSession, Agent)
        .join(Agent, Agent.id == TestSession.agent_id)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.type == "forward")
    )
    if statuses:
        base_query = base_query.where(TestSession.status.in_(tuple(statuses)))
    else:
        base_query = base_query.where(TestSession.status.in_(("running", "paused", "initializing")))
    if agent_id:
        base_query = base_query.where(TestSession.agent_id == agent_id)
    
    # Order by most recent first, then limit
    base_query = base_query.order_by(TestSession.started_at.desc().nulls_last(), TestSession.created_at.desc())
    
    # Execute single query
    db_result = await db.execute(base_query)
    rows = db_result.all()
    
    # Batch collect session IDs for trade stats (only for DB sessions not in memory)
    db_session_ids = [row[0].id for row in rows if row[0].id not in seen_ids]
    
    # Single batched query for all trade stats (instead of per-session)
    trade_stats = await _get_trade_stats(db, db_session_ids) if db_session_ids else {}
    
    # Process DB sessions with stale filtering
    for session, agent in rows:
        if session.id in seen_ids:
            continue
        
        # Skip if we've reached the limit
        if len(sessions) >= limit:
            break
        
        duration_seconds = session.elapsed_seconds or 0
        if not duration_seconds and session.started_at:
            duration_seconds = int((now - session.started_at).total_seconds())
        
        duration_hours = duration_seconds / 3600
        trades_count, win_rate = trade_stats.get(session.id, (0, 0.0))
        
        # Filter out stale sessions: running > 2 hours with 0 trades
        # Also filter out sessions with invalid agent names
        if trades_count == 0 and duration_hours > STALE_THRESHOLD_HOURS:
            continue
        
        agent_name = agent.name if agent else "Unknown Agent"
        if not agent_name or len(agent_name.strip()) < 2:
            continue
        
        sessions.append(
            ForwardActiveSession(
                id=session.id,
                agent_id=session.agent_id,
                agent_name=agent_name,
                asset=session.asset,
                status=session.status,
                started_at=session.started_at or session.created_at,
                duration_display=_format_duration(duration_seconds),
                current_pnl_pct=float(session.current_pnl_pct or 0),
                trades_count=trades_count,
                win_rate=win_rate
            )
        )
    
    # Sort final results: sessions with trades first, then by most recent
    def sort_key(s: ForwardActiveSession) -> tuple:
        # Primary: sessions with trades come first (False < True, so trades first)
        has_trades = s.trades_count == 0
        # Secondary: most recent first (negative timestamp for descending)
        timestamp = 0
        if s.started_at:
            if isinstance(s.started_at, datetime):
                timestamp = s.started_at.timestamp()
            elif hasattr(s.started_at, 'timestamp'):
                timestamp = s.started_at.timestamp()
        return (has_trades, -timestamp)
    
    sessions.sort(key=sort_key)
    
    # Apply limit after sorting
    sessions = sessions[:limit]
    
    return {"sessions": sessions}


@router.get("/backtest/active", response_model=ForwardActiveListResponse)
async def get_backtest_active_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: BacktestEngine = Depends(get_backtest_engine),
    agent_id: Optional[UUID] = None,
    statuses: Optional[List[str]] = Query(
        None,
        description="Filter by status (running, paused, initializing)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of sessions to return"),
):
    """List active backtest sessions - optimized with batched queries and stale session filtering."""
    sessions: List[ForwardActiveSession] = []
    seen_ids: Set[UUID] = set()
    now = datetime.now(timezone.utc)
    STALE_THRESHOLD_HOURS = 2  # Sessions running > 2 hours with 0 trades are considered stale
    
    # Collect in-memory sessions first (fast, no DB query) - these are definitely active
    for session_id_str, state in engine.active_sessions.items():
        if state.agent.user_id != current_user.id:
            continue
        if agent_id and state.agent.id != agent_id:
            continue
        session_uuid = UUID(session_id_str)
        stats = state.position_manager.get_stats()
        started_at = state.started_at or now
        elapsed_seconds = int((now - started_at).total_seconds())
        elapsed_hours = elapsed_seconds / 3600
        status_value = "running" if not state.is_paused else "paused"
        
        if statuses and status_value not in statuses:
            continue
        
        # Filter out stale in-memory sessions (running > 2h with 0 trades)
        if stats["total_trades"] == 0 and elapsed_hours > STALE_THRESHOLD_HOURS:
            continue
        
        sessions.append(
            ForwardActiveSession(
                id=session_uuid,
                agent_id=state.agent.id,
                agent_name=state.agent.name,
                asset=state.asset,
                status=status_value,
                started_at=started_at,
                duration_display=_format_duration(elapsed_seconds),
                current_pnl_pct=stats["equity_change_pct"],
                trades_count=stats["total_trades"],
                win_rate=stats["win_rate"]
            )
        )
        seen_ids.add(session_uuid)
    
    # Build optimized DB query - single query with join instead of multiple
    # Filter out sessions that are too old and have no trades
    base_query = (
        select(TestSession, Agent)
        .join(Agent, Agent.id == TestSession.agent_id)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.type == "backtest")
    )
    if statuses:
        base_query = base_query.where(TestSession.status.in_(tuple(statuses)))
    else:
        base_query = base_query.where(TestSession.status.in_(("running", "paused", "initializing")))
    if agent_id:
        base_query = base_query.where(TestSession.agent_id == agent_id)
    
    # Order by most recent first, then limit
    base_query = base_query.order_by(TestSession.started_at.desc().nulls_last(), TestSession.created_at.desc())
    
    # Execute single query
    db_result = await db.execute(base_query)
    rows = db_result.all()
    
    # Batch collect session IDs for trade stats (only for DB sessions not in memory)
    db_session_ids = [row[0].id for row in rows if row[0].id not in seen_ids]
    
    # Single batched query for all trade stats (instead of per-session)
    trade_stats = await _get_trade_stats(db, db_session_ids) if db_session_ids else {}
    
    # Process DB sessions with stale filtering
    for session, agent in rows:
        if session.id in seen_ids:
            continue
        
        # Skip if we've reached the limit
        if len(sessions) >= limit:
            break
        
        duration_seconds = session.elapsed_seconds or 0
        if not duration_seconds and session.started_at:
            duration_seconds = int((now - session.started_at).total_seconds())
        
        duration_hours = duration_seconds / 3600
        trades_count, win_rate = trade_stats.get(session.id, (0, 0.0))
        
        # Filter out stale sessions: running > 2 hours with 0 trades
        # Also filter out sessions with invalid agent names
        if trades_count == 0 and duration_hours > STALE_THRESHOLD_HOURS:
            continue
        
        agent_name = agent.name if agent else "Unknown Agent"
        if not agent_name or len(agent_name.strip()) < 2:
            continue
        
        sessions.append(
            ForwardActiveSession(
                id=session.id,
                agent_id=session.agent_id,
                agent_name=agent_name,
                asset=session.asset,
                status=session.status,
                started_at=session.started_at or session.created_at,
                duration_display=_format_duration(duration_seconds),
                current_pnl_pct=float(session.current_pnl_pct or 0),
                trades_count=trades_count,
                win_rate=win_rate
            )
        )
    
    # Sort final results: sessions with trades first, then by most recent
    def sort_key(s: ForwardActiveSession) -> tuple:
        # Primary: sessions with trades come first (False < True, so trades first)
        has_trades = s.trades_count == 0
        # Secondary: most recent first (negative timestamp for descending)
        timestamp = 0
        if s.started_at:
            if isinstance(s.started_at, datetime):
                timestamp = s.started_at.timestamp()
            elif hasattr(s.started_at, 'timestamp'):
                timestamp = s.started_at.timestamp()
        return (has_trades, -timestamp)
    
    sessions.sort(key=sort_key)
    
    # Apply limit after sorting
    sessions = sessions[:limit]
    
    return {"sessions": sessions}


@router.get("/forward/{id}", response_model=ForwardStatusWrapper)
async def get_forward_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine)
):
    """Get status for a forward session - optimized with single query."""
    session_state = engine.active_sessions.get(str(id))
    now = datetime.now(timezone.utc)
    
    # Fast path: session is in memory (no DB query)
    if session_state and session_state.agent.user_id == current_user.id:
        stats = session_state.position_manager.get_stats()
        open_pos = _serialize_open_position(session_state.position_manager.get_position())
        if session_state.started_at:
            # Ensure both datetimes are timezone-aware for comparison
            started_at = session_state.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed_seconds = int((now - started_at).total_seconds())
        else:
            elapsed_seconds = 0
        next_eta = None
        if session_state.next_candle_time:
            # Ensure both datetimes are timezone-aware for comparison
            next_candle_time = session_state.next_candle_time
            if next_candle_time.tzinfo is None:
                next_candle_time = next_candle_time.replace(tzinfo=timezone.utc)
            next_eta = max(0, int((next_candle_time - now).total_seconds()))
        return {
            "session": {
                "id": id,
                "status": "running" if not session_state.is_paused else "paused",
                "started_at": session_state.started_at,
                "elapsed_seconds": elapsed_seconds,
                "asset": session_state.asset,
                "timeframe": session_state.timeframe,
                "current_equity": stats["current_equity"],
                "current_pnl_pct": stats["equity_change_pct"],
                "max_drawdown_pct": session_state.max_drawdown_pct,
                "trades_count": stats["total_trades"],
                "win_rate": stats["win_rate"],
                "next_candle_eta": next_eta,
                "open_position": open_pos
            }
        }
    
    # Slow path: fetch from DB - optimized single query with joins
    result = await db.execute(
        select(TestSession, TestResult)
        .outerjoin(TestResult, TestResult.session_id == TestSession.id)
        .where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session, test_result = row
    
    if test_result:
        current_equity = float(test_result.ending_capital)
        pnl_pct = float(test_result.total_pnl_pct)
        trades_count = test_result.total_trades
        win_rate = float(test_result.win_rate or 0)
        max_drawdown = float(test_result.max_drawdown_pct or 0)
    else:
        current_equity = float(session.current_equity or session.starting_capital)
        pnl_pct = float(session.current_pnl_pct or 0)
        # Only fetch trade stats if test_result doesn't exist
        stats_map = await _get_trade_stats(db, [session.id])
        trades_count, win_rate = stats_map.get(session.id, (0, 0.0))
        max_drawdown = float(session.max_drawdown_pct or 0)
    
    elapsed_seconds = session.elapsed_seconds or 0
    if not elapsed_seconds and session.started_at:
        # Ensure both datetimes are timezone-aware for comparison
        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = int((now - started_at).total_seconds())
    
    open_position = _open_position_from_dict(session.open_position)
    
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "started_at": session.started_at,
            "elapsed_seconds": elapsed_seconds,
            "asset": session.asset,
            "timeframe": session.timeframe,
            "current_equity": current_equity,
            "current_pnl_pct": pnl_pct,
            "max_drawdown_pct": max_drawdown,
            "trades_count": trades_count,
            "win_rate": win_rate,
            "next_candle_eta": None,
            "open_position": open_position
        }
    }
# Historical presets (UTC)
_DATE_PRESET_MAP = {
    "bull": (datetime(2023, 10, 1), datetime(2024, 3, 31)),
    "crash": (datetime(2022, 11, 1), datetime(2023, 1, 31)),
}


def _resolve_date_preset(preset: str) -> Tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if preset == "7d":
        return now - timedelta(days=7), now
    if preset == "30d":
        return now - timedelta(days=30), now
    if preset == "90d":
        return now - timedelta(days=90), now
    if preset in _DATE_PRESET_MAP:
        return _DATE_PRESET_MAP[preset]
    return now - timedelta(days=30), now


def _serialize_open_position(position) -> Optional[OpenPosition]:
    if not position:
        return None
    return OpenPosition(
        type=position.action,
        entry_price=position.entry_price,
        unrealized_pnl=position.unrealized_pnl
    )


def _open_position_from_dict(data: Optional[Dict[str, Any]]) -> Optional[OpenPosition]:
    if not data:
        return None
    position_type = data.get("type") or data.get("action")
    if not position_type:
        return None
    entry_price = float(data.get("entry_price", 0.0))
    unrealized = float(data.get("unrealized_pnl", 0.0))
    return OpenPosition(
        type=position_type,
        entry_price=entry_price,
        unrealized_pnl=unrealized
    )


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _build_ws_url(path: str) -> str:
    base = settings.WEBSOCKET_BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


async def _get_trade_stats(db: AsyncSession, session_ids: List[UUID]) -> Dict[UUID, Tuple[int, float]]:
    if not session_ids:
        return {}
    result = await db.execute(
        select(
            Trade.session_id,
            func.count(Trade.id),
            func.sum(case((Trade.pnl_amount > 0, 1), else_=0))
        )
        .where(Trade.session_id.in_(session_ids))
        .group_by(Trade.session_id)
    )
    stats: Dict[UUID, Tuple[int, float]] = {}
    for session_id, total, wins in result:
        total_trades = int(total or 0)
        win_rate = (float(wins or 0) / total_trades * 100) if total_trades else 0.0
        stats[session_id] = (total_trades, win_rate)
    return stats

@router.post("/backtest/start", response_model=BacktestStartResponse)
async def start_backtest(
    request: BacktestStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: BacktestEngine = Depends(get_backtest_engine)
):
    """Start a new backtest session."""
    # Check for existing active backtests
    # Check both in-memory sessions and database
    in_memory_sessions = [
        (session_id, state) 
        for session_id, state in engine.active_sessions.items()
        if state.agent.user_id == current_user.id
    ]
    active_in_memory = len(in_memory_sessions) > 0
    
    if active_in_memory:
        logger.info(f"Found {len(in_memory_sessions)} active backtest sessions in memory for user {current_user.id}")
        for session_id, state in in_memory_sessions:
            logger.info(f"In-memory session {session_id}: agent={state.agent.name}, paused={state.is_paused}")
    
    # First, clean up stale "initializing" sessions (stuck for more than 5 minutes)
    # If a session is "initializing" but not in-memory, it's likely stuck
    stale_init_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    stale_init_sessions_result = await db.execute(
        select(TestSession)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.type == "backtest")
        .where(TestSession.status == "initializing")
        .where(TestSession.created_at < stale_init_threshold)
    )
    stale_init_sessions = stale_init_sessions_result.scalars().all()
    
    # Also check for "initializing" sessions that aren't in-memory (definitely stuck)
    in_memory_session_ids = {UUID(sid) for sid in engine.active_sessions.keys()}
    stuck_init_sessions = [
        s for s in stale_init_sessions 
        if s.id not in in_memory_session_ids
    ]
    
    if stuck_init_sessions:
        logger.info(f"Cleaning up {len(stuck_init_sessions)} stuck initializing backtest sessions (not in-memory) for user {current_user.id}")
        for stale_session in stuck_init_sessions:
            await db.execute(
                delete(TestSession).where(TestSession.id == stale_session.id)
            )
        await db.commit()
    
    # Now check for active sessions (running, paused, or recent initializing)
    # We need to filter out stale sessions (running > 2 hours with 0 trades)
    STALE_THRESHOLD_HOURS = 2
    now = datetime.now(timezone.utc)
    
    active_sessions_result = await db.execute(
        select(TestSession)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.type == "backtest")
        .where(TestSession.status.in_(("running", "paused", "initializing")))
    )
    active_sessions = active_sessions_result.scalars().all()
    
    logger.info(f"Found {len(active_sessions)} active backtest sessions in DB for user {current_user.id}")
    
    # Get trade stats for all active sessions to check if they're stale
    if active_sessions:
        session_ids = [s.id for s in active_sessions]
        trade_stats = await _get_trade_stats(db, session_ids)
        
        # Filter out stale sessions and clean them up
        stale_sessions_to_clean = []
        non_stale_sessions = []
        
        for session in active_sessions:
            trades_count, _ = trade_stats.get(session.id, (0, 0.0))
            
            # Calculate duration
            duration_seconds = session.elapsed_seconds or 0
            if not duration_seconds and session.started_at:
                duration_seconds = int((now - session.started_at).total_seconds())
            elif not duration_seconds and session.created_at:
                duration_seconds = int((now - session.created_at).total_seconds())
            
            duration_hours = duration_seconds / 3600
            
            # Mark as stale if: running/paused > 2 hours with 0 trades, or initializing > 5 minutes
            # Also mark as stale if running but stuck (no progress for > 30 minutes)
            # If initializing and not in-memory, it's definitely stuck
            is_stale = False
            if session.status == "initializing":
                # Initializing sessions are stale if:
                # 1. > 5 minutes old, OR
                # 2. Not in-memory (definitely stuck)
                is_stale = duration_seconds > 300 or session.id not in in_memory_session_ids  # 5 minutes
            elif session.status == "running":
                # Running sessions are stale if:
                # 1. > 2 hours with 0 trades, OR
                # 2. Stuck (current_candle is 0 or None and running > 30 minutes)
                current_candle = session.current_candle or 0
                is_stuck = current_candle == 0 and duration_seconds > 1800  # 30 minutes
                is_stale = (trades_count == 0 and duration_hours > STALE_THRESHOLD_HOURS) or is_stuck
            else:  # paused
                # Paused sessions are stale if > 2 hours with 0 trades
                is_stale = trades_count == 0 and duration_hours > STALE_THRESHOLD_HOURS
            
            logger.info(
                f"Session {session.id}: status={session.status}, "
                f"trades={trades_count}, duration={duration_hours:.2f}h, "
                f"current_candle={session.current_candle}, is_stale={is_stale}"
            )
            
            if is_stale:
                stale_sessions_to_clean.append(session)
            else:
                non_stale_sessions.append(session)
        
        # Clean up stale sessions
        if stale_sessions_to_clean:
            logger.info(f"Cleaning up {len(stale_sessions_to_clean)} stale backtest sessions for user {current_user.id}")
            for stale_session in stale_sessions_to_clean:
                await db.execute(
                    delete(TestSession).where(TestSession.id == stale_session.id)
                )
            await db.commit()
        
        # Only consider non-stale sessions as active
        active_in_db = len(non_stale_sessions) > 0
        logger.info(f"After cleanup: {len(non_stale_sessions)} non-stale sessions, active_in_db={active_in_db}")
    else:
        active_in_db = False
        logger.info("No active sessions found in DB")
    
    logger.info(f"Final check: active_in_memory={active_in_memory}, active_in_db={active_in_db}")
    
    if active_in_memory or active_in_db:
        raise HTTPException(
            status_code=400,
            detail="You already have an active backtest. Please stop the existing test before starting a new one."
        )
    
    # Verify agent exists and belongs to user
    # Eagerly load api_key relationship to avoid lazy loading issues in background task
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.api_key))
        .where(Agent.id == request.agent_id, Agent.user_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Extract agent values before any commits to avoid lazy loading issues
    agent_id = agent.id
    agent_name = agent.name

    # Create session record
    session_id = uuid.uuid4()
    
    # Calculate dates if preset is used
    start_date_input = request.start_date
    end_date_input = request.end_date
    
    if request.date_preset and request.date_preset != 'custom':
        start_date_input, end_date_input = _resolve_date_preset(request.date_preset)
            
    if not start_date_input or not end_date_input:
        raise HTTPException(status_code=400, detail="Start and end dates required")
    
    if isinstance(start_date_input, datetime):
        start_dt = start_date_input
        # Ensure timezone-aware (UTC)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
    else:
        start_dt = datetime.combine(start_date_input, datetime.min.time(), tzinfo=timezone.utc)
    
    if isinstance(end_date_input, datetime):
        end_dt = end_date_input
        # Ensure timezone-aware (UTC)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
    else:
        end_dt = datetime.combine(end_date_input, datetime.min.time(), tzinfo=timezone.utc)
    
    start_date = start_dt.date()
    end_date = end_dt.date()

    # Create TestSession in DB
    test_session = TestSession(
        id=session_id,
        user_id=current_user.id,
        agent_id=agent_id,
        type="backtest",
        status="initializing",
        asset=request.asset,
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date,
        starting_capital=Decimal(str(request.starting_capital)),
        playback_speed=request.playback_speed,
        decision_mode=request.decision_mode,
        decision_interval_candles=request.decision_interval_candles,
        date_preset=request.date_preset,
        safety_mode=request.safety_mode,
        allow_leverage=request.allow_leverage,
        current_equity=Decimal(str(request.starting_capital)),
        created_at=datetime.now(timezone.utc)
    )
    db.add(test_session)
    await db.commit()

    notification_service = NotificationService(db)
    try:
        await notification_service.create_notification(
            user_id=current_user.id,
            type="test_started",
            title=f"Backtest started • {request.asset.upper()}",
            message=f"{agent_name} is testing {request.asset.upper()} on {request.timeframe}",
            session_id=session_id,
        )
    except Exception as exc:
        # Don't block backtest start on notification errors
        logger.warning("Failed to create test start notification: %s", exc)

    # Start backtest in background
    # We use background_tasks to trigger the engine's start method
    # The engine will handle its own background task for the loop
    background_tasks.add_task(
        engine.start_backtest,
        session_id=str(session_id),
        agent=agent,
        asset=request.asset,
        timeframe=request.timeframe,
        start_date=start_dt,
        end_date=end_dt,
        starting_capital=request.starting_capital,
        safety_mode=request.safety_mode,
        allow_leverage=request.allow_leverage,
        playback_speed=request.playback_speed,
        decision_mode=request.decision_mode,
        decision_interval_candles=request.decision_interval_candles,
        indicator_readiness_threshold=request.indicator_readiness_threshold or 80.0,
        user_id=str(current_user.id),
    )

    preview_candles = None
    try:
        market_data_service = MarketDataService(db)
        preview_raw = await market_data_service.get_historical_data(
            asset=request.asset,
            timeframe=request.timeframe,
            start_date=start_dt,
            end_date=end_dt
        )
        preview_limit = min(500, len(preview_raw))
        if preview_limit:
            preview_candles = [
                CandleSchema(
                    timestamp=c.timestamp,
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    volume=c.volume,
                )
                for c in preview_raw[:preview_limit]
            ]
    except Exception as exc:
        logger.warning("Unable to load preview candles for session %s: %s", session_id, exc)
        preview_candles = None

    return {
        "session": BacktestSessionResponse(
            id=session_id,
            status="initializing",
            agent_id=agent_id,
            agent_name=agent_name,
            asset=request.asset,
            timeframe=request.timeframe,
            total_candles=0,
            websocket_url=_build_ws_url(f"/ws/backtest/{session_id}"),
            date_preset=request.date_preset,
            playback_speed=request.playback_speed,
            decision_mode=request.decision_mode,
            decision_interval_candles=request.decision_interval_candles,
            safety_mode=request.safety_mode,
            allow_leverage=request.allow_leverage,
            preview_candles=preview_candles,
        ),
        "message": "Backtest session created"
    }

@router.get("/backtest/{id}", response_model=BacktestStatusWrapper)
async def get_backtest_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: BacktestEngine = Depends(get_backtest_engine)
):
    """Get backtest session status - optimized with single query."""
    # Check active sessions first (in memory - fastest path)
    session_id_str = str(id)
    session_state = engine.active_sessions.get(session_id_str)
    
    if session_state:
        # Return real-time state (no DB query needed)
        stats = session_state.position_manager.get_stats()
        current_equity = stats["current_equity"]
        pnl_pct = stats["equity_change_pct"]
        open_pos = session_state.position_manager.get_position()
        open_pos_data = _serialize_open_position(open_pos)
        elapsed_seconds = 0
        if session_state.started_at:
            # Ensure started_at is timezone-aware (UTC)
            started_at = session_state.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())
        progress_pct = (
            (session_state.current_index / len(session_state.candles)) * 100
            if session_state.candles else 0
        )
        return {
            "session": {
                "id": id,
                "status": "running" if not session_state.is_paused else "paused",
                "agent_id": session_state.agent.id,
                "agent_name": session_state.agent.name,
                "asset": session_state.asset if hasattr(session_state, 'asset') else None,
                "timeframe": session_state.timeframe if hasattr(session_state, 'timeframe') else None,
                "current_candle": session_state.current_index,
                "total_candles": len(session_state.candles),
                "progress_pct": progress_pct,
                "elapsed_seconds": elapsed_seconds,
                "current_equity": current_equity,
                "current_pnl_pct": pnl_pct,
                "max_drawdown_pct": session_state.max_drawdown_pct,
                "trades_count": stats["total_trades"],
                "win_rate": stats["win_rate"],
                "open_position": open_pos_data
            }
        }
    
    # If not active, fetch from DB - optimized single query with join
    result = await db.execute(
        select(TestSession, TestResult, Agent)
        .outerjoin(TestResult, TestResult.session_id == TestSession.id)
        .outerjoin(Agent, Agent.id == TestSession.agent_id)
        .where(TestSession.id == id, TestSession.user_id == current_user.id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session, test_result, agent = row
    
    # Use test_result if available, otherwise fall back to session
    if test_result:
        current_equity = float(test_result.ending_capital)
        pnl_pct = float(test_result.total_pnl_pct)
        trades_count = test_result.total_trades
        win_rate = float(test_result.win_rate or 0)
        max_drawdown_pct = float(test_result.max_drawdown_pct or 0)
    else:
        current_equity = float(session.current_equity or session.starting_capital)
        pnl_pct = float(session.current_pnl_pct or 0)
        max_drawdown_pct = float(session.max_drawdown_pct or 0)
        trades_count = 0
        win_rate = 0.0
    
    open_position = _open_position_from_dict(session.open_position)
    
    progress_pct = 0.0
    if session.total_candles:
        progress_pct = min(100.0, (session.current_candle or 0) / session.total_candles * 100)
    if session.status == "completed":
        progress_pct = 100.0
    
    elapsed_seconds = session.elapsed_seconds or 0
    if not elapsed_seconds and session.started_at and session.completed_at:
        elapsed_seconds = int((session.completed_at - session.started_at).total_seconds())
    
    # Get agent info
    agent_id = session.agent_id
    agent_name = agent.name if agent else None
    
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "asset": session.asset,
            "current_candle": session.current_candle or 0,
            "total_candles": session.total_candles or 0,
            "progress_pct": progress_pct,
            "elapsed_seconds": elapsed_seconds,
            "current_equity": current_equity,
            "current_pnl_pct": pnl_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "trades_count": trades_count,
            "win_rate": win_rate,
            "open_position": open_position
        }
    }

@router.post("/backtest/{id}/pause", response_model=PauseResponse)
async def pause_backtest(
    id: UUID,
    current_user: dict = Depends(get_current_user),
    engine: BacktestEngine = Depends(get_backtest_engine)
):
    """Pause running backtest."""
    try:
        await engine.pause_backtest(str(id))
        return {
            "session_id": id,
            "status": "paused",
            "paused_at": datetime.now(timezone.utc)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/backtest/{id}/resume", response_model=ResumeResponse)
async def resume_backtest(
    id: UUID,
    current_user: dict = Depends(get_current_user),
    engine: BacktestEngine = Depends(get_backtest_engine)
):
    """Resume paused backtest."""
    try:
        await engine.resume_backtest(str(id))
        return {
            "session_id": id,
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/backtest/{id}/stop", response_model=StopResponse)
async def stop_backtest(
    id: UUID,
    request: StopRequest,
    current_user: dict = Depends(get_current_user),
    engine: BacktestEngine = Depends(get_backtest_engine),
    db: AsyncSession = Depends(get_db)
):
    """Stop backtest."""
    try:
        result_id = await engine.stop_backtest(str(id), close_position=request.close_position)
        final_pnl = None
        if result_id:
            result_stmt = await db.execute(
                select(TestResult).where(TestResult.id == result_id)
            )
            test_result = result_stmt.scalar_one_or_none()
            if test_result:
                final_pnl = float(test_result.total_pnl_pct)
        return {
            "session_id": id,
            "status": "completed",
            "result_id": result_id,
            "final_pnl": final_pnl
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forward/start", response_model=ForwardStartResponse)
async def start_forward_test(
    request: ForwardStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine)
):
    """Start a new forward test session."""
    # Check for existing active forward tests
    # Check both in-memory sessions and database
    active_in_memory = any(
        state.agent.user_id == current_user.id
        for state in engine.active_sessions.values()
    )
    
    # First, clean up stale "initializing" sessions (stuck for more than 5 minutes)
    # If a session is "initializing" but not in-memory, it's likely stuck
    stale_init_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    stale_init_sessions_result = await db.execute(
        select(TestSession)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.type == "forward")
        .where(TestSession.status == "initializing")
        .where(TestSession.created_at < stale_init_threshold)
    )
    stale_init_sessions = stale_init_sessions_result.scalars().all()
    
    # Also check for "initializing" sessions that aren't in-memory (definitely stuck)
    in_memory_session_ids = {UUID(sid) for sid in engine.active_sessions.keys()}
    stuck_init_sessions = [
        s for s in stale_init_sessions 
        if s.id not in in_memory_session_ids
    ]
    
    if stuck_init_sessions:
        logger.info(f"Cleaning up {len(stuck_init_sessions)} stuck initializing forward test sessions (not in-memory) for user {current_user.id}")
        for stale_session in stuck_init_sessions:
            await db.execute(
                delete(TestSession).where(TestSession.id == stale_session.id)
            )
        await db.commit()
    
    # Now check for active sessions (running, paused, or recent initializing)
    # We need to filter out stale sessions (running > 2 hours with 0 trades)
    STALE_THRESHOLD_HOURS = 2
    now = datetime.now(timezone.utc)
    
    active_sessions_result = await db.execute(
        select(TestSession)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.type == "forward")
        .where(TestSession.status.in_(("running", "paused", "initializing")))
    )
    active_sessions = active_sessions_result.scalars().all()
    
    # Get trade stats for all active sessions to check if they're stale
    if active_sessions:
        session_ids = [s.id for s in active_sessions]
        trade_stats = await _get_trade_stats(db, session_ids)
        
        # Filter out stale sessions and clean them up
        stale_sessions_to_clean = []
        non_stale_sessions = []
        
        for session in active_sessions:
            trades_count, _ = trade_stats.get(session.id, (0, 0.0))
            
            # Calculate duration
            duration_seconds = session.elapsed_seconds or 0
            if not duration_seconds and session.started_at:
                duration_seconds = int((now - session.started_at).total_seconds())
            elif not duration_seconds and session.created_at:
                duration_seconds = int((now - session.created_at).total_seconds())
            
            duration_hours = duration_seconds / 3600
            
            # Mark as stale if: running/paused > 2 hours with 0 trades, or initializing > 5 minutes
            # If initializing and not in-memory, it's definitely stuck
            is_stale = False
            if session.status == "initializing":
                # Initializing sessions are stale if:
                # 1. > 5 minutes old, OR
                # 2. Not in-memory (definitely stuck)
                is_stale = duration_seconds > 300 or session.id not in in_memory_session_ids  # 5 minutes
            elif session.status == "running":
                # Running sessions are stale if:
                # 1. > 2 hours with 0 trades, OR
                # 2. Stuck (current_candle is 0 or None and running > 30 minutes)
                current_candle = session.current_candle or 0
                is_stuck = current_candle == 0 and duration_seconds > 1800  # 30 minutes
                is_stale = (trades_count == 0 and duration_hours > STALE_THRESHOLD_HOURS) or is_stuck
            else:  # paused
                # Paused sessions are stale if > 2 hours with 0 trades
                is_stale = trades_count == 0 and duration_hours > STALE_THRESHOLD_HOURS
            
            if is_stale:
                stale_sessions_to_clean.append(session)
            else:
                non_stale_sessions.append(session)
        
        # Clean up stale sessions
        if stale_sessions_to_clean:
            logger.info(f"Cleaning up {len(stale_sessions_to_clean)} stale forward test sessions for user {current_user.id}")
            for stale_session in stale_sessions_to_clean:
                await db.execute(
                    delete(TestSession).where(TestSession.id == stale_session.id)
                )
            await db.commit()
        
        # Only consider non-stale sessions as active
        active_in_db = len(non_stale_sessions) > 0
    else:
        active_in_db = False
    
    if active_in_memory or active_in_db:
        raise HTTPException(
            status_code=400,
            detail="You already have an active forward test. Please stop the existing test before starting a new one."
        )
    
    # Eagerly load api_key relationship to avoid lazy loading issues in background task
    agent_result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.api_key))
        .where(Agent.id == request.agent_id, Agent.user_id == current_user.id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.total_profitable_tests is None or agent.total_profitable_tests <= 0:
        raise HTTPException(status_code=400, detail="Agent needs at least one profitable backtest before forward testing")
    
    session_id = uuid.uuid4()
    auto_stop_pct = Decimal(str(request.auto_stop_loss_pct)) if request.auto_stop_on_loss else None
    
    test_session = TestSession(
        id=session_id,
        user_id=current_user.id,
        agent_id=agent.id,
        type="forward",
        status="initializing",
        asset=request.asset,
        timeframe=request.timeframe,
        starting_capital=Decimal(str(request.starting_capital)),
        safety_mode=request.safety_mode,
        allow_leverage=request.allow_leverage,
        email_notifications=request.email_notifications,
        auto_stop_on_loss=request.auto_stop_on_loss,
        auto_stop_loss_pct=auto_stop_pct,
        current_equity=Decimal(str(request.starting_capital)),
        current_pnl_pct=Decimal("0"),
        created_at=datetime.utcnow()
    )
    db.add(test_session)
    await db.commit()

    notification_service = NotificationService(db)
    try:
        await notification_service.create_notification(
            user_id=current_user.id,
            type="test_started",
            title=f"Forward test started • {request.asset.upper()}",
            message=f"{agent.name} is testing {request.asset.upper()} on {request.timeframe}",
            session_id=session_id,
        )
    except Exception as exc:
        # Don't block forward test start on notification errors
        logger.warning("Failed to create test start notification: %s", exc)
    
    auto_stop_config = {
        "enabled": request.auto_stop_on_loss,
        "loss_pct": request.auto_stop_loss_pct
    }
    
    background_tasks.add_task(
        engine.start_forward_test,
        session_id=str(session_id),
        agent=agent,
        asset=request.asset,
        timeframe=request.timeframe,
        starting_capital=request.starting_capital,
        safety_mode=request.safety_mode,
        auto_stop_config=auto_stop_config,
        email_notifications=request.email_notifications,
        allow_leverage=request.allow_leverage,
        decision_mode=request.decision_mode,
        decision_interval_candles=request.decision_interval_candles,
    )
    
    return {
        "session": ForwardSessionResponse(
            id=session_id,
            status="initializing",
            agent_id=agent.id,
            agent_name=agent.name,
            asset=request.asset,
            timeframe=request.timeframe,
            websocket_url=_build_ws_url(f"/ws/forward/{session_id}")
        ),
        "message": "Forward test started"
    }


@router.delete("/cleanup", response_model=Dict[str, Any])
async def cleanup_active_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine_backtest: BacktestEngine = Depends(get_backtest_engine),
    engine_forward: ForwardEngine = Depends(get_forward_engine),
    session_type: Optional[str] = Query(None, description="Filter by type: 'backtest' or 'forward'. If not provided, cleans up both.")
):
    """
    Clean up all active test sessions for the current user.
    
    This will:
    1. Stop all in-memory sessions (both backtest and forward)
    2. Delete all active sessions from database (status: running, paused, initializing)
    3. Related data (trades, ai_thoughts, etc.) will be deleted via CASCADE
    """
    deleted_count = 0
    stopped_in_memory = 0
    
    # Stop in-memory backtest sessions
    backtest_sessions_to_stop = [
        session_id for session_id, state in engine_backtest.active_sessions.items()
        if state.agent.user_id == current_user.id
        and (not session_type or session_type == "backtest")
    ]
    for session_id in backtest_sessions_to_stop:
        try:
            await engine_backtest.stop_backtest(session_id, close_position=False)
            stopped_in_memory += 1
        except Exception as e:
            logger.warning(f"Failed to stop backtest session {session_id}: {e}")
    
    # Stop in-memory forward sessions
    forward_sessions_to_stop = [
        session_id for session_id, state in engine_forward.active_sessions.items()
        if state.agent.user_id == current_user.id
        and (not session_type or session_type == "forward")
    ]
    for session_id in forward_sessions_to_stop:
        try:
            await engine_forward.stop_forward_test(session_id, close_position=False)
            stopped_in_memory += 1
        except Exception as e:
            logger.warning(f"Failed to stop forward session {session_id}: {e}")
    
    # Delete active sessions from database
    delete_query = (
        delete(TestSession)
        .where(TestSession.user_id == current_user.id)
        .where(TestSession.status.in_(("running", "paused", "initializing")))
    )
    
    if session_type:
        delete_query = delete_query.where(TestSession.type == session_type)
    
    result = await db.execute(delete_query)
    deleted_count = result.rowcount
    await db.commit()
    
    return {
        "message": "Cleanup completed",
        "deleted_sessions": deleted_count,
        "stopped_in_memory": stopped_in_memory,
        "session_type": session_type or "both"
    }
