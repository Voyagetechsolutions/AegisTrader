"""
Property-based tests for the Level Detection Engine.

Tests Properties 8 and 9 from the design document:
- Property 8: Key Level Rounding Accuracy
- Property 9: Distance Calculation Correctness
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List

from hypothesis import given, strategies as st, settings

from backend.strategy.models import Candle, Timeframe, LevelResult
from backend.strategy.engines.level_engine import (
    LevelEngine,
    round_to_level,
    get_nearest_level_above,
    get_nearest_level_below,
    calculate_distance_to_level,
)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def create_candle(close: float) -> Candle:
    """Create a candle with the given close price."""
    return Candle(
        timestamp=datetime.now(),
        open=close,
        high=close + 10,
        low=close - 10,
        close=close,
        volume=100,
        timeframe=Timeframe.M1,
    )


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


class TestPropertyKeyLevelRounding:
    """
    Property 8: Key Level Rounding Accuracy

    For any price value, the calculated key levels should round to the
    nearest 250-point and 125-point increments using standard mathematical
    rounding rules.

    Validates: Requirements 4.1, 4.2
    """

    @given(st.floats(min_value=30000, max_value=45000, allow_nan=False))
    @settings(max_examples=200)
    def test_250_level_rounding(self, price: float):
        """Feature: python-strategy-engine, Property 8: Key Level Rounding

        250-level rounding should produce values divisible by 250.
        """
        level = round_to_level(price, 250)

        # Result should be divisible by 250
        assert level % 250 == 0, f"Level {level} not divisible by 250"

        # Result should be within 125 points of original price (half the increment)
        assert abs(price - level) <= 125, f"Level {level} too far from {price}"

    @given(st.floats(min_value=30000, max_value=45000, allow_nan=False))
    @settings(max_examples=200)
    def test_125_level_rounding(self, price: float):
        """Feature: python-strategy-engine, Property 8: Key Level Rounding

        125-level rounding should produce values divisible by 125.
        """
        level = round_to_level(price, 125)

        # Result should be divisible by 125
        assert level % 125 == 0, f"Level {level} not divisible by 125"

        # Result should be within 62.5 points of original price
        assert abs(price - level) <= 62.5, f"Level {level} too far from {price}"

    def test_exact_level_returns_itself(self):
        """Exact level values should round to themselves."""
        # 250 levels
        assert round_to_level(38000.0, 250) == 38000.0
        assert round_to_level(38250.0, 250) == 38250.0
        assert round_to_level(38500.0, 250) == 38500.0

        # 125 levels
        assert round_to_level(38000.0, 125) == 38000.0
        assert round_to_level(38125.0, 125) == 38125.0
        assert round_to_level(38250.0, 125) == 38250.0

    def test_midpoint_rounding(self):
        """Midpoint values should round correctly (banker's rounding)."""
        # 125 is midpoint between 0 and 250
        # Python's round() uses banker's rounding (round half to even)
        assert round_to_level(38125.0, 250) == 38000.0  # Rounds to even (38000/250=152)

        # 62.5 is midpoint between 0 and 125
        assert round_to_level(38062.5, 125) == 38000.0  # Rounds to even

    def test_level_above_calculation(self):
        """Should find nearest level above correctly."""
        assert get_nearest_level_above(38050, 250) == 38250
        assert get_nearest_level_above(38000, 250) == 38000  # Exact match
        assert get_nearest_level_above(38001, 250) == 38250

        assert get_nearest_level_above(38050, 125) == 38125
        assert get_nearest_level_above(38125, 125) == 38125  # Exact match

    def test_level_below_calculation(self):
        """Should find nearest level below correctly."""
        assert get_nearest_level_below(38050, 250) == 38000
        assert get_nearest_level_below(38000, 250) == 38000  # Exact match
        assert get_nearest_level_below(38249, 250) == 38000

        assert get_nearest_level_below(38150, 125) == 38125
        assert get_nearest_level_below(38125, 125) == 38125  # Exact match


class TestPropertyDistanceCalculation:
    """
    Property 9: Distance Calculation Correctness

    For any current price and key level, the distance calculation should
    return the absolute difference between the price and the nearest level.

    Validates: Requirements 4.5
    """

    @given(
        st.floats(min_value=30000, max_value=45000, allow_nan=False),
        st.floats(min_value=30000, max_value=45000, allow_nan=False)
    )
    @settings(max_examples=200)
    def test_distance_is_absolute(self, price: float, level: float):
        """Feature: python-strategy-engine, Property 9: Distance Calculation

        Distance should always be positive (absolute value).
        """
        distance = calculate_distance_to_level(price, level)
        assert distance >= 0, f"Distance {distance} should be non-negative"

    @given(
        st.floats(min_value=30000, max_value=45000, allow_nan=False),
        st.floats(min_value=30000, max_value=45000, allow_nan=False)
    )
    @settings(max_examples=200)
    def test_distance_formula_correctness(self, price: float, level: float):
        """Feature: python-strategy-engine, Property 9: Distance Calculation

        Distance should equal abs(price - level).
        """
        distance = calculate_distance_to_level(price, level)
        expected = abs(price - level)
        assert abs(distance - expected) < 0.0001

    @given(st.floats(min_value=30000, max_value=45000, allow_nan=False))
    @settings(max_examples=100)
    def test_distance_to_self_is_zero(self, price: float):
        """Distance from a price to itself should be zero."""
        distance = calculate_distance_to_level(price, price)
        assert distance == 0

    @given(
        st.floats(min_value=30000, max_value=45000, allow_nan=False),
        st.floats(min_value=30000, max_value=45000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_distance_is_symmetric(self, price: float, level: float):
        """Distance should be same regardless of direction."""
        d1 = calculate_distance_to_level(price, level)
        d2 = calculate_distance_to_level(level, price)
        assert abs(d1 - d2) < 0.0001


class TestLevelEngineIntegration:
    """Integration tests for LevelEngine."""

    def test_analyze_returns_correct_levels(self):
        """Analysis should return correct nearest levels."""
        mock_redis = MockRedisManager()
        engine = LevelEngine(redis_mgr=mock_redis)

        candles = [create_candle(38100.0)]

        async def run_test():
            return await engine.analyze(candles)

        result = run_async(run_test())

        # 38100 rounds to 38000 for 250 and 38125 for 125
        assert result.nearest_250 == 38000.0
        assert result.nearest_125 == 38125.0
        assert result.distance_to_250 == 100.0
        assert result.distance_to_125 == 25.0

    def test_is_near_level_within_tolerance(self):
        """Should detect when price is near a level."""
        engine = LevelEngine()
        engine.tolerance_250 = 30
        engine.tolerance_125 = 20

        # Price at 38020, nearest 250 is 38000, distance = 20 < 30
        assert engine.is_near_level(38020.0, "250") is True

        # Price at 38050, nearest 250 is 38000, distance = 50 > 30
        assert engine.is_near_level(38050.0, "250") is False

        # Price at 38135, nearest 125 is 38125, distance = 10 < 20
        assert engine.is_near_level(38135.0, "125") is True

    def test_get_levels_in_range(self):
        """Should return all levels within a price range."""
        engine = LevelEngine()

        # Range 38000 to 38600 should include 38000, 38250, 38500
        levels = engine.get_levels_in_range(38000, 38600, "250")
        assert 38000 in levels
        assert 38250 in levels
        assert 38500 in levels
        assert 38750 not in levels

        # 125-point levels in same range
        levels_125 = engine.get_levels_in_range(38000, 38300, "125")
        assert 38000 in levels_125
        assert 38125 in levels_125
        assert 38250 in levels_125

    def test_level_history_tracking(self):
        """Should track level changes in history."""
        mock_redis = MockRedisManager()
        engine = LevelEngine(redis_mgr=mock_redis)

        async def run_test():
            # Analyze at different prices
            await engine.analyze([create_candle(38100.0)])
            await engine.analyze([create_candle(38300.0)])  # Different levels
            return await engine.get_level_history(count=5)

        history = run_async(run_test())
        assert len(history) == 2

    def test_confluence_contribution_near_level(self):
        """Should give high score when near a level."""
        engine = LevelEngine()
        engine.tolerance_250 = 30

        # Very close to 250 level
        result = LevelResult(
            nearest_250=38000.0,
            nearest_125=38000.0,
            distance_to_250=15.0,  # Within tolerance
            distance_to_125=0.0,
        )

        contribution = engine.get_confluence_contribution(result)
        assert "near_250_level" in contribution
        assert contribution["near_250_level"] == 15.0

    def test_confluence_contribution_far_from_level(self):
        """Should give no score when far from levels."""
        engine = LevelEngine()
        engine.tolerance_250 = 30
        engine.tolerance_125 = 20

        # Far from all levels
        result = LevelResult(
            nearest_250=38000.0,
            nearest_125=38000.0,
            distance_to_250=100.0,
            distance_to_125=50.0,
        )

        contribution = engine.get_confluence_contribution(result)
        assert "near_250_level" not in contribution
        assert "near_125_level" not in contribution

    def test_get_next_levels(self):
        """Should return correct next levels above and below."""
        engine = LevelEngine()

        levels = engine.get_next_levels(38100.0)

        assert levels["250"]["above"] == 38250.0
        assert levels["250"]["below"] == 38000.0
        assert levels["125"]["above"] == 38125.0
        assert levels["125"]["below"] == 38000.0

    def test_empty_candles_returns_zeros(self):
        """Should handle empty candle list gracefully."""
        mock_redis = MockRedisManager()
        engine = LevelEngine(redis_mgr=mock_redis)

        async def run_test():
            return await engine.analyze([])

        result = run_async(run_test())

        assert result.nearest_250 == 0.0
        assert result.nearest_125 == 0.0
        assert result.distance_to_250 == 0.0
        assert result.distance_to_125 == 0.0
