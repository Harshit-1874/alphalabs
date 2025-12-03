"""
Dashboard Endpoints.

Purpose:
    Exposes RESTful API endpoints for Dashboard operations.
    Acts as the interface between the frontend and the Dashboard Service.

Data Flow:
    - Incoming: HTTP requests for dashboard statistics, activity feed, and quick-start progress.
    - Processing:
        - Authenticates user via Clerk.
        - Delegates business logic to DashboardService.
        - Handles HTTP errors and validation.
    - Outgoing: JSON responses containing dashboard data to the client.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies import get_current_user
from services.dashboard_service import DashboardService
from schemas.dashboard_schemas import (
    DashboardStatsResponse,
    ActivityResponse,
    QuickStartResponse
)
from models import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard overview statistics.
    
    Returns aggregated metrics including:
    - Total agents (not archived)
    - Total tests run
    - Best PnL across all results
    - Average win rate
    - Trends (comparison to previous period)
    - Best performing agent
    
    Requires authentication.
    """
    service = DashboardService(db)
    
    try:
        stats = await service.get_stats(user_id=current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard statistics: {str(e)}"
        )


@router.get("/activity", response_model=ActivityResponse)
async def get_dashboard_activity(
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of activity items to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activity feed for dashboard.
    
    Returns a list of recent user activities including:
    - Agent creation
    - Test starts and completions
    - Certificate generation
    - Other user actions
    
    Query Parameters:
    - limit: Maximum number of items to return (1-50, default: 10)
    
    Requires authentication.
    """
    service = DashboardService(db)
    
    try:
        activity = await service.get_activity(
            user_id=current_user.id,
            limit=limit
        )
        return {"activity": activity}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity feed: {str(e)}"
        )


@router.get("/quick-start", response_model=QuickStartResponse)
async def get_quick_start_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get onboarding quick-start progress.
    
    Returns completion status for key onboarding steps:
    1. Create first agent
    2. Run first backtest
    3. Generate first certificate
    
    Includes overall progress percentage and navigation links
    for incomplete steps.
    
    Requires authentication.
    """
    service = DashboardService(db)
    
    try:
        progress = await service.get_quick_start_progress(user_id=current_user.id)
        return progress
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quick-start progress: {str(e)}"
        )
