from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, async_session_maker
from schemas.arena_schemas import (
    BacktestStartRequest, BacktestStartResponse, BacktestSessionResponse,
    BacktestStatusResponse, PauseResponse, ResumeResponse, StopRequest, StopResponse,
    OpenPosition, BacktestStatusWrapper
)
from models.agent import Agent
from models.arena import TestSession
from models.result import TestResult
from services.trading.backtest_engine import BacktestEngine
from websocket.manager import websocket_manager
from api.users import get_current_user

router = APIRouter(prefix="/api/arena", tags=["arena"])

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

# Singleton instance of BacktestEngine
# Initialized lazily or on module load
_backtest_engine: Optional[BacktestEngine] = None

def get_backtest_engine() -> BacktestEngine:
    """Get or create the singleton BacktestEngine instance."""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine(
            session_factory=async_session_maker,
            websocket_manager=websocket_manager
        )
    return _backtest_engine

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
    result = await db.execute(
        select(Agent).where(Agent.id == request.agent_id, Agent.user_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create session record
    session_id = uuid.uuid4()
    
    # Calculate dates if preset is used
    start_date = request.start_date
    end_date = request.end_date
    
    if request.date_preset and request.date_preset != 'custom':
        start_date, end_date = _resolve_date_preset(request.date_preset)
            
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Start and end dates required")
    
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

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
        start_date=start_date,
        end_date=end_date,
        starting_capital=request.starting_capital,
        safety_mode=request.safety_mode
    )

    return {
        "session": {
            "id": session_id,
            "status": "initializing",
            "agent_id": agent.id,
            "agent_name": agent.name,
            "asset": request.asset,
            "timeframe": request.timeframe,
            "total_candles": 0, # Will be updated by engine
            "websocket_url": f"wss://api.alphalab.io/ws/backtest/{session_id}"
        },
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
    
    open_position = None
    if session.open_position:
        open_position = OpenPosition(
            type=session.open_position.get("type", "long"),
            entry_price=session.open_position.get("entry_price", 0.0),
            unrealized_pnl=session.open_position.get("unrealized_pnl", 0.0)
        )
    
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
