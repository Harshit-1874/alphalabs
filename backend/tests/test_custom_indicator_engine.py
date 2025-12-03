"""
Unit tests for CustomIndicatorEngine.

Tests cover:
- JSON rule parsing and validation
- Recursive formula evaluation with nested operators
- Indicator reference resolution
- Circular dependency detection
- Error handling for invalid JSON structures
- Integration with IndicatorCalculator
"""

import pytest
from datetime import datetime, timedelta
from typing import List
import pandas as pd

from services.trading.indicator_calculator import IndicatorCalculator, Candle
from services.trading.custom_indicator_engine import CustomIndicatorEngine, CustomIndicatorError


class TestCustomIndicatorEngine:
    """Test suite for CustomIndicatorEngine"""
    
    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Generate sample DataFrame for testing"""
        data = {
            'open': [100.0 + i for i in range(50)],
            'high': [105.0 + i for i in range(50)],
            'low': [95.0 + i for i in range(50)],
            'close': [102.0 + i for i in range(50)],
            'volume': [1000.0 + (i * 10) for i in range(50)]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def available_indicators(self, sample_df) -> dict:
        """Generate available indicators for testing"""
        return {
            'open': sample_df['open'],
            'high': sample_df['high'],
            'low': sample_df['low'],
            'close': sample_df['close'],
            'volume': sample_df['volume'],
            'rsi': pd.Series([50.0 + i for i in range(50)]),
            'macd': pd.Series([10.0 + (i * 0.5) for i in range(50)]),
            'sma_50': pd.Series([100.0 + i for i in range(50)]),
            'atr': pd.Series([5.0 + (i * 0.1) for i in range(50)])
        }
    
    @pytest.fixture
    def sample_candles(self) -> List[Candle]:
        """Generate sample candle data for integration tests"""
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        candles = []
        
        for i in range(250):
            price = 50000.0 + (i * 10)
            candles.append(Candle(
                timestamp=base_time + timedelta(hours=i),
                open=price,
                high=price + 50,
                low=price - 50,
                close=price + 25,
                volume=1000000.0 + (i * 1000)
            ))
        
        return candles
    
    # Test initialization
    
    def test_init(self, sample_df, available_indicators):
        """Test engine initialization"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        assert engine.df is not None
        assert len(engine.available_indicators) == len(available_indicators)
        assert len(engine.custom_indicators) == 0
        assert len(engine.calculation_cache) == 0
    
    # Test rule validation
    
    def test_add_valid_rule(self, sample_df, available_indicators):
        """Test adding a valid custom indicator rule"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        engine.add_rule(rule)
        
        assert "test_indicator" in engine.custom_indicators
        assert engine.custom_indicators["test_indicator"] == rule
    
    def test_missing_required_field(self, sample_df, available_indicators):
        """Test that missing required fields raise error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        # Missing 'formula' field
        rule = {
            "name": "test_indicator",
            "type": "composite"
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INVALID_RULE_STRUCTURE'
        assert 'formula' in str(exc_info.value)
    
    def test_invalid_indicator_type(self, sample_df, available_indicators):
        """Test that invalid indicator type raises error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "invalid_type",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INVALID_INDICATOR_TYPE'
    
    def test_empty_name(self, sample_df, available_indicators):
        """Test that empty name raises error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INVALID_RULE_STRUCTURE'
    
    def test_duplicate_name(self, sample_df, available_indicators):
        """Test that duplicate indicator names raise error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        engine.add_rule(rule)
        
        # Try to add again
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'DUPLICATE_INDICATOR_NAME'
    
    def test_name_conflict_with_existing(self, sample_df, available_indicators):
        """Test that name conflicts with existing indicators raise error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "rsi",  # Conflicts with existing indicator
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "macd"},
                "right": {"value": 50}
            }
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INDICATOR_NAME_CONFLICT'
    
    # Test operator validation
    
    def test_invalid_operator(self, sample_df, available_indicators):
        """Test that invalid operators raise error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "%",  # Invalid operator
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INVALID_OPERATOR'
        assert '%' in str(exc_info.value)
    
    def test_all_valid_operators(self, sample_df, available_indicators):
        """Test that all valid operators work"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        operators = ['+', '-', '*', '/']
        
        for op in operators:
            rule = {
                "name": f"test_{op}",
                "type": "composite",
                "formula": {
                    "operator": op,
                    "left": {"indicator": "rsi"},
                    "right": {"value": 2}
                }
            }
            
            engine.add_rule(rule)
            result = engine.calculate(f"test_{op}")
            
            assert isinstance(result, pd.Series)
            assert len(result) == 50
    
    # Test operand validation
    
    def test_invalid_operand_type(self, sample_df, available_indicators):
        """Test that invalid operand types raise error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": "not_a_number"}  # Invalid value type
            }
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INVALID_OPERAND_TYPE'
    
    def test_missing_operands(self, sample_df, available_indicators):
        """Test that missing operands raise error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        # Missing right operand
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"}
                # Missing 'right'
            }
        }
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.add_rule(rule)
        
        assert exc_info.value.error_code == 'INVALID_FORMULA_STRUCTURE'
    
    # Test formula evaluation
    
    def test_simple_addition(self, sample_df, available_indicators):
        """Test simple addition formula"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "rsi_plus_50",
            "type": "derived",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        engine.add_rule(rule)
        result = engine.calculate("rsi_plus_50")
        
        # Result should be rsi + 50
        expected = available_indicators['rsi'] + 50
        pd.testing.assert_series_equal(result, expected)
    
    def test_simple_subtraction(self, sample_df, available_indicators):
        """Test simple subtraction formula"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "close_minus_sma",
            "type": "composite",
            "formula": {
                "operator": "-",
                "left": {"indicator": "close"},
                "right": {"indicator": "sma_50"}
            }
        }
        
        engine.add_rule(rule)
        result = engine.calculate("close_minus_sma")
        
        # Result should be close - sma_50
        expected = available_indicators['close'] - available_indicators['sma_50']
        pd.testing.assert_series_equal(result, expected)
    
    def test_simple_multiplication(self, sample_df, available_indicators):
        """Test simple multiplication formula"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "rsi_times_two",
            "type": "derived",
            "formula": {
                "operator": "*",
                "left": {"indicator": "rsi"},
                "right": {"value": 2}
            }
        }
        
        engine.add_rule(rule)
        result = engine.calculate("rsi_times_two")
        
        # Result should be rsi * 2
        expected = available_indicators['rsi'] * 2
        pd.testing.assert_series_equal(result, expected)
    
    def test_simple_division(self, sample_df, available_indicators):
        """Test simple division formula"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "close_div_sma",
            "type": "composite",
            "formula": {
                "operator": "/",
                "left": {"indicator": "close"},
                "right": {"indicator": "sma_50"}
            }
        }
        
        engine.add_rule(rule)
        result = engine.calculate("close_div_sma")
        
        # Result should be close / sma_50
        expected = available_indicators['close'] / available_indicators['sma_50']
        pd.testing.assert_series_equal(result, expected)
    
    def test_division_by_zero(self, sample_df, available_indicators):
        """Test that division by zero produces NaN"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "div_by_zero",
            "type": "derived",
            "formula": {
                "operator": "/",
                "left": {"indicator": "rsi"},
                "right": {"value": 0}
            }
        }
        
        engine.add_rule(rule)
        result = engine.calculate("div_by_zero")
        
        # All values should be inf or NaN
        assert all(pd.isna(result) | (result == float('inf')) | (result == float('-inf')))
    
    # Test nested formulas
    
    def test_nested_formula(self, sample_df, available_indicators):
        """Test nested formula evaluation"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        # (rsi + 50) * 0.01
        rule = {
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
        }
        
        engine.add_rule(rule)
        result = engine.calculate("price_momentum")
        
        # Result should be (rsi + 50) * 0.01
        expected = (available_indicators['rsi'] + 50) * 0.01
        pd.testing.assert_series_equal(result, expected)
    
    def test_complex_nested_formula(self, sample_df, available_indicators):
        """Test complex nested formula from documentation"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        # (close - sma_50) / atr
        rule = {
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
        }
        
        engine.add_rule(rule)
        result = engine.calculate("mean_reversion")
        
        # Result should be (close - sma_50) / atr
        expected = (available_indicators['close'] - available_indicators['sma_50']) / available_indicators['atr']
        pd.testing.assert_series_equal(result, expected)
    
    def test_deeply_nested_formula(self, sample_df, available_indicators):
        """Test deeply nested formula"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        # ((rsi + macd) / 2) * (close / sma_50)
        rule = {
            "name": "complex_signal",
            "type": "composite",
            "formula": {
                "operator": "*",
                "left": {
                    "operator": "/",
                    "left": {
                        "operator": "+",
                        "left": {"indicator": "rsi"},
                        "right": {"indicator": "macd"}
                    },
                    "right": {"value": 2}
                },
                "right": {
                    "operator": "/",
                    "left": {"indicator": "close"},
                    "right": {"indicator": "sma_50"}
                }
            }
        }
        
        engine.add_rule(rule)
        result = engine.calculate("complex_signal")
        
        # Verify result is a Series with correct length
        assert isinstance(result, pd.Series)
        assert len(result) == 50
    
    # Test indicator reference resolution
    
    def test_reference_nonexistent_indicator(self, sample_df, available_indicators):
        """Test that referencing non-existent indicator raises error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "nonexistent"},
                "right": {"value": 50}
            }
        }
        
        engine.add_rule(rule)
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.calculate("test_indicator")
        
        assert exc_info.value.error_code == 'INDICATOR_NOT_FOUND'
        assert 'nonexistent' in str(exc_info.value)
    
    def test_reference_custom_indicator(self, sample_df, available_indicators):
        """Test referencing another custom indicator"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        # First custom indicator
        rule1 = {
            "name": "weighted_rsi",
            "type": "derived",
            "formula": {
                "operator": "*",
                "left": {"indicator": "rsi"},
                "right": {"value": 0.7}
            }
        }
        
        # Second custom indicator referencing first
        rule2 = {
            "name": "adjusted_signal",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "weighted_rsi"},
                "right": {"value": 10}
            }
        }
        
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        
        result = engine.calculate("adjusted_signal")
        
        # Result should be (rsi * 0.7) + 10
        expected = (available_indicators['rsi'] * 0.7) + 10
        pd.testing.assert_series_equal(result, expected)
    
    # Test circular dependency detection
    
    def test_self_reference(self, sample_df, available_indicators):
        """Test that self-referencing indicator raises error"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "circular",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "circular"},
                "right": {"value": 1}
            }
        }
        
        engine.add_rule(rule)
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.calculate("circular")
        
        assert exc_info.value.error_code == 'CIRCULAR_DEPENDENCY'
    
    def test_circular_dependency_two_indicators(self, sample_df, available_indicators):
        """Test circular dependency between two indicators"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule1 = {
            "name": "indicator_a",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "indicator_b"},
                "right": {"value": 1}
            }
        }
        
        rule2 = {
            "name": "indicator_b",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "indicator_a"},
                "right": {"value": 1}
            }
        }
        
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        
        with pytest.raises(CustomIndicatorError) as exc_info:
            engine.calculate("indicator_a")
        
        assert exc_info.value.error_code == 'CIRCULAR_DEPENDENCY'
    
    # Test caching
    
    def test_calculation_caching(self, sample_df, available_indicators):
        """Test that calculations are cached"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        engine.add_rule(rule)
        
        # First calculation
        result1 = engine.calculate("test_indicator")
        assert "test_indicator" in engine.calculation_cache
        
        # Second calculation should use cache
        result2 = engine.calculate("test_indicator")
        
        # Results should be identical
        pd.testing.assert_series_equal(result1, result2)
    
    def test_clear_cache(self, sample_df, available_indicators):
        """Test cache clearing"""
        engine = CustomIndicatorEngine(sample_df, available_indicators)
        
        rule = {
            "name": "test_indicator",
            "type": "composite",
            "formula": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            }
        }
        
        engine.add_rule(rule)
        engine.calculate("test_indicator")
        
        assert len(engine.calculation_cache) > 0
        
        engine.clear_cache()
        
        assert len(engine.calculation_cache) == 0
    
    # Test integration with IndicatorCalculator
    
    def test_integration_with_calculator(self, sample_candles):
        """Test custom indicators integrated with IndicatorCalculator"""
        custom_rules = [
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
            }
        ]
        
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd'],
            custom_indicators=custom_rules,
            mode='omni'
        )
        
        result = calc.calculate_all(100)
        
        # Should include both standard and custom indicators
        assert 'rsi' in result
        assert 'macd' in result
        assert 'price_momentum' in result
        
        # Custom indicator should have a value
        assert result['price_momentum'] is not None
    
    def test_integration_multiple_custom_indicators(self, sample_candles):
        """Test multiple custom indicators with IndicatorCalculator"""
        custom_rules = [
            {
                "name": "weighted_rsi",
                "type": "derived",
                "formula": {
                    "operator": "*",
                    "left": {"indicator": "rsi"},
                    "right": {"value": 0.7}
                }
            },
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
            }
        ]
        
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'sma_50', 'atr'],
            custom_indicators=custom_rules,
            mode='omni'
        )
        
        result = calc.calculate_all(100)
        
        # Should include all indicators
        assert 'rsi' in result
        assert 'sma_50' in result
        assert 'atr' in result
        assert 'weighted_rsi' in result
        assert 'mean_reversion' in result
        
        # All should have values
        assert all(result[key] is not None for key in result)
    
    def test_get_custom_indicator_names(self, sample_candles):
        """Test getting custom indicator names from calculator"""
        custom_rules = [
            {
                "name": "custom_1",
                "type": "derived",
                "formula": {
                    "operator": "*",
                    "left": {"indicator": "rsi"},
                    "right": {"value": 2}
                }
            },
            {
                "name": "custom_2",
                "type": "derived",
                "formula": {
                    "operator": "+",
                    "left": {"indicator": "macd"},
                    "right": {"value": 10}
                }
            }
        ]
        
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd'],
            custom_indicators=custom_rules,
            mode='omni'
        )
        
        custom_names = calc.get_custom_indicator_names()
        
        assert len(custom_names) == 2
        assert 'custom_1' in custom_names
        assert 'custom_2' in custom_names
    
    def test_no_custom_indicators(self, sample_candles):
        """Test calculator without custom indicators"""
        calc = IndicatorCalculator(
            candles=sample_candles,
            enabled_indicators=['rsi', 'macd'],
            mode='omni'
        )
        
        custom_names = calc.get_custom_indicator_names()
        
        assert len(custom_names) == 0
    
    def test_invalid_custom_rule_in_calculator(self, sample_candles):
        """Test that invalid custom rule raises error in calculator"""
        custom_rules = [
            {
                "name": "invalid",
                "type": "composite",
                "formula": {
                    "operator": "%",  # Invalid operator
                    "left": {"indicator": "rsi"},
                    "right": {"value": 2}
                }
            }
        ]
        
        with pytest.raises(ValueError):
            IndicatorCalculator(
                candles=sample_candles,
                enabled_indicators=['rsi'],
                custom_indicators=custom_rules,
                mode='omni'
            )
