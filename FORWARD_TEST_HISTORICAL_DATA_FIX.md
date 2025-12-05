# Forward Test Historical Data Fix

## Problem

When creating a forward test, the historical chart data for the asset was not loading. Users would see an empty chart instead of seeing the historical price action and indicators.

## Root Cause

The issue was in the `backend/services/trading/forward_engine/engine.py` file, specifically in the `_process_forward_test` method around lines 400-430.

### What Was Happening

1. The code was setting `end_date = datetime.now(timezone.utc)` - the current time
2. It would then request historical data up to NOW
3. **Problem**: Market data providers like yfinance don't have data for incomplete candles
   - Example: If it's 3:30 PM and you're using 1h timeframe, yfinance doesn't have the 3:00-4:00 PM candle yet because it's not complete
   - This would cause the API call to return no data or incomplete data
4. The error was being caught silently, and the forward test would continue WITHOUT historical data

### Why It Was Hard to Spot

- The error was logged as a warning: `logger.warning(f"No historical candles fetched for {session_state.asset}")`
- The forward test would still start, just without historical context
- No error was shown to the user in the UI

## The Fix

### 1. Adjusted `end_date` Calculation

Instead of requesting data up to NOW, we now request data up to the **last complete candle**:

```python
# BEFORE (Broken):
end_date = datetime.now(timezone.utc)

# AFTER (Fixed):
if session_state.timeframe == '15m':
    # For 15m, go back 30 minutes to ensure we get complete candles
    end_date = now - timedelta(minutes=30)
elif session_state.timeframe == '1h':
    # For 1h, go back 2 hours to ensure we get complete candles
    end_date = now - timedelta(hours=2)
elif session_state.timeframe == '4h':
    # For 4h, go back 8 hours to ensure we get complete candles
    end_date = now - timedelta(hours=8)
elif session_state.timeframe == '1d':
    # For 1d, go back 2 days to ensure we get complete candles
    end_date = now - timedelta(days=2)
```

**Why this works**: By going back a bit further than the current time, we ensure we're only requesting complete candles that yfinance has data for.

### 2. Improved Error Logging

Added much more visible error messages with emojis and detailed information:

```python
# Clear success message:
logger.info(
    f"✓ Successfully fetched {len(historical_candles)} historical candles "
    f"for {session_state.asset} {session_state.timeframe} "
    f"(from {historical_candles[0].timestamp.date()} to {historical_candles[-1].timestamp.date()})"
)

# Clear warning when no data:
logger.warning(
    f"⚠️ WARNING: No historical candles fetched for {session_state.asset} {session_state.timeframe}! "
    f"Forward test will start WITHOUT historical chart data."
)

# Clear error message:
logger.error(
    f"❌ ERROR: Could not fetch historical candles: {e}"
)
```

### 3. User-Facing Error Messages

Added WebSocket broadcasts to show errors to users in the UI:

```python
await self.broadcaster.broadcast_error(
    session_id,
    "Historical data unavailable - starting with limited context"
)
```

## Testing

To test the fix:

1. Create a new forward test
2. You should now see:
   - Historical candles loading on the chart
   - Indicators calculated for historical candles
   - Complete chart context before the forward test starts

## Files Changed

- `backend/services/trading/forward_engine/engine.py`
  - Lines ~400-430: Fixed date calculation logic
  - Lines ~433-450: Improved success logging
  - Lines ~529-550: Improved error logging and user feedback

## Impact

- ✅ Forward tests now show full historical chart data
- ✅ Indicators are properly initialized with historical context
- ✅ AI agent has proper market context when making first decision
- ✅ Better error visibility for debugging
- ✅ Clear user feedback when data loading fails

## Related Issues

This fix aligns the forward test behavior with the backtest behavior, which was already working correctly. Both now use the same approach to fetch historical data, ensuring consistency across the platform.

