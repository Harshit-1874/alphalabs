from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AssetMetadata(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    available: bool = True
    min_lookback_days: Optional[int] = None
    max_lookback_days: Optional[int] = None


class TimeframeMetadata(BaseModel):
    id: str
    name: str
    minutes: int
    interval: str


class AssetResponse(BaseModel):
    assets: List[AssetMetadata]


class TimeframeResponse(BaseModel):
    timeframes: List[TimeframeMetadata]

class CandleSchema(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class CandleWithIndicatorsSchema(BaseModel):
    """Extended candle schema that includes indicator values."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: Dict[str, Optional[float]] = Field(default_factory=dict)

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


class DatePresetMetadata(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    days: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class PlaybackSpeedMetadata(BaseModel):
    id: str
    name: str
    ms: int


class PresetResponse(BaseModel):
    date_presets: List[DatePresetMetadata]
    playback_speeds: List[PlaybackSpeedMetadata]


class IndicatorDefinition(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class IndicatorCategorySchema(BaseModel):
    id: str
    name: str
    indicators: List[IndicatorDefinition]


class IndicatorCatalogResponse(BaseModel):
    categories: List[IndicatorCategorySchema]
