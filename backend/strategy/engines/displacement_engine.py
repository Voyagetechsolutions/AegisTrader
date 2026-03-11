"""
Displacement Candle Detection Engine for the Python Strategy Engine.

Detects strong momentum candles with large bodies relative to their range,
indicating significant directional moves.
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Candle, Timeframe, Direction, DisplacementResult


def is_displacement_candle(candle: Candle, min_points: int = 50, min_body_pct: float = 0.8) -> bool:
    """
    Check if a candle qualifies as a displacement candle.

    Criteria:
    - Total range >= min_points
    - Body represents >= min_body_pct of total range

    Args:
        candle: Candle to check.
        min_points: Minimum movement in points.
        min_body_pct: Minimum body percentage of range.

    Returns:
        True if displacement candle.
    """
    total_range = candle.high - candle.low
    if total_range < min_points:
        return False

    body_size = abs(candle.close - candle.open)
    body_percentage = body_size / total_range if total_range > 0 else 0

    return body_percentage >= min_body_pct


def get_displacement_direction(candle: Candle) -> Direction:
    """Get the direction of a displacement candle."""
    if candle.close > candle.open:
        return Direction.LONG
    return Direction.SHORT


def calculate_displacement_strength(candle: Candle) -> float:
    """
    Calculate displacement strength (0-100).

    Based on body percentage and total range.
    """
    total_range = candle.high - candle.low
    if total_range == 0:
        return 0.0

    body_size = abs(candle.close - candle.open)
    body_pct = body_size / total_range

    # Strength is combination of body percentage and range
    # Normalize range to ~0-1 assuming typical ranges
    range_factor = min(total_range / 100, 1.0)

    return min((body_pct * 60) + (range_factor * 40), 100.0)


class DisplacementEngine:
    """
    Detects displacement candles indicating strong momentum.

    Displacement candles have:
    - At least 50 points of movement
    - Body >= 80% of total range (minimal wicks)
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("displacement_engine")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings

        self.min_points = strategy_settings.displacement_min_points  # 50
        self.min_body_pct = strategy_settings.displacement_body_percentage  # 0.8

        # 12-hour displacement history
        self._displacement_history: Dict[Timeframe, List[Dict[str, Any]]] = {}
        self._history_hours = strategy_settings.displacement_history_hours

    async def analyze(self, candles: List[Candle], timeframe: Timeframe) -> DisplacementResult:
        """
        Analyze for displacement candles.

        Args:
            candles: List of candles (newest first).
            timeframe: Timeframe being analyzed.

        Returns:
            DisplacementResult with recent displacement info.
        """
        if not candles:
            return DisplacementResult(recent_displacement=None, direction=None, strength=0.0)

        # Check recent candles for displacement
        displacements = []
        for i, candle in enumerate(candles[:20]):  # Check last 20 candles
            if is_displacement_candle(candle, self.min_points, self.min_body_pct):
                disp = {
                    "timestamp": candle.timestamp.isoformat(),
                    "direction": get_displacement_direction(candle).value,
                    "range": candle.high - candle.low,
                    "body_pct": abs(candle.close - candle.open) / (candle.high - candle.low),
                    "strength": calculate_displacement_strength(candle),
                    "index": i,
                }
                displacements.append(disp)

        # Update history
        if timeframe not in self._displacement_history:
            self._displacement_history[timeframe] = []

        for disp in displacements:
            disp["timeframe"] = timeframe.value
            self._displacement_history[timeframe].append(disp)

        # Clean old entries
        self._clean_old_displacements(timeframe)

        # Persist
        await self._persist_displacements()

        # Return most recent
        recent = displacements[0] if displacements else None
        direction = Direction(recent["direction"]) if recent else None
        strength = recent["strength"] if recent else 0.0

        return DisplacementResult(
            recent_displacement=recent,
            direction=direction,
            strength=strength,
        )

    def _clean_old_displacements(self, timeframe: Timeframe):
        """Remove displacements older than history limit."""
        if timeframe not in self._displacement_history:
            return

        from datetime import timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._history_hours)
        self._displacement_history[timeframe] = [
            d for d in self._displacement_history[timeframe]
            if datetime.fromisoformat(d["timestamp"]) > cutoff
        ]

    async def _persist_displacements(self):
        """Persist displacement history to Redis."""
        try:
            redis_client = await self.redis_mgr.get_redis()
            await redis_client.set("displacement:history", json.dumps(
                {tf.value: history for tf, history in self._displacement_history.items()}
            ))
        except Exception as e:
            self.logger.error(f"Failed to persist displacements: {e}")

    def get_confluence_contribution(self, result: DisplacementResult) -> Dict[str, float]:
        """Calculate confluence score contribution."""
        scores = {}

        if result.recent_displacement:
            # Score based on strength and recency
            strength = result.strength
            index = result.recent_displacement.get("index", 10)

            if index <= 3 and strength >= 70:
                scores["strong_displacement"] = 12.0
            elif index <= 5 and strength >= 50:
                scores["moderate_displacement"] = 8.0
            elif index <= 10:
                scores["recent_displacement"] = 5.0

            # Direction bonus
            if result.direction == Direction.LONG:
                scores["bullish_displacement"] = 3.0
            else:
                scores["bearish_displacement"] = 3.0

        return scores


# Global instance
displacement_engine = DisplacementEngine()
