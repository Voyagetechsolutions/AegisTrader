"""
session_filter.py
Checks whether the current SAST time falls within an active trading session.
Sessions are configurable per user; defaults match the PRD.
"""

from datetime import datetime, time
from typing import Optional
import pytz

SAST = pytz.timezone("Africa/Johannesburg")

DEFAULT_SESSIONS: dict[str, dict[str, str]] = {
    "london":     {"start": "10:00", "end": "13:00"},
    "new_york":   {"start": "15:30", "end": "17:30"},
    "power_hour": {"start": "20:00", "end": "22:00"},
}


def _parse_time(t: str) -> time:
    """Parse 'HH:MM' into a time object."""
    h, m = t.split(":")
    return time(int(h), int(m))


def get_active_session(
    sessions: Optional[dict[str, dict[str, str]]] = None,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """
    Return the name of the currently active session, or None if outside all windows.

    Args:
        sessions: dict of session definitions. Falls back to DEFAULT_SESSIONS.
        now: datetime to check (defaults to current SAST time).

    Returns:
        Session name string (e.g. "london", "new_york", "power_hour") or None.
    """
    if sessions is None:
        sessions = DEFAULT_SESSIONS

    if now is None:
        now = datetime.now(SAST)
    elif now.tzinfo is None:
        now = SAST.localize(now)
    else:
        now = now.astimezone(SAST)

    current_time = now.time().replace(second=0, microsecond=0)

    for name, window in sessions.items():
        start = _parse_time(window["start"])
        end = _parse_time(window["end"])
        if start <= current_time <= end:
            return name

    return None


def is_within_session(
    sessions: Optional[dict[str, dict[str, str]]] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Return True if any session is currently active."""
    return get_active_session(sessions=sessions, now=now) is not None
