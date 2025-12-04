"""
Indicator Calculator Service (The Buffet)

This service calculates technical indicators from candle data using the ta library.
Supports 20+ indicators across Momentum, Trend, Volatility, and Volume categories.
Enforces mode-specific restrictions (Monk Mode vs Omni Mode).
Supports custom indicators via JSON-based rule definitions.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
import pandas as pd
import ta
from .custom_indicator_engine import CustomIndicatorEngine, CustomIndicatorError

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Represents a single candlestick with OHLCV data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorCalculator:
    """
    Calculates technical indicators from candle data based on user configuration.
    Pre-calculates all math using pandas-ta before sending to AI.
    
    Supports two modes:
    - Monk Mode: Only RSI and MACD (information deprivation)
    - Omni Mode: All 20+ indicators available
    """
    
    # Define all available indicators by category
    MOMENTUM_INDICATORS = ['rsi', 'stoch', 'cci', 'mom', 'ao']
    TREND_INDICATORS = ['macd', 'ema_20', 'ema_50', 'ema_200', 'sma_20', 'sma_50', 'sma_200', 'adx', 'psar']
    VOLATILITY_INDICATORS = ['bbands', 'atr', 'kc', 'donchian']
    VOLUME_INDICATORS = ['obv', 'vwap', 'mfi', 'cmf', 'ad_line']
    ADVANCED_INDICATORS = ['supertrend', 'ichimoku', 'zscore']
    INDICATOR_ALIAS_MAP: Dict[str, List[str]] = {
        'stochastic': ['stoch'],
        'ema': ['ema_20', 'ema_50', 'ema_200'],
        'sma': ['sma_20', 'sma_50', 'sma_200'],
        'bb': ['bbands'],
        'keltner': ['kc'],
        'dc': ['donchian'],
        'ad': ['ad_line'],
    }

    # Approximate minimum history (in bars) required before each indicator
    # produces stable, non-null values. Used to decide when it's safe to call
    # the LLM for trading decisions.
    # 
    # These values are based on standard technical analysis practices:
    # - Simple indicators (RSI, SMA, EMA): match their period
    # - Complex indicators (MACD, Ichimoku): use longest component period
    # - Cumulative indicators (OBV, AD Line): can start immediately (1 bar)
    # - Indicators with multiple periods: use the longest period for stability
    INDICATOR_MIN_HISTORY: Dict[str, int] = {
        # Momentum
        'rsi': 14,           # Standard 14-period RSI
        'stoch': 14,         # Standard 14-period Stochastic
        'cci': 20,           # Standard 20-period CCI
        'mom': 10,           # 10-period Momentum/ROC
        'ao': 34,            # Awesome Oscillator uses 5 and 34 periods (use 34 for stability)
        # Trend
        'macd': 26,          # MACD slow EMA window (12, 26, 9 default)
        'ema_20': 20,        # 20-period EMA
        'ema_50': 50,        # 50-period EMA
        'ema_200': 200,      # 200-period EMA
        'sma_20': 20,        # 20-period SMA
        'sma_50': 50,        # 50-period SMA
        'sma_200': 200,      # 200-period SMA
        'adx': 14,           # Standard 14-period ADX
        'psar': 5,           # Parabolic SAR can start early (typically 2-5 bars)
        # Volatility
        'bbands': 20,        # Standard 20-period Bollinger Bands
        'atr': 14,           # Standard 14-period ATR
        'kc': 20,            # Keltner Channels typically use 20-period EMA
        'donchian': 20,      # Standard 20-period Donchian Channels
        # Volume
        'obv': 1,            # OBV is cumulative, can start from first candle
        'vwap': 1,           # VWAP can calculate from first candle
        'mfi': 14,           # Standard 14-period MFI
        'cmf': 20,           # Standard 20-period CMF
        'ad_line': 1,        # A/D Line is cumulative, can start from first candle
        # Advanced
        'supertrend': 10,    # Supertrend uses 10-period ATR in this implementation
        'ichimoku': 52,      # Ichimoku Cloud requires 52 periods for Senkou Span B (full cloud)
        'zscore': 20,        # 20-period Z-score
    }
    
    ALL_INDICATORS = (
        MOMENTUM_INDICATORS + 
        TREND_INDICATORS + 
        VOLATILITY_INDICATORS + 
        VOLUME_INDICATORS + 
        ADVANCED_INDICATORS
    )
    
    # Monk mode restrictions
    MONK_MODE_INDICATORS = ['rsi', 'macd']
    
    def __init__(
        self, 
        candles: List[Candle], 
        enabled_indicators: List[str], 
        mode: str = "omni",
        custom_indicators: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the indicator calculator.
        
        Args:
            candles: List of historical candle data
            enabled_indicators: List of indicator names to calculate
            mode: "monk" or "omni" - determines available indicators
            custom_indicators: Optional list of custom indicator rule definitions
        """
        self.candles = candles
        self.mode = mode.lower()
        self.cache: Dict[str, pd.Series] = {}
        self.custom_indicator_rules = custom_indicators or []
        self.custom_engine: Optional[CustomIndicatorEngine] = None
        
        # Validate mode
        if self.mode not in ['monk', 'omni']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'monk' or 'omni'")
        
        normalized = self._normalize_indicators(enabled_indicators)
        # Validate and filter enabled indicators based on mode
        self.enabled_indicators = self._validate_indicators(normalized)
        
        # Convert candles to DataFrame
        self.df = self._candles_to_dataframe(candles)
        
        # Pre-calculate all enabled indicators
        if len(self.df) > 0:
            self._calculate_with_pandas_ta()
            
            # Initialize and calculate custom indicators if provided
            if self.custom_indicator_rules:
                self._initialize_custom_indicators()
    
    @classmethod
    def _normalize_indicators(cls, enabled_indicators: List[str]) -> List[str]:
        """
        Normalize requested indicator names:
        - Lowercase / trim
        - Expand aliases (e.g. 'ema' -> ['ema_20','ema_50','ema_200'])
        - Deduplicate while preserving order
        """
        normalized: List[str] = []
        for indicator in enabled_indicators or []:
            key = indicator.strip().lower()
            if not key:
                continue
            mapped = cls.INDICATOR_ALIAS_MAP.get(key)
            if mapped:
                normalized.extend(mapped)
            else:
                normalized.append(key)
        # remove duplicates preserve order
        seen = set()
        deduped: List[str] = []
        for indicator in normalized:
            if indicator not in seen:
                deduped.append(indicator)
                seen.add(indicator)
        return deduped
    
    def _validate_indicators(self, enabled_indicators: List[str]) -> List[str]:
        """
        Validate enabled indicators against mode restrictions.
        
        Args:
            enabled_indicators: List of requested indicators
            
        Returns:
            List of valid indicators for the current mode
            
        Raises:
            ValueError: If invalid indicators are requested
        """
        # Check if all requested indicators are valid
        invalid_indicators = [ind for ind in enabled_indicators if ind not in self.ALL_INDICATORS]
        if invalid_indicators:
            raise ValueError(f"Invalid indicators: {invalid_indicators}")
        
        # Enforce Monk Mode restrictions
        if self.mode == 'monk':
            # Only allow RSI and MACD in Monk Mode
            restricted = [ind for ind in enabled_indicators if ind not in self.MONK_MODE_INDICATORS]
            if restricted:
                raise ValueError(
                    f"Monk Mode only allows {self.MONK_MODE_INDICATORS}. "
                    f"Restricted indicators: {restricted}"
                )
            return enabled_indicators
        
        # Omni Mode allows all indicators
        return enabled_indicators
    
    def _candles_to_dataframe(self, candles: List[Candle]) -> pd.DataFrame:
        """
        Convert list of Candle objects to pandas DataFrame.
        
        Args:
            candles: List of Candle objects
            
        Returns:
            DataFrame with OHLCV columns
        """
        if not candles:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        data = {
            'timestamp': [c.timestamp for c in candles],
            'open': [c.open for c in candles],
            'high': [c.high for c in candles],
            'low': [c.low for c in candles],
            'close': [c.close for c in candles],
            'volume': [c.volume for c in candles]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def _calculate_with_pandas_ta(self) -> None:
        """
        Calculate all enabled indicators using ta library.
        Results are cached in self.cache for fast lookup.
        Handles insufficient data by leaving NaN values.
        """
        # MOMENTUM INDICATORS
        
        if 'rsi' in self.enabled_indicators:
            # RSI - Relative Strength Index (default period 14)
            self.cache['rsi'] = ta.momentum.RSIIndicator(self.df['close'], window=14).rsi()
        
        if 'stoch' in self.enabled_indicators:
            # Stochastic Oscillator
            stoch_indicator = ta.momentum.StochasticOscillator(
                self.df['high'], self.df['low'], self.df['close']
            )
            self.cache['stoch'] = stoch_indicator.stoch()
        
        if 'cci' in self.enabled_indicators:
            # CCI - Commodity Channel Index (default period 20)
            self.cache['cci'] = ta.trend.CCIIndicator(
                self.df['high'], self.df['low'], self.df['close'], window=20
            ).cci()
        
        if 'mom' in self.enabled_indicators:
            # Momentum (rate of change, default period 10)
            self.cache['mom'] = ta.momentum.ROCIndicator(self.df['close'], window=10).roc()
        
        if 'ao' in self.enabled_indicators:
            # Awesome Oscillator
            self.cache['ao'] = ta.momentum.AwesomeOscillatorIndicator(
                self.df['high'], self.df['low']
            ).awesome_oscillator()
        
        # TREND INDICATORS
        
        if 'macd' in self.enabled_indicators:
            # MACD - Moving Average Convergence Divergence
            macd_indicator = ta.trend.MACD(self.df['close'])
            self.cache['macd'] = macd_indicator.macd()
        
        if 'ema_20' in self.enabled_indicators:
            self.cache['ema_20'] = ta.trend.EMAIndicator(self.df['close'], window=20).ema_indicator()
        
        if 'ema_50' in self.enabled_indicators:
            self.cache['ema_50'] = ta.trend.EMAIndicator(self.df['close'], window=50).ema_indicator()
        
        if 'ema_200' in self.enabled_indicators:
            self.cache['ema_200'] = ta.trend.EMAIndicator(self.df['close'], window=200).ema_indicator()
        
        if 'sma_20' in self.enabled_indicators:
            self.cache['sma_20'] = ta.trend.SMAIndicator(self.df['close'], window=20).sma_indicator()
        
        if 'sma_50' in self.enabled_indicators:
            self.cache['sma_50'] = ta.trend.SMAIndicator(self.df['close'], window=50).sma_indicator()
        
        if 'sma_200' in self.enabled_indicators:
            self.cache['sma_200'] = ta.trend.SMAIndicator(self.df['close'], window=200).sma_indicator()
        
        if 'adx' in self.enabled_indicators:
            # ADX - Average Directional Index
            self.cache['adx'] = ta.trend.ADXIndicator(
                self.df['high'], self.df['low'], self.df['close']
            ).adx()
        
        if 'psar' in self.enabled_indicators:
            # Parabolic SAR
            psar_indicator = ta.trend.PSARIndicator(
                self.df['high'], self.df['low'], self.df['close']
            )
            # Combine up and down trends
            psar_up = psar_indicator.psar_up()
            psar_down = psar_indicator.psar_down()
            self.cache['psar'] = psar_up.fillna(psar_down)
        
        # VOLATILITY INDICATORS
        
        if 'bbands' in self.enabled_indicators:
            # Bollinger Bands - store middle band value
            bbands_indicator = ta.volatility.BollingerBands(self.df['close'])
            self.cache['bbands'] = bbands_indicator.bollinger_mavg()
        
        if 'atr' in self.enabled_indicators:
            # ATR - Average True Range
            self.cache['atr'] = ta.volatility.AverageTrueRange(
                self.df['high'], self.df['low'], self.df['close']
            ).average_true_range()
        
        if 'kc' in self.enabled_indicators:
            # Keltner Channels - store middle line
            kc_indicator = ta.volatility.KeltnerChannel(
                self.df['high'], self.df['low'], self.df['close']
            )
            self.cache['kc'] = kc_indicator.keltner_channel_mband()
        
        if 'donchian' in self.enabled_indicators:
            # Donchian Channels - store middle line
            donchian_indicator = ta.volatility.DonchianChannel(
                self.df['high'], self.df['low'], self.df['close']
            )
            self.cache['donchian'] = donchian_indicator.donchian_channel_mband()
        
        # VOLUME INDICATORS
        
        if 'obv' in self.enabled_indicators:
            # OBV - On Balance Volume
            self.cache['obv'] = ta.volume.OnBalanceVolumeIndicator(
                self.df['close'], self.df['volume']
            ).on_balance_volume()
        
        if 'vwap' in self.enabled_indicators:
            # VWAP - Volume Weighted Average Price
            self.cache['vwap'] = ta.volume.VolumeWeightedAveragePrice(
                self.df['high'], self.df['low'], self.df['close'], self.df['volume']
            ).volume_weighted_average_price()
        
        if 'mfi' in self.enabled_indicators:
            # MFI - Money Flow Index
            self.cache['mfi'] = ta.volume.MFIIndicator(
                self.df['high'], self.df['low'], self.df['close'], self.df['volume']
            ).money_flow_index()
        
        if 'cmf' in self.enabled_indicators:
            # CMF - Chaikin Money Flow
            self.cache['cmf'] = ta.volume.ChaikinMoneyFlowIndicator(
                self.df['high'], self.df['low'], self.df['close'], self.df['volume']
            ).chaikin_money_flow()
        
        if 'ad_line' in self.enabled_indicators:
            # Accumulation/Distribution Line
            self.cache['ad_line'] = ta.volume.AccDistIndexIndicator(
                self.df['high'], self.df['low'], self.df['close'], self.df['volume']
            ).acc_dist_index()
        
        # ADVANCED INDICATORS
        
        if 'supertrend' in self.enabled_indicators:
            # Supertrend - using ATR-based calculation
            # Note: ta library doesn't have supertrend, so we'll implement a simple version
            atr = ta.volatility.AverageTrueRange(
                self.df['high'], self.df['low'], self.df['close'], window=10
            ).average_true_range()
            hl_avg = (self.df['high'] + self.df['low']) / 2
            multiplier = 3.0
            upper_band = hl_avg + (multiplier * atr)
            lower_band = hl_avg - (multiplier * atr)
            # Simplified: use lower band for uptrend, upper for downtrend
            self.cache['supertrend'] = lower_band
        
        if 'ichimoku' in self.enabled_indicators:
            # Ichimoku Cloud - store conversion line (Tenkan-sen)
            ichimoku_indicator = ta.trend.IchimokuIndicator(
                self.df['high'], self.df['low']
            )
            self.cache['ichimoku'] = ichimoku_indicator.ichimoku_conversion_line()
        
        if 'zscore' in self.enabled_indicators:
            # Z-Score for mean reversion (using 20-period)
            window = 20
            mean = self.df['close'].rolling(window=window).mean()
            std = self.df['close'].rolling(window=window).std()
            self.cache['zscore'] = (self.df['close'] - mean) / std
    
    def calculate_all(self, index: int) -> Dict[str, Optional[float]]:
        """
        Calculate all enabled indicators for the candle at the given index.
        Includes both standard indicators and custom indicators.
        
        Args:
            index: Index of the candle in the DataFrame
            
        Returns:
            Dictionary mapping indicator names to their values.
            Returns None for indicators with insufficient data.
        """
        if index < 0 or index >= len(self.df):
            raise IndexError(f"Index {index} out of range for {len(self.df)} candles")
        
        result = {}
        
        # Return values from cache for each enabled indicator
        for indicator in self.enabled_indicators:
            if indicator in self.cache:
                value = self.cache[indicator].iloc[index]
                # Convert NaN to None for JSON serialization
                result[indicator] = None if pd.isna(value) else float(value)
            else:
                result[indicator] = None
        
        # Add custom indicator values (using user-defined names)
        if self.custom_engine:
            for custom_name in self.custom_engine.get_custom_indicator_names():
                if custom_name in self.cache:
                    value = self.cache[custom_name].iloc[index]
                    # Convert NaN to None for JSON serialization
                    result[custom_name] = None if pd.isna(value) else float(value)
                else:
                    result[custom_name] = None
        
        return result
    
    def get_mode(self) -> str:
        """Return the current mode (monk or omni)"""
        return self.mode
    
    def get_enabled_indicators(self) -> List[str]:
        """Return list of enabled indicators"""
        return self.enabled_indicators.copy()
    
    def get_dataframe(self) -> pd.DataFrame:
        """Return the underlying DataFrame (for testing/debugging)"""
        return self.df.copy()
    
    def _initialize_custom_indicators(self) -> None:
        """
        Initialize the custom indicator engine and calculate custom indicators.
        Adds custom indicator values to the cache.
        """
        # Build available indicators dictionary (OHLCV + calculated indicators)
        available_indicators = {
            'open': self.df['open'],
            'high': self.df['high'],
            'low': self.df['low'],
            'close': self.df['close'],
            'volume': self.df['volume'],
            **self.cache  # All calculated indicators
        }
        
        # Initialize custom indicator engine
        self.custom_engine = CustomIndicatorEngine(
            df=self.df,
            available_indicators=available_indicators
        )
        
        # Add all custom indicator rules
        for rule in self.custom_indicator_rules:
            try:
                self.custom_engine.add_rule(rule)
            except CustomIndicatorError as e:
                # Re-raise with more context
                raise ValueError(f"Failed to add custom indicator rule: {e}")
        
        # Calculate all custom indicators and add to cache
        for name in self.custom_engine.get_custom_indicator_names():
            try:
                self.cache[name] = self.custom_engine.calculate(name)
            except CustomIndicatorError as e:
                # Re-raise with more context
                raise ValueError(f"Failed to calculate custom indicator '{name}': {e}")
    
    def get_custom_indicator_names(self) -> List[str]:
        """
        Get list of custom indicator names.
        
        Returns:
            List of custom indicator names, or empty list if none defined
        """
        if self.custom_engine:
            return self.custom_engine.get_custom_indicator_names()
        return []

    @classmethod
    def compute_min_history(cls, enabled_indicators: List[str]) -> int:
        """
        Compute the approximate minimum number of candles required before all
        requested indicators are expected to have non-null values.

        This is a conservative estimate used to decide when it's reasonable to
        start asking the LLM for trading decisions.
        """
        normalized = cls._normalize_indicators(enabled_indicators)
        max_history = 0
        for ind in normalized:
            required = cls.INDICATOR_MIN_HISTORY.get(ind, 0)
            if required > max_history:
                max_history = required
        return max_history
    
    def check_indicator_readiness(self, index: int, min_ready_percentage: float = 0.8) -> bool:
        """
        Check if a sufficient percentage of indicators are ready (non-null) at the given index.
        
        This allows trading to start when most indicators are ready, rather than waiting
        for ALL indicators (especially slow ones like SMA_200).
        
        Args:
            index: Candle index to check
            min_ready_percentage: Minimum percentage of indicators that must be ready (default 0.8 = 80%)
            
        Returns:
            True if sufficient indicators are ready, False otherwise
        """
        if index < 0 or index >= len(self.df):
            return False
        
        indicators = self.calculate_all(index)
        
        # Count total indicators (standard + custom)
        total_indicator_count = len(self.enabled_indicators)
        if self.custom_engine:
            total_indicator_count += len(self.custom_engine.get_custom_indicator_names())
        
        if total_indicator_count == 0:
            return True  # No indicators to wait for
        
        # Count how many indicators are ready (not None)
        ready_count = sum(1 for value in indicators.values() if value is not None)
        ready_percentage = ready_count / total_indicator_count
        
        # Debug logging for troubleshooting
        if index == 33 or (ready_percentage >= min_ready_percentage and index < 50):
            not_ready = [name for name, value in indicators.items() if value is None]
            logger.debug(
                f"Indicator readiness at index {index}: {ready_count}/{total_indicator_count} "
                f"({ready_percentage*100:.1f}%) ready. Not ready: {not_ready[:10]}"
            )
        
        return ready_percentage >= min_ready_percentage
    
    def find_first_ready_index(self, min_ready_percentage: float = 0.8) -> int:
        """
        Find the first candle index where sufficient indicators are ready.
        
        This is more accurate than compute_min_history because it checks actual
        indicator values rather than using conservative estimates.
        
        Args:
            min_ready_percentage: Minimum percentage of indicators that must be ready (default 0.8 = 80%)
            
        Returns:
            First index where sufficient indicators are ready, or 0 if already ready
        """
        if len(self.df) == 0:
            return 0
        
        # Count total indicators for logging
        total_indicator_count = len(self.enabled_indicators)
        if self.custom_engine:
            total_indicator_count += len(self.custom_engine.get_custom_indicator_names())
        
        logger.debug(
            f"Finding first ready index: {total_indicator_count} total indicators "
            f"({len(self.enabled_indicators)} standard + "
            f"{len(self.custom_engine.get_custom_indicator_names()) if self.custom_engine else 0} custom), "
            f"{min_ready_percentage*100}% threshold"
        )
        
        # Start checking from a reasonable minimum (e.g., 14 for RSI)
        # to avoid checking every single candle
        min_check = min(14, len(self.df) - 1)
        
        for i in range(min_check, len(self.df)):
            if self.check_indicator_readiness(i, min_ready_percentage):
                # Log which indicators are ready/not ready at the found index
                indicators = self.calculate_all(i)
                ready = [name for name, value in indicators.items() if value is not None]
                not_ready = [name for name, value in indicators.items() if value is None]
                logger.info(
                    f"First ready index: {i} ({len(ready)}/{total_indicator_count} indicators ready, "
                    f"{len(ready)/total_indicator_count*100:.1f}%). Not ready: {not_ready}"
                )
                return i
        
        # If we get here, return the last index (indicators may never all be ready)
        logger.warning(
            f"Could not find ready index with {min_ready_percentage*100}% threshold. "
            f"Returning last index: {len(self.df) - 1}"
        )
        return len(self.df) - 1