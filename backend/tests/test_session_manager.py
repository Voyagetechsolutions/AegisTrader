"""
Tests for SessionManager.

Validates:
- Session timing detection
- Session override functionality
- Signal window enforcement
- Session trade limit tracking
"""

import pytest
from datetime import datetime
import pytz

from backend.strategy.session_manager import SessionManager
from backend.strategy.dual_engine_models import SessionType, EngineType


class TestSessionManager:
    """Test SessionManager functionality."""

    def test_session_initialization(self):
        """Test SessionManager initializes with correct sessions."""
        sm = SessionManager(timezone="Africa/Johannesburg")
        
        assert "london" in sm.sessions
        assert "new_york" in sm.sessions
        assert "power_hour" in sm.sessions
        assert not sm._override_enabled
        
        # Verify signal window
        assert sm.signal_window_start.hour == 10
        assert sm.signal_window_start.minute == 0
        assert sm.signal_window_end.hour == 22
        assert sm.signal_window_end.minute == 0

    def test_london_session_detection(self):
        """Test London session (10:00-13:00 SAST) is detected."""
        sm = SessionManager()
        test_time = datetime(2024, 1, 15, 11, 30, tzinfo=pytz.timezone("Africa/Johannesburg"))
        assert sm.is_within_session(test_time)
        assert sm.get_active_session(test_time) == SessionType.LONDON

    def test_outside_all_sessions(self):
        """Test time outside all sessions returns None."""
        sm = SessionManager()
        test_time = datetime(2024, 1, 15, 3, 0, tzinfo=pytz.timezone("Africa/Johannesburg"))
        assert not sm.is_within_session(test_time)
        assert sm.get_active_session(test_time) is None

    def test_session_override(self):
        """Test session override allows trading outside sessions."""
        sm = SessionManager()
        test_time = datetime(2024, 1, 15, 3, 0, tzinfo=pytz.timezone("Africa/Johannesburg"))
        
        sm.enable_override()
        assert sm.is_within_session(test_time)
        
        sm.disable_override()
        assert not sm.is_within_session(test_time)

    def test_signal_window_enforcement(self):
        """Test signal window enforcement (10:00-22:00 SAST)."""
        sm = SessionManager()
        
        # Within signal window
        test_time_within = datetime(2024, 1, 15, 15, 0, tzinfo=pytz.timezone("Africa/Johannesburg"))
        assert sm.is_signal_permitted(test_time_within, EngineType.CORE_STRATEGY)
        
        # Outside signal window (before)
        test_time_before = datetime(2024, 1, 15, 9, 0, tzinfo=pytz.timezone("Africa/Johannesburg"))
        assert not sm.is_signal_permitted(test_time_before, EngineType.CORE_STRATEGY)
        
        # Outside signal window (after)
        test_time_after = datetime(2024, 1, 15, 23, 0, tzinfo=pytz.timezone("Africa/Johannesburg"))
        assert not sm.is_signal_permitted(test_time_after, EngineType.QUICK_SCALP)

    def test_session_trade_limit_tracking(self):
        """Test session trade limit tracking."""
        sm = SessionManager()
        
        # Check initial state
        assert sm.get_session_trade_count(SessionType.LONDON) == 0
        assert sm.check_session_limit(SessionType.LONDON)
        
        # Increment and check
        for i in range(5):
            sm.increment_session_trade_count(SessionType.LONDON)
            assert sm.get_session_trade_count(SessionType.LONDON) == i + 1
        
        # Should hit limit at 5
        assert not sm.check_session_limit(SessionType.LONDON)
        
        # Reset and verify
        sm.reset_session_trade_counts()
        assert sm.get_session_trade_count(SessionType.LONDON) == 0
        assert sm.check_session_limit(SessionType.LONDON)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
