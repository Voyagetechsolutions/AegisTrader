"""
Property-based tests for the Candle Aggregator.

Tests Properties 4 and 5 from the design document:
- Property 4: Candle Aggregation Mathematical Correctness
- Property 5: Session Boundary Alignment
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import List

from hypothesis import given, strategies as st, settings, assume

from backend.strategy.models import Candle, Timeframe
from backend.strategy.candle_aggregator import (
    CandleAggregator,
    calculate_aggregated_ohlcv,
    get_timeframe_minutes,
    TIMEFRAME_MINUTES,
)


def run_async(coro):
    """Helper to run async code in sync context for hypothesis tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Custom strategies for generating test data
@st.composite
def valid_candle_sequence_strategy(draw, count: int = 5):
    """Generate a valid sequence of 1M candles with realistic price movement."""
    base_price = draw(st.floats(min_value=35000, max_value=40000, allow_nan=False))
    base_time = datetime(2026, 3, 10, 10, 0, 0)  # Start at 10:00

    candles = []
    current_price = base_price

    for i in range(count):
        # Generate realistic OHLC
        movement = draw(st.floats(min_value=-50, max_value=50, allow_nan=False))
        open_price = current_price
        close_price = current_price + movement

        # High/Low must encompass open and close
        extra_high = draw(st.floats(min_value=0, max_value=30, allow_nan=False))
        extra_low = draw(st.floats(min_value=0, max_value=30, allow_nan=False))

        high_price = max(open_price, close_price) + extra_high
        low_price = min(open_price, close_price) - extra_low

        volume = draw(st.integers(min_value=100, max_value=10000))

        candle = Candle(
            timestamp=base_time + timedelta(minutes=i),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timeframe=Timeframe.M1,
        )
        candles.append(candle)
        current_price = close_price

    return candles


@st.composite
def m5_candle_sequence_strategy(draw):
    """Generate exactly 5 candles for M5 aggregation testing."""
    return draw(valid_candle_sequence_strategy(count=5))


@st.composite
def m15_candle_sequence_strategy(draw):
    """Generate exactly 15 candles for M15 aggregation testing."""
    return draw(valid_candle_sequence_strategy(count=15))


def create_1m_candle(
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: int = 100
) -> Candle:
    """Helper to create a 1M candle."""
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timeframe=Timeframe.M1,
    )


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self.data = {}

    async def zadd(self, key, mapping):
        if key not in self.data:
            self.data[key] = {}
        self.data[key].update(mapping)
        return len(mapping)

    async def zcard(self, key):
        return len(self.data.get(key, {}))

    async def zpopmin(self, key, count):
        if key not in self.data:
            return []
        items = sorted(self.data[key].items(), key=lambda x: x[1])
        removed = items[:count]
        self.data[key] = dict(items[count:])
        return removed

    async def zrevrange(self, key, start, end):
        if key not in self.data:
            return []
        items = sorted(self.data[key].items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in items[start:end + 1]]


class MockRedisManager:
    """Mock Redis manager for testing."""

    def __init__(self):
        self._redis = MockRedis()

    async def get_redis(self):
        return self._redis


