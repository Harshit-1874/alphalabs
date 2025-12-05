"""
Session state management for backtest engine.

This module contains the SessionState dataclass that represents the runtime
state of a backtest session, including candle data, position management,
indicator calculation, and AI trading components.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from models.agent import Agent
from services.market_data_service import Candle
from services.trading.indicator_calculator import IndicatorCalculator
from services.trading.position_manager import PositionManager
from services.ai_trader import AITrader

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """
    Represents the runtime state of a backtest session.
    
    Attributes:
        session_id: Unique session identifier
        agent: Agent configuration
        candles: Historical candle data
        current_index: Current candle being processed
        position_manager: Position management instance
        indicator_calculator: Indicator calculation instance
        ai_trader: AI decision making instance
        is_paused: Whether session is paused
        is_stopped: Whether session is stopped
        pause_event: Asyncio event for pause coordination
        ai_thoughts: List of AI reasoning records
    """
    session_id: str
    agent: Agent
    candles: List[Candle]
    current_index: int
    position_manager: PositionManager
    indicator_calculator: IndicatorCalculator
    ai_trader: AITrader
    is_paused: bool = False
    is_stopped: bool = False
    pause_event: asyncio.Event = field(default=None)
    ai_thoughts: List[Dict[str, Any]] = field(default=None)
    started_at: datetime = field(default=None)
    equity_curve: List[Dict[str, Any]] = field(default=None)
    peak_equity: float = 0.0
    max_drawdown_pct: float = 0.0
    allow_leverage: bool = False
    # Index of first candle where all enabled indicators are expected to be
    # non-null. We only start calling the LLM for trading decisions from this
    # index onward.
    decision_start_index: int = 0
    # Optional pending order placed by the AI (for limit-like entries). The
    # engine will attempt to fill this when price reaches the requested
    # entry_price on subsequent candles.
    pending_order: Optional[Dict[str, Any]] = None
    playback_speed: str = "normal"
    decision_mode: str = "every_candle"
    decision_interval_candles: int = 1
    # Council Mode Configuration
    council_mode: bool = False
    council_config: Optional[Dict[str, Any]] = None
    user_id: str = ""
    asset: str = ""
    timeframe: str = ""
    # Playback speed: 'slow' (1000ms), 'normal' (500ms), 'fast' (200ms), 'instant' (0ms)
    playback_speed: str = "normal"
    
    def __post_init__(self):
        """
        Initialize default values for mutable fields.
        
        Creates a new asyncio.Event for pause coordination if not provided,
        and initializes an empty list for AI thoughts if not provided.
        The pause event starts in the unpaused state (set).
        """
        if self.pause_event is None:
            self.pause_event = asyncio.Event()
            self.pause_event.set()  # Start unpaused
        if self.ai_thoughts is None:
            self.ai_thoughts = []
        if self.equity_curve is None:
            self.equity_curve = []
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
        if not self.peak_equity:
            self.peak_equity = self.position_manager.starting_capital
