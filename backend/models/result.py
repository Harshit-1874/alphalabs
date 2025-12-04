"""
Result domain models for finalized test metrics and certificates.

This module contains models related to test results and shareable certificates:
- TestResult: Finalized test metrics with comprehensive performance data
- Certificate: Shareable performance certificates with verification codes
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Computed, DECIMAL, ForeignKey, Index, 
    Integer, String, Text, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin


class TestResult(Base, UUIDMixin):
    """
    Finalized test result with comprehensive metrics.
    
    Created when a test session completes successfully. Stores all
    performance metrics, equity curve data, and AI analysis summary.
    Has a one-to-one relationship with TestSession.
    
    The is_profitable field is a computed column that automatically
    determines if the test was profitable based on total_pnl_pct.
    
    Relationships:
    - session: One-to-one with TestSession (parent session)
    - user: Many-to-one with User (result owner)
    - agent: Many-to-one with Agent (agent that was tested)
    - certificate: One-to-one with Certificate (shareable certificate)
    
    Example:
        result = TestResult(
            session_id=session.id,
            user_id=user.id,
            agent_id=agent.id,
            type="backtest",
            asset="BTC/USDT",
            mode="monk",
            timeframe="1h",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            starting_capital=Decimal("10000.00"),
            ending_capital=Decimal("12450.00"),
            total_pnl_pct=Decimal("24.50"),
            win_rate=Decimal("65.00")
        )
    """
    __tablename__ = "test_results"
    __table_args__ = (
        Index('idx_results_user', 'user_id'),
        Index('idx_results_agent', 'agent_id'),
        Index('idx_results_profitable', 'user_id', 'is_profitable'),
        Index('idx_results_type', 'user_id', 'type'),
        Index('idx_results_date', 'user_id', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
        CheckConstraint(
            "type IN ('backtest', 'forward')",
            name="check_result_type_values"
        ),
        CheckConstraint(
            "mode IN ('monk', 'omni')",
            name="check_result_mode_values"
        ),
    )
    
    # Foreign Keys
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to parent test session"
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who owns this result"
    )
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to agent that was tested"
    )
    
    # Test Information
    type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Test type: 'backtest' or 'forward'"
    )
    
    asset: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Trading asset (e.g., 'BTC/USDT')"
    )
    
    mode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Agent mode: 'monk' or 'omni'"
    )
    
    timeframe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Chart timeframe (e.g., '1h', '4h', '1d')"
    )
    
    # Time Range
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Test start timestamp"
    )
    
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Test end timestamp"
    )
    
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total test duration in seconds"
    )
    
    duration_display: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Human-readable duration (e.g., '30 days', '48 hours')"
    )
    
    # Capital
    starting_capital: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        comment="Initial capital"
    )
    
    ending_capital: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        comment="Final capital"
    )
    
    # Primary Metrics
    total_pnl_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        comment="Total profit/loss amount"
    )
    
    total_pnl_pct: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 4),
        nullable=False,
        comment="Total profit/loss percentage"
    )
    
    total_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total number of trades executed"
    )
    
    winning_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of winning trades"
    )
    
    losing_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of losing trades"
    )
    
    win_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        nullable=False,
        comment="Win rate percentage"
    )
    
    # Advanced Metrics
    max_drawdown_pct: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Maximum drawdown percentage"
    )
    
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(6, 3),
        comment="Sharpe ratio (risk-adjusted return)"
    )
    
    profit_factor: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(6, 3),
        comment="Profit factor (gross profit / gross loss)"
    )
    
    avg_trade_pnl: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Average PnL per trade"
    )
    
    best_trade_pnl: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Best trade PnL percentage"
    )
    
    worst_trade_pnl: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Worst trade PnL percentage"
    )
    
    avg_holding_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Average holding time in seconds"
    )
    
    avg_holding_time_display: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Human-readable average holding time"
    )
    
    # Equity Curve Data (JSONB)
    equity_curve: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Sampled equity curve points for charting: [{time, value, drawdown}]"
    )
    
    # AI Analysis Summary
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="AI-generated summary of test performance"
    )
    
    # Computed Column
    is_profitable: Mapped[bool] = mapped_column(
        Boolean,
        Computed("(total_pnl_pct >= 0)", persisted=True),
        nullable=False,
        comment="Whether the test was profitable (computed)"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="NOW()",
        nullable=False,
        comment="Result creation timestamp"
    )
    
    # Relationships
    session: Mapped["TestSession"] = relationship(
        "TestSession",
        back_populates="test_result"
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="test_results"
    )
    
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="test_results"
    )
    
    certificate: Mapped[Optional["Certificate"]] = relationship(
        "Certificate",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="result",
        cascade="all, delete-orphan"
    )
    
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="result",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<TestResult(id={self.id}, type={self.type}, asset={self.asset}, pnl={self.total_pnl_pct}%)>"


class Certificate(Base, UUIDMixin):
    """
    Shareable performance certificate with verification.
    
    Generated when a user wants to share their test results publicly.
    Contains a unique verification code and cached display data for
    the public verification page. Includes URLs for generated assets
    (PDF, image, QR code).
    
    Relationships:
    - result: One-to-one with TestResult (parent result)
    - user: Many-to-one with User (certificate owner)
    
    Example:
        certificate = Certificate(
            result_id=result.id,
            user_id=user.id,
            verification_code="ALX-2025-1127-A3F8K",
            agent_name="Momentum Trader",
            model="deepseek-r1",
            mode="monk",
            test_type="backtest",
            asset="BTC/USDT",
            pnl_pct=Decimal("24.50"),
            win_rate=Decimal("65.00"),
            total_trades=42,
            duration_display="30 days",
            test_period="Jan 1 - Jan 31, 2025",
            share_url="https://example.com/verify/ALX-2025-1127-A3F8K"
        )
    """
    __tablename__ = "certificates"
    __table_args__ = (
        Index('idx_certificates_user', 'user_id'),
        Index('idx_certificates_code', 'verification_code'),
        Index('idx_certificates_result', 'result_id'),
        CheckConstraint(
            "test_type IN ('backtest', 'forward')",
            name="check_cert_test_type_values"
        ),
        CheckConstraint(
            "mode IN ('monk', 'omni')",
            name="check_cert_mode_values"
        ),
    )
    
    # Foreign Keys
    result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_results.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Reference to parent test result"
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who owns this certificate"
    )
    
    # Verification
    verification_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        comment="Unique verification code (e.g., 'ALX-2025-1127-A3F8K')"
    )
    
    # Cached Display Data (for public verification page)
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Agent name (cached)"
    )
    
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="LLM model used (cached)"
    )
    
    mode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Agent mode: 'monk' or 'omni' (cached)"
    )
    
    test_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Test type: 'backtest' or 'forward' (cached)"
    )
    
    asset: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Trading asset (cached)"
    )
    
    # Key Metrics (cached)
    pnl_pct: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 4),
        nullable=False,
        comment="Total PnL percentage (cached)"
    )
    
    win_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        nullable=False,
        comment="Win rate percentage (cached)"
    )
    
    total_trades: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total trades (cached)"
    )
    
    max_drawdown_pct: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Maximum drawdown percentage (cached)"
    )
    
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(6, 3),
        comment="Sharpe ratio (cached)"
    )
    
    duration_display: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Human-readable duration (cached)"
    )
    
    test_period: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Test period display (e.g., 'Oct 1 - Nov 1, 2025')"
    )
    
    # Generated Assets
    pdf_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="URL to generated PDF certificate"
    )
    
    image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="URL to generated certificate image"
    )
    
    qr_code_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="URL to generated QR code"
    )
    
    # Sharing
    share_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Public verification URL"
    )
    
    view_count: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Number of times certificate was viewed"
    )
    
    # Timestamps
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="NOW()",
        nullable=False,
        comment="Certificate issuance timestamp"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="NOW()",
        nullable=False,
        comment="Record creation timestamp"
    )
    
    # Relationships
    result: Mapped["TestResult"] = relationship(
        "TestResult",
        back_populates="certificate"
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="certificates"
    )
    
    def __repr__(self) -> str:
        return f"<Certificate(id={self.id}, code={self.verification_code}, pnl={self.pnl_pct}%)>"
