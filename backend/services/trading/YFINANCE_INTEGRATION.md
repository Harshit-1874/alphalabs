# yfinance Integration Guide

## Overview

The `IndicatorCalculator` is fully compatible with data from yfinance. This document shows how to convert yfinance data to our `Candle` format for backtesting.

## Data Format Compatibility

### yfinance Output
```python
import yfinance as yf

ticker = yf.Ticker("BTC-USD")
df = ticker.history(period="1mo", interval="1h")

# DataFrame structure:
# Index: DatetimeIndex
# Columns: Open, High, Low, Close, Volume
```

### Our Candle Format
```python
@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

## Conversion Pattern

### Simple Conversion
```python
from services.trading.indicator_calculator import Candle
import yfinance as yf

# Fetch data
ticker = yf.Ticker("BTC-USD")
df = ticker.history(period="3mo", interval="1h")

# Convert to Candle objects
candles = [
    Candle(
        timestamp=index,
        open=float(row['Open']),
        high=float(row['High']),
        low=float(row['Low']),
        close=float(row['Close']),
        volume=float(row['Volume'])
    )
    for index, row in df.iterrows()
]

# Use with IndicatorCalculator
from services.trading.indicator_calculator import IndicatorCalculator

calc = IndicatorCalculator(
    candles=candles,
    enabled_indicators=['rsi', 'macd', 'ema_20', 'sma_50'],
    mode='omni'
)

# Calculate indicators for the latest candle
result = calc.calculate_all(len(candles) - 1)
print(result)
# {'rsi': 45.2, 'macd': 123.4, 'ema_20': 42500.0, 'sma_50': 42300.0}
```

## Market Data Service Implementation

When implementing the `MarketDataService`, use this pattern:

```python
class MarketDataService:
    async def get_historical_data(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        """Fetch historical data from yfinance"""
        
        # Map our asset format to yfinance ticker
        ticker_map = {
            'BTC/USDT': 'BTC-USD',
            'ETH/USDT': 'ETH-USD',
            'SOL/USDT': 'SOL-USD'
        }
        
        # Map our timeframe to yfinance interval
        interval_map = {
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        
        ticker_symbol = ticker_map.get(asset, asset)
        interval = interval_map.get(timeframe, '1h')
        
        # Fetch from yfinance
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval
        )
        
        # Convert to Candle objects
        candles = [
            Candle(
                timestamp=index.to_pydatetime(),
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=float(row['Volume'])
            )
            for index, row in df.iterrows()
        ]
        
        return candles
```

## Data Requirements

### Minimum Data for Indicators

Different indicators require different amounts of historical data:

| Indicator | Minimum Candles | Notes |
|-----------|----------------|-------|
| RSI | 14 | Default period |
| MACD | 26 | Slow EMA period |
| EMA_20 | 20 | Period length |
| EMA_50 | 50 | Period length |
| EMA_200 | 200 | Period length |
| SMA_20 | 20 | Period length |
| SMA_50 | 50 | Period length |
| SMA_200 | 200 | Period length |
| ATR | 14 | Default period |
| Bollinger Bands | 20 | Default period |
| Stochastic | 14 | Default period |

**Recommendation:** Fetch at least **250 candles** to ensure all indicators have sufficient data.

## Edge Cases Handled

The `IndicatorCalculator` handles these yfinance edge cases:

1. **Insufficient Data**: Returns `None` for indicators that don't have enough historical data
2. **Small Prices**: Works correctly with altcoins that have very small price values (e.g., 0.00012)
3. **Large Volumes**: Handles large volume numbers correctly
4. **Missing Data**: Gracefully handles NaN values in the data

## Example: Complete Backtest Setup

```python
import yfinance as yf
from datetime import datetime, timedelta
from services.trading.indicator_calculator import IndicatorCalculator, Candle

# 1. Fetch historical data
ticker = yf.Ticker("BTC-USD")
end_date = datetime.now()
start_date = end_date - timedelta(days=90)  # 3 months

df = ticker.history(
    start=start_date,
    end=end_date,
    interval="1h"
)

# 2. Convert to Candles
candles = [
    Candle(
        timestamp=index.to_pydatetime(),
        open=float(row['Open']),
        high=float(row['High']),
        low=float(row['Low']),
        close=float(row['Close']),
        volume=float(row['Volume'])
    )
    for index, row in df.iterrows()
]

print(f"Loaded {len(candles)} candles")

# 3. Initialize IndicatorCalculator
calc = IndicatorCalculator(
    candles=candles,
    enabled_indicators=['rsi', 'macd', 'ema_20', 'sma_50', 'atr', 'obv'],
    mode='omni'
)

# 4. Process each candle in backtest
for i in range(50, len(candles)):  # Start at 50 to ensure indicators have data
    candle = candles[i]
    indicators = calc.calculate_all(i)
    
    print(f"Candle {i}: {candle.timestamp}")
    print(f"  Close: ${candle.close:,.2f}")
    print(f"  RSI: {indicators['rsi']:.2f}")
    print(f"  MACD: {indicators['macd']:.2f}")
    print(f"  EMA_20: ${indicators['ema_20']:,.2f}")
    
    # Here you would:
    # - Send candle + indicators to AI for decision
    # - Execute trades based on AI decision
    # - Update position manager
    # - Broadcast events via WebSocket
```

## Performance Notes

- **Pre-calculation**: All indicators are calculated once during initialization and cached
- **Fast Lookup**: `calculate_all(index)` is O(1) - just dictionary lookups
- **Memory Efficient**: Uses pandas Series for storage, which is memory-optimized
- **Typical Performance**: <100ms to calculate all 20+ indicators for 1000 candles

## Testing

Run the integration tests to verify compatibility:

```bash
cd backend
python -m pytest tests/test_yfinance_integration.py -v
```

All tests should pass, confirming that:
- Data format conversion works correctly
- All indicators calculate properly with yfinance data
- Edge cases are handled gracefully
- Sufficient data requirements are met
