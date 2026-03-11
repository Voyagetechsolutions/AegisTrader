"""
Property-based tests for the Signal Generator.

Tests Properties 15 and 16 from the design document:
- Property 15: Signal Grade Classification
- Property 16: Session-Based Signal Filtering
"""

import pytest
import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, Any
import pytz

from hypothesis import given, strategies as st, settings

from backend.strategy.models import (
    Candle, Timeframe, Direction, SetupType, SignalGrade,
    BiasDirection, BiasResult, LevelResult, LiquidityResult,
    FVGResult, DisplacementResult, StructureResult, AnalysisResult,
)
from backend.strategy.signal_generator import (
    SignalGenerator,
    SessionManager,
    classify_signal_grade,
    determine_setup_type,
    calculate_trade_levels,
)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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


def create_analysis_result(
    bias_direction: BiasDirection = BiasDirection.BULLISH,
    ema_distance: float = 50.0,
    distance_to_250: float = 20.0,
    has_sweep: bool = True,
    has_fvg: bool = True,
    has_displacement: bool = True,
    has_structure_break: bool = True,
    break_type: str = "bos",
) -> AnalysisResult:
    """Helper to create test analysis results."""
    return AnalysisResult(
        timestamp=datetime.now(),
        timeframe=Timeframe.M15,
        bias=BiasResult(
            direction=bias_direction,
            ema_distance=ema_distance,
            structure_shift="bullish_shift" if bias_direction == BiasDirection.BULLISH else None,
        ),
        levels=LevelResult(
            nearest_250=38000.0,
            nearest_125=38000.0,
            distance_to_250=distance_to_250,
            distance_to_125=10.0,
        ),
        liquidity=LiquidityResult(
            recent_sweeps=[{"type": "buy_side"}] if has_sweep else [],
            sweep_type="buy_side" if has_sweep else None,
            time_since_sweep=15.0 if has_sweep else None,
        ),
        fvg=FVGResult(
            active_fvgs=[{"type": "bullish"}] if has_fvg else [],
            retest_opportunity={"type": "bullish"} if has_fvg else None,
        ),
        displacement=DisplacementResult(
            recent_displacement={"strength": 80} if has_displacement else None,
            direction=Direction.LONG if has_displacement else None,
            strength=80.0 if has_displacement else 0.0,
        ),
        structure=StructureResult(
            recent_breaks=[{"type": break_type}] if has_structure_break else [],
            current_trend=Direction.LONG,
            break_type=break_type if has_structure_break else None,
        ),
        confluence_score=0.0,
    )


class TestPropertySignalGradeClassification:
    """
    Property 15: Signal Grade Classification

    For any confluence score, the signal grade should be classified as:
    - A+ for scores >= 80
    - A for scores 70-79
    - B for scores 60-69
    - C for scores < 60

    Validates: Requirements 9.3
    """

    @given(st.floats(min_value=80, max_value=100, allow_nan=False))
    @settings(max_examples=50)
    def test_a_plus_grade_for_high_scores(self, score: float):
        """Feature: python-strategy-engine, Property 15: Signal Grade Classification

        Scores >= 80 should receive A+ grade.
        """
        grade = classify_signal_grade(score)
        assert grade == SignalGrade.A_PLUS

    @given(st.floats(min_value=70, max_value=79.99, allow_nan=False))
    @settings(max_examples=50)
    def test_a_grade_for_medium_scores(self, score: float):
        """Feature: python-strategy-engine, Property 15: Signal Grade Classification

        Scores 70-79 should receive A grade.
        """
        grade = classify_signal_grade(score)
        assert grade == SignalGrade.A

    @given(st.floats(min_value=60, max_value=69.99, allow_nan=False))
    @settings(max_examples=50)
    def test_b_grade_for_medium_low_scores(self, score: float):
        """Feature: python-strategy-engine, Property 15: Signal Grade Classification

        Scores 60-69 should receive B grade.
        """
        grade = classify_signal_grade(score)
        assert grade == SignalGrade.B

    @given(st.floats(min_value=0, max_value=59.99, allow_nan=False))
    @settings(max_examples=50)
    def test_c_grade_for_low_scores(self, score: float):
        """Feature: python-strategy-engine, Property 15: Signal Grade Classification

        Scores < 60 should receive C grade.
        """
        grade = classify_signal_grade(score)
        assert grade == SignalGrade.C

    def test_exact_boundaries(self):
        """Test exact grade boundary values."""
        # Exactly 80 -> A+
        assert classify_signal_grade(80.0) == SignalGrade.A_PLUS

        # Just below 80 -> A
        assert classify_signal_grade(79.99) == SignalGrade.A

        # Exactly 70 -> A
        assert classify_signal_grade(70.0) == SignalGrade.A

        # Just below 70 -> B
        assert classify_signal_grade(69.99) == SignalGrade.B

        # Exactly 60 -> B
        assert classify_signal_grade(60.0) == SignalGrade.B

        # Just below 60 -> C
        assert classify_signal_grade(59.99) == SignalGrade.C

        # Zero -> C
        assert classify_signal_grade(0.0) == SignalGrade.C

        # Max (100) -> A+
        assert classify_signal_grade(100.0) == SignalGrade.A_PLUS


