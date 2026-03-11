"""
Fair Value Gap (FVG) Detection Engine for the Python Strategy Engine.

Detects imbalances in price where gaps exist between candle wicks,
indicating unfilled orders and potential retest zones.
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Candle, Timeframe, FVGResult


class FVGStatus(Enum):
    """FVG fill status."""
    UNFILLED = "unfilled"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"


def detect_fvg(candle1: Candle, candle2: Candle, candle3: Candle, min_gap: int = 20) -> Optional[Dict[str, Any]]:
    """
    Detect a Fair Value Gap between three consecutive candles.

    Bullish FVG: Gap between candle1 high and candle3 low (gap up)
    Bearish FVG: Gap between candle1 low and candle3 high (gap down)

    Args:
        candle1: First candle (oldest).
        candle2: Middle candle.
        candle3: Third candle (newest).
        min_gap: Minimum gap size in points.

    Returns:
        FVG details or None if no valid FVG.
    """
    # Bullish FVG: candle3.low > candle1.high (gap up)
    if candle3.low > candle1.high:
        gap_size = candle3.low - candle1.high
        if gap_size >= min_gap:
            return {
                "type": "bullish",
                "top": candle3.low,
                "bottom": candle1.high,
                "size": gap_size,
                "timestamp": candle2.timestamp.isoformat(),
                "status": FVGStatus.UNFILLED.value,
            }

    # Bearish FVG: candle3.high < candle1.low (gap down)
    if candle3.high < candle1.low:
        gap_size = candle1.low - candle3.high
        if gap_size >= min_gap:
            return {
                "type": "bearish",
                "top": candle1.low,
                "bottom": candle3.high,
                "size": gap_size,
                "timestamp": candle2.timestamp.isoformat(),
                "status": FVGStatus.UNFILLED.value,
            }

    return None


def update_fvg_status(fvg: Dict[str, Any], current_price: float) -> str:
    """
    Update FVG fill status based on current price.

    Args:
        fvg: FVG dictionary.
        current_price: Current market price.

    Returns:
        Updated status string.
    """
    top = fvg["top"]
    bottom = fvg["bottom"]
    fvg_type = fvg["type"]

    if fvg_type == "bullish":
        # Price must move down into the gap to fill
        if current_price <= bottom:
            return FVGStatus.FILLED.value
        elif current_price < top:
            return FVGStatus.PARTIALLY_FILLED.value
    else:  # bearish
        # Price must move up into the gap to fill
        if current_price >= top:
            return FVGStatus.FILLED.value
        elif current_price > bottom:
            return FVGStatus.PARTIALLY_FILLED.value

    return FVGStatus.UNFILLED.value


class FVGEngine:
    """
    Detects Fair Value Gaps and tracks their fill status.

    FVGs are areas of imbalance where price moved too quickly,
    leaving gaps that often get retested.
    """

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("fvg_engine")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings
        self.min_gap = strategy_settings.fvg_min_gap  # 20 points

        # Active FVGs (48-hour registry)
        self._active_fvgs: Dict[Timeframe, List[Dict[str, Any]]] = {}
        self._history_hours = strategy_settings.fvg_history_hours

    async def analyze(self, candles: List[Candle], timeframe: Timeframe) -> FVGResult:
        """
        Analyze for Fair Value Gaps.

        Args:
            candles: List of candles (newest first).
            timeframe: Timeframe being analyzed.

        Returns:
            FVGResult with active FVGs and retest opportunities.
        """
        if len(candles) < 3:
            return FVGResult(active_fvgs=[], retest_opportunity=None)

        # Detect new FVGs
        new_fvgs = self._detect_fvgs(candles)

        # Update registry
        if timeframe not in self._active_fvgs:
            self._active_fvgs[timeframe] = []

        for fvg in new_fvgs:
            fvg["timeframe"] = timeframe.value
            self._active_fvgs[timeframe].append(fvg)

        # Update existing FVG statuses
        current_price = candles[0].close
        self._update_fvg_statuses(timeframe, current_price)

        # Clean old FVGs
        self._clean_old_fvgs(timeframe)

        # Find retest opportunity
        retest = self._find_retest_opportunity(timeframe, current_price)

        # Persist
        await self._persist_fvgs()

        active = self._active_fvgs.get(timeframe, [])
        return FVGResult(active_fvgs=active, retest_opportunity=retest)

    def _detect_fvgs(self, candles: List[Candle]) -> List[Dict[str, Any]]:
        """Detect FVGs in recent candles."""
        fvgs = []

        # Candles are newest first, need to look at consecutive triplets
        for i in range(len(candles) - 2):
            candle3 = candles[i]      # Newest
            candle2 = candles[i + 1]  # Middle
            candle1 = candles[i + 2]  # Oldest

            fvg = detect_fvg(candle1, candle2, candle3, self.min_gap)
            if fvg:
                fvgs.append(fvg)

        return fvgs

    def _update_fvg_statuses(self, timeframe: Timeframe, current_price: float):
        """Update status of all active FVGs."""
        if timeframe not in self._active_fvgs:
            return

        for fvg in self._active_fvgs[timeframe]:
            new_status = update_fvg_status(fvg, current_price)
            fvg["status"] = new_status

    def _clean_old_fvgs(self, timeframe: Timeframe):
        """Remove FVGs older than history limit or fully filled."""
        if timeframe not in self._active_fvgs:
            return

        from datetime import timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._history_hours)

        self._active_fvgs[timeframe] = [
            fvg for fvg in self._active_fvgs[timeframe]
            if (datetime.fromisoformat(fvg["timestamp"]) > cutoff and
                fvg["status"] != FVGStatus.FILLED.value)
        ]

    def _find_retest_opportunity(
        self,
        timeframe: Timeframe,
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """Find unfilled FVG near current price for potential retest."""
        if timeframe not in self._active_fvgs:
            return None

        for fvg in self._active_fvgs[timeframe]:
            if fvg["status"] == FVGStatus.UNFILLED.value:
                top = fvg["top"]
                bottom = fvg["bottom"]

                # Check if price is approaching the FVG
                distance_to_top = abs(current_price - top)
                distance_to_bottom = abs(current_price - bottom)

                if min(distance_to_top, distance_to_bottom) < 50:  # Within 50 points
                    return fvg

        return None

    async def _persist_fvgs(self):
        """Persist FVGs to Redis."""
        try:
            redis_client = await self.redis_mgr.get_redis()
            await redis_client.set("fvg:active", json.dumps(
                {tf.value: fvgs for tf, fvgs in self._active_fvgs.items()}
            ))
        except Exception as e:
            self.logger.error(f"Failed to persist FVGs: {e}")

    def get_confluence_contribution(self, result: FVGResult) -> Dict[str, float]:
        """Calculate confluence score contribution."""
        scores = {}

        if result.retest_opportunity:
            fvg_type = result.retest_opportunity["type"]
            if fvg_type == "bullish":
                scores["bullish_fvg_retest"] = 10.0
            else:
                scores["bearish_fvg_retest"] = 10.0

        # Count active unfilled FVGs
        unfilled = [f for f in result.active_fvgs if f["status"] == "unfilled"]
        if len(unfilled) >= 2:
            scores["multiple_fvgs"] = 5.0

        return scores


# Global instance
fvg_engine = FVGEngine()
