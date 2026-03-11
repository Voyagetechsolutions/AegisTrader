"""
News Filter - Blocks trading during high-impact economic events.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from dataclasses import dataclass
from enum import Enum


class ImpactLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NewsEvent:
    time: datetime
    currency: str
    event: str
    impact: ImpactLevel
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class NewsFilter:
    """Filters trades during high-impact news events."""
    
    # High-impact events that require extended blackout
    CRITICAL_EVENTS = ["CPI", "NFP", "FOMC", "Interest Rate", "GDP"]
    
    def __init__(self):
        self.events: List[NewsEvent] = []
        self.last_fetch = None
        
    def is_trading_allowed(self, timestamp: datetime) -> tuple[bool, Optional[str]]:
        """Check if trading is allowed at given time."""
        import pytz
        
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = pytz.UTC.localize(timestamp)
        
        # Refresh events if needed
        if not self.events or not self.last_fetch or (datetime.now() - self.last_fetch).days >= 1:
            self._fetch_events()
        
        # Check for nearby events
        for event in self.events:
            if event.impact != ImpactLevel.HIGH:
                continue
            
            # Ensure event time is timezone-aware
            event_time = event.time
            if event_time.tzinfo is None:
                event_time = pytz.UTC.localize(event_time)
            
            # Determine blackout window
            if any(critical in event.event for critical in self.CRITICAL_EVENTS):
                blackout_before = timedelta(minutes=30)
                blackout_after = timedelta(minutes=30)
            else:
                blackout_before = timedelta(minutes=15)
                blackout_after = timedelta(minutes=15)
            
            # Check if timestamp is in blackout window
            if event_time - blackout_before <= timestamp <= event_time + blackout_after:
                return False, f"News blackout: {event.event} at {event_time.strftime('%H:%M')}"
        
        return True, None
    
    def _fetch_events(self):
        """Fetch today's economic calendar events."""
        # Using ForexFactory calendar (free, no API key needed)
        # In production, use a paid service like Trading Economics or Investing.com
        
        try:
            # Mock implementation - replace with actual API
            self.events = self._get_mock_events()
            self.last_fetch = datetime.now()
        except Exception as e:
            print(f"Failed to fetch news events: {e}")
            # Use cached events or empty list
    
    def _get_mock_events(self) -> List[NewsEvent]:
        """Mock events for testing. Replace with real API."""
        from datetime import timezone
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return [
            NewsEvent(
                time=today.replace(hour=8, minute=30),
                currency="USD",
                event="CPI m/m",
                impact=ImpactLevel.HIGH
            ),
            NewsEvent(
                time=today.replace(hour=14, minute=0),
                currency="USD",
                event="FOMC Statement",
                impact=ImpactLevel.HIGH
            ),
            NewsEvent(
                time=today.replace(hour=15, minute=30),
                currency="USD",
                event="Unemployment Claims",
                impact=ImpactLevel.MEDIUM
            ),
        ]
    
    def get_upcoming_events(self, hours: int = 4) -> List[NewsEvent]:
        """Get upcoming high-impact events in next N hours."""
        if not self.events:
            self._fetch_events()
        
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        
        return [
            e for e in self.events
            if e.impact == ImpactLevel.HIGH and now <= e.time <= cutoff
        ]
    
    def add_manual_event(self, time: datetime, event: str, impact: ImpactLevel = ImpactLevel.HIGH):
        """Manually add a news event (for testing or custom events)."""
        self.events.append(NewsEvent(
            time=time,
            currency="USD",
            event=event,
            impact=impact
        ))


# Global instance
news_filter = NewsFilter()
