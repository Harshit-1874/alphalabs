from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.data_schemas import (
    AssetResponse, TimeframeResponse, CandleResponse, 
    IndicatorRequest, IndicatorResponse, CandleSchema
)
from services.market_data_service import MarketDataService
from services.trading.indicator_calculator import IndicatorCalculator
from api.users import get_current_user

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/assets", response_model=AssetResponse)
async def get_assets(
    current_user: dict = Depends(get_current_user)
):
    """Get list of available assets."""
    return {"assets": list(MarketDataService.ASSET_TICKER_MAP.keys())}

@router.get("/timeframes", response_model=TimeframeResponse)
async def get_timeframes(
    current_user: dict = Depends(get_current_user)
):
    """Get list of available timeframes."""
    return {"timeframes": list(MarketDataService.TIMEFRAME_INTERVAL_MAP.keys())}

@router.get("/candles", response_model=CandleResponse)
async def get_candles(
    asset: str = Query(..., description="Trading asset (e.g., BTC/USDT)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 1h)"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles if no date range"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get historical candle data."""
    service = MarketDataService(db)
    
    # Default date range if not provided
    if not start_date or not end_date:
        end_date = datetime.now()
        # Estimate duration based on limit and timeframe
        # This is a rough approximation
        if timeframe == '15m':
            delta = timedelta(minutes=15 * limit)
        elif timeframe == '1h':
            delta = timedelta(hours=1 * limit)
        elif timeframe == '4h':
            delta = timedelta(hours=4 * limit)
        elif timeframe == '1d':
            delta = timedelta(days=1 * limit)
        else:
            delta = timedelta(days=30) # Default fallback
            
        start_date = end_date - delta

    try:
        candles = await service.get_historical_data(
            asset=asset,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Convert to schema
        candle_schemas = [
            CandleSchema(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume
            ) for c in candles
        ]
        
        return {"candles": candle_schemas}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indicators", response_model=IndicatorResponse)
async def calculate_indicators(
    asset: str = Query(..., description="Trading asset"),
    timeframe: str = Query(..., description="Timeframe"),
    indicators: List[str] = Query(..., description="List of indicators to calculate"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate indicators for an asset."""
    # Fetch candles first
    service = MarketDataService(db)
    
    end_date = datetime.now()
    # Fetch enough data for indicators (limit + buffer)
    buffer_multiplier = 3 
    if timeframe == '15m':
        delta = timedelta(minutes=15 * limit * buffer_multiplier)
    elif timeframe == '1h':
        delta = timedelta(hours=1 * limit * buffer_multiplier)
    elif timeframe == '4h':
        delta = timedelta(hours=4 * limit * buffer_multiplier)
    elif timeframe == '1d':
        delta = timedelta(days=1 * limit * buffer_multiplier)
    else:
        delta = timedelta(days=90)
        
    start_date = end_date - delta
    
    try:
        candles = await service.get_historical_data(
            asset=asset,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if not candles:
            raise HTTPException(status_code=404, detail="No data found")

        # Initialize calculator
        calculator = IndicatorCalculator(
            candles=candles,
            enabled_indicators=indicators,
            mode="omni" # Allow all indicators for this endpoint
        )
        
        # Calculate for all candles
        # We only return the last 'limit' results
        result_indicators = {}
        timestamps = []
        
        # Pre-initialize lists in dict
        for ind in indicators:
            result_indicators[ind] = []
            
        # We take the last 'limit' candles
        target_candles = candles[-limit:]
        start_index = len(candles) - len(target_candles)
        
        for i in range(start_index, len(candles)):
            # Calculate at this index
            values = calculator.calculate_all(i)
            timestamps.append(candles[i].timestamp)
            
            for ind in indicators:
                result_indicators[ind].append(values.get(ind))
                
        return {
            "indicators": result_indicators,
            "timestamps": timestamps
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
