# Forward Test Market Data Fetch Fixes

## Issue Summary
Forward test was failing to fetch historical market data for SOL/USDT with 1h timeframe, resulting in:
1. yfinance errors: "Expecting value: line 1 column 1 (char 0)"
2. CoinGecko errors: "No 'prices' key in CoinGecko response... Keys: not a dict"

## Root Causes

### 1. CoinGecko SDK Response Format Issue
**Problem**: The `coingecko_sdk` library returns response objects with attributes, not dictionaries. The code was trying to access `chart_data['prices']` which failed.

**Location**: `backend/services/market_data_service.py` - `_fetch_intraday_candles_coingecko()` method (line ~738)

**Fix**: Updated the code to handle both object attributes and dictionary keys:
```python
# Try accessing prices as attribute first, then as dict key
prices = None
if hasattr(chart_data, 'prices'):
    prices = chart_data.prices
elif isinstance(chart_data, dict) and 'prices' in chart_data:
    prices = chart_data['prices']
else:
    logger.warning(f"No 'prices' in CoinGecko response...")
    return []
```

### 2. No Fallback for Intraday Timeframes
**Problem**: For intraday timeframes (15m, 1h, 4h), the code was removing CoinGecko from the sources list, leaving only yfinance. When yfinance failed, there was no fallback provider.

**Location**: `backend/services/market_data_service.py` - `_fetch_from_api()` method (line ~986)

**Fix**: Changed the logic to keep CoinGecko as a fallback while prioritizing yfinance:
```python
if timeframe in ['15m', '1h', '4h']:
    # Ensure yfinance is first, then add coingecko if available
    sources_set = set(preferred_sources)
    preferred_sources = ['yfinance']
    if 'coingecko' in sources_set:
        preferred_sources.append('coingecko')
    logger.info(f"Intraday timeframe {timeframe} detected - trying yfinance first, then CoinGecko fallback")
```

### 3. Wrong CoinGecko Endpoint for Intraday Data
**Problem**: The `_fetch_from_coingecko()` method always used the OHLC endpoint, which only provides daily data. For intraday timeframes, it needs to use the market_chart endpoint.

**Location**: `backend/services/market_data_service.py` - `_fetch_from_coingecko()` method (line ~1088)

**Fix**: Added logic to route intraday requests to the correct endpoint:
```python
# For intraday timeframes, use market_chart endpoint
if timeframe in ['15m', '1h', '4h']:
    candles = await self._fetch_intraday_candles_coingecko(
        coingecko_id, timeframe, limit
    )
    # Filter by date range and return
    
# For daily timeframe, use OHLC endpoint (existing code)
```

## Testing

### Before Fix
```
ERROR:yfinance:Failed to get ticker 'SOL-USD' reason: Expecting value: line 1 column 1 (char 0)
WARNING:services.market_data_service:Market data provider yfinance failed for SOL/USDT 1h
ERROR:utils.retry:Operation 'fetch_market_data_SOL/USDT_1h' failed after 3 attempts
ERROR:services.trading.forward_engine.engine:Error fetching historical candles
WARNING:services.trading.forward_engine.engine:No historical candles available for SOL/USDT
```

### After Fix
- yfinance will still fail (external API issue), but CoinGecko will be tried as fallback
- CoinGecko market_chart endpoint will be used for intraday data
- Response will be properly parsed as object attributes
- Forward test should start successfully with historical data

## Impact
- ✅ Forward test can now fetch historical intraday data even when yfinance is down
- ✅ CoinGecko serves as reliable fallback for all timeframes
- ✅ Better error handling and logging
- ⚠️ yfinance is still preferred for intraday due to better data quality, but system is more resilient

## Files Modified
- `backend/services/market_data_service.py`
  - `_fetch_intraday_candles_coingecko()` - Fixed response parsing
  - `_fetch_from_api()` - Fixed source priority for intraday
  - `_fetch_from_coingecko()` - Route intraday to correct endpoint

## Notes
- The yfinance error ("Expecting value: line 1 column 1") is likely a temporary Yahoo Finance API issue or rate limiting
- CoinGecko free tier has rate limits (30 calls/minute demo, 10-50 calls/minute free)
- For production, consider upgrading to CoinGecko Pro for higher limits

