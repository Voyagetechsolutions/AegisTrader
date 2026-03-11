"""
Market Regime Detection Module.

This module classifies market conditions into volatility regimes and trend strength
to enable intelligent engine selection by the Auto-Trade Decision Engine.

Without this, the decision engine is blind. This is the eyes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import numpy as np
from backend.strategy.auto_trade_decision_engine import (
    VolatilityRegime,
    TrendStrength,
    MarketRegime
)
from backend.strategy.dual_engine_models import (
    Instrument,
    OHLCVBar
)


@dataclass
class RegimeDetectorConfig:
    """Configuration for regime detection thresholds."""
    # ATR periods
    atr_period: int = 14
    atr_average_period: int = 50
    
    # Volatility thresholds (multipliers of ATR average)
    low_volatility_threshold: float = 0.8
    normal_volatility_max: float = 1.5
    high_volatility_max: float = 2.5
    # Above 2.5 = EXTREME
    
    # EMA periods for trend detection
    ema_fast_period: int = 50
    ema_slow_period: int = 200
    
    # Trend strength thresholds
    strong_trend_ema_separation: float = 0.005  # 0.5% separation
    weak_trend_ema_separation: float = 0.002   # 0.2% separation
    
    # Swing structure lookback
    swing_lookback_bars: int = 20
    
    # Range compression detection
    range_compression_threshold: float = 0.7  # 70% of average range


class RegimeDetector:
    """
    Detects market regime by analyzing:
    - Volatility (ATR-based)
    - Trend strength (EMA + swing structure)
    - Range compression/expansion
    
    This is what gives the decision engine its eyes.
    """
    
    def __init__(self, config: Optional[RegimeDetectorConfig] = None):
        """Initialize regime detector with configuration."""
        self.config = config or RegimeDetectorConfig()
    
    def detect_regime(
        self,
        instrument: Instrument,
        bars: List[OHLCVBar],
        timestamp: Optional[datetime] = None
    ) -> MarketRegime:
        """
        Detect current market regime from OHLCV data.
        
        Args:
            instrument: Trading instrument
            bars: OHLCV bars (must have at least 200 bars for full analysis)
            timestamp: Current timestamp (defaults to last bar timestamp)
        
        Returns:
            MarketRegime with volatility and trend classification
        
        Raises:
            ValueError: If insufficient data provided
        """
        if len(bars) < self.config.atr_average_period:
            raise ValueError(
                f"Insufficient data: need at least {self.config.atr_average_period} bars, "
                f"got {len(bars)}"
            )
        
        # Calculate volatility regime
        atr_current = self._calculate_atr(bars, self.config.atr_period)
        atr_average = self._calculate_atr_average(bars, self.config.atr_average_period)
        volatility_regime = self._classify_volatility(atr_current, atr_average)
        
        # Calculate trend strength
        trend_strength = self._classify_trend_strength(bars)
        
        return MarketRegime(
            instrument=instrument,
            volatility=volatility_regime,
            trend_strength=trend_strength,
            atr_current=atr_current,
            atr_average=atr_average,
            timestamp=timestamp or bars[-1].timestamp
        )
    
    def _calculate_atr(self, bars: List[OHLCVBar], period: int) -> float:
        """
        Calculate Average True Range.
        
        ATR = average of true ranges over period
        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        """
        if len(bars) < period + 1:
            raise ValueError(f"Need at least {period + 1} bars for ATR calculation")
        
        true_ranges = []
        for i in range(1, len(bars)):
            high = bars[i].high
            low = bars[i].low
            prev_close = bars[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Take last 'period' true ranges and average
        recent_trs = true_ranges[-period:]
        return sum(recent_trs) / len(recent_trs)
    
    def _calculate_atr_average(self, bars: List[OHLCVBar], period: int) -> float:
        """
        Calculate rolling average of ATR over longer period.
        
        This is the baseline for volatility comparison.
        """
        min_bars_needed = period + self.config.atr_period
        
        if len(bars) < min_bars_needed:
            # Fallback: use all available data
            if len(bars) >= self.config.atr_period + 1:
                return self._calculate_atr(bars, self.config.atr_period)
            else:
                raise ValueError(
                    f"Need at least {self.config.atr_period + 1} bars "
                    f"for ATR calculation, got {len(bars)}"
                )
        
        # Calculate ATR values over rolling windows
        atrs = []
        window_size = self.config.atr_period + 1
        
        # Calculate ATR for multiple windows across the period
        num_windows = min(period, len(bars) - window_size + 1)
        step = max(1, (len(bars) - window_size) // num_windows)
        
        for i in range(0, len(bars) - window_size + 1, step):
            window_bars = bars[i:i + window_size]
            if len(window_bars) >= window_size:
                atr = self._calculate_atr(window_bars, self.config.atr_period)
                atrs.append(atr)
        
        return sum(atrs) / len(atrs) if atrs else self._calculate_atr(bars, self.config.atr_period)
    
    def _classify_volatility(self, atr_current: float, atr_average: float) -> VolatilityRegime:
        """
        Classify volatility regime based on ATR ratio.
        
        LOW: ATR < 0.8 × average
        NORMAL: 0.8 × average ≤ ATR ≤ 1.5 × average
        HIGH: 1.5 × average < ATR ≤ 2.5 × average
        EXTREME: ATR > 2.5 × average
        """
        ratio = atr_current / atr_average if atr_average > 0 else 1.0
        
        if ratio < self.config.low_volatility_threshold:
            return VolatilityRegime.LOW
        elif ratio <= self.config.normal_volatility_max:
            return VolatilityRegime.NORMAL
        elif ratio <= self.config.high_volatility_max:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def _classify_trend_strength(self, bars: List[OHLCVBar]) -> TrendStrength:
        """
        Classify trend strength using:
        1. EMA 50 vs EMA 200 relationship and separation
        2. EMA slopes
        3. Recent swing structure quality
        
        STRONG_TREND: Clear directional bias, EMAs separated, clean swings
        WEAK_TREND: Some directional bias, EMAs close, decent swings
        RANGING: No clear direction, EMAs flat/crossing, no swing progression
        CHOPPY: Conflicting signals, EMAs whipsawing, broken swings
        """
        # Need enough data for EMA 200
        if len(bars) < self.config.ema_slow_period:
            # Fallback to simpler analysis with available data
            return self._classify_trend_simple(bars)
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(bars, self.config.ema_fast_period)
        ema_slow = self._calculate_ema(bars, self.config.ema_slow_period)
        
        # Calculate EMA separation (as percentage)
        current_price = bars[-1].close
        ema_separation = abs(ema_fast - ema_slow) / current_price
        
        # Calculate EMA slopes (rate of change over last 10 bars)
        ema_fast_slope = self._calculate_ema_slope(bars, self.config.ema_fast_period, lookback=10)
        ema_slow_slope = self._calculate_ema_slope(bars, self.config.ema_slow_period, lookback=10)
        
        # Analyze swing structure
        swing_quality = self._analyze_swing_structure(bars)
        
        # Determine trend direction
        if ema_fast > ema_slow:
            trend_direction = "up"
        elif ema_fast < ema_slow:
            trend_direction = "down"
        else:
            trend_direction = "neutral"
        
        # Check if slopes agree with direction
        slopes_agree = (
            (trend_direction == "up" and ema_fast_slope > 0 and ema_slow_slope > 0) or
            (trend_direction == "down" and ema_fast_slope < 0 and ema_slow_slope < 0)
        )
        
        # Classify based on all factors
        if (ema_separation >= self.config.strong_trend_ema_separation and
            slopes_agree and
            swing_quality >= 0.7):
            return TrendStrength.STRONG_TREND
        
        elif (ema_separation >= self.config.weak_trend_ema_separation and
              swing_quality >= 0.5):
            return TrendStrength.WEAK_TREND
        
        elif swing_quality < 0.3 or abs(ema_fast_slope) < 0.0001:
            # Very low swing quality or flat EMAs = ranging
            return TrendStrength.RANGING
        
        else:
            # Conflicting signals = choppy
            return TrendStrength.CHOPPY
    
    def _classify_trend_simple(self, bars: List[OHLCVBar]) -> TrendStrength:
        """
        Simplified trend classification when insufficient data for full analysis.
        Uses only swing structure.
        """
        swing_quality = self._analyze_swing_structure(bars)
        
        if swing_quality >= 0.7:
            return TrendStrength.STRONG_TREND
        elif swing_quality >= 0.5:
            return TrendStrength.WEAK_TREND
        elif swing_quality >= 0.3:
            return TrendStrength.RANGING
        else:
            return TrendStrength.CHOPPY
    
    def _calculate_ema(self, bars: List[OHLCVBar], period: int) -> float:
        """
        Calculate Exponential Moving Average.
        
        EMA = (Close - EMA_prev) × multiplier + EMA_prev
        multiplier = 2 / (period + 1)
        """
        if len(bars) < period:
            # Use SMA as fallback
            closes = [bar.close for bar in bars[-period:]]
            return sum(closes) / len(closes)
        
        multiplier = 2.0 / (period + 1)
        
        # Start with SMA for first value
        closes = [bar.close for bar in bars]
        ema = sum(closes[:period]) / period
        
        # Calculate EMA for remaining values
        for i in range(period, len(closes)):
            ema = (closes[i] - ema) * multiplier + ema
        
        return ema
    
    def _calculate_ema_slope(
        self,
        bars: List[OHLCVBar],
        ema_period: int,
        lookback: int = 10
    ) -> float:
        """
        Calculate slope of EMA over lookback period.
        
        Positive slope = uptrend
        Negative slope = downtrend
        Near-zero slope = flat/ranging
        """
        if len(bars) < ema_period + lookback:
            return 0.0
        
        # Calculate EMA at current and lookback positions
        ema_current = self._calculate_ema(bars, ema_period)
        ema_past = self._calculate_ema(bars[:-lookback], ema_period)
        
        # Normalize slope by price
        current_price = bars[-1].close
        slope = (ema_current - ema_past) / current_price / lookback
        
        return slope
    
    def _analyze_swing_structure(self, bars: List[OHLCVBar]) -> float:
        """
        Analyze swing structure quality.
        
        Returns quality score 0.0 to 1.0:
        - 1.0 = Perfect swing progression (higher highs + higher lows OR lower highs + lower lows)
        - 0.5 = Mixed/ranging swings
        - 0.0 = Completely choppy/broken swings
        """
        lookback = min(self.config.swing_lookback_bars, len(bars))
        if lookback < 4:
            return 0.5  # Not enough data
        
        recent_bars = bars[-lookback:]
        
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(1, len(recent_bars) - 1):
            # Swing high: higher than neighbors
            if (recent_bars[i].high > recent_bars[i-1].high and
                recent_bars[i].high > recent_bars[i+1].high):
                swing_highs.append(recent_bars[i].high)
            
            # Swing low: lower than neighbors
            if (recent_bars[i].low < recent_bars[i-1].low and
                recent_bars[i].low < recent_bars[i+1].low):
                swing_lows.append(recent_bars[i].low)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return 0.5  # Not enough swings
        
        # Check for higher highs/lows (uptrend)
        higher_highs = sum(1 for i in range(1, len(swing_highs)) if swing_highs[i] > swing_highs[i-1])
        higher_lows = sum(1 for i in range(1, len(swing_lows)) if swing_lows[i] > swing_lows[i-1])
        
        # Check for lower highs/lows (downtrend)
        lower_highs = sum(1 for i in range(1, len(swing_highs)) if swing_highs[i] < swing_highs[i-1])
        lower_lows = sum(1 for i in range(1, len(swing_lows)) if swing_lows[i] < swing_lows[i-1])
        
        # Calculate consistency scores
        total_high_swings = len(swing_highs) - 1
        total_low_swings = len(swing_lows) - 1
        
        uptrend_score = (higher_highs + higher_lows) / (total_high_swings + total_low_swings)
        downtrend_score = (lower_highs + lower_lows) / (total_high_swings + total_low_swings)
        
        # Return best score (either uptrend or downtrend consistency)
        return max(uptrend_score, downtrend_score)
    
    def detect_range_compression(self, bars: List[OHLCVBar]) -> bool:
        """
        Detect if market is in range compression (potential breakout setup).
        
        Range compression = recent ranges significantly smaller than average.
        This often precedes explosive moves.
        """
        if len(bars) < 20:
            return False
        
        # Calculate recent average range (last 5 bars)
        recent_ranges = [bar.high - bar.low for bar in bars[-5:]]
        recent_avg = sum(recent_ranges) / len(recent_ranges)
        
        # Calculate longer-term average range (last 20 bars)
        all_ranges = [bar.high - bar.low for bar in bars[-20:]]
        long_avg = sum(all_ranges) / len(all_ranges)
        
        # Compression if recent range < 70% of long-term average
        return recent_avg < (long_avg * self.config.range_compression_threshold)