class TestPropertyCandleAggregationCorrectness:
    """
    Property 4: Candle Aggregation Mathematical Correctness

    For any set of 1-minute candles being aggregated to a higher timeframe,
    the resulting candle should follow OHLC rules:
    - Open equals first candle's open
    - High equals maximum high
    - Low equals minimum low
    - Close equals last candle's close

    Validates: Requirements 2.5
    """

    @given(m5_candle_sequence_strategy())
    @settings(max_examples=100)
    def test_aggregated_open_equals_first_candle_open(self, candles: List[Candle]):
        """Feature: python-strategy-engine, Property 4: Candle Aggregation

        Aggregated Open must equal first candle's Open.
        """
        result = calculate_aggregated_ohlcv(candles)
        assert result["open"] == candles[0].open

    @given(m5_candle_sequence_strategy())
    @settings(max_examples=100)
    def test_aggregated_high_equals_max_high(self, candles: List[Candle]):
        """Feature: python-strategy-engine, Property 4: Candle Aggregation

        Aggregated High must equal maximum High across all candles.
        """
        result = calculate_aggregated_ohlcv(candles)
        expected_high = max(c.high for c in candles)
        assert result["high"] == expected_high

    @given(m5_candle_sequence_strategy())
    @settings(max_examples=100)
    def test_aggregated_low_equals_min_low(self, candles: List[Candle]):
        """Feature: python-strategy-engine, Property 4: Candle Aggregation

        Aggregated Low must equal minimum Low across all candles.
        """
        result = calculate_aggregated_ohlcv(candles)
        expected_low = min(c.low for c in candles)
        assert result["low"] == expected_low

    @given(m5_candle_sequence_strategy())
    @settings(max_examples=100)
    def test_aggregated_close_equals_last_candle_close(self, candles: List[Candle]):
        """Feature: python-strategy-engine, Property 4: Candle Aggregation

        Aggregated Close must equal last candle's Close.
        """
        result = calculate_aggregated_ohlcv(candles)
        assert result["close"] == candles[-1].close

    @given(m5_candle_sequence_strategy())
    @settings(max_examples=100)
    def test_aggregated_volume_equals_sum_of_volumes(self, candles: List[Candle]):
        """Feature: python-strategy-engine, Property 4: Candle Aggregation

        Aggregated Volume must equal sum of all volumes.
        """
        result = calculate_aggregated_ohlcv(candles)
        expected_volume = sum(c.volume for c in candles)
        assert result["volume"] == expected_volume

    @given(m15_candle_sequence_strategy())
    @settings(max_examples=50)
    def test_m15_aggregation_correctness(self, candles: List[Candle]):
        """M15 aggregation should follow same OHLC rules."""
        result = calculate_aggregated_ohlcv(candles)

        assert result["open"] == candles[0].open
        assert result["high"] == max(c.high for c in candles)
        assert result["low"] == min(c.low for c in candles)
        assert result["close"] == candles[-1].close
        assert result["volume"] == sum(c.volume for c in candles)

    def test_single_candle_aggregation(self):
        """Single candle aggregation should return same values."""
        candle = create_1m_candle(
            datetime(2026, 3, 10, 10, 0),
            open_price=38000.0,
            high=38050.0,
            low=37950.0,
            close=38025.0,
            volume=500,
        )

        result = calculate_aggregated_ohlcv([candle])

        assert result["open"] == 38000.0
        assert result["high"] == 38050.0
        assert result["low"] == 37950.0
        assert result["close"] == 38025.0
        assert result["volume"] == 500

    def test_empty_candle_list(self):
        """Empty candle list should return zeros."""
        result = calculate_aggregated_ohlcv([])

        assert result["open"] == 0
        assert result["high"] == 0
        assert result["low"] == 0
        assert result["close"] == 0
        assert result["volume"] == 0

    def test_aggregator_produces_correct_candle(self):
        """CandleAggregator should produce correctly aggregated candles."""
        mock_redis = MockRedisManager()
        aggregator = CandleAggregator(redis_mgr=mock_redis)

        # Create 5 candles for M5 aggregation
        candles = [
            create_1m_candle(datetime(2026, 3, 10, 10, 0), 38000, 38020, 37980, 38010, 100),
            create_1m_candle(datetime(2026, 3, 10, 10, 1), 38010, 38030, 37990, 38025, 150),
            create_1m_candle(datetime(2026, 3, 10, 10, 2), 38025, 38050, 38000, 38040, 200),
            create_1m_candle(datetime(2026, 3, 10, 10, 3), 38040, 38060, 38020, 38035, 180),
            create_1m_candle(datetime(2026, 3, 10, 10, 4), 38035, 38045, 37970, 38000, 120),
        ]

        aggregated = aggregator._aggregate_candles(Timeframe.M5, candles)

        assert aggregated is not None
        assert aggregated.open == 38000  # First candle's open
        assert aggregated.high == 38060  # Max high (candle 4)
        assert aggregated.low == 37970   # Min low (candle 5)
        assert aggregated.close == 38000 # Last candle's close
        assert aggregated.volume == 750  # Sum of volumes
        assert aggregated.timeframe == Timeframe.M5


