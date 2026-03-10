"""Unit tests for the session filter module."""
import pytest
from datetime import datetime
import pytz
from backend.modules.session_filter import get_active_session, is_within_session

SAST = pytz.timezone("Africa/Johannesburg")


def sast(h, m):
    return SAST.localize(datetime(2025, 1, 6, h, m))  # Monday


def test_london_session_start():
    assert get_active_session(now=sast(10, 0)) == "london"


def test_london_session_mid():
    assert get_active_session(now=sast(11, 30)) == "london"


def test_london_session_end():
    assert get_active_session(now=sast(13, 0)) == "london"


def test_between_london_and_ny():
    assert get_active_session(now=sast(14, 0)) is None


def test_new_york_session():
    assert get_active_session(now=sast(16, 0)) == "new_york"


def test_new_york_session_end():
    assert get_active_session(now=sast(17, 30)) == "new_york"


def test_after_ny_before_power():
    assert get_active_session(now=sast(18, 0)) is None


def test_power_hour():
    assert get_active_session(now=sast(21, 0)) == "power_hour"


def test_outside_all_sessions():
    assert get_active_session(now=sast(8, 0)) is None


def test_midnight():
    assert get_active_session(now=sast(0, 0)) is None


def test_is_within_session_true():
    assert is_within_session(now=sast(11, 0)) is True


def test_is_within_session_false():
    assert is_within_session(now=sast(9, 0)) is False


def test_custom_sessions():
    custom = {"custom": {"start": "08:00", "end": "09:00"}}
    assert get_active_session(sessions=custom, now=sast(8, 30)) == "custom"
    assert get_active_session(sessions=custom, now=sast(10, 0)) is None
