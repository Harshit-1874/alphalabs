# Trading Services

## Indicator Calculator (The Buffet)

The Indicator Calculator service provides technical indicator calculations for trading strategies.

### Features

- **22+ Technical Indicators** across 5 categories:
  - **Momentum**: RSI, Stochastic, CCI, Momentum, Awesome Oscillator
  - **Trend**: MACD, EMA (20/50/200), SMA (20/50/200), ADX, Parabolic SAR
  - **Volatility**: Bollinger Bands, ATR, Keltner Channels, Donchian Channels
  - **Volume**: OBV, VWAP, MFI, Chaikin Money Flow
  - **Advanced**: Supertrend, Ichimoku, Z-Score

- **Mode-Based Restrictions**:
  - **Monk Mode**: Only RSI and MACD (information deprivation for focused strategies)
  - **Omni Mode**: All indicators available

- **Efficient Caching**: Pre-calculates all indicators once using pandas for fast lookups

### Usage

```python
from indicator_calculator import IndicatorCalculator, Candle
from datetime import datetime

# Create candle data
candles = [
    Candle(
        timestamp=datetime(2024, 1, 1, 0, 0),
        open=50000.0,
        high=50500.0,
        low=49500.0,
        close=50200.0,
        volume=1000000.0
    ),
    # ... more candles
]

# Initialize calculator in Omni Mode with selected indicators
calc = IndicatorCalculator(
    candles=candles,
    enabled_indicators=['rsi', 'macd', 'ema_20', 'atr', 'vwap'],
    mode='omni'
)

# Get indicator values for a specific candle
indicators = calc.calculate_all(index=50)
print(indicators)
# Output: {'rsi': 46.32, 'macd': 81.04, 'ema_20': 50694.33, 'atr': 252.27, 'vwap': 50698.24}

# Monk Mode - only RSI and MACD allowed
monk_calc = IndicatorCalculator(
    candles=candles,
    enabled_indicators=['rsi', 'macd'],
    mode='monk'
)
```

### Error Handling

The calculator handles several edge cases:

- **Insufficient Data**: Returns `None` for indicators that need more historical data
- **Invalid Indicators**: Raises `ValueError` for unknown indicator names
- **Mode Violations**: Raises `ValueError` if Monk Mode restrictions are violated

### Implementation Details

- Uses the `ta` library for all technical indicator calculations
- Converts candle data to pandas DataFrame for efficient computation
- Caches all indicator values for O(1) lookup performance
- Handles NaN values gracefully by converting to `None` for JSON serialization

### Testing

Run the test suite:

```bash
python backend/services/trading/test_indicator_calculator.py
```

The test suite covers:
- Monk Mode restrictions
- Omni Mode functionality
- All indicator categories
- Insufficient data handling
- Invalid indicator validation
