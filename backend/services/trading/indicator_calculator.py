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
import pandas as pd
import ta
from .custom_indicator_engine import CustomIndicatorEngine, CustomIndicatorError


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
    
    def _normalize_indicators(self, enabled_indicators: List[str]) -> List[str]:
        normalized: List[str] = []
        for indicator in enabled_indicators or []:
            key = indicator.strip().lower()
            if not key:
                continue
            mapped = self.INDICATOR_ALIAS_MAP.get(key)
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
