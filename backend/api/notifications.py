"""
Notification Endpoints.

Purpose:
    Exposes RESTful API endpoints for Notification operations.
    Acts as the interface between the frontend and the Notification Service.

Data Flow:
    - Incoming: HTTP requests for notification operations (List, Read, Clear).
    - Processing:
        - Authenticates user via Clerk.
        - Delegates business logic to NotificationService.
        - Handles HTTP errors (404 Not Found, 400 Bad Request).
    - Outgoing: JSON responses containing notification details to the client.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database import get_db
from dependencies import get_current_user
from services.notification_service import NotificationService
from schemas.notification_schemas import (
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse
)
from models import User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter to show only unread notifications"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user notifications with pagination and filtering.
    
    Query Parameters:
    - unread_only: If true, only return unread notifications
    - limit: Maximum number of notifications to return (1-100, default: 20)
    - offset: Number of notifications to skip for pagination (default: 0)
    
    Returns paginated list of notifications ordered by created_at DESC (newest first).
    """
    service = NotificationService(db)
    
    try:
        notifications, total = await service.list_notifications(
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )
        
        unread_count = await service.get_unread_count(user_id=current_user.id)
        # Serialize notifications (now async)
        serialized = [await service.serialize_notification(n) for n in notifications]
        
        return NotificationListResponse(
            notifications=serialized,
            total=total,
            unread_count=unread_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}"
        )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get count of unread notifications for the current user.
    
    Used for displaying notification badge in the UI.
    """
    service = NotificationService(db)
    
    try:
        unread_count = await service.get_unread_count(user_id=current_user.id)
        
        return UnreadCountResponse(count=unread_count)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unread count: {str(e)}"
        )


@router.post("/{notification_id}/read", response_model=NotificationItem)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a specific notification as read.
    
    Validates that the notification belongs to the requesting user.
    Updates is_read to true and sets read_at timestamp.
    """
    service = NotificationService(db)
    
    try:
        notification = await service.mark_as_read(
            notification_id=notification_id,
            user_id=current_user.id
        )
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or does not belong to user"
            )
        
        return await service.serialize_notification(notification)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications as read for the current user.
    
    Returns the number of notifications that were marked as read.
    """
    service = NotificationService(db)
    
    try:
        updated_count = await service.mark_all_read(user_id=current_user.id)
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Marked {updated_count} notification(s) as read"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.delete("/clear")
async def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all notifications for the current user.
    
    Returns the number of notifications that were deleted.
    """
    service = NotificationService(db)
    
    try:
        deleted_count = await service.clear_all(user_id=current_user.id)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} notification(s)"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear notifications: {str(e)}"
        )
