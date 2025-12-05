"""
Test to verify the forward test date calculation logic.

This script simulates the date calculation logic used in the forward test engine
to ensure we're requesting data for complete candles only.
"""

from datetime import datetime, timedelta, timezone


def calculate_end_date(timeframe: str) -> tuple[datetime, datetime, int]:
    """
    Calculate the end_date for historical data fetch based on timeframe.
    
    Returns:
        (now, end_date, days_back)
    """
    now = datetime.now(timezone.utc)
    required_candles = 300  # Example
    
    if timeframe == '15m':
        # For 15m, go back 30 minutes to ensure we get complete candles
        end_date = now - timedelta(minutes=30)
        days_back = (required_candles * 15) // (24 * 60) + 1
    elif timeframe == '1h':
        # For 1h, go back 2 hours to ensure we get complete candles
        end_date = now - timedelta(hours=2)
        days_back = (required_candles // 24) + 1
    elif timeframe == '4h':
        # For 4h, go back 8 hours to ensure we get complete candles
        end_date = now - timedelta(hours=8)
        days_back = (required_candles // 6) + 1
    elif timeframe == '1d':
        # For 1d, go back 2 days to ensure we get complete candles
        end_date = now - timedelta(days=2)
        days_back = required_candles
    else:
        # Default: go back 1 day
        end_date = now - timedelta(days=1)
        days_back = 30  # Default
    
    return now, end_date, days_back


def main():
    print("=" * 80)
    print("Forward Test Date Calculation Logic Test")
    print("=" * 80)
    print()
    
    timeframes = ['15m', '1h', '4h', '1d']
    
    for tf in timeframes:
        now, end_date, days_back = calculate_end_date(tf)
        start_date = end_date - timedelta(days=days_back)
        
        print(f"Timeframe: {tf}")
        print(f"  Current time:     {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  End date (query): {end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Time buffer:      {(now - end_date).total_seconds() / 3600:.1f} hours")
        print(f"  Start date:       {start_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Days back:        {days_back} days")
        print(f"  Date range:       {(end_date - start_date).days} days")
        print()
    
    print("=" * 80)
    print("✓ All calculations complete!")
    print()
    print("Key insight: By setting end_date BEFORE the current time,")
    print("we ensure we only request complete candles that yfinance has data for.")
    print("=" * 80)


if __name__ == "__main__":
    main()