class TestPropertySessionBoundaryAlignment:
    """
    Property 5: Session Boundary Alignment

    For any daily candle aggregation, the candle boundaries should align
    with 00:00 UTC regardless of when the individual 1-minute candles
    were received.

    Validates: Requirements 2.3
    """

    def test_daily_boundary_at_2359_utc(self):
        """Daily candle should complete at 23:59 UTC."""
        aggregator = CandleAggregator()

        # 23:59 UTC should mark end of daily candle
        timestamp = datetime(2026, 3, 10, 23, 59, 0, tzinfo=timezone.utc)
        assert aggregator._is_daily_boundary(timestamp) is True

    def test_daily_boundary_not_at_other_times(self):
        """Daily candle should not complete at other times."""
        aggregator = CandleAggregator()

        # Various non-boundary times
        test_times = [
            datetime(2026, 3, 10, 0, 0, 0),
            datetime(2026, 3, 10, 12, 0, 0),
            datetime(2026, 3, 10, 23, 0, 0),
            datetime(2026, 3, 10, 23, 58, 0),
        ]

        for timestamp in test_times:
            assert aggregator._is_daily_boundary(timestamp) is False, f"Failed for {timestamp}"

    def test_weekly_boundary_friday_2359_utc(self):
        """Weekly candle should complete at Friday 23:59 UTC."""
        aggregator = CandleAggregator()

        # Friday March 13, 2026 at 23:59 UTC
        friday = datetime(2026, 3, 13, 23, 59, 0, tzinfo=timezone.utc)
        assert friday.weekday() == 4  # Verify it's Friday
        assert aggregator._is_weekly_boundary(friday) is True

    def test_weekly_boundary_not_on_other_days(self):
        """Weekly candle should not complete on other days."""
        aggregator = CandleAggregator()

        # Monday through Thursday and Saturday/Sunday
        for day_offset in [0, 1, 2, 3, 5, 6]:  # Skip Friday (4)
            # March 9, 2026 is Monday
            test_day = datetime(2026, 3, 9 + day_offset, 23, 59, 0, tzinfo=timezone.utc)
            if test_day.weekday() != 4:  # Not Friday
                assert aggregator._is_weekly_boundary(test_day) is False

    def test_daily_candle_timestamp_alignment(self):
        """Daily candle timestamp should align to 00:00."""
        aggregator = CandleAggregator()

        # Candle at 15:30 should align to 00:00 of same day
        candle_time = datetime(2026, 3, 10, 15, 30, 45)
        aligned = aggregator._align_to_timeframe_start(candle_time, Timeframe.DAILY)

        assert aligned.hour == 0
        assert aligned.minute == 0
        assert aligned.second == 0
        assert aligned.day == 10

    def test_weekly_candle_timestamp_alignment(self):
        """Weekly candle timestamp should align to Monday 00:00."""
        aggregator = CandleAggregator()

        # Wednesday March 11, 2026 should align to Monday March 9, 2026
        wednesday = datetime(2026, 3, 11, 14, 30, 0)
        aligned = aggregator._align_to_timeframe_start(wednesday, Timeframe.WEEKLY)

        assert aligned.weekday() == 0  # Monday
        assert aligned.hour == 0
        assert aligned.minute == 0
        assert aligned.day == 9  # March 9, 2026 is Monday

    @given(st.integers(min_value=0, max_value=59))
    @settings(max_examples=60)
    def test_m5_boundary_at_correct_minutes(self, minute: int):
        """M5 candle should complete at minutes 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59."""
        aggregator = CandleAggregator()

        timestamp = datetime(2026, 3, 10, 10, minute, 0)
        is_complete = aggregator._is_timeframe_complete(timestamp, Timeframe.M5)

        # M5 completes when next minute crosses 5-minute boundary
        expected = (minute + 1) % 5 == 0
        assert is_complete == expected, f"Failed at minute {minute}"

    @given(st.integers(min_value=0, max_value=59))
    @settings(max_examples=60)
    def test_m15_boundary_at_correct_minutes(self, minute: int):
        """M15 candle should complete at minutes 14, 29, 44, 59."""
        aggregator = CandleAggregator()

        timestamp = datetime(2026, 3, 10, 10, minute, 0)
        is_complete = aggregator._is_timeframe_complete(timestamp, Timeframe.M15)

        # M15 completes when next minute crosses 15-minute boundary
        expected = (minute + 1) % 15 == 0
        assert is_complete == expected, f"Failed at minute {minute}"

    def test_h1_boundary_at_minute_59(self):
        """H1 candle should complete at minute 59."""
        aggregator = CandleAggregator()

        # Minute 59 should complete hourly candle
        timestamp = datetime(2026, 3, 10, 10, 59, 0)
        assert aggregator._is_timeframe_complete(timestamp, Timeframe.H1) is True

        # Other minutes should not
        for minute in [0, 30, 58]:
            timestamp = datetime(2026, 3, 10, 10, minute, 0)
            assert aggregator._is_timeframe_complete(timestamp, Timeframe.H1) is False

    def test_h4_boundary_at_correct_hours(self):
        """H4 candle should complete at hours 3, 7, 11, 15, 19, 23 minute 59."""
        aggregator = CandleAggregator()

        # Valid H4 boundary hours
        boundary_hours = [3, 7, 11, 15, 19, 23]

        for hour in range(24):
            timestamp = datetime(2026, 3, 10, hour, 59, 0)
            is_complete = aggregator._is_timeframe_complete(timestamp, Timeframe.H4)
            expected = hour in boundary_hours
            assert is_complete == expected, f"Failed at hour {hour}"

    def test_h1_timestamp_alignment(self):
        """H1 candle timestamp should align to XX:00."""
        aggregator = CandleAggregator()

        candle_time = datetime(2026, 3, 10, 10, 45, 30)
        aligned = aggregator._align_to_timeframe_start(candle_time, Timeframe.H1)

        assert aligned.hour == 10
        assert aligned.minute == 0
        assert aligned.second == 0

    def test_h4_timestamp_alignment(self):
        """H4 candle timestamp should align to 00:00, 04:00, 08:00, 12:00, 16:00, 20:00."""
        aggregator = CandleAggregator()

        test_cases = [
            (datetime(2026, 3, 10, 1, 30), 0),
            (datetime(2026, 3, 10, 5, 45), 4),
            (datetime(2026, 3, 10, 11, 15), 8),
            (datetime(2026, 3, 10, 14, 0), 12),
            (datetime(2026, 3, 10, 18, 30), 16),
            (datetime(2026, 3, 10, 22, 45), 20),
        ]

        for candle_time, expected_hour in test_cases:
            aligned = aggregator._align_to_timeframe_start(candle_time, Timeframe.H4)
            assert aligned.hour == expected_hour, f"Failed for {candle_time}"
            assert aligned.minute == 0

    def test_m5_timestamp_alignment(self):
        """M5 candle timestamp should align to 5-minute boundaries."""
        aggregator = CandleAggregator()

        test_cases = [
            (datetime(2026, 3, 10, 10, 3), 0),
            (datetime(2026, 3, 10, 10, 7), 5),
            (datetime(2026, 3, 10, 10, 12), 10),
            (datetime(2026, 3, 10, 10, 47), 45),
            (datetime(2026, 3, 10, 10, 58), 55),
        ]

        for candle_time, expected_minute in test_cases:
            aligned = aggregator._align_to_timeframe_start(candle_time, Timeframe.M5)
            assert aligned.minute == expected_minute, f"Failed for {candle_time}"