class TestPropertySessionBasedFiltering:
    """
    Property 16: Session-Based Signal Filtering

    For any time outside the active trading sessions, signal generation
    should be suppressed unless override mode is enabled.

    Trading sessions (SAST):
    - London: 10:00-13:00
    - NY: 15:30-17:30
    - Power Hour: 20:00-22:00

    Validates: Requirements 9.5, 10.2
    """

    def test_london_session_active(self):
        """Signal should be allowed during London session."""
        manager = SessionManager(timezone="Africa/Johannesburg")
        tz = pytz.timezone("Africa/Johannesburg")

        # 11:00 SAST - within London session
        test_time = tz.localize(datetime(2026, 3, 10, 11, 0, 0))

        assert manager.is_within_session(test_time) is True
        assert manager.get_active_session(test_time) == "london"

    def test_ny_session_active(self):
        """Signal should be allowed during NY session."""
        manager = SessionManager(timezone="Africa/Johannesburg")
        tz = pytz.timezone("Africa/Johannesburg")

        # 16:00 SAST - within NY session
        test_time = tz.localize(datetime(2026, 3, 10, 16, 0, 0))

        assert manager.is_within_session(test_time) is True
        assert manager.get_active_session(test_time) == "new_york"

    def test_power_hour_session_active(self):
        """Signal should be allowed during Power Hour."""
        manager = SessionManager(timezone="Africa/Johannesburg")
        tz = pytz.timezone("Africa/Johannesburg")

        # 21:00 SAST - within Power Hour
        test_time = tz.localize(datetime(2026, 3, 10, 21, 0, 0))

        assert manager.is_within_session(test_time) is True
        assert manager.get_active_session(test_time) == "power_hour"

    def test_outside_all_sessions(self):
        """Signal should be blocked outside all sessions."""
        manager = SessionManager(timezone="Africa/Johannesburg")
        tz = pytz.timezone("Africa/Johannesburg")

        # 8:00 SAST - before London
        test_time = tz.localize(datetime(2026, 3, 10, 8, 0, 0))
        assert manager.is_within_session(test_time) is False

        # 14:00 SAST - between London and NY
        test_time = tz.localize(datetime(2026, 3, 10, 14, 0, 0))
        assert manager.is_within_session(test_time) is False

        # 23:00 SAST - after Power Hour
        test_time = tz.localize(datetime(2026, 3, 10, 23, 0, 0))
        assert manager.is_within_session(test_time) is False

    def test_override_mode(self):
        """Override mode should allow signals outside sessions."""
        manager = SessionManager(timezone="Africa/Johannesburg")
        tz = pytz.timezone("Africa/Johannesburg")

        # 8:00 SAST - normally blocked
        test_time = tz.localize(datetime(2026, 3, 10, 8, 0, 0))

        # Without override
        assert manager.is_within_session(test_time) is False

        # With override
        manager.enable_override()
        assert manager.is_within_session(test_time) is True

        # Disable override
        manager.disable_override()
        assert manager.is_within_session(test_time) is False

    def test_session_boundaries(self):
        """Test exact session boundary times."""
        manager = SessionManager(timezone="Africa/Johannesburg")
        tz = pytz.timezone("Africa/Johannesburg")

        # London start (10:00)
        assert manager.is_within_session(
            tz.localize(datetime(2026, 3, 10, 10, 0, 0))
        ) is True

        # London end (13:00)
        assert manager.is_within_session(
            tz.localize(datetime(2026, 3, 10, 13, 0, 0))
        ) is True

        # Just after London (13:01)
        assert manager.is_within_session(
            tz.localize(datetime(2026, 3, 10, 13, 1, 0))
        ) is False


