"""
Trading Services Package.

Purpose:
    Contains all trading-related services including backtest engine,
    forward test engine, position management, and indicator calculation.
"""

from .indicator_calculator import IndicatorCalculator, Candle
from .custom_indicator_engine import CustomIndicatorEngine, CustomIndicatorError
from .position_manager import PositionManager, Position, Trade

__all__ = [
    'IndicatorCalculator',
    'Candle',
    'CustomIndicatorEngine',
    'CustomIndicatorError',
    'PositionManager',
    'Position',
    'Trade'
]
