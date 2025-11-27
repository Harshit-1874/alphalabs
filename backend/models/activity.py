"""
Activity domain models for notifications, activity logs, and market data cache.

This module contains models related to user activity tracking and data caching:
- Notification: User notifications for test events and alerts
- ActivityLog: Dashboard activity feed tracking user actions
- MarketDataCache: Historical OHLCV data with pre-calculated indicators
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, DECIMAL, ForeignKey, Index, 
    Integer, String, Text, DateTime, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    """
    User notification model for test events and alerts.
    
    Stores notifications for various events in the system such as:
    - Test completion (backtest/forward test finished)
    - Trade execution (new trade opened/closed)
    - Stop loss hit (risk management alert)
    - System alerts (maintenance, updates)
    
    Notifications can be linked to specific entities (test sessions, results)
    and are marked as read/unread for UI display.
    
    Relationships:
    - user: Many-to-one with User (notification recipient)
    - session: Many-to-one with TestSession (optional, related session)
    - result: Many-to-one with TestResult (optional, related result)
    
    Example:
        notification = Notification(
            user_id=user.id,
            type="test_completed",
            title="Backtest Complete",
            message="Your BTC/USDT backtest finished with +24.5% PnL",
            session_id=session.id,
            result_id=result.id,
            is_read=False
        )
    """
    __tablename__ = "notifications"
    __table_args__ = (
        Index('idx_notifications_user', 'user_id'),
        Index('idx_notifications_read', 'user_id', 'is_read'),
        Index('idx_notifications_date', 'user_id', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
        CheckConstraint(
            "type IN ('test_completed', 'trade_executed', 'stop_loss_hit', 'system_alert', 'daily_summary')",
            name="check_notification_type_values"
        ),
    )
    
    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who receives this notification"
    )
    
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="CASCADE"),
        comment="Optional reference to related test session"
    )
    
    result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("test_results.id", ondelete="CASCADE"),
        comment="Optional reference to related test result"
    )
    
    # Notification Content
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Notification type: 'test_completed', 'trade_executed', 'stop_loss_hit', 'system_alert', 'daily_summary'"
    )
    
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Notification title"
    )
    
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Notification message body"
    )
    
    # Status
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Whether notification has been read"
    )
    
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Timestamp when notification was marked as read"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications"
    )
    
    session: Mapped[Optional["TestSession"]] = relationship(
        "TestSession",
        back_populates="notifications"
    )
    
    result: Mapped[Optional["TestResult"]] = relationship(
        "TestResult",
        back_populates="notifications"
    )
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.type}, user_id={self.user_id}, read={self.is_read})>"


class ActivityLog(Base, UUIDMixin, TimestampMixin):
    """
    Activity log model for dashboard activity feed.
    
    Tracks user actions and system events for display in the dashboard
    activity feed. Provides a chronological record of:
    - Agent creation/updates
    - Test session starts/completions
    - Result generation
    - Settings changes
    - API key management
    
    The metadata JSONB field stores action-specific details that vary
    by activity type (e.g., changed fields, previous values, etc.).
    
    Relationships:
    - user: Many-to-one with User (user who performed the action)
    - agent: Many-to-one with Agent (optional, related agent)
    - session: Many-to-one with TestSession (optional, related session)
    - result: Many-to-one with TestResult (optional, related result)
    
    Example:
        activity = ActivityLog(
            user_id=user.id,
            activity_type="agent_created",
            description="Created new agent 'Momentum Trader'",
            agent_id=agent.id,
            metadata={
                "agent_name": "Momentum Trader",
                "mode": "monk",
                "model": "deepseek-r1"
            }
        )
    """
    __tablename__ = "activity_logs"
    __table_args__ = (
        Index('idx_activity_logs_user', 'user_id'),
        Index('idx_activity_logs_type', 'user_id', 'activity_type'),
        Index('idx_activity_logs_date', 'user_id', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
        CheckConstraint(
            "activity_type IN ('agent_created', 'agent_updated', 'agent_deleted', 'test_started', 'test_completed', 'result_generated', 'certificate_created', 'settings_updated', 'api_key_added')",
            name="check_activity_type_values"
        ),
    )
    
    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who performed the action"
    )
    
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        comment="Optional reference to related agent"
    )
    
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="SET NULL"),
        comment="Optional reference to related test session"
    )
    
    result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("test_results.id", ondelete="SET NULL"),
        comment="Optional reference to related test result"
    )
    
    # Activity Details
    activity_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Activity type: 'agent_created', 'agent_updated', 'test_started', etc."
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable description of the activity"
    )
    
    activity_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Additional activity-specific data (changed fields, values, etc.)"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="activity_logs"
    )
    
    agent: Mapped[Optional["Agent"]] = relationship(
        "Agent",
        back_populates="activity_logs"
    )
    
    session: Mapped[Optional["TestSession"]] = relationship(
        "TestSession",
        back_populates="activity_logs"
    )
    
    result: Mapped[Optional["TestResult"]] = relationship(
        "TestResult",
        back_populates="activity_logs"
    )
    
    def __repr__(self) -> str:
        return f"<ActivityLog(id={self.id}, type={self.activity_type}, user_id={self.user_id})>"


class MarketDataCache(Base, UUIDMixin, TimestampMixin):
    """
    Market data cache model for historical OHLCV data.
    
    Caches historical candlestick data with pre-calculated technical
    indicators to reduce API calls and improve performance. Data is
    stored per asset, timeframe, and timestamp combination.
    
    The indicators JSONB field stores pre-calculated indicator values
    (e.g., RSI, MACD, moving averages) to avoid recalculation.
    
    Example:
        cache_entry = MarketDataCache(
            asset="BTC/USDT",
            timeframe="1h",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            open=Decimal("42000.00"),
            high=Decimal("42500.00"),
            low=Decimal("41800.00"),
            close=Decimal("42300.00"),
            volume=Decimal("1234.56"),
            indicators={
                "rsi_14": 65.4,
                "macd": {"macd": 120.5, "signal": 115.2, "histogram": 5.3},
                "sma_20": 41950.0,
                "ema_50": 41800.0
            }
        )
    """
    __tablename__ = "market_data_cache"
    __table_args__ = (
        UniqueConstraint('asset', 'timeframe', 'timestamp', name='uq_market_data_asset_timeframe_timestamp'),
        Index('idx_market_data_asset', 'asset'),
        Index('idx_market_data_timeframe', 'asset', 'timeframe'),
        Index('idx_market_data_timestamp', 'asset', 'timeframe', 'timestamp', postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'}),
    )
    
    # Market Data Identifiers
    asset: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Trading asset (e.g., 'BTC/USDT', 'ETH/USDT')"
    )
    
    timeframe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Candlestick timeframe (e.g., '1m', '5m', '1h', '4h', '1d')"
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Candle open timestamp"
    )
    
    # OHLCV Data
    open: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Opening price"
    )
    
    high: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Highest price"
    )
    
    low: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Lowest price"
    )
    
    close: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Closing price"
    )
    
    volume: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Trading volume"
    )
    
    # Pre-calculated Indicators
    indicators: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Pre-calculated technical indicators (RSI, MACD, moving averages, etc.)"
    )
    
    def __repr__(self) -> str:
        return f"<MarketDataCache(asset={self.asset}, timeframe={self.timeframe}, timestamp={self.timestamp}, close={self.close})>"
