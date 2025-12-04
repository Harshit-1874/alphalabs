
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple, Dict, List, Any, Set
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
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
from config import settings
from api.users import get_current_user

router = APIRouter(prefix="/api/arena", tags=["arena"])


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
):
    """List active forward sessions."""
    sessions: List[ForwardActiveSession] = []
    seen_ids: Set[UUID] = set()
    now = datetime.utcnow()
    
    for session_id_str, state in engine.active_sessions.items():
        if state.agent.user_id != current_user.id:
            continue
        if agent_id and state.agent.id != agent_id:
            continue
        session_uuid = UUID(session_id_str)
        stats = state.position_manager.get_stats()
        started_at = state.started_at or now
        elapsed_seconds = int((now - started_at).total_seconds())
        status_value = "running" if not state.is_paused else "paused"
        if statuses and status_value not in statuses:
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
    
    db_result = await db.execute(base_query)
    rows = db_result.all()
    db_session_ids = [row[0].id for row in rows if row[0].id not in seen_ids]
    trade_stats = await _get_trade_stats(db, db_session_ids)
    
    for session, agent in rows:
        if session.id in seen_ids:
            continue
        duration_seconds = session.elapsed_seconds or 0
        if not duration_seconds and session.started_at:
            duration_seconds = int((now - session.started_at).total_seconds())
        trades_count, win_rate = trade_stats.get(session.id, (0, 0.0))
        sessions.append(
            ForwardActiveSession(
                id=session.id,
                agent_id=session.agent_id,
                agent_name=agent.name if agent else "Unknown Agent",
                asset=session.asset,
                status=session.status,
                started_at=session.started_at or session.created_at,
                duration_display=_format_duration(duration_seconds),
                current_pnl_pct=float(session.current_pnl_pct or 0),
                trades_count=trades_count,
                win_rate=win_rate
            )
        )
    
    return {"sessions": sessions}


