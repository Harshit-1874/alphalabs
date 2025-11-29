"""
Market Data Service for fetching and caching historical and live market data.

Purpose:
    Provides a unified interface for fetching market data with multi-layer caching:
    1. In-memory cache (fastest)
    2. Database cache (persistent)
    3. External API (yfinance as fallback)

Features:
    - Multi-layer caching strategy
    - Support for multiple assets (BTC/USDT, ETH/USDT, SOL/USDT)
    - Support for multiple timeframes (15m, 1h, 4h, 1d)
    - Rate limit handling with exponential backoff
    - Graceful fallback to cached data on API failure

Usage:
    service = MarketDataService(db_session)
    candles = await service.get_historical_data(
        asset="BTC/USDT",
        timeframe="1h",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 31)
    )
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import hashlib
import logging
from functools import lru_cache

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf

from models import MarketDataCache
from config import settings
from utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """
    Candlestick data structure.
    
    Represents a single OHLCV (Open, High, Low, Close, Volume) candle
    for a specific timestamp and timeframe.
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataService:
    """
    Market data service with multi-layer caching.
    
    Implements a three-tier caching strategy:
    1. In-memory cache (Dict) - fastest, volatile
    2. Database cache (PostgreSQL) - persistent, fast
    3. External API (yfinance) - slowest, always fresh
    
    Attributes:
        db: Database session for cache operations
        memory_cache: In-memory LRU cache for recent queries
        
    Example:
        async with get_db() as db:
            service = MarketDataService(db)
            candles = await service.get_historical_data(
                asset="BTC/USDT",
                timeframe="1h",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 3, 31)
            )
    """
    
    # Supported assets and their yfinance ticker mappings
    ASSET_TICKER_MAP = {
        'BTC/USDT': 'BTC-USD',
        'ETH/USDT': 'ETH-USD',
        'SOL/USDT': 'SOL-USD',
    }
    
    # Supported timeframes and their yfinance interval mappings
    TIMEFRAME_INTERVAL_MAP = {
        '15m': '15m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d',
    }
    
    def __init__(self, db: AsyncSession):
        """
        Initialize market data service.
        
        Args:
            db: Database session for cache operations
        """
        self.db = db
        self.memory_cache: Dict[str, List[Candle]] = {}
        
        logger.info("MarketDataService initialized")
    
    def _generate_cache_key(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        Generate unique cache key for a data request.
        
        Creates a deterministic hash key based on request parameters
        to enable efficient cache lookups.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            str: Unique cache key (SHA256 hash)
            
        Example:
            key = service._generate_cache_key(
                "BTC/USDT", "1h",
                datetime(2024, 1, 1),
                datetime(2024, 3, 31)
            )
            # Returns: "a3f5c8d9e2b1..."
        """
        # Create deterministic string representation
        key_string = f"{asset}:{timeframe}:{start_date.isoformat()}:{end_date.isoformat()}"
        
        # Generate SHA256 hash for compact key
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()
        
        return cache_key
    
    def _validate_parameters(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> None:
        """
        Validate request parameters.
        
        Ensures that asset, timeframe, and date range are valid
        before attempting to fetch data.
        
        Args:
            asset: Trading asset
            timeframe: Candlestick timeframe
            start_date: Start of date range
            end_date: End of date range
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate asset
        if asset not in self.ASSET_TICKER_MAP:
            supported = ', '.join(self.ASSET_TICKER_MAP.keys())
            raise ValueError(
                f"Unsupported asset '{asset}'. "
                f"Supported assets: {supported}"
            )
        
        # Validate timeframe
        if timeframe not in self.TIMEFRAME_INTERVAL_MAP:
            supported = ', '.join(self.TIMEFRAME_INTERVAL_MAP.keys())
            raise ValueError(
                f"Unsupported timeframe '{timeframe}'. "
                f"Supported timeframes: {supported}"
            )
        
        # Validate date range
        if start_date >= end_date:
            raise ValueError(
                f"start_date ({start_date}) must be before end_date ({end_date})"
            )
        
        # Validate date range is not too far in the future
        if start_date > datetime.now():
            raise ValueError(
                f"start_date ({start_date}) cannot be in the future"
            )
    
    async def get_historical_data(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        """
        Get historical candlestick data with multi-layer caching.
        
        Implements three-tier caching strategy:
        1. Check in-memory cache first (fastest)
        2. Check database cache if not in memory
        3. Fetch from external API if not cached
        4. Store in both memory and database cache
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List[Candle]: List of candlestick data
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If data fetch fails and no cache available
            
        Example:
            candles = await service.get_historical_data(
                asset="BTC/USDT",
                timeframe="1h",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 3, 31)
            )
        """
        # Validate parameters
        self._validate_parameters(asset, timeframe, start_date, end_date)
        
        # Generate cache key
        cache_key = self._generate_cache_key(asset, timeframe, start_date, end_date)
        
        # 1. Check in-memory cache
        if cache_key in self.memory_cache:
            logger.info(
                f"Cache hit (memory): {asset} {timeframe} "
                f"{start_date.date()} to {end_date.date()}"
            )
            return self.memory_cache[cache_key]
        
        # 2. Check database cache
        db_candles = await self._load_from_db_cache(
            asset, timeframe, start_date, end_date
        )
        
        if db_candles:
            logger.info(
                f"Cache hit (database): {asset} {timeframe} "
                f"{start_date.date()} to {end_date.date()} "
                f"({len(db_candles)} candles)"
            )
            # Store in memory cache for faster future access
            self.memory_cache[cache_key] = db_candles
            return db_candles
        
        # 3. Fetch from external API with retry logic
        logger.info(
            f"Cache miss: Fetching from API: {asset} {timeframe} "
            f"{start_date.date()} to {end_date.date()}"
        )
        
        try:
            # Use retry logic for API calls
            api_candles = await retry_with_backoff(
                lambda: self._fetch_from_api(asset, timeframe, start_date, end_date),
                max_retries=settings.MAX_RETRIES,
                base_delay=settings.RETRY_BASE_DELAY,
                max_delay=settings.RETRY_MAX_DELAY,
                exceptions=(Exception,),
                operation_name=f"fetch_market_data_{asset}_{timeframe}"
            )
            
            # 4. Store in both caches
            await self._cache_to_db(asset, timeframe, api_candles)
            self.memory_cache[cache_key] = api_candles
            
            logger.info(
                f"Fetched and cached {len(api_candles)} candles for "
                f"{asset} {timeframe}"
            )
            
            return api_candles
            
        except Exception as e:
            logger.error(f"Failed to fetch data from API after retries: {e}")
            
            # Try to return partial cached data as fallback
            partial_candles = await self._load_from_db_cache(
                asset, timeframe, start_date, end_date, partial_ok=True
            )
            
            if partial_candles:
                logger.warning(
                    f"Using partial cached data ({len(partial_candles)} candles) "
                    f"due to API failure"
                )
                return partial_candles
            
            # No cache available, re-raise exception
            raise
    
    async def get_latest_candle(
        self,
        asset: str,
        timeframe: str
    ) -> Candle:
        """
        Get the most recent closed candle.
        
        Fetches the latest completed candlestick for the specified
        asset and timeframe. Used for forward testing to get real-time data.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            
        Returns:
            Candle: Most recent closed candle
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If data fetch fails
            
        Example:
            latest = await service.get_latest_candle("BTC/USDT", "1h")
            print(f"Latest BTC price: ${latest.close:,.2f}")
        """
        # Validate parameters
        if asset not in self.ASSET_TICKER_MAP:
            supported = ', '.join(self.ASSET_TICKER_MAP.keys())
            raise ValueError(
                f"Unsupported asset '{asset}'. Supported: {supported}"
            )
        
        if timeframe not in self.TIMEFRAME_INTERVAL_MAP:
            supported = ', '.join(self.TIMEFRAME_INTERVAL_MAP.keys())
            raise ValueError(
                f"Unsupported timeframe '{timeframe}'. Supported: {supported}"
            )
        
        # Fetch recent data (last 2 candles to ensure we get a closed one)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2)  # Get enough data
        
        candles = await self.get_historical_data(
            asset, timeframe, start_date, end_date
        )
        
        if not candles:
            raise Exception(f"No data available for {asset} {timeframe}")
        
        # Return the most recent candle
        return candles[-1]
    
    async def _load_from_db_cache(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        partial_ok: bool = False
    ) -> Optional[List[Candle]]:
        """
        Load candlestick data from database cache.
        
        Queries the market_data_cache table for cached candles
        within the specified date range.
        
        Args:
            asset: Trading asset
            timeframe: Candlestick timeframe
            start_date: Start of date range
            end_date: End of date range
            partial_ok: If True, return partial data even if incomplete
            
        Returns:
            Optional[List[Candle]]: Cached candles or None if not found
        """
        try:
            # Query database cache
            stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.asset == asset,
                    MarketDataCache.timeframe == timeframe,
                    MarketDataCache.timestamp >= start_date,
                    MarketDataCache.timestamp <= end_date
                )
            ).order_by(MarketDataCache.timestamp)
            
            result = await self.db.execute(stmt)
            cache_entries = result.scalars().all()
            
            if not cache_entries:
                return None
            
            # Convert to Candle objects
            candles = [
                Candle(
                    timestamp=entry.timestamp,
                    open=float(entry.open),
                    high=float(entry.high),
                    low=float(entry.low),
                    close=float(entry.close),
                    volume=float(entry.volume)
                )
                for entry in cache_entries
            ]
            
            # Check if we have complete data (unless partial is ok)
            if not partial_ok:
                # Estimate expected number of candles
                expected_candles = self._estimate_candle_count(
                    start_date, end_date, timeframe
                )
                
                # Allow 10% tolerance for weekends/holidays
                if len(candles) < expected_candles * 0.9:
                    logger.debug(
                        f"Incomplete cache: got {len(candles)}, "
                        f"expected ~{expected_candles}"
                    )
                    return None
            
            return candles
            
        except Exception as e:
            logger.error(f"Error loading from database cache: {e}")
            return None
    
    def _estimate_candle_count(
        self,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> int:
        """
        Estimate expected number of candles for a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            timeframe: Candlestick timeframe
            
        Returns:
            int: Estimated candle count
        """
        duration = end_date - start_date
        
        # Map timeframe to minutes
        timeframe_minutes = {
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
        }
        
        minutes = timeframe_minutes.get(timeframe, 60)
        total_minutes = duration.total_seconds() / 60
        
        return int(total_minutes / minutes)
    
    async def _fetch_from_api(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        """
        Fetch candlestick data from external API (yfinance).
        
        Uses yfinance library to fetch historical OHLCV data.
        Converts yfinance DataFrame format to our Candle objects.
        Includes rate limit handling and timeout protection.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List[Candle]: Fetched candles
            
        Raises:
            Exception: If API fetch fails or rate limit exceeded
            
        Example:
            candles = await service._fetch_from_api(
                "BTC/USDT", "1h",
                datetime(2024, 1, 1),
                datetime(2024, 3, 31)
            )
        """
        # Map to yfinance ticker and interval
        ticker_symbol = self.ASSET_TICKER_MAP[asset]
        interval = self.TIMEFRAME_INTERVAL_MAP[timeframe]
        
        logger.info(
            f"Fetching from yfinance: {ticker_symbol} "
            f"interval={interval} from {start_date.date()} to {end_date.date()}"
        )
        
        try:
            # Fetch data from yfinance (runs in thread pool to avoid blocking)
            import asyncio
            loop = asyncio.get_event_loop()
            
            def fetch_sync():
                ticker = yf.Ticker(ticker_symbol)
                return ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True,  # Adjust for splits/dividends
                    actions=False  # Don't include dividend/split actions
                )
            
            # Run with timeout to prevent hanging
            df = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_sync),
                timeout=settings.MARKET_DATA_TIMEOUT
            )
            
            if df.empty:
                raise Exception(
                    f"No data returned from yfinance for {ticker_symbol} "
                    f"{interval} from {start_date.date()} to {end_date.date()}"
                )
            
            # Convert DataFrame to Candle objects
            candles = []
            for index, row in df.iterrows():
                # Handle timezone-aware datetime
                timestamp = index.to_pydatetime()
                if timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)
                
                candle = Candle(
                    timestamp=timestamp,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                )
                candles.append(candle)
            
            logger.info(
                f"Successfully fetched {len(candles)} candles from yfinance"
            )
            
            return candles
            
        except asyncio.TimeoutError:
            logger.error(
                f"yfinance API timeout after {settings.MARKET_DATA_TIMEOUT}s "
                f"for {ticker_symbol}"
            )
            raise Exception(
                f"Market data fetch timed out after {settings.MARKET_DATA_TIMEOUT}s"
            )
        except Exception as e:
            # Check for rate limit errors
            error_str = str(e).lower()
            if 'rate limit' in error_str or '429' in error_str:
                logger.error(f"yfinance rate limit exceeded: {e}")
                raise Exception(
                    f"Rate limit exceeded for market data API. "
                    f"Please try again later."
                )
            
            logger.error(f"yfinance API error: {e}")
            raise Exception(f"Failed to fetch data from yfinance: {e}")
    
    async def _cache_to_db(
        self,
        asset: str,
        timeframe: str,
        candles: List[Candle]
    ) -> None:
        """
        Store candlestick data in database cache.
        
        Inserts candles into the market_data_cache table.
        Uses INSERT ... ON CONFLICT DO NOTHING to avoid duplicates.
        
        Args:
            asset: Trading asset
            timeframe: Candlestick timeframe
            candles: Candles to cache
            
        Example:
            await service._cache_to_db("BTC/USDT", "1h", candles)
        """
        if not candles:
            return
        
        try:
            # Create cache entries
            cache_entries = []
            for candle in candles:
                entry = MarketDataCache(
                    asset=asset,
                    timeframe=timeframe,
                    timestamp=candle.timestamp,
                    open=Decimal(str(candle.open)),
                    high=Decimal(str(candle.high)),
                    low=Decimal(str(candle.low)),
                    close=Decimal(str(candle.close)),
                    volume=Decimal(str(candle.volume)),
                    indicators=None  # Indicators calculated separately
                )
                cache_entries.append(entry)
            
            # Bulk insert with conflict handling
            # Use merge to handle duplicates (update if exists)
            for entry in cache_entries:
                await self.db.merge(entry)
            
            await self.db.commit()
            
            logger.info(
                f"Cached {len(cache_entries)} candles to database "
                f"for {asset} {timeframe}"
            )
            
        except Exception as e:
            logger.error(f"Error caching to database: {e}")
            await self.db.rollback()
            # Don't raise - caching failure shouldn't break the flow
