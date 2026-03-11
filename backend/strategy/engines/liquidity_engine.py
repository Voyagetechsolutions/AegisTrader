"""
Liquidity Sweep Detection Engine for the Python Strategy Engine.

Detects buy-side and sell-side liquidity sweeps based on wick extensions
beyond previous swing highs/lows.
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Candle, Timeframe, LiquidityResult


class LiquidityEngine:
    """
    Detects liquidity sweeps in market structure.

    A liquidity sweep occurs when price wicks beyond a previous swing
    high/low by at least the threshold (10 points) and then reverses.
    """

    SWEEP_THRESHOLD = 10  # Minimum wick extension in points
    REVERSAL_CANDLES = 3  # Number of candles to confirm reversal

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("liquidity_engine")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings

        # 24-hour sweep history
        self._sweep_history: List[Dict[str, Any]] = []
        self._history_hours = strategy_settings.liquidity_history_hours

    async def analyze(self, candles: List[Candle], timeframe: Timeframe) -> LiquidityResult:
        """
        Analyze for liquidity sweeps.

        Args:
            candles: List of candles (newest first).
            timeframe: Timeframe being analyzed.

        Returns:
            LiquidityResult with recent sweeps.
        """
        if len(candles) < 10:
            return LiquidityResult(recent_sweeps=[], sweep_type=None, time_since_sweep=None)

        # Detect sweeps in recent candles
        sweeps = []

        # Look for buy-side (above resistance) and sell-side (below support) sweeps
        for i in range(min(20, len(candles) - 5)):
            sweep = self._detect_sweep_at_index(candles, i)
            if sweep:
                sweeps.append(sweep)

        # Update history
        await self._update_sweep_history(sweeps, timeframe)

        # Get recent sweeps
        recent_sweeps = self._get_recent_sweeps()
        sweep_type = recent_sweeps[0]["type"] if recent_sweeps else None
        time_since = self._calculate_time_since_sweep(recent_sweeps)

        return LiquidityResult(
            recent_sweeps=recent_sweeps,
            sweep_type=sweep_type,
            time_since_sweep=time_since,
        )

    def _detect_sweep_at_index(self, candles: List[Candle], index: int) -> Optional[Dict[str, Any]]:
        """Detect a liquidity sweep at a specific candle index."""
        if index + 5 >= len(candles):
            return None

        current = candles[index]
        lookback = candles[index + 1:index + 6]

        # Find swing high/low in lookback
        swing_high = max(c.high for c in lookback)
        swing_low = min(c.low for c in lookback)

        sweep = None

        # Buy-side sweep: wick extends above swing high then reverses
        if current.high > swing_high + self.SWEEP_THRESHOLD:
            wick_extension = current.high - swing_high
            # Check for reversal (close below high)
            if current.close < swing_high:
                sweep = {
                    "type": "buy_side",
                    "timestamp": current.timestamp.isoformat(),
                    "level": swing_high,
                    "extension": wick_extension,
                    "candle_high": current.high,
                }

        # Sell-side sweep: wick extends below swing low then reverses
        if current.low < swing_low - self.SWEEP_THRESHOLD:
            wick_extension = swing_low - current.low
            # Check for reversal (close above low)
            if current.close > swing_low:
                sweep = {
                    "type": "sell_side",
                    "timestamp": current.timestamp.isoformat(),
                    "level": swing_low,
                    "extension": wick_extension,
                    "candle_low": current.low,
                }

        return sweep

    async def _update_sweep_history(self, new_sweeps: List[Dict], timeframe: Timeframe):
        """Update sweep history and persist."""
        for sweep in new_sweeps:
            sweep["timeframe"] = timeframe.value
            self._sweep_history.append(sweep)

        # Clean old entries
        from datetime import timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._history_hours)
        self._sweep_history = [
            s for s in self._sweep_history
            if datetime.fromisoformat(s["timestamp"]) > cutoff
        ]

        # Persist to Redis
        try:
            redis_client = await self.redis_mgr.get_redis()
            await redis_client.set("liquidity:sweeps", json.dumps(self._sweep_history))
        except Exception as e:
            self.logger.error(f"Failed to persist sweep history: {e}")

    def _get_recent_sweeps(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get most recent sweeps."""
        return self._sweep_history[-count:] if self._sweep_history else []

    def _calculate_time_since_sweep(self, sweeps: List[Dict]) -> Optional[float]:
        """Calculate time since most recent sweep in minutes."""
        if not sweeps:
            return None
        latest = datetime.fromisoformat(sweeps[-1]["timestamp"])
        from datetime import timezone
        return (datetime.now(timezone.utc) - latest).total_seconds() / 60

    def get_confluence_contribution(self, result: LiquidityResult) -> Dict[str, float]:
        """Calculate confluence score contribution."""
        scores = {}

        if result.recent_sweeps:
            # Recent sweep adds to confluence
            if result.time_since_sweep and result.time_since_sweep < 60:  # Within last hour
                if result.sweep_type == "buy_side":
                    scores["recent_buyside_sweep"] = 12.0
                elif result.sweep_type == "sell_side":
                    scores["recent_sellside_sweep"] = 12.0

        return scores


# Global instance
liquidity_engine = LiquidityEngine()
