from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel

class ResultListItem(BaseModel):
    id: UUID
    type: str
    agent_id: UUID
    agent_name: str
    asset: str
    mode: str
    created_at: datetime
    duration_display: str
    total_trades: int
    total_pnl_pct: float
    win_rate: float
    max_drawdown_pct: float
    sharpe_ratio: float
    is_profitable: bool
    has_certificate: bool

class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int

class ResultListResponse(BaseModel):
    results: List[ResultListItem]
    pagination: Pagination

class ResultStatsByType(BaseModel):
    count: int
    profitable: int

class ResultStats(BaseModel):
    total_tests: int
    profitable: int
    profitable_pct: float
    best_result: float
    worst_result: float
    avg_pnl: float
    by_type: Dict[str, ResultStatsByType]

class ResultStatsResponse(BaseModel):
    stats: ResultStats

class TradeSchema(BaseModel):
    trade_number: int
    type: str
    entry_price: float
    exit_price: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl_amount: Optional[float]
    pnl_pct: Optional[float]
    entry_reasoning: Optional[str]
    exit_type: Optional[str]

class ResultDetail(BaseModel):
    id: UUID
    session_id: UUID
    type: str
    agent_id: UUID
    agent_name: str
    model: str
    asset: str
    mode: str
    start_date: datetime
    end_date: datetime
    starting_capital: float
    ending_capital: float
    total_pnl_pct: float
    total_trades: int
    win_rate: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    trades: List[TradeSchema]

class ResultDetailResponse(BaseModel):
    result: ResultDetail

class TradeListResponse(BaseModel):
    trades: List[TradeSchema]

class AIThoughtSchema(BaseModel):
    candle_number: int
    timestamp: datetime
    decision: str
    reasoning: str
    indicator_values: Dict[str, float]

class ReasoningResponse(BaseModel):
    thoughts: List[AIThoughtSchema]
