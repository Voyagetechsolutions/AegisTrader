"""
Property-based tests for Analysis Engines (Liquidity, FVG, Displacement, Structure).

Tests Properties 10-14 from the design document.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List

from hypothesis import given, strategies as st, settings

from backend.strategy.models import Candle, Timeframe, Direction
from backend.strategy.engines.liquidity_engine import LiquidityEngine
from backend.strategy.engines.fvg_engine import (
    FVGEngine, detect_fvg, update_fvg_status, FVGStatus
)
from backend.strategy.engines.displacement_engine import (
    DisplacementEngine, is_displacement_candle, calculate_displacement_strength
)
from backend.strategy.engines.structure_engine import (
    StructureEngine, find_swing_points, detect_structure_break, BreakType
)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def create_candle(
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: int = 100
) -> Candle:
    """Create a candle with specified OHLC."""
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timeframe=Timeframe.M5,
    )


class MockRedis:
    def __init__(self):
        self.data = {}
    async def set(self, key, value):
        self.data[key] = value
    async def get(self, key):
        return self.data.get(key)


class MockRedisManager:
    def __init__(self):
        self._redis = MockRedis()
    async def get_redis(self):
        return self._redis


# Property 10: Liquidity Sweep Detection
class TestPropertyLiquiditySweep:
    """
    Property 10: Liquidity Sweep Detection

    For any price wick that extends beyond a previous swing high/low
    by at least 10 points, the system should detect and classify it
    as buy-side or sell-side liquidity sweep.

    Validates: Requirements 5.1, 5.4
    """

    def test_buy_side_sweep_detection(self):
        """Wick above swing high should be detected as buy-side sweep."""
        base_time = datetime(2026, 3, 10, 10, 0)

        # Create candles with a clear swing high, then a sweep
        candles = [
            # Current candle sweeps above previous high
            create_candle(base_time, 38100, 38180, 38080, 38090),  # Wick to 38180
            # Previous candles with swing high at 38150
            create_candle(base_time - timedelta(minutes=5), 38140, 38150, 38120, 38145),
            create_candle(base_time - timedelta(minutes=10), 38130, 38145, 38110, 38140),
            create_candle(base_time - timedelta(minutes=15), 38120, 38140, 38100, 38130),
            create_candle(base_time - timedelta(minutes=20), 38100, 38130, 38090, 38120),
            create_candle(base_time - timedelta(minutes=25), 38090, 38120, 38080, 38100),
        ]

        engine = LiquidityEngine()
        sweep = engine._detect_sweep_at_index(candles, 0)

        assert sweep is not None
        assert sweep["type"] == "buy_side"

    def test_sell_side_sweep_detection(self):
        """Wick below swing low should be detected as sell-side sweep."""
        base_time = datetime(2026, 3, 10, 10, 0)

        candles = [
            # Current candle sweeps below previous low
            create_candle(base_time, 38100, 38110, 38020, 38090),  # Wick to 38020
            # Previous candles with swing low at 38050
            create_candle(base_time - timedelta(minutes=5), 38060, 38080, 38050, 38055),
            create_candle(base_time - timedelta(minutes=10), 38070, 38090, 38055, 38060),
            create_candle(base_time - timedelta(minutes=15), 38080, 38100, 38060, 38070),
            create_candle(base_time - timedelta(minutes=20), 38090, 38110, 38070, 38080),
            create_candle(base_time - timedelta(minutes=25), 38100, 38120, 38080, 38090),
        ]

        engine = LiquidityEngine()
        sweep = engine._detect_sweep_at_index(candles, 0)

        assert sweep is not None
        assert sweep["type"] == "sell_side"

    def test_no_sweep_within_threshold(self):
        """Small wicks should not be detected as sweeps."""
        base_time = datetime(2026, 3, 10, 10, 0)

        candles = [
            # Wick only extends 5 points (below 10 threshold)
            create_candle(base_time, 38100, 38155, 38095, 38140),
            create_candle(base_time - timedelta(minutes=5), 38140, 38150, 38120, 38145),
            create_candle(base_time - timedelta(minutes=10), 38130, 38145, 38110, 38140),
            create_candle(base_time - timedelta(minutes=15), 38120, 38140, 38100, 38130),
            create_candle(base_time - timedelta(minutes=20), 38100, 38130, 38090, 38120),
            create_candle(base_time - timedelta(minutes=25), 38090, 38120, 38080, 38100),
        ]

        engine = LiquidityEngine()
        sweep = engine._detect_sweep_at_index(candles, 0)

        assert sweep is None


# Property 11: FVG Detection and Classification
class TestPropertyFVGDetection:
    """
    Property 11: FVG Detection and Classification

    For any three consecutive candles where the gap between candle 1's high/low
    and candle 3's low/high exceeds 20 points with no overlapping wicks,
    the system should detect an FVG and classify it as bullish or bearish.

    Validates: Requirements 6.1, 6.2
    """

    def test_bullish_fvg_detection(self):
        """Gap up with no overlap should be detected as bullish FVG."""
        base_time = datetime(2026, 3, 10, 10, 0)

        candle1 = create_candle(base_time, 38000, 38050, 37980, 38030)  # High: 38050
        candle2 = create_candle(base_time + timedelta(minutes=5), 38060, 38100, 38050, 38090)
        candle3 = create_candle(base_time + timedelta(minutes=10), 38100, 38150, 38080, 38140)  # Low: 38080

        # Gap: 38080 - 38050 = 30 points (> 20)
        fvg = detect_fvg(candle1, candle2, candle3, min_gap=20)

        assert fvg is not None
        assert fvg["type"] == "bullish"
        assert fvg["size"] == 30

    def test_bearish_fvg_detection(self):
        """Gap down with no overlap should be detected as bearish FVG."""
        base_time = datetime(2026, 3, 10, 10, 0)

        candle1 = create_candle(base_time, 38100, 38120, 38080, 38090)  # Low: 38080
        candle2 = create_candle(base_time + timedelta(minutes=5), 38050, 38070, 38030, 38040)
        candle3 = create_candle(base_time + timedelta(minutes=10), 38020, 38050, 38000, 38030)  # High: 38050

        # Gap: 38080 - 38050 = 30 points (> 20)
        fvg = detect_fvg(candle1, candle2, candle3, min_gap=20)

        assert fvg is not None
        assert fvg["type"] == "bearish"
        assert fvg["size"] == 30

    def test_no_fvg_with_overlap(self):
        """Overlapping wicks should not produce FVG."""
        base_time = datetime(2026, 3, 10, 10, 0)

        candle1 = create_candle(base_time, 38000, 38050, 37980, 38030)
        candle2 = create_candle(base_time + timedelta(minutes=5), 38040, 38080, 38020, 38070)
        candle3 = create_candle(base_time + timedelta(minutes=10), 38060, 38100, 38040, 38090)  # Low overlaps with candle1 high

        fvg = detect_fvg(candle1, candle2, candle3, min_gap=20)

        assert fvg is None

    @given(st.floats(min_value=1, max_value=19, allow_nan=False))
    @settings(max_examples=20)
    def test_no_fvg_below_threshold(self, gap_size: float):
        """Gaps below threshold should not be detected."""
        base_time = datetime(2026, 3, 10, 10, 0)

        candle1 = create_candle(base_time, 38000, 38050, 37980, 38030)
        candle2 = create_candle(base_time + timedelta(minutes=5), 38060, 38080, 38050, 38070)
        candle3 = create_candle(base_time + timedelta(minutes=10), 38070, 38100, 38050 + gap_size, 38090)

        fvg = detect_fvg(candle1, candle2, candle3, min_gap=20)

        assert fvg is None


# Property 12: FVG Fill Status Tracking
class TestPropertyFVGFillStatus:
    """
    Property 12: FVG Fill Status Tracking

    For any detected FVG, when price action overlaps with the gap range,
    the fill status should update to "partially filled" or "filled".

    Validates: Requirements 6.3
    """

    def test_bullish_fvg_unfilled(self):
        """Price above FVG should keep status unfilled."""
        fvg = {"type": "bullish", "top": 38100, "bottom": 38050}

        status = update_fvg_status(fvg, 38120)  # Price above FVG

        assert status == FVGStatus.UNFILLED.value

    def test_bullish_fvg_partially_filled(self):
        """Price entering FVG should show partially filled."""
        fvg = {"type": "bullish", "top": 38100, "bottom": 38050}

        status = update_fvg_status(fvg, 38075)  # Price inside FVG

        assert status == FVGStatus.PARTIALLY_FILLED.value

    def test_bullish_fvg_filled(self):
        """Price below FVG bottom should show filled."""
        fvg = {"type": "bullish", "top": 38100, "bottom": 38050}

        status = update_fvg_status(fvg, 38040)  # Price below FVG

        assert status == FVGStatus.FILLED.value

    def test_bearish_fvg_unfilled(self):
        """Price below FVG should keep status unfilled."""
        fvg = {"type": "bearish", "top": 38100, "bottom": 38050}

        status = update_fvg_status(fvg, 38030)  # Price below FVG

        assert status == FVGStatus.UNFILLED.value

    def test_bearish_fvg_filled(self):
        """Price above FVG top should show filled."""
        fvg = {"type": "bearish", "top": 38100, "bottom": 38050}

        status = update_fvg_status(fvg, 38110)  # Price above FVG

        assert status == FVGStatus.FILLED.value


# Property 13: Displacement Candle Validation
class TestPropertyDisplacementCandle:
    """
    Property 13: Displacement Candle Validation

    For any single candle with movement exceeding 50 points, it should be
    classified as displacement only if the candle body represents more than
    80% of the total range (minimal wicks).

    Validates: Requirements 7.1, 7.3
    """

    @given(
        st.floats(min_value=55, max_value=200, allow_nan=False),
        st.floats(min_value=0.82, max_value=0.98, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_valid_displacement_detected(self, range_size: float, body_pct: float):
        """Large body candles should be detected as displacement."""
        # Construct candle where range = high - low = range_size
        # Body = close - open = range_size * body_pct
        body_size = range_size * body_pct
        wick_each = (range_size - body_size) / 2

        open_price = 38000.0
        close_price = open_price + body_size
        low_price = open_price - wick_each
        high_price = close_price + wick_each

        candle = create_candle(
            datetime.now(),
            open_price,
            high_price,
            low_price,
            close_price,
        )

        # Verify construction is correct
        actual_range = candle.high - candle.low
        actual_body = abs(candle.close - candle.open)
        actual_body_pct = actual_body / actual_range

        is_disp = is_displacement_candle(candle, min_points=50, min_body_pct=0.8)

        assert is_disp is True, f"Range={actual_range:.2f}, Body%={actual_body_pct:.2f}"

    @given(st.floats(min_value=10, max_value=49, allow_nan=False))
    @settings(max_examples=30)
    def test_small_range_not_displacement(self, range_size: float):
        """Small range candles should not be displacement."""
        candle = create_candle(
            datetime.now(),
            38000,
            38000 + range_size,
            38000,
            38000 + range_size * 0.9,  # Large body but small range
        )

        is_disp = is_displacement_candle(candle, min_points=50, min_body_pct=0.8)

        assert is_disp is False

    def test_large_wicks_not_displacement(self):
        """Large wicks (small body %) should not be displacement."""
        # 100 point range but only 50% body
        candle = create_candle(
            datetime.now(),
            38000,
            38100,   # High
            38000,   # Low
            38050,   # Close - 50% body
        )

        is_disp = is_displacement_candle(candle, min_points=50, min_body_pct=0.8)

        assert is_disp is False

    def test_displacement_strength_calculation(self):
        """Displacement strength should reflect body % and range."""
        # Strong displacement: 100 pt range, 90% body
        strong_candle = create_candle(datetime.now(), 38000, 38100, 37995, 38090)

        # Weak displacement: 60 pt range, 85% body
        weak_candle = create_candle(datetime.now(), 38000, 38060, 37996, 38050)

        strong_strength = calculate_displacement_strength(strong_candle)
        weak_strength = calculate_displacement_strength(weak_candle)

        assert strong_strength > weak_strength


# Property 14: Structure Break Classification
class TestPropertyStructureBreak:
    """
    Property 14: Structure Break Classification

    For any price movement that breaks previous swing highs/lows, the system
    should classify it as BOS (break of structure) when in trend direction
    or CHoCH (change of character) when counter-trend.

    Validates: Requirements 8.1, 8.2, 8.3
    """

    def test_bullish_bos_in_uptrend(self):
        """Breaking swing high in uptrend should be bullish BOS."""
        swing_highs = [38100]
        swing_lows = [37900]
        previous_trend = Direction.LONG

        break_info = detect_structure_break(
            current_high=38150,
            current_low=38050,
            recent_swing_highs=swing_highs,
            recent_swing_lows=swing_lows,
            previous_trend=previous_trend,
        )

        assert break_info is not None
        assert break_info["type"] == BreakType.BOS.value
        assert break_info["direction"] == "bullish_bos"

    def test_bullish_choch_in_downtrend(self):
        """Breaking swing high in downtrend should be bullish CHoCH."""
        swing_highs = [38100]
        swing_lows = [37900]
        previous_trend = Direction.SHORT

        break_info = detect_structure_break(
            current_high=38150,
            current_low=38050,
            recent_swing_highs=swing_highs,
            recent_swing_lows=swing_lows,
            previous_trend=previous_trend,
        )

        assert break_info is not None
        assert break_info["type"] == BreakType.CHOCH.value
        assert break_info["direction"] == "bullish_choch"

    def test_bearish_bos_in_downtrend(self):
        """Breaking swing low in downtrend should be bearish BOS."""
        swing_highs = [38100]
        swing_lows = [37900]
        previous_trend = Direction.SHORT

        break_info = detect_structure_break(
            current_high=37950,
            current_low=37850,  # Below swing low
            recent_swing_highs=swing_highs,
            recent_swing_lows=swing_lows,
            previous_trend=previous_trend,
        )

        assert break_info is not None
        assert break_info["type"] == BreakType.BOS.value
        assert break_info["direction"] == "bearish_bos"

    def test_bearish_choch_in_uptrend(self):
        """Breaking swing low in uptrend should be bearish CHoCH."""
        swing_highs = [38100]
        swing_lows = [37900]
        previous_trend = Direction.LONG

        break_info = detect_structure_break(
            current_high=37950,
            current_low=37850,  # Below swing low
            recent_swing_highs=swing_highs,
            recent_swing_lows=swing_lows,
            previous_trend=previous_trend,
        )

        assert break_info is not None
        assert break_info["type"] == BreakType.CHOCH.value
        assert break_info["direction"] == "bearish_choch"

    def test_no_break_within_range(self):
        """Price within swing range should not produce break."""
        swing_highs = [38100]
        swing_lows = [37900]
        previous_trend = Direction.LONG

        break_info = detect_structure_break(
            current_high=38050,  # Below swing high
            current_low=37950,   # Above swing low
            recent_swing_highs=swing_highs,
            recent_swing_lows=swing_lows,
            previous_trend=previous_trend,
        )

        assert break_info is None

    def test_find_swing_points(self):
        """Should correctly identify swing highs and lows."""
        base_time = datetime(2026, 3, 10, 10, 0)

        # Create candles with clear swing points
        candles = []
        # Pattern: up, up, peak, down, down, up, up, valley, up, up
        prices = [100, 110, 120, 110, 100, 90, 80, 70, 80, 90, 100, 110, 120]
        for i, price in enumerate(prices):
            candles.append(create_candle(
                base_time - timedelta(minutes=i * 5),
                price, price + 5, price - 5, price
            ))

        swing_highs, swing_lows = find_swing_points(candles, lookback=2)

        # Should find swing points
        assert len(swing_highs) > 0 or len(swing_lows) > 0