class TestCandleAggregatorIntegration:
    """Integration tests for CandleAggregator."""

    def test_process_m5_candle_completion(self):
        """Processing 5 candles should produce one M5 candle."""
        mock_redis = MockRedisManager()
        aggregator = CandleAggregator(redis_mgr=mock_redis)

        async def run_test():
            completed_candles = []

            # Process 5 candles ending at minute 4 (M5 boundary)
            for i in range(5):
                candle = create_1m_candle(
                    datetime(2026, 3, 10, 10, i),
                    38000 + i * 10,
                    38020 + i * 10,
                    37980 + i * 10,
                    38010 + i * 10,
                    100,
                )
                completed = await aggregator.process_new_candle(candle)
                completed_candles.extend(completed)

            return completed_candles

        completed = run_async(run_test())

        # Should have exactly one M5 candle
        m5_candles = [c for c in completed if c.timeframe == Timeframe.M5]
        assert len(m5_candles) == 1

    def test_callback_invoked_on_completion(self):
        """Registered callbacks should be invoked when candle completes."""
        mock_redis = MockRedisManager()
        aggregator = CandleAggregator(redis_mgr=mock_redis)
        callback_invocations = []

        def on_complete(candle: Candle):
            callback_invocations.append(candle)

        aggregator.register_candle_complete_callback(on_complete)

        async def run_test():
            for i in range(5):
                candle = create_1m_candle(
                    datetime(2026, 3, 10, 10, i),
                    38000, 38050, 37950, 38025, 100,
                )
                await aggregator.process_new_candle(candle)

        run_async(run_test())

        # Callback should have been invoked for M5 completion
        assert len(callback_invocations) > 0
        assert any(c.timeframe == Timeframe.M5 for c in callback_invocations)

    def test_rebuild_from_1m_candles(self):
        """Should correctly rebuild higher timeframe candles from 1M data."""
        mock_redis = MockRedisManager()
        aggregator = CandleAggregator(redis_mgr=mock_redis)

        # Create 15 1M candles (should produce 3 M5 candles)
        candles_1m = []
        for i in range(15):
            candle = create_1m_candle(
                datetime(2026, 3, 10, 10, i),
                38000 + i,
                38050 + i,
                37950 + i,
                38025 + i,
                100,
            )
            candles_1m.append(candle)

        async def run_test():
            return await aggregator.rebuild_from_1m_candles(candles_1m, Timeframe.M5)

        m5_candles = run_async(run_test())

        assert len(m5_candles) == 3

        # Verify first M5 candle
        first_m5 = m5_candles[0]
        assert first_m5.open == 38000  # First of first 5
        assert first_m5.close == 38029  # Last of first 5 (38025 + 4)

    def test_skip_duplicate_candles(self):
        """Should skip processing duplicate candles."""
        mock_redis = MockRedisManager()
        aggregator = CandleAggregator(redis_mgr=mock_redis)

        async def run_test():
            candle = create_1m_candle(
                datetime(2026, 3, 10, 10, 0),
                38000, 38050, 37950, 38025, 100,
            )

            # Process same candle twice
            result1 = await aggregator.process_new_candle(candle)
            result2 = await aggregator.process_new_candle(candle)

            return result1, result2

        result1, result2 = run_async(run_test())

        # Second call should be skipped (empty result)
        assert result2 == []

    def test_get_timeframe_candles(self):
        """Should retrieve stored candles from Redis."""
        mock_redis = MockRedisManager()
        aggregator = CandleAggregator(redis_mgr=mock_redis)

        async def run_test():
            # Process enough candles to complete multiple M5 periods
            for period in range(3):
                for i in range(5):
                    minute = period * 5 + i
                    candle = create_1m_candle(
                        datetime(2026, 3, 10, 10, minute),
                        38000, 38050, 37950, 38025, 100,
                    )
                    await aggregator.process_new_candle(candle)

            # Retrieve M5 candles
            return await aggregator.get_timeframe_candles(Timeframe.M5, count=10)

        candles = run_async(run_test())

        assert len(candles) == 3  # Three complete M5 periods


class TestTimeframeConstants:
    """Test timeframe constants and utilities."""

    def test_timeframe_minutes_values(self):
        """Verify timeframe minute values are correct."""
        assert get_timeframe_minutes(Timeframe.M1) == 1
        assert get_timeframe_minutes(Timeframe.M5) == 5
        assert get_timeframe_minutes(Timeframe.M15) == 15
        assert get_timeframe_minutes(Timeframe.H1) == 60
        assert get_timeframe_minutes(Timeframe.H4) == 240
        assert get_timeframe_minutes(Timeframe.DAILY) == 1440
        assert get_timeframe_minutes(Timeframe.WEEKLY) == 10080

    def test_all_timeframes_have_minutes(self):
        """All timeframes should have minute values defined."""
        for tf in Timeframe:
            assert tf in TIMEFRAME_MINUTES
