"""
Property-based tests for the Market Data Layer.

Tests Properties 1 and 2 from the design document:
- Property 1: Market Data Integrity
- Property 2: Rolling Window Storage Limits
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from hypothesis import given, strategies as st, settings, assume

from backend.strategy.models import Candle, Timeframe
from backend.strategy.market_data import MarketDataLayer
from backend.strategy.config import RedisManager
from backend.strategy.exceptions import MT5ConnectionError


def run_async(coro):
    """Helper to run async code in sync context for hypothesis tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Custom strategies for generating test data
@st.composite
def valid_ohlc_strategy(draw):
    """Generate valid OHLCV data where High >= Open,Close and Low <= Open,Close."""
    open_price = draw(st.floats(min_value=30000, max_value=45000, allow_nan=False))
    close_price = draw(st.floats(min_value=30000, max_value=45000, allow_nan=False))

    # High must be >= max(open, close)
    min_high = max(open_price, close_price)
    high_price = draw(st.floats(min_value=min_high, max_value=min_high + 500, allow_nan=False))

    # Low must be <= min(open, close)
    max_low = min(open_price, close_price)
    low_price = draw(st.floats(min_value=max_low - 500, max_value=max_low, allow_nan=False))

    volume = draw(st.integers(min_value=0, max_value=1000000))

    # Timestamp within valid range (last 24 hours)
    minutes_ago = draw(st.integers(min_value=1, max_value=1440))
    timestamp = datetime.now() - timedelta(minutes=minutes_ago)

    return {
        "timestamp": timestamp,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }


@st.composite
def invalid_ohlc_strategy(draw):
    """Generate invalid OHLCV data that violates integrity rules."""
    violation_type = draw(st.sampled_from([
        "high_below_open",
        "low_above_close",
        "high_below_low",
        "negative_volume",
        "future_timestamp",
        "old_timestamp",
    ]))

    base_price = draw(st.floats(min_value=35000, max_value=40000, allow_nan=False))

    if violation_type == "high_below_open":
        return {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "open": base_price + 100,
            "high": base_price,  # High < Open - Invalid
            "low": base_price - 100,
            "close": base_price,
            "volume": 1000,
        }
    elif violation_type == "low_above_close":
        return {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "open": base_price,
            "high": base_price + 100,
            "low": base_price + 50,  # Low > Close - Invalid
            "close": base_price - 50,
            "volume": 1000,
        }
    elif violation_type == "high_below_low":
        return {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "open": base_price,
            "high": base_price - 100,  # High < Low - Invalid
            "low": base_price + 100,
            "close": base_price,
            "volume": 1000,
        }
    elif violation_type == "negative_volume":
        return {
            "timestamp": datetime.now() - timedelta(minutes=5),
            "open": base_price,
            "high": base_price + 50,
            "low": base_price - 50,
            "close": base_price,
            "volume": -100,  # Negative volume - Invalid
        }
    elif violation_type == "future_timestamp":
        return {
            "timestamp": datetime.now() + timedelta(hours=1),  # Future - Invalid
            "open": base_price,
            "high": base_price + 50,
            "low": base_price - 50,
            "close": base_price,
            "volume": 1000,
        }
    else:  # old_timestamp
        return {
            "timestamp": datetime.now() - timedelta(days=2),  # Too old - Invalid
            "open": base_price,
            "high": base_price + 50,
            "low": base_price - 50,
            "close": base_price,
            "volume": 1000,
        }


def create_candle(data: dict, timeframe: Timeframe = Timeframe.M1) -> Candle:
    """Helper to create a Candle from dictionary data."""
    return Candle(
        timestamp=data["timestamp"],
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        volume=data["volume"],
        timeframe=timeframe,
    )


