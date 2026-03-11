"""
Session Manager for the Python Strategy Engine.

Manages trading session windows with timezone support and daylight saving time handling.
Provides session validation for signal filtering.

Requirements: 3.1-3.5, 9.1-9.7
"""

from datetime import datetime, time
from typing import Optional, Dict
import pytz

from backend.strategy.config import strategy_settings
from backend.strategy.logging_config import get_component_logger
from backend.strategy.dual_engine_models import EngineType, SessionType


class SessionManager:
    """
    Manages trading session windows with timezone support.
    
    Handles:
    - Signal window enforcement (10:00-22:00 SAST) - Requirements 3.1-3.5
    - London session (10:00-13:00 SAST) - Requirement 9.1
    - NY Open session (15:30-18:00 SAST) - Requirement 9.2
    - Power Hour session (20:00-22:00 SAST) - Requirement 9.3
    - Session trade limit tracking - Requirements 9.5-9.7
    - Session override for testing/manual control
    - Daylight saving time adjustments
    """

    def __init__(self, timezone: str = "Africa/Johannesburg"):
        self.logger = get_component_logger("session_manager")
        self.tz = pytz.timezone(timezone)
        self.settings = strategy_settings
        self._override_enabled = False

        # Signal window (10:00-22:00 SAST) - Requirements 3.2, 3.3
        self.signal_window_start = time(10, 0)
        self.signal_window_end = time(22, 0)

        # Parse session times from config
        self.sessions = {
            "london": self._parse_session(
                strategy_settings.london_start,
                strategy_settings.london_end
            ),
            "new_york": self._parse_session(
                strategy_settings.ny_start,
                strategy_settings.ny_end
            ),
            "power_hour": self._parse_session(
                strategy_settings.power_start,
                strategy_settings.power_end
            ),
        }

        # Session trade counters - Requirements 9.5-9.7
        self._session_trade_counts: Dict[SessionType, int] = {
            SessionType.LONDON: 0,
            SessionType.NY_OPEN: 0,
            SessionType.POWER_HOUR: 0,
        }

        # Session trade limits - Requirements 9.5-9.7
        self._session_trade_limits: Dict[SessionType, int] = {
            SessionType.LONDON: 5,      # Requirement 9.5
            SessionType.NY_OPEN: 5,     # Requirement 9.6
            SessionType.POWER_HOUR: 3,  # Requirement 9.7
        }

        self.logger.info(f"SessionManager initialized with timezone: {timezone}")
        self.logger.debug(f"Sessions configured: {list(self.sessions.keys())}")
        self.logger.debug(f"Signal window: {self.signal_window_start} - {self.signal_window_end}")

    def _parse_session(self, start: str, end: str) -> Dict[str, time]:
        """Parse session time strings to time objects."""
        start_parts = start.split(":")
        end_parts = end.split(":")
        return {
            "start": time(int(start_parts[0]), int(start_parts[1])),
            "end": time(int(end_parts[0]), int(end_parts[1])),
        }

    def is_within_session(self, now: Optional[datetime] = None) -> bool:
        """
        Check if current time is within any active trading session.
        
        Args:
            now: Optional datetime to check (defaults to current time).
            
        Returns:
            True if within any session or override is enabled.
        """
        if self._override_enabled:
            return True

        if now is None:
            now = datetime.now(self.tz)
        elif now.tzinfo is None:
            now = self.tz.localize(now)
        else:
            now = now.astimezone(self.tz)

        current_time = now.time()

        for session_name, session_times in self.sessions.items():
            if session_times["start"] <= current_time <= session_times["end"]:
                return True

        return False

    def is_signal_permitted(
        self,
        current_time: Optional[datetime] = None,
        engine: Optional[EngineType] = None
    ) -> bool:
        """
        Check if signal generation is permitted within the signal window (10:00-22:00 SAST).
        
        Requirements 3.2, 3.3, 3.4, 3.5:
        - Permit signal generation between 10:00 and 22:00 SAST
        - Block signal generation outside this window
        - Apply to both Core Strategy Engine and Quick Scalp Engine
        
        Args:
            current_time: Optional datetime to check (defaults to current time in SAST).
            engine: Optional engine type (for logging purposes).
            
        Returns:
            True if within signal window (10:00-22:00 SAST).
        """
        if current_time is None:
            current_time = datetime.now(self.tz)
        elif current_time.tzinfo is None:
            current_time = self.tz.localize(current_time)
        else:
            current_time = current_time.astimezone(self.tz)

        time_only = current_time.time()
        
        # Check if within signal window (10:00-22:00 SAST)
        permitted = self.signal_window_start <= time_only <= self.signal_window_end
        
        if not permitted:
            self.logger.debug(
                f"Signal generation blocked for {engine.value if engine else 'engine'}: "
                f"time {time_only} outside signal window "
                f"({self.signal_window_start}-{self.signal_window_end})"
            )
        
        return permitted

    def get_active_session(self, now: Optional[datetime] = None) -> Optional[SessionType]:
        """
        Get the currently active session type.
        
        Requirements 9.1-9.4:
        - London: 10:00-13:00 SAST
        - NY Open: 15:30-18:00 SAST
        - Power Hour: 20:00-22:00 SAST
        
        Args:
            now: Optional datetime to check (defaults to current time).
            
        Returns:
            SessionType enum (LONDON, NY_OPEN, POWER_HOUR) or None.
        """
        if now is None:
            now = datetime.now(self.tz)
        elif now.tzinfo is None:
            now = self.tz.localize(now)
        else:
            now = now.astimezone(self.tz)

        current_time = now.time()

        # Map internal session names to SessionType enum
        session_map = {
            "london": SessionType.LONDON,
            "new_york": SessionType.NY_OPEN,
            "power_hour": SessionType.POWER_HOUR,
        }

        for name, session_times in self.sessions.items():
            if session_times["start"] <= current_time <= session_times["end"]:
                return session_map.get(name)

        return None

    def get_session_status(self, now: Optional[datetime] = None) -> Dict[str, any]:
        """
        Get detailed session status information.
        
        Returns:
            Dict with active session, override status, and session windows.
        """
        active = self.get_active_session(now)
        within = self.is_within_session(now)

        return {
            "active_session": active.value if active else None,
            "within_session": within,
            "override_enabled": self._override_enabled,
            "sessions": {
                name: {
                    "start": times["start"].strftime("%H:%M"),
                    "end": times["end"].strftime("%H:%M"),
                }
                for name, times in self.sessions.items()
            },
            "timezone": str(self.tz),
            "session_trade_counts": {
                session.value: count 
                for session, count in self._session_trade_counts.items()
            },
            "session_trade_limits": {
                session.value: limit 
                for session, limit in self._session_trade_limits.items()
            },
        }

    def check_session_limit(
        self,
        session: SessionType,
        current_count: Optional[int] = None
    ) -> bool:
        """
        Check if session trade limit has been reached.
        
        Requirements 9.5-9.7:
        - London: max 5 trades
        - NY Open: max 5 trades
        - Power Hour: max 3 trades
        
        Args:
            session: The session type to check.
            current_count: Optional override for current count (uses internal counter if None).
            
        Returns:
            True if limit not exceeded, False if limit reached.
        """
        if current_count is None:
            current_count = self._session_trade_counts.get(session, 0)
        
        limit = self._session_trade_limits.get(session, 0)
        
        if current_count >= limit:
            self.logger.warning(
                f"Session trade limit reached for {session.value}: "
                f"{current_count}/{limit} trades"
            )
            return False
        
        return True

    def increment_session_trade_count(self, session: SessionType) -> None:
        """
        Increment the trade count for a specific session.
        
        Args:
            session: The session type to increment.
        """
        if session in self._session_trade_counts:
            self._session_trade_counts[session] += 1
            self.logger.debug(
                f"Session trade count incremented for {session.value}: "
                f"{self._session_trade_counts[session]}/{self._session_trade_limits[session]}"
            )

    def reset_session_trade_counts(self) -> None:
        """
        Reset all session trade counts to zero.
        
        Should be called at the start of each trading day.
        """
        self._session_trade_counts = {
            SessionType.LONDON: 0,
            SessionType.NY_OPEN: 0,
            SessionType.POWER_HOUR: 0,
        }
        self.logger.info("Session trade counts reset to zero")

    def get_session_trade_count(self, session: SessionType) -> int:
        """
        Get the current trade count for a specific session.
        
        Args:
            session: The session type to query.
            
        Returns:
            Current trade count for the session.
        """
        return self._session_trade_counts.get(session, 0)

    def enable_override(self):
        """Enable session override (allow signals outside sessions)."""
        self._override_enabled = True
        self.logger.warning("Session override ENABLED - signals allowed outside sessions")

    def disable_override(self):
        """Disable session override."""
        self._override_enabled = False
        self.logger.info("Session override DISABLED - normal session filtering active")

    def is_override_enabled(self) -> bool:
        """Check if session override is currently enabled."""
        return self._override_enabled


# Global instance
session_manager = SessionManager()
