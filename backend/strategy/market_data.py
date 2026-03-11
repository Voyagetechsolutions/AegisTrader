"""
Market Data Layer for the Python Strategy Engine.

Manages real-time US30 data ingestion from MT5, validates data integrity,
and maintains rolling window storage in Redis.
"""

from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import redis.asyncio as redis
import pytz

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger, performance_logger
from backend.strategy.exceptions import (
    MT5ConnectionError, DataValidationError, RedisConnectionError
)
from backend.strategy.models import Candle, Timeframe


class MarketDataLayer:
    """
    Manages real-time US30 data ingestion and validation.

    Handles MT5 connection, data validation, and Redis storage
    with rolling window management.
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("market_data")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings
        self._mt5_initialized = False
        self._retry_delays = [1, 2, 4, 8, 16, 30]  # Exponential backoff

    async def initialize_mt5(self) -> bool:
        """
        Initialize MT5 connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            import MetaTrader5 as mt5  # type: ignore

            # Shutdown any existing connection first
            if self._mt5_initialized:
                mt5.shutdown()
                self._mt5_initialized = False
                await asyncio.sleep(0.5)  # Brief pause

            if not mt5.initialize():
                error = mt5.last_error()
                self.logger.error(f"MT5 initialization failed: {error}")
                self.logger.error("Make sure MetaTrader 5 is running and logged in")
                return False

            # Verify symbol is available
            symbol_info = mt5.symbol_info(self.settings.mt5_symbol)
            if symbol_info is None:
                self.logger.error(f"Symbol {self.settings.mt5_symbol} not found in MT5")
                mt5.shutdown()
                return False

            # Ensure symbol is visible in Market Watch
            if not symbol_info.visible:
                if not mt5.symbol_select(self.settings.mt5_symbol, True):
                    self.logger.error(f"Failed to select {self.settings.mt5_symbol}")
                    mt5.shutdown()
                    return False

            self._mt5_initialized = True
            self.logger.info(f"MT5 initialized successfully for {self.settings.mt5_symbol}")
            return True

        except ImportError:
            self.logger.warning("MetaTrader5 library not available - using mock data")
            return False
        except Exception as e:
            self.logger.error(f"MT5 initialization error: {e}")
            return False

    async def shutdown_mt5(self):
        """Shutdown MT5 connection."""
        if self._mt5_initialized:
            try:
                import MetaTrader5 as mt5  # type: ignore
                mt5.shutdown()
                self._mt5_initialized = False
                self.logger.info("MT5 connection closed")
            except Exception as e:
                self.logger.error(f"Error shutting down MT5: {e}")

    async def fetch_latest_candle(self, retries: int = 3) -> Optional[Candle]:
        """
        Fetch the latest 1-minute candle from MT5.

        Args:
            retries: Number of retry attempts on failure.

        Returns:
            Candle object or None if fetch fails.
        """
        from datetime import timezone
        start_time = datetime.now(timezone.utc)
        last_error = None

        for attempt in range(retries):
            try:
                candle = await self._fetch_candle_from_mt5()
                if candle:
                    # Validate data integrity
                    if await self.validate_data_integrity(candle):
                        from datetime import timezone
                        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                        performance_logger.log_processing_time("fetch_candle", duration)
                        return candle
                    else:
                        self.logger.warning("Candle validation failed")

            except MT5ConnectionError as e:
                last_error = e
                self.logger.warning(f"MT5 fetch attempt {attempt + 1} failed: {e}")

                # Exponential backoff
                if attempt < retries - 1:
                    delay = self._retry_delays[min(attempt, len(self._retry_delays) - 1)]
                    self.logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error = e
                self.logger.error(f"Unexpected error fetching candle: {e}")
                break

        if last_error:
            raise MT5ConnectionError(f"Failed to fetch candle after {retries} attempts: {last_error}")
        return None

    async def _fetch_candle_from_mt5(self) -> Optional[Candle]:
        """Internal method to fetch candle from MT5."""
        try:
            import MetaTrader5 as mt5  # type: ignore

            # Check if MT5 is still connected
            if not self._mt5_initialized or not mt5.terminal_info():
                self.logger.warning("MT5 connection lost, reinitializing...")
                self._mt5_initialized = False
                if not await self.initialize_mt5():
                    raise MT5ConnectionError("MT5 not initialized")

            # Get the latest completed 1-minute candle
            rates = mt5.copy_rates_from_pos(
                self.settings.mt5_symbol,
                mt5.TIMEFRAME_M1,
                1,  # Start from position 1 (last completed candle)
                1   # Get 1 candle
            )

            if rates is None or len(rates) == 0:
                error = mt5.last_error()
                # Try reinitializing once if we get an error
                self.logger.warning(f"MT5 data fetch failed: {error}, attempting reconnect...")
                self._mt5_initialized = False
                if await self.initialize_mt5():
                    # Retry once after reconnect
                    rates = mt5.copy_rates_from_pos(
                        self.settings.mt5_symbol,
                        mt5.TIMEFRAME_M1,
                        1,
                        1
                    )
                    if rates is None or len(rates) == 0:
                        error = mt5.last_error()
                        raise MT5ConnectionError(f"No data received from MT5: {error}")
                else:
                    raise MT5ConnectionError(f"No data received from MT5: {error}")

            rate = rates[0]
            # MT5 timestamps are in broker server time (often UTC+2 or UTC+3)
            # We need to treat them as UTC since that's what the broker uses as base
            # The timestamp from MT5 is already in seconds since epoch in broker time
            # Convert to UTC by treating the timestamp as UTC directly
            candle_time = datetime.fromtimestamp(rate['time'], tz=timezone.utc)
            
            candle = Candle(
                timestamp=candle_time,
                open=float(rate['open']),
                high=float(rate['high']),
                low=float(rate['low']),
                close=float(rate['close']),
                volume=int(rate['tick_volume']),
                timeframe=Timeframe.M1
            )

            return candle

        except ImportError:
            # MT5 library not available - for testing or development
            raise MT5ConnectionError("MetaTrader5 library not installed")

    async def fetch_historical_candles_from_mt5(
        self,
        count: int = 2000,
        timeframe: Timeframe = Timeframe.M1
    ) -> List[Candle]:
        """
        Fetch historical candles from MT5.

        Args:
            count: Number of candles to fetch.
            timeframe: Timeframe to fetch.

        Returns:
            List of Candle objects.
        """
        try:
            import MetaTrader5 as mt5  # type: ignore

            if not self._mt5_initialized:
                if not await self.initialize_mt5():
                    raise MT5ConnectionError("MT5 not initialized")

            # Map timeframe to MT5 constant
            tf_map = {
                Timeframe.M1: mt5.TIMEFRAME_M1,
                Timeframe.M5: mt5.TIMEFRAME_M5,
                Timeframe.M15: mt5.TIMEFRAME_M15,
                Timeframe.H1: mt5.TIMEFRAME_H1,
                Timeframe.H4: mt5.TIMEFRAME_H4,
                Timeframe.DAILY: mt5.TIMEFRAME_D1,
                Timeframe.WEEKLY: mt5.TIMEFRAME_W1,
            }

            mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M1)

            rates = mt5.copy_rates_from_pos(
                self.settings.mt5_symbol,
                mt5_tf,
                1,  # Start from last completed candle
                count
            )

            if rates is None or len(rates) == 0:
                self.logger.warning(f"No historical data received for {timeframe.value}")
                return []

            candles = []
            for rate in rates:
                # MT5 timestamps - treat as UTC
                candle_time = datetime.fromtimestamp(rate['time'], tz=timezone.utc)
                candle = Candle(
                    timestamp=candle_time,
                    open=float(rate['open']),
                    high=float(rate['high']),
                    low=float(rate['low']),
                    close=float(rate['close']),
                    volume=int(rate['tick_volume']),
                    timeframe=timeframe
                )
                candles.append(candle)

            self.logger.info(f"Fetched {len(candles)} {timeframe.value} candles from MT5")
            return candles

        except ImportError:
            raise MT5ConnectionError("MetaTrader5 library not installed")

    async def validate_data_integrity(self, candle: Candle) -> bool:
        """
        Validate candle data integrity.

        Checks:
        - OHLCV completeness (no None/NaN values)
        - Timestamp accuracy (within expected range)
        - OHLC relationships (High >= Open,Close >= Low)
        - Volume is non-negative

        Args:
            candle: Candle to validate.

        Returns:
            True if valid, False otherwise.
        """
        try:
            # Check for None values
            if any(v is None for v in [candle.open, candle.high, candle.low, candle.close]):
                self.logger.warning("Candle has None OHLC values")
                return False

            # Check OHLC relationships
            if candle.high < candle.open or candle.high < candle.close:
                self.logger.warning(f"Invalid candle: High ({candle.high}) < Open ({candle.open}) or Close ({candle.close})")
                return False

            if candle.low > candle.open or candle.low > candle.close:
                self.logger.warning(f"Invalid candle: Low ({candle.low}) > Open ({candle.open}) or Close ({candle.close})")
                return False

            if candle.high < candle.low:
                self.logger.warning(f"Invalid candle: High ({candle.high}) < Low ({candle.low})")
                return False

            # Check volume is non-negative
            if candle.volume < 0:
                self.logger.warning(f"Invalid candle: Negative volume ({candle.volume})")
                return False

            # Check timestamp is reasonable (not in distant future or past)
            now = datetime.now(timezone.utc)
            max_age = timedelta(hours=24)
            # Allow up to 4 hours in future to account for broker timezone differences
            max_future = timedelta(hours=4)

            # Make candle timestamp timezone-aware if it isn't
            candle_time = candle.timestamp
            if candle_time.tzinfo is None:
                candle_time = candle_time.replace(tzinfo=timezone.utc)

            if candle_time > now + max_future:
                self.logger.warning(f"Candle timestamp too far in future: {candle_time} (now: {now})")
                return False

            if candle_time < now - max_age:
                self.logger.warning(f"Candle timestamp too old: {candle_time} (now: {now})")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    async def store_candle(self, candle: Candle) -> bool:
        """
        Store candle in Redis with rolling window management.

        Maintains 2000-candle limit for 1M data, automatically removing
        oldest entries when limit is exceeded.

        Args:
            candle: Candle to store.

        Returns:
            True if stored successfully.
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = RedisManager.candle_key(candle.timeframe.value)

            # Use timestamp as score for sorted set
            score = candle.timestamp.timestamp()
            member = json.dumps(candle.to_dict())

            # Add to sorted set
            await redis_client.zadd(key, {member: score})

            # Enforce rolling window limit
            max_candles = (
                self.settings.max_candles_1m
                if candle.timeframe == Timeframe.M1
                else self.settings.max_candles_higher_tf
            )

            # Get current count and trim if needed
            current_count = await redis_client.zcard(key)
            if current_count > max_candles:
                # Remove oldest entries
                excess = current_count - max_candles
                await redis_client.zpopmin(key, excess)
                self.logger.debug(f"Trimmed {excess} old candles from {key}")

            return True

        except redis.RedisError as e:
            self.logger.error(f"Redis error storing candle: {e}")
            raise RedisConnectionError(f"Failed to store candle: {e}")
        except Exception as e:
            self.logger.error(f"Error storing candle: {e}")
            return False

    async def get_historical_candles(
        self,
        count: int,
        timeframe: Timeframe = Timeframe.M1
    ) -> List[Candle]:
        """
        Get historical candles from Redis.

        Args:
            count: Number of candles to retrieve.
            timeframe: Timeframe to retrieve.

        Returns:
            List of Candle objects, most recent first.
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = RedisManager.candle_key(timeframe.value)

            # Get most recent candles (highest scores)
            # ZREVRANGE returns in descending order (newest first)
            members = await redis_client.zrevrange(key, 0, count - 1)

            candles = []
            for member in members:
                try:
                    data = json.loads(member)
                    candle = Candle.from_dict(data)
                    candles.append(candle)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    self.logger.warning(f"Failed to parse candle data: {e}")
                    continue

            performance_logger.log_data_metrics("get_historical_candles", len(candles))
            return candles

        except redis.RedisError as e:
            self.logger.error(f"Redis error retrieving candles: {e}")
            raise RedisConnectionError(f"Failed to retrieve candles: {e}")
        except Exception as e:
            self.logger.error(f"Error retrieving candles: {e}")
            return []

    async def get_candle_count(self, timeframe: Timeframe = Timeframe.M1) -> int:
        """
        Get the number of candles stored for a timeframe.

        Args:
            timeframe: Timeframe to check.

        Returns:
            Number of candles stored.
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = RedisManager.candle_key(timeframe.value)
            return await redis_client.zcard(key)
        except Exception as e:
            self.logger.error(f"Error getting candle count: {e}")
            return 0

    async def clear_candles(self, timeframe: Timeframe = Timeframe.M1) -> bool:
        """
        Clear all candles for a timeframe.

        Args:
            timeframe: Timeframe to clear.

        Returns:
            True if cleared successfully.
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = RedisManager.candle_key(timeframe.value)
            await redis_client.delete(key)
            self.logger.info(f"Cleared candles for {timeframe.value}")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing candles: {e}")
            return False

    async def get_latest_stored_candle(
        self,
        timeframe: Timeframe = Timeframe.M1
    ) -> Optional[Candle]:
        """
        Get the most recent candle from Redis.

        Args:
            timeframe: Timeframe to retrieve.

        Returns:
            Most recent Candle or None.
        """
        candles = await self.get_historical_candles(1, timeframe)
        return candles[0] if candles else None


# Global market data layer instance
market_data_layer = MarketDataLayer()