class TestPropertyMarketDataIntegrity:
    """
    Property 1: Market Data Integrity

    For any fetched market data, the validation process should ensure
    OHLCV completeness, timestamp accuracy, and proper sequencing before storage.

    Validates: Requirements 1.2
    """

    @given(valid_ohlc_strategy())
    @settings(max_examples=100)
    def test_valid_candles_pass_validation(self, data):
        """Feature: python-strategy-engine, Property 1: Market Data Integrity

        Valid OHLCV data should pass validation.
        """
        mdl = MarketDataLayer()
        candle = create_candle(data)

        result = run_async(mdl.validate_data_integrity(candle))

        assert result is True, f"Valid candle failed validation: {data}"

    @given(invalid_ohlc_strategy())
    @settings(max_examples=100)
    def test_invalid_candles_fail_validation(self, data):
        """Feature: python-strategy-engine, Property 1: Market Data Integrity

        Invalid OHLCV data should fail validation.
        """
        mdl = MarketDataLayer()
        candle = create_candle(data)

        result = run_async(mdl.validate_data_integrity(candle))

        assert result is False, f"Invalid candle passed validation: {data}"

    def test_high_equals_open_close_is_valid(self):
        """Edge case: High equals both Open and Close (doji-like candle)."""
        mdl = MarketDataLayer()
        candle = Candle(
            timestamp=datetime.now() - timedelta(minutes=5),
            open=38000.0,
            high=38000.0,
            low=37950.0,
            close=38000.0,
            volume=100,
            timeframe=Timeframe.M1,
        )

        result = run_async(mdl.validate_data_integrity(candle))

        assert result is True

    def test_low_equals_open_close_is_valid(self):
        """Edge case: Low equals both Open and Close."""
        mdl = MarketDataLayer()
        candle = Candle(
            timestamp=datetime.now() - timedelta(minutes=5),
            open=38000.0,
            high=38050.0,
            low=38000.0,
            close=38000.0,
            volume=100,
            timeframe=Timeframe.M1,
        )

        result = run_async(mdl.validate_data_integrity(candle))

        assert result is True

    def test_flat_candle_is_valid(self):
        """Edge case: All OHLC values are equal (flat candle)."""
        mdl = MarketDataLayer()
        candle = Candle(
            timestamp=datetime.now() - timedelta(minutes=5),
            open=38000.0,
            high=38000.0,
            low=38000.0,
            close=38000.0,
            volume=0,
            timeframe=Timeframe.M1,
        )

        result = run_async(mdl.validate_data_integrity(candle))

        assert result is True

    def test_zero_volume_is_valid(self):
        """Edge case: Zero volume is acceptable."""
        mdl = MarketDataLayer()
        candle = Candle(
            timestamp=datetime.now() - timedelta(minutes=5),
            open=38000.0,
            high=38050.0,
            low=37950.0,
            close=38025.0,
            volume=0,
            timeframe=Timeframe.M1,
        )

        result = run_async(mdl.validate_data_integrity(candle))

        assert result is True


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

    async def delete(self, key):
        self.data.pop(key, None)
        return 1


class MockRedisManager:
    """Mock Redis manager for testing."""

    def __init__(self):
        self._redis = MockRedis()

    async def get_redis(self):
        return self._redis


class TestPropertyRollingWindowStorage:
    """
    Property 2: Rolling Window Storage Limits

    For any data storage component (candles, analysis results, signals),
    adding items beyond the configured limit should maintain exactly the
    specified count by removing the oldest entries.

    Validates: Requirements 1.3, 2.2, 3.6, 4.4
    """

    @given(st.integers(min_value=10, max_value=100))
    @settings(max_examples=50)
    def test_rolling_window_maintains_limit(self, max_candles):
        """Feature: python-strategy-engine, Property 2: Rolling Window Storage Limits

        Adding candles beyond limit should trim to exact limit.
        """
        mock_redis_mgr = MockRedisManager()
        mdl = MarketDataLayer(redis_mgr=mock_redis_mgr)
        mdl.settings.max_candles_1m = max_candles

        async def run_test():
            # Add more candles than the limit
            candles_to_add = max_candles + 20

            for i in range(candles_to_add):
                candle = Candle(
                    timestamp=datetime.now() - timedelta(minutes=candles_to_add - i),
                    open=38000.0 + i,
                    high=38050.0 + i,
                    low=37950.0 + i,
                    close=38025.0 + i,
                    volume=100,
                    timeframe=Timeframe.M1,
                )
                await mdl.store_candle(candle)

            # Verify count is exactly the limit
            count = await mdl.get_candle_count(Timeframe.M1)
            return count

        count = run_async(run_test())
        assert count == max_candles, f"Expected {max_candles} candles, got {count}"

    def test_oldest_candles_removed_first(self):
        """Oldest candles should be removed when limit is exceeded."""
        mock_redis_mgr = MockRedisManager()
        mdl = MarketDataLayer(redis_mgr=mock_redis_mgr)
        mdl.settings.max_candles_1m = 5

        async def run_test():
            base_time = datetime.now()

            # Add 10 candles with distinct timestamps
            for i in range(10):
                candle = Candle(
                    timestamp=base_time - timedelta(minutes=10 - i),
                    open=38000.0 + i * 10,
                    high=38050.0 + i * 10,
                    low=37950.0 + i * 10,
                    close=38025.0 + i * 10,
                    volume=i,
                    timeframe=Timeframe.M1,
                )
                await mdl.store_candle(candle)

            # Get remaining candles
            candles = await mdl.get_historical_candles(10, Timeframe.M1)
            return candles

        candles = run_async(run_test())

        # Should have exactly 5 candles
        assert len(candles) == 5

        # The oldest candles (indices 0-4) should have been removed
        # Remaining should be the newest (indices 5-9)
        # Volumes should be 5, 6, 7, 8, 9 (newest first means 9, 8, 7, 6, 5)
        volumes = [c.volume for c in candles]
        assert volumes == [9, 8, 7, 6, 5], f"Expected [9,8,7,6,5], got {volumes}"

    def test_under_limit_no_trimming(self):
        """Adding candles under limit should not remove any."""
        mock_redis_mgr = MockRedisManager()
        mdl = MarketDataLayer(redis_mgr=mock_redis_mgr)
        mdl.settings.max_candles_1m = 100

        async def run_test():
            # Add only 50 candles
            for i in range(50):
                candle = Candle(
                    timestamp=datetime.now() - timedelta(minutes=50 - i),
                    open=38000.0,
                    high=38050.0,
                    low=37950.0,
                    close=38025.0,
                    volume=i,
                    timeframe=Timeframe.M1,
                )
                await mdl.store_candle(candle)

            count = await mdl.get_candle_count(Timeframe.M1)
            return count

        count = run_async(run_test())
        assert count == 50

    def test_exact_limit_no_trimming(self):
        """Adding exactly limit candles should keep all."""
        mock_redis_mgr = MockRedisManager()
        mdl = MarketDataLayer(redis_mgr=mock_redis_mgr)
        mdl.settings.max_candles_1m = 20

        async def run_test():
            for i in range(20):
                candle = Candle(
                    timestamp=datetime.now() - timedelta(minutes=20 - i),
                    open=38000.0,
                    high=38050.0,
                    low=37950.0,
                    close=38025.0,
                    volume=i,
                    timeframe=Timeframe.M1,
                )
                await mdl.store_candle(candle)

            count = await mdl.get_candle_count(Timeframe.M1)
            return count

        count = run_async(run_test())
        assert count == 20

    def test_higher_timeframe_uses_different_limit(self):
        """Higher timeframes should use max_candles_higher_tf limit."""
        mock_redis_mgr = MockRedisManager()
        mdl = MarketDataLayer(redis_mgr=mock_redis_mgr)
        mdl.settings.max_candles_1m = 2000
        mdl.settings.max_candles_higher_tf = 10

        async def run_test():
            # Add 20 hourly candles
            for i in range(20):
                candle = Candle(
                    timestamp=datetime.now() - timedelta(hours=20 - i),
                    open=38000.0,
                    high=38050.0,
                    low=37950.0,
                    close=38025.0,
                    volume=i,
                    timeframe=Timeframe.H1,
                )
                await mdl.store_candle(candle)

            count = await mdl.get_candle_count(Timeframe.H1)
            return count

        count = run_async(run_test())
        assert count == 10


