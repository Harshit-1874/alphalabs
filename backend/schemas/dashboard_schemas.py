"""
Dashboard Schemas.

Purpose:
    Defines Pydantic models for dashboard statistics, activity feed, and quick-start progress.
    Validates dashboard data responses and formats aggregated statistics.

Data Flow:
    - Incoming: Query parameters for filtering activity and stats.
    - Processing: Validates constraints and formats response data.
    - Outgoing: Structured data for the Dashboard Service, and JSON responses for the API.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class DashboardStatsResponse(BaseModel):
    """
    Schema for dashboard overview statistics.
    
    Contains aggregated metrics about user's agents, tests, and performance,
    including trend comparisons and best performing agent information.
    """
    total_agents: int = Field(
        ...,
        description="Total number of active (non-archived) agents"
    )
    tests_run: int = Field(
        ...,
        description="Total number of tests executed"
    )
    best_pnl: Optional[Decimal] = Field(
        default=None,
        description="Best PnL percentage achieved across all tests"
    )
    avg_win_rate: Optional[Decimal] = Field(
        default=None,
        description="Average win rate across all tests"
    )
    trends: Dict[str, Any] = Field(
        default_factory=dict,
        description="Trend metrics comparing current period to previous period"
    )
    best_agent: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Information about the best performing agent"
    )


class ActivityItem(BaseModel):
    """
    Schema for a single activity feed item.
    
    Represents a user action or test completion event in the activity feed,
    with relevant context and links to related entities.
    """
    id: UUID = Field(
        ...,
        description="Activity log entry ID"
    )
    type: str = Field(
        ...,
        description="Activity type: 'agent_created', 'test_started', 'test_completed', 'certificate_generated', etc."
    )
    agent_name: Optional[str] = Field(
        default=None,
        description="Name of the agent involved in the activity"
    )
    description: str = Field(
        ...,
        description="Human-readable description of the activity"
    )
    pnl: Optional[Decimal] = Field(
        default=None,
        description="PnL percentage if activity is test-related"
    )
    result_id: Optional[UUID] = Field(
        default=None,
        description="Test result ID if activity is test-related"
    )
    timestamp: datetime = Field(
        ...,
        description="When the activity occurred"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ActivityResponse(BaseModel):
    """
    Schema for activity feed response.
    
    Used by the activity endpoint to return a list of recent
    user activities for display in the dashboard.
    """
    activity: List[ActivityItem] = Field(
        ...,
        description="List of recent activity items"
    )


class QuickStartStep(BaseModel):
    """
    Schema for a single quick-start onboarding step.
    
    Represents one step in the onboarding process with completion
    status and navigation information.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the step"
    )
    label: str = Field(
        ...,
        description="Short label for the step"
    )
    description: str = Field(
        ...,
        description="Detailed description of what the step involves"
    )
    is_complete: bool = Field(
        ...,
        description="Whether the user has completed this step"
    )
    href: str = Field(
        ...,
        description="Navigation URL for the step"
    )
    cta_text: str = Field(
        ...,
        description="Call-to-action button text"
    )


class QuickStartResponse(BaseModel):
    """
    Schema for quick-start onboarding progress.
    
    Used by the quick-start endpoint to return onboarding steps
    with completion status and overall progress percentage.
    """
    steps: List[QuickStartStep] = Field(
        ...,
        description="List of onboarding steps"
    )
    progress_pct: float = Field(
        ...,
        description="Overall completion percentage (0-100)"
    )
