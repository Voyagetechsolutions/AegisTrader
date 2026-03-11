"""
Property-based tests for the Bias Detection Engine.

Tests Properties 6 and 7 from the design document:
- Property 6: EMA Calculation Accuracy
- Property 7: Bias Classification Logic
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List

from hypothesis import given, strategies as st, settings, assume

from backend.strategy.models import Candle, Timeframe, BiasDirection, BiasResult
from backend.strategy.engines.bias_engine import (
    BiasEngine,
    calculate_ema,
    calculate_ema_series,
)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def create_candle(
    timestamp: datetime,
    close: float,
    open_price: float = None,
    high: float = None,
    low: float = None,
    volume: int = 100
) -> Candle:
    """Helper to create a candle with defaults."""
    if open_price is None:
        open_price = close
    if high is None:
        high = max(open_price, close) + 10
    if low is None:
        low = min(open_price, close) - 10

    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timeframe=Timeframe.M1,
    )


def create_candle_series(closes: List[float], base_time: datetime = None) -> List[Candle]:
    """Create a series of candles from close prices (newest first for Redis format)."""
    if base_time is None:
        base_time = datetime(2026, 3, 10, 10, 0)

    candles = []
    for i, close in enumerate(closes):
        candle = create_candle(
            timestamp=base_time - timedelta(minutes=i),
            close=close,
        )
        candles.append(candle)

    return candles


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self.data = {}

    async def set(self, key, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)


class MockRedisManager:
    """Mock Redis manager for testing."""

    def __init__(self):
        self._redis = MockRedis()

    async def get_redis(self):
        return self._redis


class TestPropertyEMACalculation:
    """
    Property 6: EMA Calculation Accuracy

    For any sequence of price data and specified period, the calculated EMA
    should match the mathematical formula:
    EMA = (Price × Multiplier) + (Previous EMA × (1 - Multiplier))
    where Multiplier = 2/(Period + 1).

    Validates: Requirements 3.1
    """

    @given(st.lists(st.floats(min_value=30000, max_value=45000, allow_nan=False),
                    min_size=21, max_size=100))
    @settings(max_examples=100)
    def test_ema_formula_correctness(self, prices: List[float]):
        """Feature: python-strategy-engine, Property 6: EMA Calculation Accuracy

        EMA should follow the standard formula.
        """
        period = 21
        multiplier = 2 / (period + 1)

        # Calculate EMA manually
        sma = sum(prices[:period]) / period
        expected_ema = sma

        for price in prices[period:]:
            expected_ema = (price * multiplier) + (expected_ema * (1 - multiplier))

        # Calculate using our function
        actual_ema = calculate_ema(prices, period)

        # Should match within floating point precision
        assert actual_ema is not None
        assert abs(actual_ema - expected_ema) < 0.0001, \
            f"EMA mismatch: {actual_ema} vs {expected_ema}"

    @given(st.integers(min_value=5, max_value=50))
    @settings(max_examples=50)
    def test_ema_multiplier_calculation(self, period: int):
        """Multiplier should be 2/(period+1)."""
        expected_multiplier = 2 / (period + 1)

        # Generate test prices
        prices = [38000.0 + i for i in range(period + 10)]

        # The multiplier is implicit in the EMA calculation
        # Verify by checking EMA responds correctly to price changes
        ema1 = calculate_ema(prices, period)

        # Add a new higher price
        new_price = 40000.0
        prices_new = prices + [new_price]
        ema2 = calculate_ema(prices_new, period)

        # New EMA should be: (new_price * multiplier) + (old_ema * (1 - multiplier))
        expected_ema2 = (new_price * expected_multiplier) + (ema1 * (1 - expected_multiplier))

        assert abs(ema2 - expected_ema2) < 0.0001

    def test_ema_insufficient_data_returns_none(self):
        """EMA should return None with insufficient data."""
        prices = [38000.0] * 10  # Only 10 prices, need 21
        result = calculate_ema(prices, 21)
        assert result is None

    def test_ema_exact_period_uses_sma(self):
        """EMA with exactly period prices should equal SMA."""
        prices = [38000.0, 38100.0, 38050.0, 38200.0, 38150.0]
        period = 5

        ema = calculate_ema(prices, period)
        sma = sum(prices) / len(prices)

        assert ema == sma

    def test_ema_series_length(self):
        """EMA series should have correct length."""
        prices = [38000.0 + i * 10 for i in range(30)]
        period = 21

        series = calculate_ema_series(prices, period)

        # Series should have same length as prices
        assert len(series) == len(prices)

        # First period-1 values should be None
        for i in range(period - 1):
            assert series[i] is None

        # Remaining values should not be None
        for i in range(period - 1, len(prices)):
            assert series[i] is not None

    def test_ema_weighted_toward_recent_prices(self):
        """EMA should weight recent prices more heavily."""
        # Flat prices then a jump
        prices = [38000.0] * 20 + [40000.0]
        period = 21

        ema = calculate_ema(prices, period)

        # EMA should be between 38000 and 40000, closer to 38000
        # due to the 20 flat prices outweighing the single jump
        assert 38000 < ema < 40000
        assert ema < 39000  # Should be closer to 38000


class TestPropertyBiasClassification:
    """
    Property 7: Bias Classification Logic

    For any price and EMA pair, the bias classification should be:
    - Bullish when price > EMA + 10 points
    - Bearish when price < EMA - 10 points
    - Neutral when price is within ±10 points of EMA

    Validates: Requirements 3.2, 3.3, 3.4
    """

    @given(st.floats(min_value=11, max_value=1000, allow_nan=False))
    @settings(max_examples=100)
    def test_bullish_classification(self, distance: float):
        """Feature: python-strategy-engine, Property 7: Bias Classification

        Price > EMA + 10 points should be classified as bullish.
        """
        engine = BiasEngine()
        direction = engine._classify_bias(distance)
        assert direction == BiasDirection.BULLISH

    @given(st.floats(min_value=-1000, max_value=-11, allow_nan=False))
    @settings(max_examples=100)
    def test_bearish_classification(self, distance: float):
        """Feature: python-strategy-engine, Property 7: Bias Classification

        Price < EMA - 10 points should be classified as bearish.
        """
        engine = BiasEngine()
        direction = engine._classify_bias(distance)
        assert direction == BiasDirection.BEARISH

    @given(st.floats(min_value=-10, max_value=10, allow_nan=False))
    @settings(max_examples=100)
    def test_neutral_classification(self, distance: float):
        """Feature: python-strategy-engine, Property 7: Bias Classification

        Price within ±10 points of EMA should be classified as neutral.
        """
        engine = BiasEngine()
        direction = engine._classify_bias(distance)
        assert direction == BiasDirection.NEUTRAL

    def test_exact_threshold_boundaries(self):
        """Test exact boundary values."""
        engine = BiasEngine()

        # Exactly at +10 should be neutral
        assert engine._classify_bias(10.0) == BiasDirection.NEUTRAL

        # Exactly at -10 should be neutral
        assert engine._classify_bias(-10.0) == BiasDirection.NEUTRAL

        # Just above +10 should be bullish
        assert engine._classify_bias(10.01) == BiasDirection.BULLISH

        # Just below -10 should be bearish
        assert engine._classify_bias(-10.01) == BiasDirection.BEARISH

    def test_structure_shift_detection(self):
        """Test structure shift detection logic."""
        engine = BiasEngine()

        # Bullish shift: from bearish to bullish
        shift = engine._detect_structure_shift(BiasDirection.BEARISH, BiasDirection.BULLISH)
        assert shift == "bullish_shift"

        # Bullish shift: from neutral to bullish
        shift = engine._detect_structure_shift(BiasDirection.NEUTRAL, BiasDirection.BULLISH)
        assert shift == "bullish_shift"

        # Bearish shift: from bullish to bearish
        shift = engine._detect_structure_shift(BiasDirection.BULLISH, BiasDirection.BEARISH)
        assert shift == "bearish_shift"

        # Bearish shift: from neutral to bearish
        shift = engine._detect_structure_shift(BiasDirection.NEUTRAL, BiasDirection.BEARISH)
        assert shift == "bearish_shift"

        # No shift: same direction
        shift = engine._detect_structure_shift(BiasDirection.BULLISH, BiasDirection.BULLISH)
        assert shift is None

        # No shift: to neutral
        shift = engine._detect_structure_shift(BiasDirection.BULLISH, BiasDirection.NEUTRAL)
        assert shift is None


class TestBiasEngineIntegration:
    """Integration tests for BiasEngine."""

    def test_analyze_bullish_market(self):
        """Uptrending market should show bullish bias."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        # Create uptrending prices (newest first)
        prices = list(reversed([38000 + i * 20 for i in range(25)]))
        candles = create_candle_series(prices)

        async def run_test():
            return await engine.analyze(candles, Timeframe.M15)

        result = run_async(run_test())

        assert result.direction == BiasDirection.BULLISH
        assert result.ema_distance > 10  # Price should be well above EMA

    def test_analyze_bearish_market(self):
        """Downtrending market should show bearish bias."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        # Create downtrending prices (newest first)
        prices = list(reversed([40000 - i * 20 for i in range(25)]))
        candles = create_candle_series(prices)

        async def run_test():
            return await engine.analyze(candles, Timeframe.M15)

        result = run_async(run_test())

        assert result.direction == BiasDirection.BEARISH
        assert result.ema_distance < -10

    def test_analyze_ranging_market(self):
        """Sideways market should show neutral bias."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        # Create flat prices
        prices = [38000.0] * 25
        candles = create_candle_series(prices)

        async def run_test():
            return await engine.analyze(candles, Timeframe.M15)

        result = run_async(run_test())

        assert result.direction == BiasDirection.NEUTRAL
        assert abs(result.ema_distance) <= 10

    def test_insufficient_candles(self):
        """Should return neutral bias with insufficient data."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        # Only 10 candles, need 21
        prices = [38000.0] * 10
        candles = create_candle_series(prices)

        async def run_test():
            return await engine.analyze(candles, Timeframe.M15)

        result = run_async(run_test())

        assert result.direction == BiasDirection.NEUTRAL
        assert result.ema_distance == 0.0

    def test_bias_history_storage(self):
        """Bias history should be stored and retrievable."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        # Analyze twice
        prices1 = [38000 + i * 10 for i in range(25)]
        prices2 = [38000 + i * 20 for i in range(25)]

        async def run_test():
            candles1 = create_candle_series(list(reversed(prices1)))
            candles2 = create_candle_series(list(reversed(prices2)))

            await engine.analyze(candles1, Timeframe.M15)
            await engine.analyze(candles2, Timeframe.M15)

            return await engine.get_bias_history(Timeframe.M15, count=5)

        history = run_async(run_test())

        assert len(history) == 2

    def test_structure_shift_in_analysis(self):
        """Structure shift should be detected across analyses."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        async def run_test():
            # First analysis: bearish
            bearish_prices = list(reversed([40000 - i * 20 for i in range(25)]))
            candles1 = create_candle_series(bearish_prices)
            result1 = await engine.analyze(candles1, Timeframe.M15)

            # Second analysis: bullish (shift)
            bullish_prices = list(reversed([38000 + i * 20 for i in range(25)]))
            candles2 = create_candle_series(bullish_prices)
            result2 = await engine.analyze(candles2, Timeframe.M15)

            return result1, result2

        result1, result2 = run_async(run_test())

        assert result1.direction == BiasDirection.BEARISH
        assert result2.direction == BiasDirection.BULLISH
        assert result2.structure_shift == "bullish_shift"

    def test_confluence_contribution(self):
        """Should calculate correct confluence contribution."""
        engine = BiasEngine()

        # Bullish bias
        bullish_result = BiasResult(
            direction=BiasDirection.BULLISH,
            ema_distance=50.0,
            structure_shift="bullish_shift",
        )
        contribution = engine.get_confluence_contribution(bullish_result)

        assert "bias_bullish" in contribution
        assert contribution["bias_bullish"] == 10.0
        assert "structure_shift_bull" in contribution
        assert contribution["structure_shift_bull"] == 5.0

    def test_htf_alignment_check(self):
        """Should correctly check higher timeframe alignment."""
        engine = BiasEngine()

        ltf_bias = BiasDirection.BULLISH
        htf_results = {
            Timeframe.H1: BiasResult(BiasDirection.BULLISH, 50.0),
            Timeframe.H4: BiasResult(BiasDirection.BULLISH, 30.0),
        }

        assert engine.check_htf_alignment(ltf_bias, htf_results) is True

        # Misaligned
        htf_results[Timeframe.H4] = BiasResult(BiasDirection.BEARISH, -30.0)
        assert engine.check_htf_alignment(ltf_bias, htf_results) is False

    def test_ema_caching(self):
        """EMA values should be cached after analysis."""
        mock_redis = MockRedisManager()
        engine = BiasEngine(redis_mgr=mock_redis)

        prices = [38000 + i * 10 for i in range(25)]
        candles = create_candle_series(list(reversed(prices)))

        async def run_test():
            await engine.analyze(candles, Timeframe.M15)
            return engine.get_current_ema(Timeframe.M15)

        ema = run_async(run_test())

        assert ema is not None
        assert 38000 < ema < 40000
