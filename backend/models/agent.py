"""
Agent domain model for AI trading agent configurations.

This module contains the Agent model which represents AI trading agents
created by users. Each agent has identity, model configuration, indicators,
and strategy settings.
"""
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean, DECIMAL, ForeignKey, Index, Integer, 
    String, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Agent(Base, UUIDMixin, TimestampMixin):
    """
    AI trading agent configuration model.
    
    Represents a user-created AI trading agent with its identity, model
    configuration, data indicators, and strategy prompt. Agents can be
    tested in both backtest and forward test modes.
    
    The agent stores computed statistics that are updated after each test
    completion via database triggers.
    
    Relationships:
    - user: Many-to-one with User (agent owner)
    - api_key: Many-to-one with ApiKey (API key used for LLM calls)
    - test_sessions: One-to-many with TestSession (all test runs)
    - test_results: One-to-many with TestResult (completed tests)
    
    Example:
        agent = Agent(
            user_id=user.id,
            api_key_id=api_key.id,
            name="Momentum Trader",
            mode="monk",
            model="deepseek-r1",
            indicators=["rsi_14", "macd", "ema_20"],
            strategy_prompt="Trade based on RSI oversold/overbought..."
        )
    """
    __tablename__ = "agents"
    __table_args__ = (
        Index('idx_agents_user', 'user_id'),
        Index('idx_agents_active', 'user_id', postgresql_where="is_archived = false"),
        CheckConstraint(
            "mode IN ('monk', 'omni')",
            name="check_mode_values"
        ),
    )
    
    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who owns this agent"
    )
    
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        comment="Reference to API key used for LLM calls"
    )
    
    # Identity
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Agent display name"
    )
    
    mode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Agent mode: 'monk' (limited indicators) or 'omni' (all indicators)"
    )
    
    # Model Configuration
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="LLM model identifier (e.g., 'deepseek-r1', 'claude-3.5-sonnet')"
    )
    
    # Data Buffet - Indicators
    indicators: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        server_default="{}",
        nullable=False,
        comment="Array of standard indicator IDs available to the agent"
    )
    
    custom_indicators: Mapped[list] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
        comment="Array of custom indicator definitions with name and formula"
    )
    
    # Strategy
    strategy_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Trading strategy instructions for the AI agent"
    )
    
    # Computed Statistics (updated by database trigger after test completion)
    tests_run: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Total number of completed tests"
    )
    
    best_pnl: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        comment="Best PnL percentage achieved across all tests"
    )
    
    total_profitable_tests: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Number of tests that ended with positive PnL"
    )
    
    avg_win_rate: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2),
        comment="Average win rate across all tests"
    )
    
    avg_drawdown: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2),
        comment="Average maximum drawdown across all tests"
    )
    
    # Status
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Whether the agent is archived (soft delete)"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="agents"
    )
    
    api_key: Mapped[Optional["ApiKey"]] = relationship(
        "ApiKey",
        back_populates="agents"
    )
    
    test_sessions: Mapped[List["TestSession"]] = relationship(
        "TestSession",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    test_results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, mode={self.mode}, model={self.model})>"
