"""
Notification Schemas.

Purpose:
    Defines Pydantic models for notification retrieval and management.
    Validates notification responses and formats notification list data.

Data Flow:
    - Incoming: Query parameters for filtering notifications.
    - Processing: Validates constraints and formats response data.
    - Outgoing: Structured data for the Notification Service, and JSON responses for the API.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class NotificationResponse(BaseModel):
    """
    Schema for notification data returned to the user.
    
    Contains all information needed to display a notification in the UI,
    including content, status, and related entity references.
    """
    id: UUID
    user_id: UUID
    
    # Related entities
    session_id: Optional[UUID] = None
    result_id: Optional[UUID] = None
    
    # Content
    type: str = Field(
        ...,
        description="Notification type: 'test_completed', 'trade_executed', 'stop_loss_hit', 'system_alert', 'daily_summary'"
    )
    title: str = Field(
        ...,
        description="Notification title"
    )
    message: str = Field(
        ...,
        description="Notification message body"
    )
    
    # Status
    is_read: bool = Field(
        ...,
        description="Whether notification has been read"
    )
    read_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when notification was marked as read"
    )
    
    # Timestamps
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """
    Schema for paginated list of notifications.
    
    Used by the list notifications endpoint to return a paginated
    collection of notifications with total count for UI pagination.
    """
    notifications: List[NotificationResponse] = Field(
        ...,
        description="List of notifications for the current page"
    )
    total: int = Field(
        ...,
        description="Total number of notifications matching the query"
    )
    unread_count: int = Field(
        ...,
        description="Total number of unread notifications"
    )


class UnreadCountResponse(BaseModel):
    """
    Schema for unread notification count.
    
    Used by the unread count endpoint to return just the count
    of unread notifications for badge display in the UI.
    """
    unread_count: int = Field(
        ...,
        description="Number of unread notifications"
    )
