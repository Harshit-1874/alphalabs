"""
Validation Utilities.

Purpose:
    Input validation functions for dates, numeric limits, assets, timeframes, etc.

Usage:
    from utils.validators import validate_date_range, validate_asset
"""
from datetime import datetime
from typing import Optional, List
from exceptions import InvalidDateRangeError, InvalidParameterError


# Supported assets and timeframes
SUPPORTED_ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
SUPPORTED_TIMEFRAMES = ["15m", "1h", "4h", "1d"]


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Validate that end_date is after start_date.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Raises:
        InvalidDateRangeError: If end_date is not after start_date
    """
    if end_date <= start_date:
        raise InvalidDateRangeError(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )


def validate_asset(asset: str) -> None:
    """
    Validate that asset is supported.
    
    Args:
        asset: Asset symbol (e.g., "BTC/USDT")
        
    Raises:
        InvalidParameterError: If asset is not supported
    """
    if asset not in SUPPORTED_ASSETS:
        raise InvalidParameterError(
            parameter="asset",
            value=asset,
            reason=f"Must be one of: {', '.join(SUPPORTED_ASSETS)}"
        )


def validate_timeframe(timeframe: str) -> None:
    """
    Validate that timeframe is supported.
    
    Args:
        timeframe: Timeframe (e.g., "1h", "4h")
        
    Raises:
        InvalidParameterError: If timeframe is not supported
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise InvalidParameterError(
            parameter="timeframe",
            value=timeframe,
            reason=f"Must be one of: {', '.join(SUPPORTED_TIMEFRAMES)}"
        )


def validate_percentage(value: float, parameter: str, min_val: float = 0.0, max_val: float = 1.0) -> None:
    """
    Validate that a percentage value is within range.
    
    Args:
        value: The percentage value (0.0 to 1.0)
        parameter: Parameter name for error message
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Raises:
        InvalidParameterError: If value is out of range
    """
    if not (min_val <= value <= max_val):
        raise InvalidParameterError(
            parameter=parameter,
            value=value,
            reason=f"Must be between {min_val} and {max_val}"
        )


def validate_positive_number(value: float, parameter: str) -> None:
    """
    Validate that a number is positive.
    
    Args:
        value: The numeric value
        parameter: Parameter name for error message
        
    Raises:
        InvalidParameterError: If value is not positive
    """
    if value <= 0:
        raise InvalidParameterError(
            parameter=parameter,
            value=value,
            reason="Must be a positive number"
        )


def validate_leverage(leverage: int) -> None:
    """
    Validate that leverage is within allowed range (1-5).
    
    Args:
        leverage: Leverage multiplier
        
    Raises:
        InvalidParameterError: If leverage is out of range
    """
    if not (1 <= leverage <= 5):
        raise InvalidParameterError(
            parameter="leverage",
            value=leverage,
            reason="Must be between 1 and 5"
        )


def validate_indicator_list(indicators: List[str], mode: str) -> None:
    """
    Validate indicator list based on mode restrictions.
    
    Args:
        indicators: List of indicator names
        mode: Trading mode ("monk" or "omni")
        
    Raises:
        InvalidParameterError: If indicators are invalid for the mode
    """
    if mode == "monk":
        allowed = ["rsi", "macd"]
        invalid = [ind for ind in indicators if ind.lower() not in allowed]
        if invalid:
            raise InvalidParameterError(
                parameter="indicators",
                value=indicators,
                reason=f"Monk mode only allows RSI and MACD. Invalid: {', '.join(invalid)}"
            )
    
    if not indicators:
        raise InvalidParameterError(
            parameter="indicators",
            value=indicators,
            reason="At least one indicator must be selected"
        )
