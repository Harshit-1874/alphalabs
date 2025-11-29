"""
Market Data Service Example

This example demonstrates how to use the MarketDataService to fetch
and cache historical market data.

Usage:
    python examples/market_data_example.py
"""
import asyncio
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_data_service import MarketDataService
from database import get_db


async def main():
    """Demonstrate MarketDataService usage."""
    
    print("=" * 70)
    print("Market Data Service Example")
    print("=" * 70)
    
    # Get database session
    async for db in get_db():
        # Initialize service
        service = MarketDataService(db)
        
        # Example 1: Fetch BTC/USDT 1h data for last 7 days
        print("\n1. Fetching BTC/USDT 1h data (last 7 days)...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        try:
            candles = await service.get_historical_data(
                asset="BTC/USDT",
                timeframe="1h",
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"   ✓ Fetched {len(candles)} candles")
            print(f"   First candle: {candles[0].timestamp} - Close: ${candles[0].close:,.2f}")
            print(f"   Last candle:  {candles[-1].timestamp} - Close: ${candles[-1].close:,.2f}")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Example 2: Fetch same data again (should hit cache)
        print("\n2. Fetching same data again (should hit cache)...")
        
        try:
            candles = await service.get_historical_data(
                asset="BTC/USDT",
                timeframe="1h",
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"   ✓ Retrieved {len(candles)} candles from cache")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Example 3: Get latest candle
        print("\n3. Getting latest BTC/USDT 1h candle...")
        
        try:
            latest = await service.get_latest_candle("BTC/USDT", "1h")
            print(f"   ✓ Latest candle: {latest.timestamp}")
            print(f"     Open:   ${latest.open:,.2f}")
            print(f"     High:   ${latest.high:,.2f}")
            print(f"     Low:    ${latest.low:,.2f}")
            print(f"     Close:  ${latest.close:,.2f}")
            print(f"     Volume: {latest.volume:,.2f}")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Example 4: Fetch ETH/USDT 4h data
        print("\n4. Fetching ETH/USDT 4h data (last 30 days)...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        try:
            candles = await service.get_historical_data(
                asset="ETH/USDT",
                timeframe="4h",
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"   ✓ Fetched {len(candles)} candles")
            print(f"   Price range: ${min(c.close for c in candles):,.2f} - ${max(c.close for c in candles):,.2f}")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Example 5: Test error handling with invalid asset
        print("\n5. Testing error handling (invalid asset)...")
        
        try:
            candles = await service.get_historical_data(
                asset="INVALID/USDT",
                timeframe="1h",
                start_date=start_date,
                end_date=end_date
            )
            print(f"   ✗ Should have raised error")
            
        except ValueError as e:
            print(f"   ✓ Correctly caught error: {e}")
        
        print("\n" + "=" * 70)
        print("Example completed!")
        print("=" * 70)
        
        break  # Exit after first iteration


if __name__ == "__main__":
    asyncio.run(main())
