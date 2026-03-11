"""
Bias Detection Engine for the Python Strategy Engine.

Calculates 21-period EMA across timeframes and classifies market bias
as bullish, bearish, or neutral based on price position relative to EMA.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import defaultdict

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Candle, Timeframe, BiasDirection, BiasResult


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.

    Formula: EMA = (Price × Multiplier) + (Previous EMA × (1 - Multiplier))
    where Multiplier = 2 / (Period + 1)

    Args:
        prices: List of prices (oldest to newest).
        period: EMA period.

    Returns:
        EMA value or None if insufficient data.
    """
    if len(prices) < period:
        return None

    # Calculate multiplier
    multiplier = 2 / (period + 1)

    # Initialize EMA with SMA of first 'period' values
    ema = sum(prices[:period]) / period

    # Calculate EMA for remaining values
    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return ema


def calculate_ema_series(prices: List[float], period: int) -> List[float]:
    """
    Calculate EMA series for all valid points.

    Args:
        prices: List of prices (oldest to newest).
        period: EMA period.

    Returns:
        List of EMA values (same length as prices, with None for initial values).
    """
    if len(prices) < period:
        return []

    multiplier = 2 / (period + 1)
    ema_values = []

    # Initialize with SMA
    ema = sum(prices[:period]) / period

    # Fill initial values with None equivalent (we'll use the SMA)
    for i in range(period - 1):
        ema_values.append(None)

    ema_values.append(ema)

    # Calculate remaining EMAs
    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
        ema_values.append(ema)

    return ema_values


