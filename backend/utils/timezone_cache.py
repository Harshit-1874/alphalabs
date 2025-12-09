"""
Timezone Caching Utility.

Purpose:
    Provides a cached list of valid timezones to avoid expensive database queries
    to pg_timezone_names. This eliminates the need for repeated queries that were
    showing up as slow queries in Supabase dashboard.

Performance Impact:
    - Eliminates ~366ms average query time (28 calls = 10+ seconds saved)
    - Reduces database load by caching timezone data in application memory
    - One-time initialization cost vs repeated database queries

Usage:
    from utils.timezone_cache import is_valid_timezone, get_all_timezones
    
    if is_valid_timezone("America/New_York"):
        # timezone is valid
"""
import logging
from typing import Set, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Global cache for timezones
_TIMEZONE_CACHE: Optional[Set[str]] = None


def _initialize_timezone_cache() -> Set[str]:
    """
    Initialize timezone cache from pytz.
    This is called once at application startup.
    
    Returns:
        Set of valid timezone strings
    """
    try:
        import pytz
        timezones = set(pytz.all_timezones)
        logger.info(f"Timezone cache initialized with {len(timezones)} timezones")
        return timezones
    except ImportError:
        logger.warning("pytz not available, using minimal timezone set")
        # Fallback to common timezones if pytz not available
        return {
            "UTC",
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Australia/Sydney",
        }


def get_all_timezones() -> Set[str]:
    """
    Get all valid timezones from cache.
    Initializes cache on first call.
    
    Returns:
        Set of valid timezone strings
    """
    global _TIMEZONE_CACHE
    
    if _TIMEZONE_CACHE is None:
        _TIMEZONE_CACHE = _initialize_timezone_cache()
    
    return _TIMEZONE_CACHE


@lru_cache(maxsize=512)
def is_valid_timezone(timezone: str) -> bool:
    """
    Check if a timezone string is valid.
    Uses LRU cache for frequently checked timezones.
    
    Args:
        timezone: Timezone string to validate (e.g., "America/New_York")
    
    Returns:
        True if timezone is valid, False otherwise
    """
    return timezone in get_all_timezones()


def validate_timezone(timezone: Optional[str]) -> Optional[str]:
    """
    Validate timezone string and raise ValueError if invalid.
    
    Args:
        timezone: Timezone string to validate
    
    Returns:
        The validated timezone string
    
    Raises:
        ValueError: If timezone is invalid
    """
    if timezone is not None and not is_valid_timezone(timezone):
        raise ValueError(f"Invalid timezone: {timezone}")
    return timezone


# Initialize cache at module import time
# This ensures the cache is ready before any requests are processed
_TIMEZONE_CACHE = _initialize_timezone_cache()
