"""
Integration test to verify IndicatorCalculator works with yfinance data format.

This test demonstrates that the indicator calculator can process real market data
from yfinance, which will be used for backtesting.
"""

import pytest
from datetime import datetime
from typing import List

from services.trading.indicator_calculator import IndicatorCalculator, Candle


class TestYFinanceIntegration:
    """Test that IndicatorCalculator works with yfinance data format"""
    
    def test_yfinance_data_format_compatibility(self):
        """
        Test that our Candle dataclass matches yfinance DataFrame structure.
        
        yfinance returns a DataFrame with columns:
        - Open, High, Low, Close, Volume
        - Index is datetime
        
        Our Candle expects:
        - timestamp (datetime), open, high, low, close, volume (all floats)
        """
        # Simulate yfinance data structure
        # In real usage, you would do:
        # import yfinance as yf
        # ticker = yf.Ticker("BTC-USD")
        # df = ticker.history(period="1mo", interval="1h")
        
        # Mock yfinance-like data
        yfinance_data = [
            {
                'timestamp': datetime(2024, 1, 1, 0, 0),
                'Open': 42000.50,
                'High': 42500.75,
                'Low': 41800.25,
                'Close': 42300.00,
                'Volume': 1500000000.0
            },
            {
                'timestamp': datetime(2024, 1, 1, 1, 0),
                'Open': 42300.00,
                'High': 42800.00,
                'Low': 42100.00,
                'Close': 42600.50,
                'Volume': 1600000000.0
            },
            # Add more candles for indicator calculation
        ]
        
        # Add 100 more candles with realistic price movement
        base_price = 42600.50
        from datetime import timedelta
        for i in range(2, 102):
            price = base_price + (i * 50) + (100 * (i % 5))
            yfinance_data.append({
                'timestamp': datetime(2024, 1, 1, 0, 0) + timedelta(hours=i),
                'Open': price,
                'High': price + 200,
                'Low': price - 200,
                'Close': price + 100,
                'Volume': 1500000000.0 + (i * 10000000)
            })
        
        # Convert yfinance format to our Candle format
        candles = [
            Candle(
                timestamp=row['timestamp'],
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=float(row['Volume'])
            )
            for row in yfinance_data
        ]
        
        # Test that IndicatorCalculator can process this data
        calc = IndicatorCalculator(
            candles=candles,
            enabled_indicators=['rsi', 'macd', 'ema_20', 'sma_50', 'atr', 'obv'],
            mode='omni'
        )
        
        # Verify indicators are calculated
        result = calc.calculate_all(50)
        
        assert 'rsi' in result
        assert 'macd' in result
        assert 'ema_20' in result
        assert 'sma_50' in result
        assert 'atr' in result
        assert 'obv' in result
        
        # All indicators should have values at index 50
        assert result['rsi'] is not None
        assert result['macd'] is not None
        assert result['ema_20'] is not None
        assert result['sma_50'] is not None
        assert result['atr'] is not None
        assert result['obv'] is not None
        
        # Verify values are reasonable
        assert 0 <= result['rsi'] <= 100
        assert result['ema_20'] > 0
        assert result['sma_50'] > 0
        assert result['atr'] > 0
    
    def test_yfinance_column_mapping(self):
        """
        Test that we can easily map yfinance DataFrame columns to Candle objects.
        
        This demonstrates the conversion pattern that will be used in the
        Market Data Service.
        """
        # Simulate a yfinance DataFrame row
        yf_row = {
            'Open': 50000.0,
            'High': 50500.0,
            'Low': 49500.0,
            'Close': 50200.0,
            'Volume': 2000000000.0
        }
        yf_timestamp = datetime(2024, 1, 15, 12, 0)
        
        # Convert to Candle (this is the pattern to use in MarketDataService)
        candle = Candle(
            timestamp=yf_timestamp,
            open=float(yf_row['Open']),
            high=float(yf_row['High']),
            low=float(yf_row['Low']),
            close=float(yf_row['Close']),
            volume=float(yf_row['Volume'])
        )
        
        # Verify conversion
        assert candle.timestamp == yf_timestamp
        assert candle.open == 50000.0
        assert candle.high == 50500.0
        assert candle.low == 49500.0
        assert candle.close == 50200.0
        assert candle.volume == 2000000000.0
    
    def test_handles_yfinance_edge_cases(self):
        """
        Test that IndicatorCalculator handles edge cases from yfinance data:
        - Missing volume data (some assets)
        - Very small price values (altcoins)
        - Very large volume values
        """
        # Test with small prices (like some altcoins)
        from datetime import timedelta
        base_time = datetime(2024, 1, 1, 0, 0)
        small_price_candles = [
            Candle(
                timestamp=base_time + timedelta(hours=i),
                open=0.00012 + (i * 0.000001),
                high=0.00013 + (i * 0.000001),
                low=0.00011 + (i * 0.000001),
                close=0.000125 + (i * 0.000001),
                volume=1000000000.0
            )
            for i in range(100)
        ]
        
        calc = IndicatorCalculator(
            candles=small_price_candles,
            enabled_indicators=['rsi', 'ema_20'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        # Should still calculate indicators correctly
        assert result['rsi'] is not None
        assert result['ema_20'] is not None
        assert 0 <= result['rsi'] <= 100
        assert result['ema_20'] > 0
    
    def test_sufficient_data_for_all_indicators(self):
        """
        Test that we know the minimum data requirements for each indicator.
        
        This is important for the Market Data Service to know how much
        historical data to fetch.
        """
        # Create exactly 200 candles (minimum for SMA_200)
        from datetime import timedelta
        base_time = datetime(2024, 1, 1, 0, 0)
        candles = [
            Candle(
                timestamp=base_time + timedelta(hours=i),
                open=50000.0 + i,
                high=50100.0 + i,
                low=49900.0 + i,
                close=50050.0 + i,
                volume=1000000.0
            )
            for i in range(200)
        ]
        
        # Test with indicators that need different amounts of data
        calc = IndicatorCalculator(
            candles=candles,
            enabled_indicators=['rsi', 'ema_20', 'sma_50', 'sma_200'],
            mode='omni'
        )
        
        # At index 199 (last candle), all should have values
        result = calc.calculate_all(199)
        
        assert result['rsi'] is not None  # Needs 14 periods
        assert result['ema_20'] is not None  # Needs 20 periods
        assert result['sma_50'] is not None  # Needs 50 periods
        assert result['sma_200'] is not None  # Needs 200 periods
        
        # But at earlier indices, some might be None
        early_result = calc.calculate_all(10)
        assert early_result['rsi'] is None  # Not enough data yet
        assert early_result['ema_20'] is None
        assert early_result['sma_50'] is None
        assert early_result['sma_200'] is None
    
    def test_real_world_data_pattern(self):
        """
        Test with a realistic price pattern that mimics actual market behavior.
        
        This ensures indicators work correctly with real-world volatility.
        """
        # Create candles with realistic price action
        candles = []
        base_time = datetime(2024, 1, 1, 0, 0)
        base_price = 45000.0
        
        for i in range(250):
            # Simulate some volatility and trend
            trend = i * 10  # Upward trend
            volatility = 200 * (1 if i % 3 == 0 else -1)  # Some noise
            
            price = base_price + trend + volatility
            
            candles.append(Candle(
                timestamp=base_time.replace(hour=i % 24, day=1 + i // 24),
                open=price,
                high=price + 150,
                low=price - 150,
                close=price + 50,
                volume=1500000000.0 + (i * 5000000)
            ))
        
        # Test with all indicator categories
        calc = IndicatorCalculator(
            candles=candles,
            enabled_indicators=[
                'rsi', 'macd',  # Momentum/Trend
                'ema_20', 'sma_50',  # Moving averages
                'bbands', 'atr',  # Volatility
                'obv', 'vwap'  # Volume
            ],
            mode='omni'
        )
        
        result = calc.calculate_all(220)
        
        # All indicators should work with realistic data
        assert all(result[key] is not None for key in result.keys())
        
        # Verify reasonable ranges
        assert 0 <= result['rsi'] <= 100
        assert result['ema_20'] > 0
        assert result['sma_50'] > 0
        assert result['atr'] > 0
        assert result['obv'] != 0  # Should accumulate volume