class BiasEngine:
    """
    Detects market bias using EMA analysis and structure shifts.

    Classifies bias as:
    - Bullish: Price > EMA + threshold
    - Bearish: Price < EMA - threshold
    - Neutral: Price within ±threshold of EMA
    - Bull Shift: Transition from bearish/neutral to bullish
    - Bear Shift: Transition from bullish/neutral to bearish
    """

    # Bias threshold in points (price distance from EMA)
    BIAS_THRESHOLD = 10.0

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("bias_engine")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings
        self.ema_period = strategy_settings.ema_period  # Default: 21

        # Cache for EMA values per timeframe
        self._ema_cache: Dict[Timeframe, float] = {}

        # Bias history per timeframe (last 100 entries)
        self._bias_history: Dict[Timeframe, List[Dict[str, Any]]] = defaultdict(list)
        self._max_history = 100

    async def analyze(self, candles: List[Candle], timeframe: Timeframe) -> BiasResult:
        """
        Analyze market bias for a timeframe.

        Args:
            candles: List of candles (newest first from Redis).
            timeframe: Timeframe being analyzed.

        Returns:
            BiasResult with direction and EMA distance.
        """
        if not candles or len(candles) < self.ema_period:
            self.logger.debug(f"Insufficient candles for {timeframe.value} bias analysis")
            return BiasResult(
                direction=BiasDirection.NEUTRAL,
                ema_distance=0.0,
                structure_shift=None,
            )

        # Candles are newest first, reverse for EMA calculation
        prices = [c.close for c in reversed(candles)]
        current_price = candles[0].close

        # Calculate EMA
        ema = calculate_ema(prices, self.ema_period)
        if ema is None:
            return BiasResult(
                direction=BiasDirection.NEUTRAL,
                ema_distance=0.0,
                structure_shift=None,
            )

        # Cache EMA value
        self._ema_cache[timeframe] = ema

        # Calculate distance from EMA
        ema_distance = current_price - ema

        # Classify bias
        direction = self._classify_bias(ema_distance)

        # Detect structure shift
        previous_bias = self._get_previous_bias(timeframe)
        structure_shift = self._detect_structure_shift(previous_bias, direction)

        # Create result
        result = BiasResult(
            direction=direction,
            ema_distance=ema_distance,
            structure_shift=structure_shift,
        )

        # Store in history
        await self._store_bias_history(timeframe, result, current_price, ema)

        return result

    def _classify_bias(self, ema_distance: float) -> BiasDirection:
        """
        Classify bias based on distance from EMA.

        Args:
            ema_distance: Price - EMA value.

        Returns:
            BiasDirection classification.
        """
        if ema_distance > self.BIAS_THRESHOLD:
            return BiasDirection.BULLISH
        elif ema_distance < -self.BIAS_THRESHOLD:
            return BiasDirection.BEARISH
        else:
            return BiasDirection.NEUTRAL

    def _get_previous_bias(self, timeframe: Timeframe) -> Optional[BiasDirection]:
        """Get the previous bias direction for a timeframe."""
        history = self._bias_history.get(timeframe, [])
        if history:
            return BiasDirection(history[-1]["direction"])
        return None

    def _detect_structure_shift(
        self,
        previous: Optional[BiasDirection],
        current: BiasDirection
    ) -> Optional[str]:
        """
        Detect structure shift (change in bias direction).

        Args:
            previous: Previous bias direction.
            current: Current bias direction.

        Returns:
            "bullish_shift" or "bearish_shift" or None.
        """
        if previous is None:
            return None

        # Bull shift: moving to bullish from non-bullish
        if current == BiasDirection.BULLISH and previous != BiasDirection.BULLISH:
            return "bullish_shift"

        # Bear shift: moving to bearish from non-bearish
        if current == BiasDirection.BEARISH and previous != BiasDirection.BEARISH:
            return "bearish_shift"

        return None

    async def _store_bias_history(
        self,
        timeframe: Timeframe,
        result: BiasResult,
        price: float,
        ema: float
    ):
        """Store bias result in history."""
        from datetime import timezone
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": result.direction.value,
            "ema_distance": result.ema_distance,
            "structure_shift": result.structure_shift,
            "price": price,
            "ema": ema,
        }

        self._bias_history[timeframe].append(entry)

        # Enforce max history limit
        if len(self._bias_history[timeframe]) > self._max_history:
            self._bias_history[timeframe] = self._bias_history[timeframe][-self._max_history:]

        # Persist to Redis
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = f"bias:history:{timeframe.value}"
            await redis_client.set(key, json.dumps(self._bias_history[timeframe][-self._max_history:]))
        except Exception as e:
            self.logger.error(f"Failed to persist bias history: {e}")

    async def get_bias_history(
        self,
        timeframe: Timeframe,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent bias history for a timeframe.

        Args:
            timeframe: Timeframe to query.
            count: Number of entries to retrieve.

        Returns:
            List of bias history entries (newest first).
        """
        history = self._bias_history.get(timeframe, [])
        return list(reversed(history[-count:]))

    def get_current_ema(self, timeframe: Timeframe) -> Optional[float]:
        """Get the current cached EMA value for a timeframe."""
        return self._ema_cache.get(timeframe)

    def get_confluence_contribution(self, result: BiasResult) -> Dict[str, float]:
        """
        Calculate confluence score contribution from bias analysis.

        Returns:
            Dictionary with score contributions.
        """
        scores = {}

        # Base bias alignment score
        if result.direction == BiasDirection.BULLISH:
            scores["bias_bullish"] = 10.0
        elif result.direction == BiasDirection.BEARISH:
            scores["bias_bearish"] = 10.0
        else:
            scores["bias_neutral"] = 0.0

        # Structure shift bonus
        if result.structure_shift == "bullish_shift":
            scores["structure_shift_bull"] = 5.0
        elif result.structure_shift == "bearish_shift":
            scores["structure_shift_bear"] = 5.0

        return scores

    async def get_multi_timeframe_bias(
        self,
        candles_by_tf: Dict[Timeframe, List[Candle]]
    ) -> Dict[Timeframe, BiasResult]:
        """
        Analyze bias across multiple timeframes.

        Args:
            candles_by_tf: Dictionary of candles by timeframe.

        Returns:
            Dictionary of BiasResult by timeframe.
        """
        results = {}
        for tf, candles in candles_by_tf.items():
            results[tf] = await self.analyze(candles, tf)
        return results

    def check_htf_alignment(
        self,
        ltf_bias: BiasDirection,
        htf_results: Dict[Timeframe, BiasResult]
    ) -> bool:
        """
        Check if lower timeframe bias aligns with higher timeframes.

        Args:
            ltf_bias: Lower timeframe bias direction.
            htf_results: Higher timeframe bias results.

        Returns:
            True if aligned, False otherwise.
        """
        if ltf_bias == BiasDirection.NEUTRAL:
            return False

        for tf, result in htf_results.items():
            if result.direction != ltf_bias and result.direction != BiasDirection.NEUTRAL:
                return False

        return True

    async def load_history_from_redis(self, timeframe: Timeframe):
        """Load bias history from Redis on startup."""
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = f"bias:history:{timeframe.value}"
            data = await redis_client.get(key)
            if data:
                self._bias_history[timeframe] = json.loads(data)
        except Exception as e:
            self.logger.error(f"Failed to load bias history: {e}")


# Global bias engine instance
bias_engine = BiasEngine()
