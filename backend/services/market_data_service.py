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
from datetime import datetime, timedelta, timezone
from dateutil import parser
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import logging
from functools import lru_cache

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf
from coingecko_sdk import CoinGecko

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
    
    # Supported assets and their provider metadata
    ASSET_CATALOG: Dict[str, Dict[str, Any]] = {
        'BTC/USDT': {
            'ticker': 'BTC-USD',
            'coingecko_id': 'bitcoin',
            'name': 'Bitcoin',
            'icon': '₿',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 720,
            'sources': ['coingecko', 'yfinance'],
        },
        'ETH/USDT': {
            'ticker': 'ETH-USD',
            'coingecko_id': 'ethereum',
            'name': 'Ethereum',
            'icon': 'Ξ',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 720,
            'sources': ['coingecko', 'yfinance'],
        },
        'SOL/USDT': {
            'name': 'Solana',
            'icon': '◎',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 365,
            'sources': ['coingecko', 'yfinance'],
            'ticker': 'SOL-USD',
            'coingecko_id': 'solana',
        },
        'XRP/USDT': {
            'name': 'XRP',
            'icon': '✕',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 365,
            'sources': ['coingecko', 'yfinance'],
            'ticker': 'XRP-USD',
            'coingecko_id': 'ripple',
        },
        'ADA/USDT': {
            'name': 'Cardano',
            'icon': '₳',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 365,
            'sources': ['coingecko', 'yfinance'],
            'ticker': 'ADA-USD',
            'coingecko_id': 'cardano',
        },
        'DOGE/USDT': {
            'name': 'Dogecoin',
            'icon': 'Ð',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 365,
            'sources': ['coingecko', 'yfinance'],
            'ticker': 'DOGE-USD',
            'coingecko_id': 'dogecoin',
        },
        'BNB/USDT': {
            'ticker': 'BNB-USD',
            'coingecko_id': 'binancecoin',
            'name': 'Binance Coin',
            'icon': 'Ɓ',
            'available': True,
            'min_lookback_days': 7,
            'max_lookback_days': 365,
            'sources': ['coingecko', 'yfinance'],
        },
    }
    ASSET_TICKER_MAP = {
        asset: meta['ticker']
        for asset, meta in ASSET_CATALOG.items()
        if meta.get('ticker')
    }
    ASSET_COINGECKO_MAP = {
        asset: meta['coingecko_id']
        for asset, meta in ASSET_CATALOG.items()
        if meta.get('coingecko_id')
    }
    
    TIMEFRAME_CATALOG: Dict[str, Dict[str, Any]] = {
        '15m': {'interval': '15m', 'name': '15 Minutes', 'minutes': 15},
        '1h': {'interval': '1h', 'name': '1 Hour', 'minutes': 60},
        '4h': {'interval': '4h', 'name': '4 Hours', 'minutes': 240},
        '1d': {'interval': '1d', 'name': '1 Day', 'minutes': 1440},
    }
    TIMEFRAME_INTERVAL_MAP = {k: v['interval'] for k, v in TIMEFRAME_CATALOG.items()}
    
    DATE_PRESETS: List[Dict[str, Any]] = [
        {"id": "7d", "name": "Last 7 days", "description": "Most recent week", "days": 7},
        {"id": "30d", "name": "Last 30 days", "description": "Most recent month", "days": 30},
        {"id": "90d", "name": "Last 90 days", "description": "Most recent quarter", "days": 90},
        {"id": "bull", "name": "Bull Run", "description": "Oct 2023 - Mar 2024", "start_date": "2023-10-01", "end_date": "2024-03-31"},
        {"id": "crash", "name": "Crash Recovery", "description": "Nov 2022 - Jan 2023", "start_date": "2022-11-01", "end_date": "2023-01-31"},
    ]
    
    PLAYBACK_SPEEDS: List[Dict[str, Any]] = [
        {"id": "slow", "name": "Slow (1s/candle)", "ms": 1000},
        {"id": "normal", "name": "Normal (500ms/candle)", "ms": 500},
        {"id": "fast", "name": "Fast (200ms/candle)", "ms": 200},
        {"id": "instant", "name": "Instant", "ms": 0},
    ]
    
    INDICATOR_CATEGORIES: List[Dict[str, Any]] = [
        {
            "id": "momentum",
            "name": "Momentum",
            "indicators": [
                {"id": "rsi", "name": "RSI (Relative Strength Index)", "description": "Measures overbought/oversold conditions"},
                {"id": "stoch", "name": "Stochastic Oscillator", "description": "Compares close to price range"},
                {"id": "cci", "name": "CCI (Commodity Channel Index)", "description": "Identifies cyclical trends"},
                {"id": "mom", "name": "Momentum", "description": "Rate of price change"},
                {"id": "ao", "name": "AO (Awesome Oscillator)", "description": "Market momentum measurement"},
            ],
        },
        {
            "id": "trend",
            "name": "Trend",
            "indicators": [
                {"id": "macd", "name": "MACD", "description": "Trend-following momentum indicator"},
                {"id": "ema", "name": "EMA (Exponential Moving Average)", "description": "Smoothed average weighting recent prices"},
                {"id": "sma", "name": "SMA (Simple Moving Average)", "description": "Average price over period"},
                {"id": "adx", "name": "ADX (Average Directional Index)", "description": "Measures trend strength"},
                {"id": "psar", "name": "Parabolic SAR", "description": "Highlights potential reversals"},
            ],
        },
        {
            "id": "volatility",
            "name": "Volatility",
            "indicators": [
                {"id": "atr", "name": "ATR (Average True Range)", "description": "Measures market volatility"},
                {"id": "bb", "name": "Bollinger Bands", "description": "Volatility-based envelopes"},
                {"id": "kc", "name": "Keltner Channels", "description": "Volatility-based channels"},
            ],
        },
        {
            "id": "volume",
            "name": "Volume",
            "indicators": [
                {"id": "volume", "name": "Volume", "description": "Total traded amount"},
                {"id": "obv", "name": "OBV (On-Balance Volume)", "description": "Tracks buying/selling pressure"},
                {"id": "vwap", "name": "VWAP", "description": "Volume weighted average price"},
            ],
        },
    ]
    
    def __init__(self, db: AsyncSession):
        """
        Initialize market data service.
        
        Args:
            db: Database session for cache operations
        """
        self.db = db
        self.memory_cache: Dict[str, List[Candle]] = {}
        # Initialize CoinGecko with API key
        # CoinGecko requires an API key even for free Demo plan (30 calls/min, 10k calls/month)
        # Get your free API key from: https://www.coingecko.com/en/api/pricing
        api_key = getattr(settings, 'COINGECKO_API_KEY', None)
        if api_key:
            self.coingecko = CoinGecko(api_key=api_key)
            logger.info("MarketDataService initialized with CoinGecko API key")
        else:
            # Try without API key (may work for some endpoints, but not recommended)
            self.coingecko = CoinGecko()
            logger.warning(
                "MarketDataService initialized without CoinGecko API key. "
                "Set COINGECKO_API_KEY in .env for better rate limits. "
                "Get free API key: https://www.coingecko.com/en/api/pricing"
            )
    
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
        if start_date > datetime.now(timezone.utc):
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
    
    async def get_current_price(self, asset: str) -> Optional[Dict[str, float]]:
        """
        Get the current real-time price for an asset from CoinGecko API.
        
        Uses CoinGecko REST API for live market data.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            
        Returns:
            Dict with current price data: {
                'price': float,
                'high_24h': float,
                'low_24h': float,
                'volume_24h': float,
                'change_24h': float,
                'change_pct_24h': float
            } or None if unavailable
        """
        # Get CoinGecko ID (e.g., BTC/USDT -> bitcoin)
        asset_info = self.ASSET_CATALOG.get(asset.upper())
        if not asset_info:
            logger.warning(f"Unknown asset: {asset}")
            return None
        
        coingecko_id = asset_info.get('coingecko_id')
        if not coingecko_id:
            logger.warning(f"No CoinGecko ID for {asset}")
            return None
        
        try:
            # CoinGecko simple/price endpoint
            import asyncio
            loop = asyncio.get_event_loop()
            
            def fetch_price_sync():
                return self.coingecko.simple.price(
                    ids=[coingecko_id],
                    vs_currencies=['usd'],
                    include_24hr_change=True,
                    include_24hr_vol=True,
                    include_24hr_high=True,
                    include_24hr_low=True
                )
            
            data = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_price_sync),
                timeout=5.0
            )
            
            if not data or coingecko_id not in data:
                raise ValueError(f"No price data from CoinGecko for {coingecko_id}")
            
            coin_data = data[coingecko_id]
            current_price = float(coin_data.get('usd', 0))
            
            if current_price == 0:
                raise ValueError("Invalid price from CoinGecko")
            
            high_24h = float(coin_data.get('usd_24h_high', current_price))
            low_24h = float(coin_data.get('usd_24h_low', current_price))
            volume_24h = float(coin_data.get('usd_24h_vol', 0))
            change_pct_24h = float(coin_data.get('usd_24h_change', 0))
            change_24h = current_price * (change_pct_24h / 100) if change_pct_24h else 0
            
            logger.info(
                f"CoinGecko price response for {asset} ({coingecko_id}): price={current_price}"
            )
            
            return {
                'price': current_price,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'volume_24h': volume_24h,
                'change_24h': change_24h,
                'change_pct_24h': change_pct_24h,
            }
        except Exception as e:
            logger.error(f"Error fetching current price from CoinGecko for {asset}: {e}")
            return None
    
    async def get_historical_candles_coingecko(
        self,
        asset: str,
        timeframe: str,
        limit: int = 500
    ) -> List[Candle]:
        """
        Fetch historical candles from CoinGecko API.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1h', '15m', '1d')
            limit: Number of candles to fetch (default: 500)
            
        Returns:
            List of Candle objects sorted by timestamp (oldest first)
        """
        # Get CoinGecko ID
        asset_info = self.ASSET_CATALOG.get(asset.upper())
        if not asset_info:
            logger.warning(f"Unknown asset: {asset}")
            return []
        
        coingecko_id = asset_info.get('coingecko_id')
        if not coingecko_id:
            logger.warning(f"No CoinGecko ID for {asset}")
            return []
        
        # Map timeframe to CoinGecko interval (days)
        # CoinGecko OHLC endpoint supports: 1, 7, 14, 30, 90, 180, 365, max
        # We'll calculate days based on timeframe and limit
        timeframe_days_map = {
            '15m': 1,  # 1 day for 15m gives ~96 candles
            '1h': 1,   # 1 day for 1h gives ~24 candles
            '4h': 7,   # 7 days for 4h gives ~42 candles
            '1d': 90,  # 90 days for 1d gives ~90 candles
        }
        days = timeframe_days_map.get(timeframe.lower(), 1)
        
        # Adjust days based on limit to get enough data
        if timeframe == '15m':
            days = max(1, (limit // 96) + 1)
        elif timeframe == '1h':
            days = max(1, (limit // 24) + 1)
        elif timeframe == '4h':
            days = max(7, (limit // 6) + 1)
        elif timeframe == '1d':
            days = min(365, max(90, limit))
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            def fetch_ohlc_sync():
                return self.coingecko.coins.ohlc(
                    id=coingecko_id,
                    vs_currency='usd',
                    days=days
                )
            
            ohlc_data = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_ohlc_sync),
                timeout=30.0
            )
            
            if not ohlc_data:
                logger.warning(f"No historical data from CoinGecko for {asset}")
                return []
            
            # CoinGecko OHLC format: [timestamp_ms, open, high, low, close]
            candles = []
            interval_ms = self.TIMEFRAME_INTERVAL_MS.get(timeframe.lower(), 60 * 60 * 1000)
            
            for entry in ohlc_data:
                try:
                    timestamp_ms = int(entry[0])
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                    
                    candle = Candle(
                        timestamp=timestamp,
                        open=float(entry[1]),
                        high=float(entry[2]),
                        low=float(entry[3]),
                        close=float(entry[4]),
                        volume=0.0  # CoinGecko OHLC doesn't include volume
                    )
                    candles.append(candle)
                except Exception as e:
                    logger.debug(f"Error parsing CoinGecko OHLC entry: {e}")
                    continue
            
            # Filter and resample to match requested timeframe if needed
            # For now, we'll use the data as-is since CoinGecko returns daily by default
            # For intraday, we might need to use market_chart endpoint
            if timeframe in ['15m', '1h', '4h']:
                # For intraday, try market_chart endpoint
                candles = await self._fetch_intraday_candles_coingecko(
                    coingecko_id, timeframe, limit
                )
            
            # Sort by timestamp (oldest first)
            candles.sort(key=lambda c: c.timestamp)
            
            # Limit to requested number
            candles = candles[-limit:] if len(candles) > limit else candles
            
            logger.info(f"Fetched {len(candles)} historical candles from CoinGecko for {asset} {timeframe}")
            return candles
                
        except Exception as e:
            logger.error(f"Error fetching historical data from CoinGecko for {asset}: {e}")
            return []
    
    async def _fetch_intraday_candles_coingecko(
        self,
        coingecko_id: str,
        timeframe: str,
        limit: int
    ) -> List[Candle]:
        """Fetch intraday candles using CoinGecko market_chart endpoint."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Calculate days needed based on timeframe and limit
            if timeframe == '15m':
                days = max(1, (limit * 15) // (24 * 60) + 1)
            elif timeframe == '1h':
                days = max(1, (limit // 24) + 1)
            elif timeframe == '4h':
                days = max(1, (limit // 6) + 1)
            else:
                days = 1
            
            def fetch_market_chart_sync():
                return self.coingecko.coins.market_chart(
                    id=coingecko_id,
                    vs_currency='usd',
                    days=min(days, 1)  # Market chart max 1 day for free tier
                )
            
            chart_data = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_market_chart_sync),
                timeout=30.0
            )
            
            if not chart_data or 'prices' not in chart_data:
                return []
            
            # Convert prices to candles
            # Market chart gives us prices array: [timestamp_ms, price]
            prices = chart_data.get('prices', [])
            
            if not prices:
                return []
            
            # Group prices by timeframe interval
            candles = []
            interval_ms = self.TIMEFRAME_INTERVAL_MS.get(timeframe.lower(), 60 * 60 * 1000)
            
            current_bucket_start = None
            current_candle = None
            
            for price_entry in prices:
                timestamp_ms = int(price_entry[0])
                price = float(price_entry[1])
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                
                # Calculate bucket start time
                bucket_start_ms = (timestamp_ms // interval_ms) * interval_ms
                
                if current_bucket_start != bucket_start_ms:
                    # Save previous candle if exists
                    if current_candle:
                        candles.append(current_candle)
                    
                    # Start new candle
                    current_bucket_start = bucket_start_ms
                    current_candle = Candle(
                        timestamp=datetime.fromtimestamp(bucket_start_ms / 1000, tz=timezone.utc),
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        volume=0.0
                    )
                else:
                    # Update current candle
                    if current_candle:
                        current_candle.high = max(current_candle.high, price)
                        current_candle.low = min(current_candle.low, price)
                        current_candle.close = price
            
            # Add last candle
            if current_candle:
                candles.append(current_candle)
            
            return candles[-limit:] if len(candles) > limit else candles
            
        except Exception as e:
            logger.error(f"Error fetching intraday candles from CoinGecko: {e}")
            return []
    
    async def get_latest_candle(
        self,
        asset: str,
        timeframe: str
    ) -> Optional[Candle]:
        """
        Get the most recent closed candle using CoinGecko API.
        
        For forward testing, fetches the latest closed candle from CoinGecko.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe (e.g., '1h')
            
        Returns:
            Candle: Most recent closed candle or None
        """
        try:
            # Fetch last 2 candles from CoinGecko to ensure we get a closed one
            candles = await self.get_historical_candles_coingecko(
                asset,
                timeframe,
                limit=2
            )
            
            if not candles or len(candles) == 0:
                logger.warning(f"No candles available for {asset} {timeframe}")
                return None
            
            # Return the most recent (last) candle
            return candles[-1]
        except Exception as e:
            logger.error(f"Error getting latest candle from CoinGecko for {asset}: {e}")
            return None
    
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
    TIMEFRAME_INTERVAL_MS: Dict[str, int] = {
        '15m': 15 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
    }
    
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
        Fetch candlestick data from external providers with fallbacks.
        
        For crypto assets, tries FreeCryptoAPI first (free, real-time).
        Falls back to CoinGecko API, then yfinance.
        """
        metadata = self.ASSET_CATALOG.get(asset, {})
        
        # Check if it's a crypto asset (has /USDT or /USD)
        is_crypto = '/' in asset and asset.split('/')[1] in ['USDT', 'USD', 'BTC', 'ETH']
        
        # For crypto, try FreeCryptoAPI first (only for daily timeframe)
        if is_crypto and timeframe == '1d':
            try:
                return await self._fetch_from_freecryptoapi(asset, timeframe, start_date, end_date)
            except Exception as exc:
                logger.warning(
                    f"FreeCryptoAPI failed for {asset} {timeframe}: {exc}, trying fallback"
                )
        
        # Fallback to configured sources
        preferred_sources = metadata.get('sources', ['yfinance'])
        last_error: Optional[Exception] = None
        
        for source in preferred_sources:
            try:
                if source == 'coingecko':
                    return await self._fetch_from_coingecko(asset, timeframe, start_date, end_date)
                if source == 'yfinance':
                    return await self._fetch_from_yfinance(asset, timeframe, start_date, end_date)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Market data provider %s failed for %s %s: %s",
                    source,
                    asset,
                    timeframe,
                    exc
                )
        
        if last_error:
            raise Exception(f"Failed to fetch data for {asset} {timeframe}: {last_error}")
        
        raise Exception(f"No configured data sources for {asset}")
    
    async def _fetch_from_yfinance(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        ticker_symbol = self.ASSET_TICKER_MAP.get(asset)
        if not ticker_symbol:
            raise Exception(f"No yfinance ticker configured for {asset}")
        
        interval = self.TIMEFRAME_INTERVAL_MAP[timeframe]
        logger.info(
            "Fetching from yfinance: %s interval=%s from %s to %s",
            ticker_symbol,
            interval,
            start_date.date(),
            end_date.date()
        )
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        def fetch_sync():
            ticker = yf.Ticker(ticker_symbol)
            return ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True,
                actions=False
            )
        
        try:
            df = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_sync),
                timeout=settings.MARKET_DATA_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise Exception(
                f"Market data fetch timed out after {settings.MARKET_DATA_TIMEOUT}s"
            )
        
        if df.empty:
            raise Exception(
                f"No data returned from yfinance for {ticker_symbol} "
                f"{interval} from {start_date.date()} to {end_date.date()}"
            )
        
        candles: List[Candle] = []
        for index, row in df.iterrows():
            timestamp = index.to_pydatetime()
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
            
            candles.append(
                Candle(
                    timestamp=timestamp,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume']),
                )
            )
        
        logger.info(
            "Successfully fetched %s candles from yfinance", len(candles)
        )
        return candles
    
    async def _fetch_from_coingecko(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        coingecko_id = self.ASSET_COINGECKO_MAP.get(asset)
        if not coingecko_id:
            raise Exception(f"No CoinGecko ID configured for {asset}")
        
        interval = self.TIMEFRAME_INTERVAL_MAP[timeframe]
        logger.info(
            "Fetching from CoinGecko: %s interval=%s from %s to %s",
            coingecko_id,
            interval,
            start_date.date(),
            end_date.date()
        )
        
        # Calculate days needed
        duration = end_date - start_date
        days = max(1, duration.days + 1)
        days = min(days, 365)  # CoinGecko free tier max is 365 days
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            def fetch_ohlc_sync():
                return self.coingecko.coins.ohlc(
                    id=coingecko_id,
                    vs_currency='usd',
                    days=days
                )
            
            ohlc_data = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_ohlc_sync),
                timeout=settings.MARKET_DATA_TIMEOUT
            )
            
            if not ohlc_data:
                raise Exception(f"No data returned from CoinGecko for {coingecko_id}")
            
            # CoinGecko OHLC format: [timestamp_ms, open, high, low, close]
            candles: List[Candle] = []
            for entry in ohlc_data:
                try:
                    timestamp_ms = int(entry[0])
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                    
                    # Filter by date range
                    if timestamp < start_date or timestamp > end_date:
                        continue
                    
                    candle = Candle(
                        timestamp=timestamp,
                        open=float(entry[1]),
                        high=float(entry[2]),
                        low=float(entry[3]),
                        close=float(entry[4]),
                        volume=0.0  # CoinGecko OHLC doesn't include volume
                    )
                    candles.append(candle)
                except Exception as e:
                    logger.debug(f"Error parsing CoinGecko OHLC entry: {e}")
                    continue
            
            # Sort by timestamp
            candles.sort(key=lambda c: c.timestamp)
            
            if not candles:
                raise Exception(
                    f"No data returned from CoinGecko for {coingecko_id} {interval} "
                    f"from {start_date.date()} to {end_date.date()}"
                )
            
            logger.info(
                "Successfully fetched %s candles from CoinGecko", len(candles)
            )
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching from CoinGecko: {e}")
            raise
    
    async def _fetch_from_freecryptoapi(
        self,
        asset: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        """
        Fetch historical OHLC data from FreeCryptoAPI.
        
        Note: FreeCryptoAPI getOHLC returns daily candles only.
        For intraday timeframes (15m, 1h, 4h), we'll need to use fallback.
        
        Args:
            asset: Trading asset (e.g., 'BTC/USDT')
            timeframe: Timeframe (only '1d' is supported by FreeCryptoAPI OHLC)
            start_date: Start date
            end_date: End date
            
        Returns:
            List[Candle]: Historical candlestick data
        """
        # Extract base symbol (BTC from BTC/USDT)
        base_symbol = asset.split('/')[0] if '/' in asset else asset
        
        # FreeCryptoAPI getOHLC only supports daily candles
        if timeframe != '1d':
            raise Exception(f"FreeCryptoAPI getOHLC only supports daily (1d) timeframe, got {timeframe}")
        
        try:
            async with httpx.AsyncClient(timeout=settings.MARKET_DATA_TIMEOUT) as client:
                # Use getOHLC endpoint for historical data
                response = await client.get(
                    "https://api.freecryptoapi.com/v1/getOHLC",
                    params={
                        "symbol": base_symbol,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "apikey": "ohy9ctcu1pkbiciq4rzt"
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("status") or not data.get("result"):
                    raise Exception(f"No data returned from FreeCryptoAPI for {base_symbol}")
                
                candles: List[Candle] = []
                for entry in data["result"]:
                    # Parse timestamp
                    time_close_str = entry.get("time_close", "")
                    if time_close_str:
                        try:
                            timestamp = datetime.strptime(time_close_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            # Try date-only format
                            timestamp = datetime.strptime(time_close_str.split()[0], "%Y-%m-%d")
                    else:
                        # Fallback to end_date if no timestamp
                        timestamp = end_date
                    
                    candles.append(
                        Candle(
                            timestamp=timestamp,
                            open=float(entry.get("open", 0)),
                            high=float(entry.get("high", 0)),
                            low=float(entry.get("low", 0)),
                            close=float(entry.get("close", 0)),
                            volume=0.0,  # FreeCryptoAPI OHLC doesn't include volume
                        )
                    )
                
                logger.info(
                    f"Successfully fetched {len(candles)} candles from FreeCryptoAPI for {base_symbol}"
                )
                return candles
                
        except Exception as e:
            logger.error(f"Error fetching from FreeCryptoAPI for {asset}: {e}")
            raise
    
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
