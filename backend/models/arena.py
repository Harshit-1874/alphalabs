"""
Arena domain models for test sessions and trading activity.

This module contains models related to testing and trading:
- TestSession: Active and completed test sessions (backtest and forward)
- Trade: Individual trade records within sessions
- AiThought: AI reasoning log for each decision point
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, DATE, DECIMAL, ForeignKey, Index, 
    Integer, String, Text, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class TestSession(Base, UUIDMixin, TimestampMixin):
    """
    Test session model for backtest and forward test runs.
    
    Represents an active or completed test session where an AI agent
    trades on historical data (backtest) or live data (forward test).
    Tracks configuration, runtime state, and current position.
    
    Relationships:
    - user: Many-to-one with User (session owner)
    - agent: Many-to-one with Agent (agent being tested)
    - trades: One-to-many with Trade (all trades in this session)
    - ai_thoughts: One-to-many with AiThought (reasoning log)
    - test_result: One-to-one with TestResult (finalized metrics)
    
    Example:
        session = TestSession(
            user_id=user.id,
            agent_id=agent.id,
            type="backtest",
            status="running",
            asset="BTC/USDT",
            timeframe="1h",
            starting_capital=Decimal("10000.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
    """
    __test__ = False  # Prevent pytest from collecting this as a test class
    __tablename__ = "test_sessions"
    __table_args__ = (
        Index('idx_sessions_user', 'user_id'),
        Index('idx_sessions_agent', 'agent_id'),
        Index('idx_sessions_active', 'user_id', 'status', 
              postgresql_where="status IN ('running', 'paused')"),
        Index('idx_sessions_type', 'type', 'status'),
        CheckConstraint(
            "type IN ('backtest', 'forward')",
            name="check_type_values"
        ),
        CheckConstraint(
            "status IN ('configuring', 'initializing', 'running', 'paused', 'completed', 'failed', 'stopped')",
            name="check_status_values"
        ),
    )
    
    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to user who owns this session"
    )
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to agent being tested"
    )
    
    # Session Type and Status
    type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Session type: 'backtest' or 'forward'"
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="configuring",
        nullable=False,
        comment="Current session status"
    )
    
    # Configuration
    asset: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Trading asset (e.g., 'BTC/USDT')"
    )
    
    timeframe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Chart timeframe (e.g., '1h', '4h', '1d')"
    )
    
    starting_capital: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        comment="Initial capital for the test"
    )
    
    safety_mode: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Whether safety mode is enabled"
    )
    
    allow_leverage: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Whether leverage is allowed"
    )
    
    # Backtest Specific Fields
    date_preset: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Date preset: '7d', '30d', 'bull', 'crash', 'custom'"
    )
    
    start_date: Mapped[Optional[date]] = mapped_column(
        DATE,
        comment="Test start date (for backtest)"
    )
    
    end_date: Mapped[Optional[date]] = mapped_column(
        DATE,
        comment="Test end date (for backtest)"
    )
    
    playback_speed: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="Playback speed: 'slow', 'normal', 'fast', 'instant'"
    )
    
    decision_mode: Mapped[str] = mapped_column(
        String(20),
        server_default="every_candle",
        nullable=False,
        comment="Decision cadence mode for AI intervention"
    )

    decision_interval_candles: Mapped[int] = mapped_column(
        Integer,
        server_default="1",
        nullable=False,
        comment="Interval between LLM decisions when using every_n_candles"
    )
    
    # Council Mode Configuration
    council_mode: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Whether council mode (multi-LLM deliberation) is enabled"
    )
    
    council_models: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Array of model IDs participating in council deliberation"
    )
    
    council_chairman_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Model ID for chairman that synthesizes final decision"
    )
    
    total_candles: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Total number of candles in backtest"
    )
    
    current_candle: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Current candle index in backtest"
    )
    
    # Forward Test Specific Fields
    email_notifications: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Send email notifications for forward test events"
    )
    
    auto_stop_on_loss: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Automatically stop on loss threshold"
    )
    
    auto_stop_loss_pct: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2),
        comment="Auto-stop loss percentage threshold"
    )
    
    # Runtime State
    current_equity: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(15, 2),
        comment="Current equity value"
    )
    
    current_pnl_pct: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Current PnL percentage"
    )
    
    max_drawdown_pct: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Maximum drawdown percentage during session"
    )
    
    elapsed_seconds: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Total elapsed time in seconds"
    )
    
    # Position State (JSONB for flexibility)
    open_position: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Current open position data if any"
    )
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="When the session started running"
    )
    
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="When the session was paused"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="When the session completed"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="test_sessions"
    )
    
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="test_sessions"
    )
    
    trades: Mapped[List["Trade"]] = relationship(
        "Trade",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    ai_thoughts: Mapped[List["AiThought"]] = relationship(
        "AiThought",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    test_result: Mapped[Optional["TestResult"]] = relationship(
        "TestResult",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<TestSession(id={self.id}, type={self.type}, status={self.status}, asset={self.asset})>"



class Trade(Base, UUIDMixin):
    """
    Individual trade record within a test session.
    
    Represents a single trade executed by an AI agent during a test session.
    Tracks entry and exit details, position size, leverage, and results.
    
    Relationships:
    - session: Many-to-one with TestSession (parent session)
    - ai_thoughts: One-to-many with AiThought (thoughts related to this trade)
    
    Example:
        trade = Trade(
            session_id=session.id,
            trade_number=1,
            type="long",
            entry_price=Decimal("67234.50"),
            entry_time=datetime.now(),
            size=Decimal("0.5"),
            leverage=1,
            stop_loss=Decimal("66500.00"),
            take_profit=Decimal("69000.00")
        )
    """
    __tablename__ = "trades"
    __table_args__ = (
        Index('idx_trades_session', 'session_id'),
        Index('idx_trades_session_time', 'session_id', 'entry_time'),
        CheckConstraint(
            "type IN ('long', 'short')",
            name="check_trade_type_values"
        ),
        CheckConstraint(
            "exit_type IN ('take_profit', 'stop_loss', 'manual', 'signal')",
            name="check_exit_type_values"
        ),
    )
    
    # Foreign Key
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to parent test session"
    )
    
    # Trade Details
    trade_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential trade number within session"
    )
    
    type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Trade type: 'long' or 'short'"
    )
    
    # Entry Details
    entry_price: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Entry price"
    )
    
    entry_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Entry timestamp"
    )
    
    entry_candle: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Candle number at entry (for backtest)"
    )
    
    entry_reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="AI reasoning for entry"
    )
    
    # Exit Details (null if position still open)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(20, 8),
        comment="Exit price"
    )
    
    exit_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Exit timestamp"
    )
    
    exit_candle: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Candle number at exit (for backtest)"
    )
    
    exit_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Exit type: 'take_profit', 'stop_loss', 'manual', 'signal'"
    )
    
    exit_reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="AI reasoning for exit"
    )
    
    # Size and Leverage
    size: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False,
        comment="Position size"
    )
    
    leverage: Mapped[int] = mapped_column(
        Integer,
        server_default="1",
        nullable=False,
        comment="Leverage used"
    )
    
    # Results
    pnl_amount: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(15, 2),
        comment="Profit/loss amount"
    )
    
    pnl_pct: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Profit/loss percentage"
    )
    
    # Risk Management
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(20, 8),
        comment="Stop loss price"
    )
    
    take_profit: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(20, 8),
        comment="Take profit price"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="NOW()",
        nullable=False,
        comment="Record creation timestamp"
    )
    
    # Relationships
    session: Mapped["TestSession"] = relationship(
        "TestSession",
        back_populates="trades"
    )
    
    ai_thoughts: Mapped[List["AiThought"]] = relationship(
        "AiThought",
        back_populates="trade",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, session_id={self.session_id}, type={self.type}, entry_price={self.entry_price})>"



class AiThought(Base, UUIDMixin):
    """
    AI reasoning log for each decision point.
    
    Captures the AI agent's thought process at each candle/decision point,
    including input data (candle, indicators), reasoning, decision, and
    any orders generated.
    
    Relationships:
    - session: Many-to-one with TestSession (parent session)
    - trade: Many-to-one with Trade (related trade if applicable)
    
    Example:
        thought = AiThought(
            session_id=session.id,
            candle_number=42,
            timestamp=datetime.now(),
            candle_data={"open": 67150.00, "high": 67320.00, ...},
            indicator_values={"rsi_14": 58.2, "macd": 0.12, ...},
            thought_type="decision",
            reasoning="RSI showing oversold conditions...",
            decision="long",
            confidence=Decimal("85.50")
        )
    """
    __tablename__ = "ai_thoughts"
    __table_args__ = (
        Index('idx_thoughts_session', 'session_id'),
        Index('idx_thoughts_session_candle', 'session_id', 'candle_number'),
        Index('idx_thoughts_trade', 'trade_id', postgresql_where="trade_id IS NOT NULL"),
        CheckConstraint(
            "thought_type IN ('analysis', 'decision', 'execution')",
            name="check_thought_type_values"
        ),
        CheckConstraint(
            "decision IN ('long', 'short', 'hold', 'close')",
            name="check_decision_values"
        ),
    )
    
    # Foreign Keys
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to parent test session"
    )
    
    trade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("trades.id", ondelete="SET NULL"),
        comment="Reference to related trade if applicable"
    )
    
    # Candle Context
    candle_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Candle number in the session"
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of the candle/decision point"
    )
    
    # Input Data Snapshot (JSONB)
    candle_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="OHLCV data for this candle"
    )
    
    indicator_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="All indicator values at this point"
    )
    
    # AI Output
    thought_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of thought: 'analysis', 'decision', 'execution'"
    )
    
    reasoning: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AI's reasoning text"
    )
    
    decision: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="Decision made: 'long', 'short', 'hold', 'close'"
    )
    
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2),
        comment="Confidence level (0-100)"
    )
    
    # Order Data (JSONB)
    order_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Order details if an order was generated"
    )
    
    # Council Deliberation Data (for multi-LLM council mode)
    council_stage1: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Stage 1: Individual responses from all council models"
    )
    
    council_stage2: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Stage 2: Peer rankings of decisions"
    )
    
    council_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Council metadata (aggregate rankings, label mappings, etc.)"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="NOW()",
        nullable=False,
        comment="Record creation timestamp"
    )
    
    # Relationships
    session: Mapped["TestSession"] = relationship(
        "TestSession",
        back_populates="ai_thoughts"
    )
    
    trade: Mapped[Optional["Trade"]] = relationship(
        "Trade",
        back_populates="ai_thoughts"
    )
    
    def __repr__(self) -> str:
        return f"<AiThought(id={self.id}, session_id={self.session_id}, candle={self.candle_number}, type={self.thought_type})>"