class TestSignalGeneratorIntegration:
    """Integration tests for SignalGenerator."""

    def test_high_confluence_generates_signal(self):
        """High confluence analysis should generate A+ signal."""
        mock_redis = MockRedisManager()
        generator = SignalGenerator(redis_mgr=mock_redis)
        generator.session_manager.enable_override()  # Allow outside sessions

        analysis = create_analysis_result(
            bias_direction=BiasDirection.BULLISH,
            ema_distance=50.0,
            distance_to_250=15.0,
            has_sweep=True,
            has_fvg=True,
            has_displacement=True,
            has_structure_break=True,
        )

        async def run_test():
            return await generator.evaluate_setup(analysis, 38020.0)

        signal = run_async(run_test())

        assert signal is not None
        assert signal.direction == Direction.LONG
        assert signal.confluence_score >= 60

    def test_low_confluence_no_signal(self):
        """Low confluence analysis should not generate signal."""
        mock_redis = MockRedisManager()
        generator = SignalGenerator(redis_mgr=mock_redis)
        generator.session_manager.enable_override()

        analysis = create_analysis_result(
            bias_direction=BiasDirection.NEUTRAL,
            ema_distance=5.0,
            distance_to_250=100.0,
            has_sweep=False,
            has_fvg=False,
            has_displacement=False,
            has_structure_break=False,
        )

        async def run_test():
            return await generator.evaluate_setup(analysis, 38020.0)

        signal = run_async(run_test())

        assert signal is None

    def test_bearish_signal_direction(self):
        """Bearish bias should generate SHORT signal."""
        mock_redis = MockRedisManager()
        generator = SignalGenerator(redis_mgr=mock_redis)
        generator.session_manager.enable_override()

        analysis = create_analysis_result(
            bias_direction=BiasDirection.BEARISH,
            ema_distance=-50.0,
            has_sweep=True,
            has_displacement=True,
            has_structure_break=True,
        )

        async def run_test():
            return await generator.evaluate_setup(analysis, 38020.0)

        signal = run_async(run_test())

        assert signal is not None
        assert signal.direction == Direction.SHORT

    def test_outside_session_no_signal(self):
        """Signal should not generate outside trading sessions."""
        mock_redis = MockRedisManager()
        generator = SignalGenerator(redis_mgr=mock_redis)
        # Don't enable override - use actual session check

        # Mock session manager to return False
        generator.session_manager._override_enabled = False

        analysis = create_analysis_result(
            bias_direction=BiasDirection.BULLISH,
            has_sweep=True,
            has_displacement=True,
        )

        # Manually set the session check to fail
        original_is_within = generator.session_manager.is_within_session

        def mock_is_within(now=None):
            return False

        generator.session_manager.is_within_session = mock_is_within

        async def run_test():
            return await generator.evaluate_setup(analysis, 38020.0)

        signal = run_async(run_test())

        assert signal is None

    def test_trade_levels_calculation_long(self):
        """Long trade levels should have SL below and TP above entry."""
        levels = calculate_trade_levels(38000.0, Direction.LONG, atr=50.0)

        assert levels["entry"] == 38000.0
        assert levels["stop_loss"] < levels["entry"]
        assert levels["take_profit"] > levels["entry"]

    def test_trade_levels_calculation_short(self):
        """Short trade levels should have SL above and TP below entry."""
        levels = calculate_trade_levels(38000.0, Direction.SHORT, atr=50.0)

        assert levels["entry"] == 38000.0
        assert levels["stop_loss"] > levels["entry"]
        assert levels["take_profit"] < levels["entry"]

    def test_setup_type_determination(self):
        """Setup type should be determined correctly."""
        # Continuation long: bullish bias, BOS
        setup = determine_setup_type(BiasDirection.BULLISH, "bullish_bos", False)
        assert setup == SetupType.CONTINUATION_LONG

        # Continuation short: bearish bias, BOS
        setup = determine_setup_type(BiasDirection.BEARISH, "bearish_bos", False)
        assert setup == SetupType.CONTINUATION_SHORT

        # Swing long: bullish with CHoCH
        setup = determine_setup_type(BiasDirection.BULLISH, "bullish_choch", True)
        assert setup == SetupType.SWING_LONG

        # Swing short: bearish with CHoCH
        setup = determine_setup_type(BiasDirection.BEARISH, "bearish_choch", True)
        assert setup == SetupType.SWING_SHORT

    def test_confluence_score_breakdown(self):
        """Confluence score should have proper breakdown."""
        mock_redis = MockRedisManager()
        generator = SignalGenerator(redis_mgr=mock_redis)

        analysis = create_analysis_result(
            bias_direction=BiasDirection.BULLISH,
            distance_to_250=15.0,
            has_sweep=True,
            has_fvg=True,
            has_displacement=True,
            has_structure_break=True,
        )

        score, breakdown = generator._calculate_confluence_score(analysis)

        assert "bias" in breakdown
        assert "levels" in breakdown
        assert "liquidity" in breakdown
        assert "fvg" in breakdown
        assert "displacement" in breakdown
        assert "structure" in breakdown
        assert "total" in breakdown

        # Total should match sum of components
        assert score == breakdown["total"]
        assert score <= 100  # Capped at 100

    def test_signal_storage(self):
        """Signals should be stored and retrievable."""
        mock_redis = MockRedisManager()
        generator = SignalGenerator(redis_mgr=mock_redis)
        generator.session_manager.enable_override()

        analysis = create_analysis_result(
            bias_direction=BiasDirection.BULLISH,
            has_sweep=True,
            has_displacement=True,
            has_structure_break=True,
        )

        async def run_test():
            await generator.evaluate_setup(analysis, 38020.0)
            return await generator.get_recent_signals(count=5)

        signals = run_async(run_test())

        assert len(signals) >= 1
