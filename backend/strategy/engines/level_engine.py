"""
Level Detection Engine for the Python Strategy Engine.

Calculates key psychological levels (250-point and 125-point increments)
and tracks distance from current price to these levels.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Candle, LevelResult


def round_to_level(price: float, increment: int) -> float:
    """
    Round a price to the nearest level increment.

    Args:
        price: Current price.
        increment: Level increment (e.g., 250 or 125).

    Returns:
        Nearest level value.
    """
    return round(price / increment) * increment


def get_nearest_level_above(price: float, increment: int) -> float:
    """Get the nearest level above the current price."""
    import math
    return math.ceil(price / increment) * increment


def get_nearest_level_below(price: float, increment: int) -> float:
    """Get the nearest level below the current price."""
    import math
    return math.floor(price / increment) * increment


def calculate_distance_to_level(price: float, level: float) -> float:
    """
    Calculate the absolute distance from price to a level.

    Args:
        price: Current price.
        level: Target level.

    Returns:
        Absolute distance in points.
    """
    return abs(price - level)


class LevelEngine:
    """
    Detects key psychological levels and calculates distances.

    Key levels are based on:
    - 250-point increments (major levels)
    - 125-point increments (minor levels)
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("level_engine")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings

        self.level_250 = strategy_settings.level_250_increment  # 250
        self.level_125 = strategy_settings.level_125_increment  # 125
        self.tolerance_250 = strategy_settings.level_250_tolerance  # 30
        self.tolerance_125 = strategy_settings.level_125_tolerance  # 20

        # Level history (last 20 levels)
        self._level_history: List[Dict[str, Any]] = []
        self._max_history = 20

        # Current levels cache
        self._current_levels: Optional[LevelResult] = None

    async def analyze(self, candles: List[Candle]) -> LevelResult:
        """
        Analyze key levels relative to current price.

        Args:
            candles: List of candles (newest first).

        Returns:
            LevelResult with nearest levels and distances.
        """
        if not candles:
            return LevelResult(
                nearest_250=0.0,
                nearest_125=0.0,
                distance_to_250=0.0,
                distance_to_125=0.0,
            )

        current_price = candles[0].close

        # Calculate nearest levels
        nearest_250 = round_to_level(current_price, self.level_250)
        nearest_125 = round_to_level(current_price, self.level_125)

        # Calculate distances
        distance_to_250 = calculate_distance_to_level(current_price, nearest_250)
        distance_to_125 = calculate_distance_to_level(current_price, nearest_125)

        result = LevelResult(
            nearest_250=nearest_250,
            nearest_125=nearest_125,
            distance_to_250=distance_to_250,
            distance_to_125=distance_to_125,
        )

        # Update cache and history
        self._current_levels = result
        await self._update_level_history(result, current_price)

        return result

    async def _update_level_history(self, result: LevelResult, price: float):
        """Update level history and persist to Redis."""
        from datetime import timezone
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": price,
            "nearest_250": result.nearest_250,
            "nearest_125": result.nearest_125,
            "distance_to_250": result.distance_to_250,
            "distance_to_125": result.distance_to_125,
        }

        # Check if level changed
        if self._level_history:
            last_entry = self._level_history[-1]
            if (last_entry["nearest_250"] != result.nearest_250 or
                last_entry["nearest_125"] != result.nearest_125):
                self.logger.info(
                    f"Level change: 250={result.nearest_250}, 125={result.nearest_125}"
                )

        self._level_history.append(entry)

        # Enforce max history
        if len(self._level_history) > self._max_history:
            self._level_history = self._level_history[-self._max_history:]

        # Persist to Redis
        try:
            redis_client = await self.redis_mgr.get_redis()
            key = "levels:history"
            await redis_client.set(key, json.dumps(self._level_history))

            # Also store current levels
            await redis_client.set("levels:current", json.dumps({
                "nearest_250": result.nearest_250,
                "nearest_125": result.nearest_125,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
        except Exception as e:
            self.logger.error(f"Failed to persist level history: {e}")

    def is_near_level(
        self,
        price: float,
        level_type: str = "250"
    ) -> bool:
        """
        Check if price is within tolerance of a key level.

        Args:
            price: Current price.
            level_type: "250" or "125".

        Returns:
            True if within tolerance.
        """
        if level_type == "250":
            increment = self.level_250
            tolerance = self.tolerance_250
        else:
            increment = self.level_125
            tolerance = self.tolerance_125

        nearest = round_to_level(price, increment)
        distance = calculate_distance_to_level(price, nearest)

        return distance <= tolerance

    def get_levels_in_range(
        self,
        low_price: float,
        high_price: float,
        level_type: str = "250"
    ) -> List[float]:
        """
        Get all key levels within a price range.

        Args:
            low_price: Lower bound.
            high_price: Upper bound.
            level_type: "250" or "125".

        Returns:
            List of levels in the range.
        """
        increment = self.level_250 if level_type == "250" else self.level_125

        # Start from level below low_price
        start_level = get_nearest_level_below(low_price, increment)
        end_level = get_nearest_level_above(high_price, increment)

        levels = []
        current = start_level
        while current <= end_level:
            if low_price <= current <= high_price:
                levels.append(current)
            current += increment

        return levels

    def get_confluence_contribution(self, result: LevelResult) -> Dict[str, float]:
        """
        Calculate confluence score contribution from level analysis.

        Returns:
            Dictionary with score contributions.
        """
        scores = {}

        # Near 250-point level (higher value)
        if result.distance_to_250 <= self.tolerance_250:
            scores["near_250_level"] = 15.0
        elif result.distance_to_250 <= self.tolerance_250 * 2:
            scores["approaching_250_level"] = 8.0

        # Near 125-point level
        if result.distance_to_125 <= self.tolerance_125:
            scores["near_125_level"] = 10.0
        elif result.distance_to_125 <= self.tolerance_125 * 2:
            scores["approaching_125_level"] = 5.0

        return scores

    async def get_level_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent level history."""
        return self._level_history[-count:]

    def get_current_levels(self) -> Optional[LevelResult]:
        """Get the cached current levels."""
        return self._current_levels

    def get_next_levels(self, price: float) -> Dict[str, Dict[str, float]]:
        """
        Get the next levels above and below current price.

        Args:
            price: Current price.

        Returns:
            Dictionary with above/below levels for each increment.
        """
        return {
            "250": {
                "above": get_nearest_level_above(price, self.level_250),
                "below": get_nearest_level_below(price, self.level_250),
            },
            "125": {
                "above": get_nearest_level_above(price, self.level_125),
                "below": get_nearest_level_below(price, self.level_125),
            },
        }

    async def load_history_from_redis(self):
        """Load level history from Redis on startup."""
        try:
            redis_client = await self.redis_mgr.get_redis()
            data = await redis_client.get("levels:history")
            if data:
                self._level_history = json.loads(data)
        except Exception as e:
            self.logger.error(f"Failed to load level history: {e}")


# Global level engine instance
level_engine = LevelEngine()
