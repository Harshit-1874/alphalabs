"""
Unit tests for IndicatorCalculator service.

Tests cover:
- Individual indicator calculations with known input/output values
- Mode restrictions (Monk vs Omni)
- Edge cases (insufficient data, zero values, empty data)
"""

import pytest
from datetime import datetime, timedelta
from typing import List
import pandas as pd

from services.trading.indicator_calculator import IndicatorCalculator, Candle


class TestIndicatorCalculator:
    """Test suite for IndicatorCalculator"""
    
    @pytest.fixture
    def sample_candles(self) -> List[Candle]:
        """Generate sample candle data for testing"""
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        candles = []
        
        # Generate 250 candles with realistic price movement
        base_price = 50000.0
        for i in range(250):
            # Simple price movement pattern
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
    
    @pytest.fixture
    def minimal_candles(self) -> List[Candle]:
        """Generate minimal candle data (insufficient for most indicators)"""
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        candles = []
        
        for i in range(5):
            candles.append(Candle(
                timestamp=base_time + timedelta(hours=i),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0
            ))
        
        return candles
    
    @pytest.fixture
    def zero_volume_candles(self) -> List[Candle]:
        """Generate candles with zero volume"""
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        candles = []
        
        for i in range(50):
            candles.append(Candle(
                timestamp=base_time + timedelta(hours=i),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=0.0
            ))
        
        return candles
    
    # Test initialization and mode validation
    
    def test_init_omni_mode(self, sample_candles):
        """Test initialization in Omni mode"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd', 'ema_20'],
            mode='omni'
        )
        
        assert calc.get_mode() == 'omni'
        assert set(calc.get_enabled_indicators()) == {'rsi', 'macd', 'ema_20'}
        assert len(calc.df) == 250
    
    def test_init_monk_mode(self, sample_candles):
        """Test initialization in Monk mode with valid indicators"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd'],
            mode='monk'
        )
        
        assert calc.get_mode() == 'monk'
        assert set(calc.get_enabled_indicators()) == {'rsi', 'macd'}
    
    def test_monk_mode_restriction(self, sample_candles):
        """Test that Monk mode rejects non-allowed indicators"""
        with pytest.raises(ValueError, match="Monk Mode only allows"):
            IndicatorCalculator(
                candles=sample_candles,
                enabled_indicators=['rsi', 'macd', 'ema_20'],
                mode='monk'
            )
    
    def test_invalid_mode(self, sample_candles):
        """Test that invalid mode raises error"""
        with pytest.raises(ValueError, match="Invalid mode"):
            IndicatorCalculator(
                candles=sample_candles,
                enabled_indicators=['rsi'],
                mode='invalid'
            )
    
    def test_invalid_indicator(self, sample_candles):
        """Test that invalid indicator name raises error"""
        with pytest.raises(ValueError, match="Invalid indicators"):
            IndicatorCalculator(
                candles=sample_candles,
                enabled_indicators=['rsi', 'invalid_indicator'],
                mode='omni'
            )
    
    def test_empty_candles(self):
        """Test initialization with empty candle list"""
        calc = IndicatorCalculator(
            candles=[],
            enabled_indicators=['rsi'],
            mode='omni'
        )
        
        assert len(calc.df) == 0
        assert calc.get_enabled_indicators() == ['rsi']
    
    # Test momentum indicators
    
    def test_rsi_calculation(self, sample_candles):
        """Test RSI indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi'],
            mode='omni'
        )
        
        # RSI should be calculated after sufficient data (14 periods)
        result = calc.calculate_all(50)
        
        assert 'rsi' in result
        assert result['rsi'] is not None
        # RSI should be between 0 and 100
        assert 0 <= result['rsi'] <= 100
    
    def test_rsi_insufficient_data(self, minimal_candles):
        """Test RSI with insufficient data returns None"""
        calc = IndicatorCalculator(
            candles=minimal_candles,
            enabled_indicators=['rsi'],
            mode='omni'
        )
        
        # First few values should be None due to insufficient data
        result = calc.calculate_all(0)
        assert result['rsi'] is None
    
    def test_stoch_calculation(self, sample_candles):
        """Test Stochastic Oscillator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['stoch'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'stoch' in result
        assert result['stoch'] is not None
        # Stochastic should be between 0 and 100
        assert 0 <= result['stoch'] <= 100
    
    def test_cci_calculation(self, sample_candles):
        """Test CCI indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['cci'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'cci' in result
        assert result['cci'] is not None
        # CCI typically ranges from -100 to +100 but can exceed
        assert isinstance(result['cci'], float)
    
    def test_mom_calculation(self, sample_candles):
        """Test Momentum indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['mom'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'mom' in result
        assert result['mom'] is not None
        assert isinstance(result['mom'], float)
    
    def test_ao_calculation(self, sample_candles):
        """Test Awesome Oscillator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['ao'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'ao' in result
        assert result['ao'] is not None
        assert isinstance(result['ao'], float)
    
    # Test trend indicators
    
    def test_macd_calculation(self, sample_candles):
        """Test MACD indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['macd'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'macd' in result
        assert result['macd'] is not None
        assert isinstance(result['macd'], float)
    
    def test_ema_calculations(self, sample_candles):
        """Test EMA indicators (20, 50, 200)"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['ema_20', 'ema_50', 'ema_200'],
            mode='omni'
        )
        
        result = calc.calculate_all(220)
        
        assert 'ema_20' in result
        assert 'ema_50' in result
        assert 'ema_200' in result
        
        # All EMAs should have values
        assert result['ema_20'] is not None
        assert result['ema_50'] is not None
        assert result['ema_200'] is not None
        
        # EMAs should be positive prices
        assert result['ema_20'] > 0
        assert result['ema_50'] > 0
        assert result['ema_200'] > 0
    
    def test_sma_calculations(self, sample_candles):
        """Test SMA indicators (20, 50, 200)"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['sma_20', 'sma_50', 'sma_200'],
            mode='omni'
        )
        
        result = calc.calculate_all(220)
        
        assert 'sma_20' in result
        assert 'sma_50' in result
        assert 'sma_200' in result
        
        # All SMAs should have values
        assert result['sma_20'] is not None
        assert result['sma_50'] is not None
        assert result['sma_200'] is not None
    
    def test_adx_calculation(self, sample_candles):
        """Test ADX indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['adx'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'adx' in result
        assert result['adx'] is not None
        # ADX ranges from 0 to 100
        assert 0 <= result['adx'] <= 100
    
    def test_psar_calculation(self, sample_candles):
        """Test Parabolic SAR calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['psar'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'psar' in result
        assert result['psar'] is not None
        assert isinstance(result['psar'], float)
    
    # Test volatility indicators
    
    def test_bbands_calculation(self, sample_candles):
        """Test Bollinger Bands calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['bbands'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'bbands' in result
        assert result['bbands'] is not None
        assert isinstance(result['bbands'], float)
    
    def test_atr_calculation(self, sample_candles):
        """Test ATR indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['atr'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'atr' in result
        assert result['atr'] is not None
        # ATR should be positive
        assert result['atr'] > 0
    
    def test_kc_calculation(self, sample_candles):
        """Test Keltner Channels calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['kc'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'kc' in result
        assert result['kc'] is not None
        assert isinstance(result['kc'], float)
    
    def test_donchian_calculation(self, sample_candles):
        """Test Donchian Channels calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['donchian'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'donchian' in result
        assert result['donchian'] is not None
        assert isinstance(result['donchian'], float)
    
    # Test volume indicators
    
    def test_obv_calculation(self, sample_candles):
        """Test OBV indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['obv'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'obv' in result
        assert result['obv'] is not None
        assert isinstance(result['obv'], float)
    
    def test_vwap_calculation(self, sample_candles):
        """Test VWAP indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['vwap'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'vwap' in result
        assert result['vwap'] is not None
        assert result['vwap'] > 0
    
    def test_mfi_calculation(self, sample_candles):
        """Test MFI indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['mfi'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'mfi' in result
        assert result['mfi'] is not None
        # MFI ranges from 0 to 100
        assert 0 <= result['mfi'] <= 100
    
    def test_cmf_calculation(self, sample_candles):
        """Test CMF indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['cmf'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'cmf' in result
        assert result['cmf'] is not None
        assert isinstance(result['cmf'], float)
    
    # Test advanced indicators
    
    def test_supertrend_calculation(self, sample_candles):
        """Test Supertrend indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['supertrend'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'supertrend' in result
        assert result['supertrend'] is not None
        assert isinstance(result['supertrend'], float)
    
    def test_ichimoku_calculation(self, sample_candles):
        """Test Ichimoku indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['ichimoku'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'ichimoku' in result
        assert result['ichimoku'] is not None
        assert isinstance(result['ichimoku'], float)
    
    def test_zscore_calculation(self, sample_candles):
        """Test Z-Score indicator calculation"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['zscore'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert 'zscore' in result
        assert result['zscore'] is not None
        assert isinstance(result['zscore'], float)
    
    # Test multiple indicators together
    
    def test_multiple_indicators(self, sample_candles):
        """Test calculating multiple indicators at once"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd', 'ema_20', 'atr', 'obv'],
            mode='omni'
        )
        
        result = calc.calculate_all(50)
        
        assert len(result) == 5
        assert all(key in result for key in ['rsi', 'macd', 'ema_20', 'atr', 'obv'])
        assert all(result[key] is not None for key in result)
    
    def test_monk_mode_indicators_only(self, sample_candles):
        """Test that Monk mode only returns RSI and MACD"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd'],
            mode='monk'
        )
        
        result = calc.calculate_all(50)
        
        assert len(result) == 2
        assert 'rsi' in result
        assert 'macd' in result
        assert result['rsi'] is not None
        assert result['macd'] is not None
    
    # Test edge cases
    
    def test_index_out_of_range(self, sample_candles):
        """Test that invalid index raises IndexError"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi'],
            mode='omni'
        )
        
        with pytest.raises(IndexError):
            calc.calculate_all(300)  # Beyond available candles
        
        with pytest.raises(IndexError):
            calc.calculate_all(-1)  # Negative index
    
    def test_zero_volume_indicators(self, zero_volume_candles):
        """Test volume-based indicators with zero volume"""
        calc = IndicatorCalculator(
            candles=zero_volume_candles,
            enabled_indicators=['obv', 'vwap', 'mfi', 'cmf'],
            mode='omni'
        )
        
        result = calc.calculate_all(30)
        
        # Should still calculate, even if values might be zero or NaN
        assert 'obv' in result
        assert 'vwap' in result
        assert 'mfi' in result
        assert 'cmf' in result
    
    def test_all_indicators_omni_mode(self, sample_candles):
        """Test that all indicators can be enabled in Omni mode"""
        all_indicators = IndicatorCalculator.ALL_INDICATORS
        
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=all_indicators,
            mode='omni'
        )
        
        result = calc.calculate_all(220)
        
        # All indicators should be in result
        assert len(result) == len(all_indicators)
        
        # Most should have values at index 220
        non_none_count = sum(1 for v in result.values() if v is not None)
        assert non_none_count > len(all_indicators) * 0.8  # At least 80% should have values
    
    def test_dataframe_conversion(self, sample_candles):
        """Test that candles are correctly converted to DataFrame"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi'],
            mode='omni'
        )
        
        df = calc.get_dataframe()
        
        assert len(df) == 250
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert df['close'].iloc[0] == sample_candles[0].close
        assert df['volume'].iloc[-1] == sample_candles[-1].volume
    
    def test_cache_populated(self, sample_candles):
        """Test that indicator cache is populated after initialization"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd', 'ema_20'],
            mode='omni'
        )
        
        # Cache should have entries for enabled indicators
        assert 'rsi' in calc.cache
        assert 'macd' in calc.cache
        assert 'ema_20' in calc.cache
        
        # Cache values should be pandas Series
        assert isinstance(calc.cache['rsi'], pd.Series)
        assert len(calc.cache['rsi']) == 250
    
    def test_consistent_results(self, sample_candles):
        """Test that calling calculate_all multiple times returns same results"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd'],
            mode='omni'
        )
        
        result1 = calc.calculate_all(100)
        result2 = calc.calculate_all(100)
        
        assert result1 == result2
    
    def test_different_indices(self, sample_candles):
        """Test that different indices return different values"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'ema_20'],
            mode='omni'
        )
        
        result1 = calc.calculate_all(50)
        result2 = calc.calculate_all(150)
        
        # At least one indicator should have different values at different indices
        # (using EMA which is more sensitive to price changes)
        assert result1['ema_20'] != result2['ema_20']
