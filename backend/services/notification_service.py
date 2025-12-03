"""
Notification Service.

Purpose:
    Encapsulates business logic for managing user notifications.
    Handles notification creation, retrieval, marking as read, and deletion.

Data Flow:
    - Incoming: User ID and notification requests from API layer
    - Processing:
        - Creates notification records in database
        - Retrieves notifications with pagination and filtering
        - Updates notification read status
        - Manages notification lifecycle
    - Outgoing: SQLAlchemy Notification model instances returned to API layer
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import joinedload
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Notification


class NotificationService:
    """Service for managing user notifications."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the notification service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_notification(
        self,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        session_id: Optional[UUID] = None,
        result_id: Optional[UUID] = None
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            user_id: ID of the user to notify
            type: Notification type (test_completed, trade_executed, etc.)
            title: Notification title
            message: Notification message body
            session_id: Optional related test session ID
            result_id: Optional related test result ID
            
        Returns:
            Notification: Newly created notification
            
        Raises:
            ValueError: If notification type is invalid
        """
        # Validate notification type
        valid_types = [
            'test_completed',
            'trade_executed',
            'stop_loss_hit',
            'system_alert',
            'daily_summary'
        ]
        
        if type not in valid_types:
            raise ValueError(
                f"Invalid notification type '{type}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )
        
        # Create notification record
        new_notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            session_id=session_id,
            result_id=result_id,
            is_read=False
        )
        
        self.db.add(new_notification)
        await self.db.commit()
        await self.db.refresh(new_notification)
        
        return new_notification
    
    async def list_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Notification]:
        """
        List user notifications with pagination and filtering.
        
        Args:
            user_id: ID of the user
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return (default: 20, max: 100)
            offset: Number of notifications to skip for pagination
            
        Returns:
            List[Notification]: List of notifications ordered by created_at DESC
        """
        # Enforce maximum limit
        limit = min(limit, 100)
        
        # Build query
        query = select(Notification).where(Notification.user_id == user_id)
        
        # Apply unread filter if requested
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        # Order by created_at descending (newest first)
        query = query.order_by(Notification.created_at.desc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        return list(notifications)
    
    async def get_unread_count(
        self,
        user_id: UUID
    ) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Number of unread notifications
        """
        result = await self.db.execute(
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        count = result.scalar_one()
        return count
    
    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        """
        Mark a notification as read.
        
        Validates that the notification belongs to the user before updating.
        
        Args:
            notification_id: ID of the notification to mark as read
            user_id: ID of the user (for ownership validation)
            
        Returns:
            Notification: Updated notification if found and owned by user
            None: If notification not found or not owned by user
        """
        # Fetch notification with ownership validation
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            return None
        
        # Update read status
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(notification)
        
        return notification
    
    async def mark_all_read(
        self,
        user_id: UUID
    ) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Number of notifications marked as read
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
            .values(
                is_read=True,
                read_at=datetime.utcnow()
            )
            .returning(Notification.id)
        )
        
        updated_ids = result.scalars().all()
        await self.db.commit()
        
        return len(updated_ids)
    
    async def clear_all(
        self,
        user_id: UUID
    ) -> int:
        """
        Delete all notifications for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Number of notifications deleted
        """
        result = await self.db.execute(
            delete(Notification)
            .where(Notification.user_id == user_id)
            .returning(Notification.id)
        )
        
        deleted_ids = result.scalars().all()
        await self.db.commit()
        
        return len(deleted_ids)