class TestCandleSerialization:
    """Test candle serialization and deserialization for Redis storage."""

    @given(valid_ohlc_strategy())
    @settings(max_examples=50)
    def test_candle_round_trip(self, data):
        """Candles should survive JSON serialization round trip."""
        candle = create_candle(data)

        # Serialize to dict
        candle_dict = candle.to_dict()

        # Verify it's JSON serializable
        json_str = json.dumps(candle_dict)

        # Deserialize back
        parsed = json.loads(json_str)
        restored = Candle.from_dict(parsed)

        # Verify equality
        assert restored.timestamp == candle.timestamp
        assert restored.open == candle.open
        assert restored.high == candle.high
        assert restored.low == candle.low
        assert restored.close == candle.close
        assert restored.volume == candle.volume
        assert restored.timeframe == candle.timeframe


class TestRetryLogic:
    """
    Property 3: Retry Logic with Exponential Backoff

    For any failed operation with retry configuration, the system should
    attempt exactly the specified number of retries with exponentially
    increasing delays between attempts.

    Validates: Requirements 1.4
    """

    def test_retry_count_matches_parameter(self):
        """Should attempt exactly the specified number of retries."""
        mdl = MarketDataLayer()
        attempt_count = 0

        async def mock_fetch():
            nonlocal attempt_count
            attempt_count += 1
            raise MT5ConnectionError("Simulated failure")

        async def run_test():
            nonlocal attempt_count
            attempt_count = 0
            with patch.object(mdl, '_fetch_candle_from_mt5', mock_fetch):
                with patch.object(mdl, '_retry_delays', [0, 0, 0, 0, 0]):  # Skip delays in tests
                    try:
                        await mdl.fetch_latest_candle(retries=3)
                    except MT5ConnectionError:
                        pass
            return attempt_count

        count = run_async(run_test())
        assert count == 3, f"Expected 3 attempts, got {count}"

    def test_successful_fetch_stops_retry(self):
        """Should stop retrying once successful."""
        mdl = MarketDataLayer()
        attempt_count = 0

        async def mock_fetch():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise MT5ConnectionError("First attempt fails")
            return Candle(
                timestamp=datetime.now() - timedelta(minutes=1),
                open=38000.0,
                high=38050.0,
                low=37950.0,
                close=38025.0,
                volume=100,
                timeframe=Timeframe.M1,
            )

        async def run_test():
            nonlocal attempt_count
            attempt_count = 0
            with patch.object(mdl, '_fetch_candle_from_mt5', mock_fetch):
                with patch.object(mdl, '_retry_delays', [0, 0, 0, 0, 0]):  # Skip delays in tests
                    candle = await mdl.fetch_latest_candle(retries=5)
            return candle, attempt_count

        candle, count = run_async(run_test())
        assert candle is not None
        assert count == 2, f"Expected 2 attempts, got {count}"
