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
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from models import Notification
from models.arena import TestSession


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
            'test_started',
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
        offset: int = 0,
    ) -> Tuple[List[Notification], int]:
        limit = min(limit, 100)
        base_filters = [Notification.user_id == user_id]
        if unread_only:
            base_filters.append(Notification.is_read == False)
        
        count_query = select(func.count(Notification.id)).where(*base_filters)
        total = (await self.db.execute(count_query)).scalar_one()
        
        query = (
            select(Notification)
            .where(*base_filters)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        return list(notifications), total
    
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

    async def serialize_notification(self, notification: Notification) -> Dict[str, Any]:
        category = self._map_category(notification.type)
        presentation_type = self._map_presentational_type(notification.type)
        action_url = await self._resolve_action_url(notification)
        return {
            "id": notification.id,
            "type": presentation_type,
            "category": category,
            "title": notification.title,
            "message": notification.message,
            "action_url": action_url,
            "session_id": notification.session_id,
            "result_id": notification.result_id,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
        }

    def _map_category(self, notification_type: str) -> str:
        mapping = {
            "test_completed": "test_complete",
            "trade_executed": "trade_activity",
            "stop_loss_hit": "risk_alert",
            "system_alert": "system",
            "daily_summary": "summary",
        }
        return mapping.get(notification_type, notification_type)

    def _map_presentational_type(self, notification_type: str) -> str:
        if notification_type == "stop_loss_hit":
            return "warning"
        if notification_type in ("system_alert", "daily_summary"):
            return "info"
        return "success"

    async def _resolve_action_url(self, notification: Notification) -> Optional[str]:
        """
        Resolve the action URL for a notification.
        
        Logic:
        - If result_id exists: route to results page
        - If session_id exists: 
          - Query session to get type (backtest/forward) and status
          - If session is running/paused: route to live arena view
          - If session is completed: route to results if result_id exists, otherwise arena view
        """
        # If result_id exists, always route to results (completed test)
        if notification.result_id:
            return f"/dashboard/results/{notification.result_id}"
        
        # If session_id exists, check session type and status
        if notification.session_id:
            # Query the session to get its type and status
            result = await self.db.execute(
                select(TestSession)
                .where(TestSession.id == notification.session_id)
            )
            session = result.scalar_one_or_none()
            
            if not session:
                # Session not found, can't determine route
                return None
            
            # Determine arena type based on session.type
            arena_type = session.type  # 'backtest' or 'forward'
            
            # If session is still running or paused, route to live view
            if session.status in ('running', 'paused', 'initializing'):
                return f"/dashboard/arena/{arena_type}/{notification.session_id}"
            
            # If session is completed, check if we have a result_id
            # (This shouldn't happen often since completed tests should have result_id,
            # but handle it just in case)
            if session.status in ('completed', 'stopped', 'failed'):
                # If notification has result_id, it would have been handled above
                # Otherwise, route to arena view (which will show completed state)
                return f"/dashboard/arena/{arena_type}/{notification.session_id}"
            
            # Default: route to arena view
            return f"/dashboard/arena/{arena_type}/{notification.session_id}"
        
        return None
