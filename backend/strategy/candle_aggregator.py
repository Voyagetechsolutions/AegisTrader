"""
Candle Aggregator for the Python Strategy Engine.

Builds higher timeframe candles from 1-minute base data using efficient
rolling window algorithms with session-aware boundary alignment.
"""

from __future__ import annotations
import asyncio
import inspect
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Callable, Any
from collections import defaultdict

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger, performance_logger
from backend.strategy.models import Candle, Timeframe


# Timeframe duration in minutes
TIMEFRAME_MINUTES = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.DAILY: 1440,
    Timeframe.WEEKLY: 10080,
}

# Number of 1M candles needed to build each timeframe
CANDLES_PER_TIMEFRAME = {
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.DAILY: 1440,
    Timeframe.WEEKLY: 10080,
}


class CandleAggregator:
    """
    Builds higher timeframe candles from 1-minute base data.

    Uses rolling window aggregation for memory efficiency and triggers
    analysis events on candle completion.
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("candle_aggregator")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings

        # In-progress candles for each timeframe (not yet complete)
        self._building_candles: Dict[Timeframe, List[Candle]] = defaultdict(list)

        # Callbacks for candle completion events
        self._on_candle_complete: List[Callable[[Candle], Any]] = []

        # Track last processed timestamp to avoid duplicates
        self._last_processed_timestamp: Optional[datetime] = None

    def register_candle_complete_callback(self, callback: Callable[[Candle], Any]):
        """Register a callback to be invoked when a candle completes."""
        self._on_candle_complete.append(callback)

    async def process_new_candle(self, candle: Candle) -> List[Candle]:
        """
        Process a new 1-minute candle and update all higher timeframes.

        Args:
            candle: The new 1-minute candle.

        Returns:
            List of completed higher timeframe candles.
        """
        if candle.timeframe != Timeframe.M1:
            self.logger.warning(f"Expected M1 candle, got {candle.timeframe.value}")
            return []

        # Skip duplicate candles
        if self._last_processed_timestamp == candle.timestamp:
            self.logger.debug(f"Skipping duplicate candle at {candle.timestamp}")
            return []

        self._last_processed_timestamp = candle.timestamp
        completed_candles = []

        # Process each higher timeframe
        for tf in [Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4, Timeframe.DAILY, Timeframe.WEEKLY]:
            completed = await self._process_timeframe(candle, tf)
            if completed:
                completed_candles.append(completed)

                # Trigger callbacks
                for callback in self._on_candle_complete:
                    try:
                        if inspect.iscoroutinefunction(callback):
                            await callback(completed)
                        else:
                            callback(completed)
                    except Exception as e:
                        self.logger.error(f"Callback error for {tf.value}: {e}")

        return completed_candles

    async def _process_timeframe(self, candle: Candle, tf: Timeframe) -> Optional[Candle]:
        """
        Process a 1M candle for a specific higher timeframe.

        Returns a completed candle if the timeframe boundary is crossed.
        """
        # Add to building candles
        self._building_candles[tf].append(candle)

        # Check if we've crossed a timeframe boundary
        if self._is_timeframe_complete(candle.timestamp, tf):
            # Aggregate and store the completed candle
            completed = self._aggregate_candles(tf, self._building_candles[tf])

            if completed:
                # Store in Redis
                await self._store_aggregated_candle(completed)

                # Clear building candles for this timeframe
                self._building_candles[tf] = []

                self.logger.debug(f"Completed {tf.value} candle at {completed.timestamp}")
                return completed

        return None

    def _is_timeframe_complete(self, timestamp: datetime, tf: Timeframe) -> bool:
        """
        Check if the current timestamp marks the end of a timeframe period.

        A timeframe is complete when the next candle would start a new period.
        """
        minutes = TIMEFRAME_MINUTES[tf]

        if tf == Timeframe.DAILY:
            # Daily candles complete at 00:00 UTC
            return self._is_daily_boundary(timestamp)
        elif tf == Timeframe.WEEKLY:
            # Weekly candles complete at 00:00 UTC on Monday
            return self._is_weekly_boundary(timestamp)
        else:
            # Standard timeframes: check if minute aligns with period
            # A candle at minute 4 with M5 would complete the 00:00-00:04 period
            # The next candle at minute 5 starts a new period
            next_minute = (timestamp.minute + 1) % 60

            if tf == Timeframe.H1:
                # Hourly completes when we're at minute 59
                return timestamp.minute == 59
            elif tf == Timeframe.H4:
                # 4H completes at hours 3, 7, 11, 15, 19, 23 minute 59
                return timestamp.minute == 59 and (timestamp.hour + 1) % 4 == 0
            else:
                # M5, M15: check if next minute crosses boundary
                return next_minute % minutes == 0

    def _is_daily_boundary(self, timestamp: datetime) -> bool:
        """Check if timestamp marks the end of a trading day (23:59 UTC)."""
        utc_time = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp
        return utc_time.hour == 23 and utc_time.minute == 59

    def _is_weekly_boundary(self, timestamp: datetime) -> bool:
        """Check if timestamp marks the end of a trading week (Friday 23:59 UTC)."""
        utc_time = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp
        # weekday() returns 4 for Friday
        return utc_time.weekday() == 4 and utc_time.hour == 23 and utc_time.minute == 59

    def _aggregate_candles(self, tf: Timeframe, candles: List[Candle]) -> Optional[Candle]:
        """
        Aggregate a list of 1M candles into a single higher timeframe candle.

        OHLC rules:
        - Open: First candle's open
        - High: Maximum high across all candles
        - Low: Minimum low across all candles
        - Close: Last candle's close
        - Volume: Sum of all volumes
        """
        if not candles:
            return None

        # Calculate OHLCV
        open_price = candles[0].open
        high_price = max(c.high for c in candles)
        low_price = min(c.low for c in candles)
        close_price = candles[-1].close
        total_volume = sum(c.volume for c in candles)

        # Timestamp is the start of the period (first candle's timestamp)
        # Align to the timeframe boundary
        timestamp = self._align_to_timeframe_start(candles[0].timestamp, tf)

        return Candle(
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=total_volume,
            timeframe=tf,
        )

    def _align_to_timeframe_start(self, timestamp: datetime, tf: Timeframe) -> datetime:
        """Align a timestamp to the start of its timeframe period."""
        minutes = TIMEFRAME_MINUTES[tf]

        if tf == Timeframe.DAILY:
            # Daily starts at 00:00 UTC
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif tf == Timeframe.WEEKLY:
            # Weekly starts at Monday 00:00 UTC
            days_since_monday = timestamp.weekday()
            start = timestamp - timedelta(days=days_since_monday)
            return start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif tf == Timeframe.H4:
            # 4H periods: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
            aligned_hour = (timestamp.hour // 4) * 4
            return timestamp.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
        elif tf == Timeframe.H1:
            # Hourly starts at XX:00
            return timestamp.replace(minute=0, second=0, microsecond=0)
        else:
            # M5, M15: align to period start
            aligned_minute = (timestamp.minute // minutes) * minutes
            return timestamp.replace(minute=aligned_minute, second=0, microsecond=0)

    async def _store_aggregated_candle(self, candle: Candle):
        """Store an aggregated candle in Redis."""
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = f"candles:{candle.timeframe.value}"

            # Use timestamp as score for sorted set
            score = candle.timestamp.timestamp()
            member = json.dumps(candle.to_dict())

            await redis_client.zadd(key, {member: score})

            # Enforce rolling window limit
            max_candles = self.settings.max_candles_higher_tf
            current_count = await redis_client.zcard(key)

            if current_count > max_candles:
                excess = current_count - max_candles
                await redis_client.zpopmin(key, excess)

        except Exception as e:
            self.logger.error(f"Error storing {candle.timeframe.value} candle: {e}")

    async def get_timeframe_candles(
        self,
        tf: Timeframe,
        count: int = 100
    ) -> List[Candle]:
        """
        Get historical candles for a specific timeframe.

        Args:
            tf: Timeframe to retrieve.
            count: Number of candles to retrieve.

        Returns:
            List of Candle objects, most recent first.
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = f"candles:{tf.value}"

            # Get most recent candles
            members = await redis_client.zrevrange(key, 0, count - 1)

            candles = []
            for member in members:
                try:
                    data = json.loads(member)
                    candle = Candle.from_dict(data)
                    candles.append(candle)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    self.logger.warning(f"Failed to parse candle data: {e}")

            return candles

        except Exception as e:
            self.logger.error(f"Error retrieving {tf.value} candles: {e}")
            return []

    async def get_current_building_candle(self, tf: Timeframe) -> Optional[Candle]:
        """
        Get the currently building (incomplete) candle for a timeframe.

        Useful for real-time display of in-progress candles.
        """
        candles = self._building_candles.get(tf, [])
        if not candles:
            return None

        return self._aggregate_candles(tf, candles)

    async def rebuild_from_1m_candles(
        self,
        candles_1m: List[Candle],
        target_tf: Timeframe
    ) -> List[Candle]:
        """
        Rebuild higher timeframe candles from a list of 1M candles.

        Useful for recovery after system restart.

        Args:
            candles_1m: List of 1M candles (oldest first).
            target_tf: Target timeframe to build.

        Returns:
            List of aggregated candles.
        """
        if not candles_1m:
            return []

        # Sort by timestamp
        sorted_candles = sorted(candles_1m, key=lambda c: c.timestamp)

        # Group by timeframe period
        period_candles: Dict[datetime, List[Candle]] = defaultdict(list)

        for candle in sorted_candles:
            period_start = self._align_to_timeframe_start(candle.timestamp, target_tf)
            period_candles[period_start].append(candle)

        # Aggregate each complete period
        aggregated = []
        for period_start in sorted(period_candles.keys()):
            candles = period_candles[period_start]
            agg = self._aggregate_candles(target_tf, candles)
            if agg:
                aggregated.append(agg)

        self.logger.info(f"Rebuilt {len(aggregated)} {target_tf.value} candles from {len(candles_1m)} 1M candles")
        return aggregated

    def clear_building_candles(self, tf: Optional[Timeframe] = None):
        """
        Clear in-progress building candles.

        Args:
            tf: Specific timeframe to clear, or None for all.
        """
        if tf:
            self._building_candles[tf] = []
        else:
            self._building_candles.clear()


# Utility functions for external use

def calculate_aggregated_ohlcv(candles: List[Candle]) -> Dict[str, float]:
    """
    Calculate aggregated OHLCV from a list of candles.

    Follows standard OHLC aggregation rules:
    - Open: First candle's open
    - High: Maximum high
    - Low: Minimum low
    - Close: Last candle's close
    - Volume: Sum of volumes

    Args:
        candles: List of candles to aggregate.

    Returns:
        Dictionary with open, high, low, close, volume keys.
    """
    if not candles:
        return {"open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}

    return {
        "open": candles[0].open,
        "high": max(c.high for c in candles),
        "low": min(c.low for c in candles),
        "close": candles[-1].close,
        "volume": sum(c.volume for c in candles),
    }


def get_timeframe_minutes(tf: Timeframe) -> int:
    """Get the duration of a timeframe in minutes."""
    return TIMEFRAME_MINUTES.get(tf, 1)


# Global candle aggregator instance
candle_aggregator = CandleAggregator()