@router.get("/forward/{id}", response_model=ForwardStatusWrapper)
async def get_forward_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    engine: ForwardEngine = Depends(get_forward_engine)
):
    """Get status for a forward session."""
    session_state = engine.active_sessions.get(str(id))
    now = datetime.utcnow()
    
    if session_state and session_state.agent.user_id == current_user.id:
        stats = session_state.position_manager.get_stats()
        open_pos = _serialize_open_position(session_state.position_manager.get_position())
        elapsed_seconds = int((now - session_state.started_at).total_seconds()) if session_state.started_at else 0
        next_eta = None
        if session_state.next_candle_time:
            next_eta = max(0, int((session_state.next_candle_time - now).total_seconds()))
        return {
            "session": {
                "id": id,
                "status": "running" if not session_state.is_paused else "paused",
                "started_at": session_state.started_at,
                "elapsed_seconds": elapsed_seconds,
                "current_equity": stats["current_equity"],
                "current_pnl_pct": stats["equity_change_pct"],
                "max_drawdown_pct": session_state.max_drawdown_pct,
                "trades_count": stats["total_trades"],
                "win_rate": stats["win_rate"],
                "next_candle_eta": next_eta,
                "open_position": open_pos
            }
        }
    
    result = await db.execute(
        select(TestSession).where(
            TestSession.id == id,
            TestSession.user_id == current_user.id,
            TestSession.type == "forward"
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    test_result_stmt = await db.execute(
        select(TestResult).where(TestResult.session_id == session.id)
    )
    test_result = test_result_stmt.scalar_one_or_none()
    
    if test_result:
        current_equity = float(test_result.ending_capital)
        pnl_pct = float(test_result.total_pnl_pct)
        trades_count = test_result.total_trades
        win_rate = float(test_result.win_rate or 0)
        max_drawdown = float(test_result.max_drawdown_pct or 0)
    else:
        current_equity = float(session.current_equity or session.starting_capital)
        pnl_pct = float(session.current_pnl_pct or 0)
        stats_map = await _get_trade_stats(db, [session.id])
        trades_count, win_rate = stats_map.get(session.id, (0, 0.0))
        max_drawdown = float(session.max_drawdown_pct or 0)
    
    elapsed_seconds = session.elapsed_seconds or 0
    if not elapsed_seconds and session.started_at:
        elapsed_seconds = int((now - session.started_at).total_seconds())
    
    open_position = _open_position_from_dict(session.open_position)
    
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "started_at": session.started_at,
            "elapsed_seconds": elapsed_seconds,
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
    now = datetime.utcnow()
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
    else:
        start_dt = datetime.combine(start_date_input, datetime.min.time())
    
    if isinstance(end_date_input, datetime):
        end_dt = end_date_input
    else:
        end_dt = datetime.combine(end_date_input, datetime.min.time())
    
    start_date = start_dt.date()
    end_date = end_dt.date()

    # Create TestSession in DB
    test_session = TestSession(
        id=session_id,
        user_id=current_user.id,
        agent_id=agent.id,
        type="backtest",
        status="initializing",
        asset=request.asset,
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date,
        starting_capital=Decimal(str(request.starting_capital)),
        playback_speed=request.playback_speed,
        date_preset=request.date_preset,
        safety_mode=request.safety_mode,
        allow_leverage=request.allow_leverage,
        current_equity=Decimal(str(request.starting_capital)),
        created_at=datetime.utcnow()
    )
    db.add(test_session)
    await db.commit()

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
            agent_id=agent.id,
            agent_name=agent.name,
            asset=request.asset,
            timeframe=request.timeframe,
            total_candles=0,
            websocket_url=_build_ws_url(f"/ws/backtest/{session_id}"),
            date_preset=request.date_preset,
            playback_speed=request.playback_speed,
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
    """Get backtest session status."""
    # Check active sessions first (in memory)
    session_id_str = str(id)
    session_state = engine.active_sessions.get(session_id_str)
    
    if session_state:
        # Return real-time state
        stats = session_state.position_manager.get_stats()
        current_equity = stats["current_equity"]
        pnl_pct = stats["equity_change_pct"]
        open_pos = session_state.position_manager.get_position()
        open_pos_data = _serialize_open_position(open_pos)
        elapsed_seconds = int((datetime.utcnow() - session_state.started_at).total_seconds()) if session_state.started_at else 0
        progress_pct = (
            (session_state.current_index / len(session_state.candles)) * 100
            if session_state.candles else 0
        )
        return {
            "session": {
                "id": id,
                "status": "running" if not session_state.is_paused else "paused",
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
    
    # If not active, fetch from DB
    result = await db.execute(
        select(TestSession).where(TestSession.id == id, TestSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    result_stmt = await db.execute(
        select(TestResult).where(TestResult.session_id == session.id)
    )
    test_result = result_stmt.scalar_one_or_none()
    
    current_equity = float(session.current_equity or session.starting_capital)
    pnl_pct = float(session.current_pnl_pct or 0)
    max_drawdown_pct = float(session.max_drawdown_pct or 0)
    trades_count = 0
    win_rate = 0.0
    if test_result:
        current_equity = float(test_result.ending_capital)
        pnl_pct = float(test_result.total_pnl_pct)
        trades_count = test_result.total_trades
        win_rate = float(test_result.win_rate or 0)
        if test_result.max_drawdown_pct is not None:
            max_drawdown_pct = float(test_result.max_drawdown_pct)
    
    open_position = _open_position_from_dict(session.open_position)
    
    progress_pct = 0.0
    if session.total_candles:
        progress_pct = min(100.0, (session.current_candle or 0) / session.total_candles * 100)
    if session.status == "completed":
        progress_pct = 100.0
    
    elapsed_seconds = session.elapsed_seconds or 0
    if not elapsed_seconds and session.started_at and session.completed_at:
        elapsed_seconds = int((session.completed_at - session.started_at).total_seconds())
    
    return {
        "session": {
            "id": session.id,
            "status": session.status,
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
            "paused_at": datetime.utcnow()
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
