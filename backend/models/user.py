"""
User domain models for authentication and user management.

This module contains models related to user accounts, settings, and API keys:
- User: Main user account synced from Clerk authentication
- UserSettings: User preferences, appearance, and risk limits
- ApiKey: Encrypted API keys for OpenRouter and other services
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, DECIMAL, Index, Integer, 
    String, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """
    User account model synced from Clerk authentication.
    
    This is the root entity for all user-specific data in the system.
    Users are created/updated via webhook from Clerk when they sign up
    or update their profile.
    
    Relationships:
    - settings: One-to-one with UserSettings
    - api_keys: One-to-many with ApiKey
    - agents: One-to-many with Agent
    - test_sessions: One-to-many with TestSession
    
    Example:
        user = User(
            clerk_id="user_2abc123",
            email="trader@example.com",
            first_name="John",
            last_name="Doe",
            plan="pro"
        )
    """
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_users_clerk_id', 'clerk_id'),
        Index('idx_users_email', 'email'),
    )
    
    # Authentication & Identity
    clerk_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Clerk authentication ID"
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="User email address"
    )
    
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="User's first name"
    )
    
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="User's last name"
    )
    
    username: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        comment="Display username"
    )
    
    image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Avatar/profile image URL"
    )
    
    # Configuration
    timezone: Mapped[str] = mapped_column(
        String(50),
        server_default="UTC",
        nullable=False,
        comment="User's timezone"
    )
    
    plan: Mapped[str] = mapped_column(
        String(20),
        server_default="free",
        nullable=False,
        comment="Subscription plan tier"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Account active status"
    )
    
    # Relationships
    settings: Mapped[Optional["UserSettings"]] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    api_keys: Mapped[List["ApiKey"]] = relationship(
        "ApiKey",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Forward references for relationships defined in other modules
    agents: Mapped[List["Agent"]] = relationship(
        "Agent",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    test_sessions: Mapped[List["TestSession"]] = relationship(
        "TestSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    test_results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, plan={self.plan})>"


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """
    User preferences and configuration settings.
    
    Stores all user-customizable settings including:
    - Appearance (theme, colors, layout)
    - Chart preferences
    - Notification settings (email and in-app)
    - Trading defaults
    - Risk management limits
    
    Has a one-to-one relationship with User.
    
    Example:
        settings = UserSettings(
            user_id=user.id,
            theme="dark",
            accent_color="cyan",
            default_capital=Decimal("10000.00"),
            max_leverage=5
        )
    """
    __tablename__ = "user_settings"
    __table_args__ = (
        Index('idx_user_settings_user', 'user_id'),
        CheckConstraint(
            "theme IN ('dark', 'light', 'system')",
            name="check_theme_values"
        ),
        CheckConstraint(
            "accent_color IN ('cyan', 'purple', 'green', 'amber')",
            name="check_accent_color_values"
        ),
        CheckConstraint(
            "max_position_size_pct BETWEEN 1 AND 100",
            name="check_max_position_size_pct_range"
        ),
        CheckConstraint(
            "max_leverage BETWEEN 1 AND 10",
            name="check_max_leverage_range"
        ),
    )
    
    # Foreign Key
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to user"
    )
    
    # Appearance Settings
    theme: Mapped[str] = mapped_column(
        String(10),
        server_default="dark",
        nullable=False,
        comment="UI theme preference"
    )
    
    accent_color: Mapped[str] = mapped_column(
        String(20),
        server_default="cyan",
        nullable=False,
        comment="UI accent color"
    )
    
    sidebar_collapsed: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Sidebar collapsed state"
    )
    
    # Chart Preferences
    chart_grid_lines: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Show grid lines on charts"
    )
    
    chart_crosshair: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Show crosshair on charts"
    )
    
    chart_candle_colors: Mapped[str] = mapped_column(
        String(20),
        server_default="green_red",
        nullable=False,
        comment="Candle color scheme"
    )
    
    # Notification Settings (JSONB)
    email_notifications: Mapped[dict] = mapped_column(
        JSONB,
        server_default="""{
            "test_completed": true,
            "trade_executed": true,
            "daily_summary": false,
            "stop_loss_hit": true,
            "marketing": false
        }""",
        nullable=False,
        comment="Email notification preferences"
    )
    
    inapp_notifications: Mapped[dict] = mapped_column(
        JSONB,
        server_default="""{
            "show_toasts": true,
            "sound_effects": true,
            "desktop_notifications": false
        }""",
        nullable=False,
        comment="In-app notification preferences"
    )
    
    # Trading Defaults
    default_asset: Mapped[str] = mapped_column(
        String(20),
        server_default="BTC/USDT",
        nullable=False,
        comment="Default trading asset"
    )
    
    default_timeframe: Mapped[str] = mapped_column(
        String(10),
        server_default="1h",
        nullable=False,
        comment="Default chart timeframe"
    )
    
    default_capital: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        server_default="10000.00",
        nullable=False,
        comment="Default starting capital"
    )
    
    default_playback_speed: Mapped[str] = mapped_column(
        String(10),
        server_default="normal",
        nullable=False,
        comment="Default backtest playback speed"
    )
    
    safety_mode_default: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Enable safety mode by default"
    )
    
    allow_leverage_default: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Allow leverage by default"
    )
    
    # Risk Limits
    max_position_size_pct: Mapped[int] = mapped_column(
        Integer,
        server_default="50",
        nullable=False,
        comment="Maximum position size as percentage of capital"
    )
    
    max_leverage: Mapped[int] = mapped_column(
        Integer,
        server_default="5",
        nullable=False,
        comment="Maximum allowed leverage"
    )
    
    max_loss_per_trade_pct: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        server_default="5.00",
        nullable=False,
        comment="Maximum loss per trade percentage"
    )
    
    max_daily_loss_pct: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        server_default="10.00",
        nullable=False,
        comment="Maximum daily loss percentage"
    )
    
    max_total_drawdown_pct: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        server_default="20.00",
        nullable=False,
        comment="Maximum total drawdown percentage"
    )
    
    # Relationship
    user: Mapped["User"] = relationship(
        "User",
        back_populates="settings"
    )
    
    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id}, theme={self.theme})>"


class ApiKey(Base, UUIDMixin, TimestampMixin):
    """
    Encrypted API key storage for external services.
    
    Stores encrypted API keys (primarily for OpenRouter) with metadata
    for display and validation. Keys are encrypted using AES-256 before
    storage and decrypted only when needed for API calls.
    
    Relationships:
    - user: Many-to-one with User
    - agents: One-to-many with Agent (agents using this key)
    
    Example:
        api_key = ApiKey(
            user_id=user.id,
            provider="openrouter",
            label="My Primary Key",
            encrypted_key=encrypt_key("sk-or-v1-..."),
            key_prefix="sk-or-v1-ab",
            is_default=True,
            status="valid"
        )
    """
    __tablename__ = "api_keys"
    __table_args__ = (
        Index('idx_api_keys_user', 'user_id'),
        Index('idx_api_keys_default', 'user_id', 'is_default', postgresql_where="is_default = true"),
        CheckConstraint(
            "status IN ('valid', 'invalid', 'untested')",
            name="check_status_values"
        ),
    )
    
    # Foreign Key
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user"
    )
    
    # Provider Information
    provider: Mapped[str] = mapped_column(
        String(50),
        server_default="openrouter",
        nullable=False,
        comment="API provider name"
    )
    
    label: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="User-defined label for the key"
    )
    
    # Encrypted Key Data
    encrypted_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-256 encrypted API key"
    )
    
    key_prefix: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="First characters of key for display (e.g., 'sk-or-v1-ab')"
    )
    
    # Key Status
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Whether this is the default key for new agents"
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="untested",
        nullable=False,
        comment="Validation status of the key"
    )
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Timestamp of last API call using this key"
    )
    
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Timestamp of last validation check"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys"
    )
    
    agents: Mapped[List["Agent"]] = relationship(
        "Agent",
        back_populates="api_key"
    )
    
    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, provider={self.provider}, prefix={self.key_prefix}, status={self.status})>"
