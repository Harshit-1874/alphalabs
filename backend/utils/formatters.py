"""
Formatting Utilities.

Purpose:
    Data formatting functions for currency, percentages, dates, etc.

Usage:
    from utils.formatters import format_currency, format_percentage
"""
from datetime import datetime
from typing import Optional


def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """
    Format a number as currency.
    
    Args:
        amount: The amount to format
        currency: Currency code (default: "USD")
        decimals: Number of decimal places
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    if currency == "USD":
        symbol = "$"
    elif currency == "EUR":
        symbol = "€"
    elif currency == "GBP":
        symbol = "£"
    else:
        symbol = currency + " "
    
    formatted = f"{abs(amount):,.{decimals}f}"
    sign = "-" if amount < 0 else ""
    
    return f"{sign}{symbol}{formatted}"


def format_percentage(value: float, decimals: int = 2, include_sign: bool = True) -> str:
    """
    Format a number as percentage.
    
    Args:
        value: The value to format (0.1 = 10%)
        decimals: Number of decimal places
        include_sign: Whether to include + sign for positive values
        
    Returns:
        Formatted percentage string (e.g., "+10.50%")
    """
    percentage = value * 100
    formatted = f"{abs(percentage):.{decimals}f}%"
    
    if percentage > 0 and include_sign:
        return f"+{formatted}"
    elif percentage < 0:
        return f"-{formatted}"
    else:
        return formatted


def format_datetime(dt: datetime, format_str: Optional[str] = None) -> str:
    """
    Format a datetime object.
    
    Args:
        dt: The datetime to format
        format_str: Custom format string (default: ISO format)
        
    Returns:
        Formatted datetime string
    """
    if format_str:
        return dt.strftime(format_str)
    return dt.isoformat()


def format_date(dt: datetime) -> str:
    """
    Format a datetime as date only.
    
    Args:
        dt: The datetime to format
        
    Returns:
        Formatted date string (e.g., "2024-03-15")
    """
    return dt.strftime("%Y-%m-%d")


def format_time(dt: datetime) -> str:
    """
    Format a datetime as time only.
    
    Args:
        dt: The datetime to format
        
    Returns:
        Formatted time string (e.g., "14:30:00")
    """
    return dt.strftime("%H:%M:%S")


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration (e.g., "2h 30m 15s")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def format_number(value: float, decimals: int = 2, compact: bool = False) -> str:
    """
    Format a number with optional compact notation.
    
    Args:
        value: The number to format
        decimals: Number of decimal places
        compact: Use compact notation (K, M, B)
        
    Returns:
        Formatted number string
    """
    if not compact:
        return f"{value:,.{decimals}f}"
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.{decimals}f}B"
    elif abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.{decimals}f}M"
    elif abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.{decimals}f}K"
    else:
        return f"{sign}{abs_value:.{decimals}f}"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length.
    
    Args:
        text: The text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
