"""
Tests for the Risk Integration Layer.

Tests Property 17: Trade Authorization
- Signals are only authorized when session is active, grade is sufficient, and risk limits allow.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytz
from hypothesis import given, strategies as st, settings

from backend.strategy.models import Signal, Direction, SignalGrade, SetupType
from backend.strategy.risk_integration import RiskIntegration, TradeAuthorization


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
        self.lists = {}

    async def set(self, key, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def lpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)

    async def ltrim(self, key, start, end):
        if key in self.lists:
            self.lists[key] = self.lists[key][start:end + 1]


class MockRedisManager:
    def __init__(self):
        self._redis = MockRedis()

    async def get_redis(self):
        return self._redis


def create_test_signal(
    direction: Direction = Direction.LONG,
    grade: SignalGrade = SignalGrade.A,
    confluence_score: float = 80.0,
) -> Signal:
    """Create a test signal."""
    return Signal(
        timestamp=datetime.now(),
        direction=direction,
        setup_type=SetupType.CONTINUATION_LONG,
        entry=38000.0,
        stop_loss=37900.0,
        take_profit=38200.0,
        confluence_score=confluence_score,
        grade=grade,
        analysis_breakdown={},
    )


class TestPropertyTradeAuthorization:
    """
    Property 17: Trade Authorization

    Signals should only be authorized when:
    - Session is active (or override enabled)
    - Signal grade meets minimum requirement
    - Risk limits allow trading
    """

    def test_authorized_when_all_conditions_met(self):
        """Signal should be authorized when session active, grade sufficient, risk allows."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()  # Simulate active session

        signal = create_test_signal(grade=SignalGrade.A)

        async def run_test():
            return await integration.authorize_trade(signal)

        auth = run_async(run_test())

        assert auth.allowed is True
        assert auth.session_active is True
        assert auth.grade_sufficient is True
        assert auth.risk_allowed is True
        assert auth.reason is None

    def test_denied_when_outside_session(self):
        """Signal should be denied when outside trading session."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        # Don't enable override - simulate outside session

        # Mock session manager to return False
        integration.session_manager.is_within_session = lambda now=None: False
        integration.session_manager.get_active_session = lambda now=None: None

        signal = create_test_signal(grade=SignalGrade.A)

        async def run_test():
            return await integration.authorize_trade(signal)

        auth = run_async(run_test())

        assert auth.allowed is False
        assert auth.session_active is False
        assert "Outside trading session" in auth.reason

    def test_denied_when_grade_insufficient(self):
        """Signal should be denied when grade below minimum."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        # B grade is below minimum A
        signal = create_test_signal(grade=SignalGrade.B)

        async def run_test():
            return await integration.authorize_trade(signal)

        auth = run_async(run_test())

        assert auth.allowed is False
        assert auth.grade_sufficient is False
        assert "below minimum" in auth.reason

    def test_a_plus_grade_always_sufficient(self):
        """A+ grade should always meet minimum requirement."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        signal = create_test_signal(grade=SignalGrade.A_PLUS)

        async def run_test():
            return await integration.authorize_trade(signal)

        auth = run_async(run_test())

        assert auth.allowed is True
        assert auth.grade_sufficient is True

    def test_session_override_allows_outside_hours(self):
        """Session override should allow trading outside normal sessions."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)

        tz = pytz.timezone("Africa/Johannesburg")
        # 8:00 SAST - normally outside sessions
        test_time = tz.localize(datetime(2026, 3, 10, 8, 0, 0))

        # Without override
        assert integration.session_manager.is_within_session(test_time) is False

        # Enable override
        integration.enable_session_override()
        assert integration.session_manager.is_within_session(test_time) is True

        # Disable override
        integration.disable_session_override()
        assert integration.session_manager.is_within_session(test_time) is False

    def test_minimum_grade_configurable(self):
        """Minimum auto-trade grade should be configurable."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        # Lower minimum to B
        integration.set_minimum_grade(SignalGrade.B)

        signal = create_test_signal(grade=SignalGrade.B)

        async def run_test():
            return await integration.authorize_trade(signal)

        auth = run_async(run_test())

        assert auth.allowed is True
        assert auth.grade_sufficient is True


class TestRiskIntegrationStatus:
    """Tests for status reporting."""

    def test_get_current_status_without_db(self):
        """Status should return session info without DB connection."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        async def run_test():
            return await integration.get_current_status()

        status = run_async(run_test())

        assert "session" in status
        assert "risk" in status
        assert "stats" in status
        assert status["session"]["active"] is True
        assert status["session"]["override_enabled"] is True

    def test_authorization_stats_tracking(self):
        """Authorization stats should track approvals and denials."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        # One approved
        signal_a = create_test_signal(grade=SignalGrade.A)
        # One denied (B grade)
        signal_b = create_test_signal(grade=SignalGrade.B)

        async def run_test():
            await integration.authorize_trade(signal_a)
            await integration.authorize_trade(signal_b)
            return integration._auth_stats

        stats = run_async(run_test())

        assert stats["approved"] == 1
        assert stats["denied_grade"] == 1


class TestGradeOrdering:
    """Test grade comparison logic."""

    @given(st.sampled_from([SignalGrade.A_PLUS, SignalGrade.A]))
    @settings(max_examples=10)
    def test_a_and_above_meet_minimum_a(self, grade: SignalGrade):
        """A and A+ grades should meet minimum A requirement."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.MIN_AUTO_GRADE = SignalGrade.A

        assert integration._check_grade_sufficient(grade) is True

    def test_b_does_not_meet_minimum_a(self):
        """B grade should not meet minimum A requirement."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.MIN_AUTO_GRADE = SignalGrade.A

        assert integration._check_grade_sufficient(SignalGrade.B) is False

    def test_all_grades_meet_minimum_b(self):
        """All grades should meet minimum B requirement."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.MIN_AUTO_GRADE = SignalGrade.B

        assert integration._check_grade_sufficient(SignalGrade.A_PLUS) is True
        assert integration._check_grade_sufficient(SignalGrade.A) is True
        assert integration._check_grade_sufficient(SignalGrade.B) is True


class TestAuthorizationLogging:
    """Test authorization logging."""

    def test_authorization_logged_to_redis(self):
        """Authorization decisions should be logged to Redis."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        signal = create_test_signal(grade=SignalGrade.A)

        async def run_test():
            await integration.authorize_trade(signal)
            return mock_redis._redis.lists.get("risk:auth_log", [])

        log = run_async(run_test())

        assert len(log) == 1

    def test_stats_persisted_to_redis(self):
        """Authorization stats should be persisted to Redis."""
        mock_redis = MockRedisManager()
        integration = RiskIntegration(redis_mgr=mock_redis)
        integration.session_manager.enable_override()

        signal = create_test_signal(grade=SignalGrade.A)

        async def run_test():
            await integration.authorize_trade(signal)
            return mock_redis._redis.data.get("risk:auth_stats")

        stats_json = run_async(run_test())

        assert stats_json is not None
        assert "approved" in stats_json
