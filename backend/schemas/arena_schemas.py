from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator

# --- Backtest Schemas ---

class BacktestStartRequest(BaseModel):
    agent_id: UUID
    asset: str
    timeframe: str
    date_preset: Optional[str] = "30d"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    starting_capital: float = Field(..., ge=100, le=1000000)
    playback_speed: str = "normal"
    safety_mode: bool = True
    allow_leverage: bool = False

    @validator('date_preset')
    def validate_preset(cls, v):
        allowed = ['7d', '30d', '90d', 'bull', 'crash', 'custom']
        if v and v not in allowed:
            raise ValueError(f"Invalid date_preset. Must be one of {allowed}")
        return v

class BacktestSessionResponse(BaseModel):
    id: UUID
    status: str
    agent_id: UUID
    agent_name: str
    asset: str
    timeframe: str
    total_candles: int
    websocket_url: str

class BacktestStartResponse(BaseModel):
    session: BacktestSessionResponse
    message: str

class OpenPosition(BaseModel):
    type: str
    entry_price: float
    unrealized_pnl: float

class BacktestStatusResponse(BaseModel):
    id: UUID
    status: str
    current_candle: int
    total_candles: int
    progress_pct: float
    elapsed_seconds: int
    current_equity: float
    current_pnl_pct: float
    max_drawdown_pct: float
    trades_count: int
    win_rate: float
    open_position: Optional[OpenPosition] = None

class BacktestStatusWrapper(BaseModel):
    session: BacktestStatusResponse

class PauseResponse(BaseModel):
    session_id: UUID
    status: str
    paused_at: datetime

class ResumeResponse(BaseModel):
    session_id: UUID
    status: str

class StopRequest(BaseModel):
    close_position: bool = True

class StopResponse(BaseModel):
    session_id: UUID
    status: str
    result_id: Optional[UUID] = None
    final_pnl: Optional[float] = None

# --- Forward Test Schemas ---

class ForwardStartRequest(BaseModel):
    agent_id: UUID
    asset: str
    timeframe: str
    starting_capital: float = Field(..., ge=100, le=1000000)
    safety_mode: bool = True
    email_notifications: bool = True
    auto_stop_on_loss: bool = True
    auto_stop_loss_pct: float = Field(10.0, ge=0.0, le=100.0)

class ForwardSessionResponse(BaseModel):
    id: UUID
    status: str
    agent_id: UUID
    agent_name: str
    asset: str
    timeframe: str
    websocket_url: str

class ForwardStartResponse(BaseModel):
    session: ForwardSessionResponse
    message: str

class ForwardActiveSession(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str
    asset: str
    status: str
    started_at: datetime
    duration_display: str
    current_pnl_pct: float
    trades_count: int
    win_rate: float

class ForwardActiveListResponse(BaseModel):
    sessions: List[ForwardActiveSession]

class ForwardStatusResponse(BaseModel):
    id: UUID
    status: str
    started_at: Optional[datetime]
    elapsed_seconds: int
    current_equity: float
    current_pnl_pct: float
    max_drawdown_pct: float
    trades_count: int
    win_rate: float
    next_candle_eta: Optional[int] = None
    open_position: Optional[OpenPosition] = None

class ForwardStatusWrapper(BaseModel):
    session: ForwardStatusResponse

class ForwardStopResponse(BaseModel):
    session_id: UUID
    status: str
    result_id: Optional[UUID] = None
    final_pnl: Optional[float] = None
    position_closed: bool
