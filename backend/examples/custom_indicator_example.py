"""
Example usage of Custom Indicator Engine with IndicatorCalculator.

This script demonstrates how to:
1. Define custom indicators using JSON rules
2. Integrate them with the IndicatorCalculator
3. Calculate and retrieve custom indicator values
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from services.trading import IndicatorCalculator, Candle

# Generate sample candle data
def generate_sample_candles(count=250):
    """Generate sample candle data for demonstration"""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []
    
    base_price = 50000.0
    for i in range(count):
        price = base_price + (i * 10) + (100 * (i % 10))
        candles.append(Candle(
            timestamp=base_time + timedelta(hours=i),
            open=price,
            high=price + 50,
            low=price - 50,
            close=price + 25,
            volume=1000000.0 + (i * 1000)
        ))
    
    return candles


# Define custom indicator rules
custom_indicator_rules = [
    # Example 1: Price Momentum
    # Formula: (rsi + 50) * 0.01
    {
        "name": "price_momentum",
        "type": "composite",
        "formula": {
            "operator": "*",
            "left": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            },
            "right": {"value": 0.01}
        }
    },
    
    # Example 2: Mean Reversion Signal
    # Formula: (close - sma_50) / atr
    {
        "name": "mean_reversion",
        "type": "composite",
        "formula": {
            "operator": "/",
            "left": {
                "operator": "-",
                "left": {"indicator": "close"},
                "right": {"indicator": "sma_50"}
            },
            "right": {"indicator": "atr"}
        }
    },
    
    # Example 3: Volatility Ratio
    # Formula: (high - low) / close
    {
        "name": "volatility_ratio",
        "type": "composite",
        "formula": {
            "operator": "/",
            "left": {
                "operator": "-",
                "left": {"indicator": "high"},
                "right": {"indicator": "low"}
            },
            "right": {"indicator": "close"}
        }
    },
    
    # Example 4: Weighted RSI
    # Formula: rsi * 0.7
    {
        "name": "weighted_rsi",
        "type": "derived",
        "formula": {
            "operator": "*",
            "left": {"indicator": "rsi"},
            "right": {"value": 0.7}
        }
    },
    
    # Example 5: Complex Signal (referencing another custom indicator)
    # Formula: weighted_rsi + 10
    {
        "name": "adjusted_signal",
        "type": "composite",
        "formula": {
            "operator": "+",
            "left": {"indicator": "weighted_rsi"},
            "right": {"value": 10}
        }
    }
]


def main():
    """Main demonstration function"""
    print("=" * 80)
    print("Custom Indicator Engine Example")
    print("=" * 80)
    print()
    
    # Generate sample data
    print("Generating sample candle data...")
    candles = generate_sample_candles(250)
    print(f"Generated {len(candles)} candles")
    print()
    
    # Initialize IndicatorCalculator with custom indicators
    print("Initializing IndicatorCalculator with custom indicators...")
    calc = IndicatorCalculator(
        candles=candles,
        enabled_indicators=['rsi', 'macd', 'sma_50', 'atr'],
        custom_indicators=custom_indicator_rules,
        mode='omni'
    )
    print("Initialization complete!")
    print()
    
    # Display enabled indicators
    print("Enabled Standard Indicators:")
    for indicator in calc.get_enabled_indicators():
        print(f"  - {indicator}")
    print()
    
    # Display custom indicators
    print("Custom Indicators:")
    for indicator in calc.get_custom_indicator_names():
        print(f"  - {indicator}")
    print()
    
    # Calculate indicators at a specific index
    index = 100
    print(f"Calculating all indicators at index {index}...")
    result = calc.calculate_all(index)
    print()
    
    # Display results
    print("Standard Indicators:")
    for key in ['rsi', 'macd', 'sma_50', 'atr']:
        if key in result:
            print(f"  {key:20s}: {result[key]:>12.4f}")
    print()
    
    print("Custom Indicators:")
    for key in calc.get_custom_indicator_names():
        if key in result:
            print(f"  {key:20s}: {result[key]:>12.4f}")
    print()
    
    # Show OHLCV data for context
    print("OHLCV Data at index {}:".format(index))
    candle = candles[index]
    print(f"  Open:   {candle.open:>12.2f}")
    print(f"  High:   {candle.high:>12.2f}")
    print(f"  Low:    {candle.low:>12.2f}")
    print(f"  Close:  {candle.close:>12.2f}")
    print(f"  Volume: {candle.volume:>12.0f}")
    print()
    
    # Demonstrate calculation at different indices
    print("Indicator values at different time points:")
    print("-" * 80)
    print(f"{'Index':<10} {'RSI':<12} {'Price Momentum':<18} {'Mean Reversion':<18}")
    print("-" * 80)
    
    for idx in [50, 100, 150, 200]:
        result = calc.calculate_all(idx)
        rsi = result.get('rsi', 0)
        momentum = result.get('price_momentum', 0)
        mean_rev = result.get('mean_reversion', 0)
        print(f"{idx:<10} {rsi:<12.2f} {momentum:<18.4f} {mean_rev:<18.4f}")
    
    print()
    print("=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
