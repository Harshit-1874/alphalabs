from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from database import get_db
from schemas.result_schemas import (
    ResultListResponse, ResultStatsResponse, ResultDetailResponse,
    TradeListResponse, ReasoningResponse, ResultListItem, Pagination,
    ResultStats, ResultStatsByType, ResultDetail, TradeSchema, AIThoughtSchema
)
from models.arena import TestSession, Trade, AiThought
from models.agent import Agent
from api.users import get_current_user

router = APIRouter(prefix="/api/results", tags=["results"])

@router.get("/", response_model=ResultListResponse)
async def list_results(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[str] = Query(None, regex="^(backtest|forward)$"),
    agent_id: Optional[UUID] = None,
    asset: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List test results with pagination and filtering."""
    # Build query
    query = select(TestSession).where(
        TestSession.user_id == current_user.id,
        TestSession.status == "completed"
    )
    
    if type:
        query = query.where(TestSession.type == type)
    if agent_id:
        query = query.where(TestSession.agent_id == agent_id)
    if asset:
        query = query.where(TestSession.asset == asset)
        
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Add sorting and pagination
    query = query.order_by(desc(TestSession.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # Fetch agent names
    # Optimization: Could use join, but for now simple queries
    items = []
    for session in sessions:
        agent_res = await db.execute(select(Agent).where(Agent.id == session.agent_id))
        agent = agent_res.scalar_one_or_none()
        agent_name = agent.name if agent else "Unknown Agent"
        
        # Calculate win rate and other stats if not stored
        # Assuming they are stored or calculated on the fly
        # For listing, we use basic info
        
        # Duration string
        duration = "0s"
        if session.started_at and session.completed_at:
            diff = session.completed_at - session.started_at
            duration = str(diff).split('.')[0]
            
        items.append(ResultListItem(
            id=session.id,
            type=session.type,
            agent_id=session.agent_id,
            agent_name=agent_name,
            asset=session.asset,
            mode="standard", # TODO: Store mode in TestSession
            created_at=session.created_at,
            duration_display=duration,
            total_trades=0, # TODO: Add to TestSession model or join
            total_pnl_pct=float(session.current_pnl_pct or 0),
            win_rate=0.0, # TODO: Add to TestSession model
            max_drawdown_pct=0.0, # TODO: Add to TestSession model
            sharpe_ratio=0.0,
            is_profitable=(session.current_pnl_pct or 0) > 0,
            has_certificate=False
        ))
        
    return {
        "results": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total or 0,
            "total_pages": (total + limit - 1) // limit if total else 0
        }
    }

@router.get("/stats", response_model=ResultStatsResponse)
async def get_result_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get aggregate statistics for all results."""
    # Base query
    base_query = select(TestSession).where(
        TestSession.user_id == current_user.id,
        TestSession.status == "completed"
    )
    
    result = await db.execute(base_query)
    sessions = result.scalars().all()
    
    total_tests = len(sessions)
    if total_tests == 0:
        return {
            "stats": {
                "total_tests": 0,
                "profitable": 0,
                "profitable_pct": 0.0,
                "best_result": 0.0,
                "worst_result": 0.0,
                "avg_pnl": 0.0,
                "by_type": {
                    "backtest": {"count": 0, "profitable": 0},
                    "forward": {"count": 0, "profitable": 0}
                }
            }
        }
        
    profitable_count = sum(1 for s in sessions if (s.current_pnl_pct or 0) > 0)
    pnls = [float(s.current_pnl_pct or 0) for s in sessions]
    
    backtest_sessions = [s for s in sessions if s.type == "backtest"]
    forward_sessions = [s for s in sessions if s.type == "forward"]
    
    return {
        "stats": {
            "total_tests": total_tests,
            "profitable": profitable_count,
            "profitable_pct": (profitable_count / total_tests) * 100,
            "best_result": max(pnls) if pnls else 0.0,
            "worst_result": min(pnls) if pnls else 0.0,
            "avg_pnl": sum(pnls) / total_tests if total_tests else 0.0,
            "by_type": {
                "backtest": {
                    "count": len(backtest_sessions),
                    "profitable": sum(1 for s in backtest_sessions if (s.current_pnl_pct or 0) > 0)
                },
                "forward": {
                    "count": len(forward_sessions),
                    "profitable": sum(1 for s in forward_sessions if (s.current_pnl_pct or 0) > 0)
                }
            }
        }
    }

@router.get("/{id}", response_model=ResultDetailResponse)
async def get_result_detail(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed result for a specific session."""
    # Get session
    result = await db.execute(
        select(TestSession).where(TestSession.id == id, TestSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Result not found")
        
    # Get agent
    agent_res = await db.execute(select(Agent).where(Agent.id == session.agent_id))
    agent = agent_res.scalar_one_or_none()
    
    # Get trades
    trades_res = await db.execute(
        select(Trade).where(Trade.session_id == id).order_by(Trade.trade_number)
    )
    trades = trades_res.scalars().all()
    
    # Convert trades
    trade_schemas = []
    win_count = 0
    for t in trades:
        trade_schemas.append(TradeSchema(
            trade_number=t.trade_number,
            type=t.type,
            entry_price=float(t.entry_price),
            exit_price=float(t.exit_price) if t.exit_price else None,
            entry_time=t.entry_time,
            exit_time=t.exit_time,
            pnl_amount=float(t.pnl_amount) if t.pnl_amount else None,
            pnl_pct=float(t.pnl_pct) if t.pnl_pct else None,
            entry_reasoning=t.entry_reasoning,
            exit_type=t.exit_type
        ))
        if t.pnl_amount and t.pnl_amount > 0:
            win_count += 1
            
    win_rate = (win_count / len(trades)) * 100 if trades else 0.0
    
    return {
        "result": {
            "id": session.id,
            "session_id": session.id,
            "type": session.type,
            "agent_id": session.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "model": agent.model if agent else "Unknown",
            "asset": session.asset,
            "mode": "standard", # TODO
            "start_date": session.start_date,
            "end_date": session.end_date or datetime.now(),
            "starting_capital": float(session.starting_capital),
            "ending_capital": float(session.current_equity or session.starting_capital),
            "total_pnl_pct": float(session.current_pnl_pct or 0),
            "total_trades": len(trades),
            "win_rate": win_rate,
            "max_drawdown_pct": 0.0, # TODO: Calculate from equity curve if available
            "sharpe_ratio": 0.0, # TODO
            "profit_factor": 0.0, # TODO
            "trades": trade_schemas
        }
    }

@router.get("/{id}/trades", response_model=TradeListResponse)
async def get_result_trades(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get trades for a result."""
    # Verify ownership
    session_res = await db.execute(
        select(TestSession).where(TestSession.id == id, TestSession.user_id == current_user.id)
    )
    if not session_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Result not found")
        
    # Get trades
    trades_res = await db.execute(
        select(Trade).where(Trade.session_id == id).order_by(Trade.trade_number)
    )
    trades = trades_res.scalars().all()
    
    return {
        "trades": [
            TradeSchema(
                trade_number=t.trade_number,
                type=t.type,
                entry_price=float(t.entry_price),
                exit_price=float(t.exit_price) if t.exit_price else None,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
                pnl_amount=float(t.pnl_amount) if t.pnl_amount else None,
                pnl_pct=float(t.pnl_pct) if t.pnl_pct else None,
                entry_reasoning=t.entry_reasoning,
                exit_type=t.exit_type
            ) for t in trades
        ]
    }

@router.get("/{id}/reasoning", response_model=ReasoningResponse)
async def get_result_reasoning(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI reasoning for a result."""
    # Verify ownership
    session_res = await db.execute(
        select(TestSession).where(TestSession.id == id, TestSession.user_id == current_user.id)
    )
    if not session_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Result not found")
        
    # Get thoughts
    thoughts_res = await db.execute(
        select(AiThought).where(AiThought.session_id == id).order_by(AiThought.candle_number)
    )
    thoughts = thoughts_res.scalars().all()
    
    return {
        "thoughts": [
            AIThoughtSchema(
                candle_number=t.candle_number,
                timestamp=t.timestamp,
                decision=t.decision or "HOLD",
                reasoning=t.reasoning,
                indicator_values=t.indicator_values or {}
            ) for t in thoughts
        ]
    }
