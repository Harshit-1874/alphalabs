from datetime import datetime, timedelta
from typing import Optional
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
from services.trading.backtest_engine import BacktestEngine
from websocket.manager import websocket_manager
from api.users import get_current_user

router = APIRouter(prefix="/api/arena", tags=["arena"])

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
        end_date = datetime.now()
        if request.date_preset == '7d':
            start_date = end_date - timedelta(days=7)
        elif request.date_preset == '30d':
            start_date = end_date - timedelta(days=30)
        elif request.date_preset == '90d':
            start_date = end_date - timedelta(days=90)
        # TODO: Implement 'bull' and 'crash' presets
        else:
            start_date = end_date - timedelta(days=30)
            
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Start and end dates required")

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
        starting_capital=request.starting_capital,
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
        pm = session_state.position_manager
        current_equity = pm.get_total_equity()
        pnl_pct = ((current_equity - pm.starting_capital) / pm.starting_capital) * 100
        
        open_pos = pm.get_position()
        open_pos_data = None
        if open_pos:
            open_pos_data = OpenPosition(
                type=open_pos.action,
                entry_price=open_pos.entry_price,
                unrealized_pnl=open_pos.unrealized_pnl
            )
            
        return {
            "session": {
                "id": id,
                "status": "running" if not session_state.is_paused else "paused",
                "current_candle": session_state.current_index,
                "total_candles": len(session_state.candles),
                "progress_pct": (session_state.current_index / len(session_state.candles)) * 100,
                "elapsed_seconds": 0, # TODO: Track elapsed time
                "current_equity": current_equity,
                "current_pnl_pct": pnl_pct,
                "max_drawdown_pct": pm.max_drawdown_pct,
                "trades_count": len(pm.get_closed_trades()),
                "win_rate": pm.get_win_rate(),
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
        
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "current_candle": session.current_candle or 0,
            "total_candles": session.total_candles or 0,
            "progress_pct": 100 if session.status == "completed" else 0,
            "elapsed_seconds": 0,
            "current_equity": 0, # TODO: Store final equity in DB
            "current_pnl_pct": 0, # TODO: Store final PnL in DB
            "max_drawdown_pct": 0,
            "trades_count": 0,
            "win_rate": 0,
            "open_position": None
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
    engine: BacktestEngine = Depends(get_backtest_engine)
):
    """Stop backtest."""
    try:
        await engine.stop_backtest(str(id))
        return {
            "session_id": id,
            "status": "completed",
            "result_id": None, # TODO: Return result ID
            "final_pnl": None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
