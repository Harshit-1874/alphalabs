from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from database import get_db
from schemas.result_schemas import (
    ResultListResponse, ResultStatsResponse, ResultDetailResponse,
    TradeListResponse, ReasoningResponse, ResultListItem, Pagination,
    ResultStats, ResultStatsByType, ResultDetail, TradeSchema, AIThoughtSchema
)
from models.arena import Trade, AiThought
from models.agent import Agent
from models.result import TestResult
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
    # Build base query
    query = (
        select(TestResult)
        .where(TestResult.user_id == current_user.id)
        .options(
            selectinload(TestResult.agent),
            selectinload(TestResult.certificate)
        )
    )
    
    if type:
        query = query.where(TestResult.type == type)
    if agent_id:
        query = query.where(TestResult.agent_id == agent_id)
    if asset:
        query = query.where(TestResult.asset == asset)
        
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    query = query.order_by(desc(TestResult.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    test_results = result.scalars().all()
    
    items: List[ResultListItem] = []
    for res in test_results:
        agent_name = res.agent.name if res.agent else "Unknown Agent"
        duration = res.duration_display or ""
        items.append(ResultListItem(
            id=res.id,
            type=res.type,
            agent_id=res.agent_id,
            agent_name=agent_name,
            asset=res.asset,
            mode=res.mode,
            created_at=res.created_at,
            duration_display=duration,
            total_trades=res.total_trades,
            total_pnl_pct=float(res.total_pnl_pct or 0),
            win_rate=float(res.win_rate or 0),
            max_drawdown_pct=float(res.max_drawdown_pct or 0),
            sharpe_ratio=float(res.sharpe_ratio or 0),
            is_profitable=res.is_profitable,
            has_certificate=bool(res.certificate)
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
    base_query = select(TestResult).where(TestResult.user_id == current_user.id)
    result = await db.execute(base_query)
    results = result.scalars().all()
    
    total_tests = len(results)
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
        
    profitable_count = sum(1 for r in results if r.is_profitable)
    pnls = [float(r.total_pnl_pct or 0) for r in results]
    
    by_type_data: Dict[str, Dict[str, int]] = {
        "backtest": {"count": 0, "profitable": 0},
        "forward": {"count": 0, "profitable": 0},
    }
    for r in results:
        bucket = by_type_data[r.type]
        bucket["count"] += 1
        if r.is_profitable:
            bucket["profitable"] += 1
    
    return {
        "stats": {
            "total_tests": total_tests,
            "profitable": profitable_count,
            "profitable_pct": (profitable_count / total_tests) * 100,
            "best_result": max(pnls) if pnls else 0.0,
            "worst_result": min(pnls) if pnls else 0.0,
            "avg_pnl": sum(pnls) / total_tests if total_tests else 0.0,
            "by_type": {
                "backtest": by_type_data["backtest"],
                "forward": by_type_data["forward"],
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
    result = await db.execute(
        select(TestResult)
        .where(TestResult.id == id, TestResult.user_id == current_user.id)
        .options(selectinload(TestResult.agent))
    )
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise HTTPException(status_code=404, detail="Result not found")
        
    # Get agent
    agent = test_result.agent
    
    # Get trades
    trades_res = await db.execute(
        select(Trade).where(Trade.session_id == test_result.session_id).order_by(Trade.trade_number)
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
            "id": test_result.id,
            "session_id": test_result.session_id,
            "type": test_result.type,
            "agent_id": test_result.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "model": agent.model if agent else "Unknown",
            "asset": test_result.asset,
            "mode": test_result.mode,
            "start_date": test_result.start_date,
            "end_date": test_result.end_date or datetime.now(),
            "starting_capital": float(test_result.starting_capital),
            "ending_capital": float(test_result.ending_capital),
            "total_pnl_pct": float(test_result.total_pnl_pct),
            "total_trades": test_result.total_trades,
            "win_rate": float(test_result.win_rate or win_rate),
            "max_drawdown_pct": float(test_result.max_drawdown_pct or 0),
            "sharpe_ratio": float(test_result.sharpe_ratio or 0),
            "profit_factor": float(test_result.profit_factor or 0),
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
    # Verify ownership via result
    result_res = await db.execute(
        select(TestResult).where(TestResult.id == id, TestResult.user_id == current_user.id)
    )
    result_row = result_res.scalar_one_or_none()
    if not result_row:
        raise HTTPException(status_code=404, detail="Result not found")
        
    # Get trades
    trades_res = await db.execute(
        select(Trade).where(Trade.session_id == result_row.session_id).order_by(Trade.trade_number)
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
    result_res = await db.execute(
        select(TestResult).where(TestResult.id == id, TestResult.user_id == current_user.id)
    )
    result_row = result_res.scalar_one_or_none()
    if not result_row:
        raise HTTPException(status_code=404, detail="Result not found")
        
    # Get thoughts
    thoughts_res = await db.execute(
        select(AiThought).where(AiThought.session_id == result_row.session_id).order_by(AiThought.candle_number)
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
