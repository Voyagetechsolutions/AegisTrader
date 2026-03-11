"""
Market Structure Analysis Engine for the Python Strategy Engine.

Detects Break of Structure (BOS) and Change of Character (CHoCH)
patterns indicating trend continuation or reversal.
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Candle, Timeframe, Direction, StructureResult


class BreakType(Enum):
    """Type of structure break."""
    BOS = "bos"     # Break of Structure (trend continuation)
    CHOCH = "choch"  # Change of Character (trend reversal)


def find_swing_points(candles: List[Candle], lookback: int = 5) -> Tuple[List[float], List[float]]:
    """
    Find swing highs and lows in candle data.

    Args:
        candles: List of candles (newest first).
        lookback: Number of candles to compare on each side.

    Returns:
        Tuple of (swing_highs, swing_lows).
    """
    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(candles) - lookback):
        candle = candles[i]

        # Check if swing high
        is_swing_high = all(
            candle.high >= candles[j].high
            for j in range(i - lookback, i + lookback + 1)
            if j != i
        )
        if is_swing_high:
            swing_highs.append(candle.high)

        # Check if swing low
        is_swing_low = all(
            candle.low <= candles[j].low
            for j in range(i - lookback, i + lookback + 1)
            if j != i
        )
        if is_swing_low:
            swing_lows.append(candle.low)

    return swing_highs, swing_lows


def detect_structure_break(
    current_high: float,
    current_low: float,
    recent_swing_highs: List[float],
    recent_swing_lows: List[float],
    previous_trend: Optional[Direction]
) -> Optional[Dict[str, Any]]:
    """
    Detect a structure break.

    BOS: Price breaks previous swing in trend direction
    CHoCH: Price breaks previous swing against trend direction

    Args:
        current_high: Current candle high.
        current_low: Current candle low.
        recent_swing_highs: Recent swing high levels.
        recent_swing_lows: Recent swing low levels.
        previous_trend: Previous trend direction.

    Returns:
        Break details or None.
    """
    if not recent_swing_highs or not recent_swing_lows:
        return None

    last_swing_high = recent_swing_highs[0] if recent_swing_highs else None
    last_swing_low = recent_swing_lows[0] if recent_swing_lows else None

    # Bullish break (price breaks above swing high)
    if last_swing_high and current_high > last_swing_high:
        if previous_trend == Direction.LONG:
            return {
                "type": BreakType.BOS.value,
                "direction": "bullish_bos",
                "level": last_swing_high,
                "break_price": current_high,
            }
        else:
            return {
                "type": BreakType.CHOCH.value,
                "direction": "bullish_choch",
                "level": last_swing_high,
                "break_price": current_high,
            }

    # Bearish break (price breaks below swing low)
    if last_swing_low and current_low < last_swing_low:
        if previous_trend == Direction.SHORT:
            return {
                "type": BreakType.BOS.value,
                "direction": "bearish_bos",
                "level": last_swing_low,
                "break_price": current_low,
            }
        else:
            return {
                "type": BreakType.CHOCH.value,
                "direction": "bearish_choch",
                "level": last_swing_low,
                "break_price": current_low,
            }

    return None


class StructureEngine:
    """
    Analyzes market structure for BOS and CHoCH patterns.

    - BOS (Break of Structure): Trend continuation signal
    - CHoCH (Change of Character): Trend reversal signal
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("structure_engine")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings

        # Current trend by timeframe
        self._current_trend: Dict[Timeframe, Direction] = {}

        # 24-hour structure break history
        self._break_history: Dict[Timeframe, List[Dict[str, Any]]] = {}
        self._history_hours = strategy_settings.structure_history_hours

    async def analyze(self, candles: List[Candle], timeframe: Timeframe) -> StructureResult:
        """
        Analyze market structure.

        Args:
            candles: List of candles (newest first).
            timeframe: Timeframe being analyzed.

        Returns:
            StructureResult with recent breaks and trend info.
        """
        if len(candles) < 15:
            return StructureResult(recent_breaks=[], current_trend=None, break_type=None)

        # Find swing points
        swing_highs, swing_lows = find_swing_points(candles)

        # Get previous trend
        previous_trend = self._current_trend.get(timeframe)

        # Detect structure break
        current = candles[0]
        structure_break = detect_structure_break(
            current.high,
            current.low,
            swing_highs,
            swing_lows,
            previous_trend,
        )

        # Update trend based on break
        if structure_break:
            structure_break["timestamp"] = current.timestamp.isoformat()
            structure_break["timeframe"] = timeframe.value

            # Update history
            if timeframe not in self._break_history:
                self._break_history[timeframe] = []
            self._break_history[timeframe].append(structure_break)

            # Update current trend
            if "bullish" in structure_break["direction"]:
                self._current_trend[timeframe] = Direction.LONG
            else:
                self._current_trend[timeframe] = Direction.SHORT

        # Clean old history
        self._clean_old_breaks(timeframe)

        # Persist
        await self._persist_structure()

        # Get recent breaks
        recent_breaks = self._break_history.get(timeframe, [])[-5:]
        current_trend = self._current_trend.get(timeframe)
        break_type = structure_break["type"] if structure_break else None

        return StructureResult(
            recent_breaks=recent_breaks,
            current_trend=current_trend,
            break_type=break_type,
        )

    def _clean_old_breaks(self, timeframe: Timeframe):
        """Remove breaks older than history limit."""
        if timeframe not in self._break_history:
            return

        from datetime import timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._history_hours)
        self._break_history[timeframe] = [
            b for b in self._break_history[timeframe]
            if datetime.fromisoformat(b["timestamp"]) > cutoff
        ]

    async def _persist_structure(self):
        """Persist structure data to Redis."""
        try:
            redis_client = await self.redis_mgr.get_redis()

            # Save break history
            await redis_client.set("structure:breaks", json.dumps(
                {tf.value: breaks for tf, breaks in self._break_history.items()}
            ))

            # Save current trends
            await redis_client.set("structure:trends", json.dumps(
                {tf.value: trend.value for tf, trend in self._current_trend.items()}
            ))
        except Exception as e:
            self.logger.error(f"Failed to persist structure: {e}")

    def get_confluence_contribution(self, result: StructureResult) -> Dict[str, float]:
        """Calculate confluence score contribution."""
        scores = {}

        if result.recent_breaks:
            latest_break = result.recent_breaks[-1]
            break_type = latest_break["type"]
            direction = latest_break["direction"]

            if break_type == BreakType.BOS.value:
                if "bullish" in direction:
                    scores["bullish_bos"] = 10.0
                else:
                    scores["bearish_bos"] = 10.0
            elif break_type == BreakType.CHOCH.value:
                if "bullish" in direction:
                    scores["bullish_choch"] = 15.0
                else:
                    scores["bearish_choch"] = 15.0

        # Trend alignment bonus
        if result.current_trend:
            scores["trend_established"] = 5.0

        return scores


# Global instance
structure_engine = StructureEngine()
