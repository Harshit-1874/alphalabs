from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AssetResponse(BaseModel):
    assets: List[str]

class TimeframeResponse(BaseModel):
    timeframes: List[str]

class CandleSchema(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class CandleResponse(BaseModel):
    candles: List[CandleSchema]

class IndicatorRequest(BaseModel):
    asset: str
    timeframe: str
    indicators: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class IndicatorResponse(BaseModel):
    indicators: Dict[str, List[Optional[float]]]
    timestamps: List[datetime]
