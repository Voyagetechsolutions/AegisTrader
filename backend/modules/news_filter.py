"""
news_filter.py
Checks for high-impact economic news blackout windows.

Per dual-engine-strategy-system spec (Requirements 17.1-17.7):
- Block trading 30 minutes before news events
- Block trading 60 minutes after news events
- Track CPI, NFP, FOMC, Fed speeches as high-impact events

Data source: ForexFactory calendar (scraped via aiohttp) or manual overrides stored in DB.
The BYPASS setting (NEWS_FILTER_BYPASS=true) disables the filter for testing.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.models import NewsEvent

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")

# Events requiring tracking per spec (CPI, NFP, FOMC, Fed speeches)
HIGH_IMPACT_EVENTS = frozenset([
    "cpi", "nfp", "non-farm", "fomc", "federal", "interest rate",
    "rate decision", "inflation", "gdp", "employment", "fed speech",
    "fed chair", "powell", "yellen", "treasury secretary",
])

# Per spec: 30 minutes before, 60 minutes after
NEWS_BUFFER_BEFORE = 30   # minutes
NEWS_BUFFER_AFTER = 60    # minutes


@dataclass
class NewsCheckResult:
    blocked: bool
    reason: Optional[str] = None
    blocking_event: Optional[str] = None
    minutes_until_clear: Optional[int] = None
    conservative_mode: bool = False  # True when calendar unavailable


def _is_high_impact(title: str) -> bool:
    """Return True if event title matches a high-impact keyword (CPI, NFP, FOMC, Fed speeches)."""
    lower = title.lower()
    return any(kw in lower for kw in HIGH_IMPACT_EVENTS)


async def check_news_blackout(
    db: AsyncSession,
    now: Optional[datetime] = None,
    processing_buffer_seconds: int = 5,
    enable_conservative_mode: bool = True,
) -> NewsCheckResult:
    """
    Check if auto trading is currently blocked by a news blackout.
    Returns NewsCheckResult with blocked=True if trading should be paused.

    Per spec Requirements 17.2-17.3:
    - Blocks trading 30 minutes before news events
    - Blocks trading 60 minutes after news events

    Conservative Mode (Requirement 17.7):
    When calendar is unavailable and conservative mode is enabled,
    blocks trading during typical news times:
    - 08:30 SAST (±30min window)
    - 10:00 SAST (±30min window)
    - 14:00 SAST (±30min window)
    - 15:30 SAST (±30min window)
    - 19:00 SAST (±30min window)

    Args:
        db: Database session
        now: Current time (defaults to UTC now)
        processing_buffer_seconds: Buffer for signal processing time (default 5s)
        enable_conservative_mode: Enable conservative mode when calendar unavailable
    """
    if settings.news_filter_bypass:
        return NewsCheckResult(blocked=False, reason="News filter bypassed (dev mode)")

    if now is None:
        now = datetime.now(pytz.UTC)
    elif now.tzinfo is None:
        now = pytz.UTC.localize(now)
    else:
        now = now.astimezone(pytz.UTC)
    
    # Add processing buffer to account for execution delay
    # This prevents signals arriving 2s before news from executing during news
    effective_now = now + timedelta(seconds=processing_buffer_seconds)

    # Fetch events from DB within the relevant window
    # Use 60 minutes as the max buffer (after event)
    window_start = effective_now - timedelta(minutes=NEWS_BUFFER_AFTER)
    window_end = effective_now + timedelta(minutes=NEWS_BUFFER_BEFORE)

    try:
        result = await db.execute(
            select(NewsEvent).where(
                NewsEvent.starts_at >= window_start,
                NewsEvent.starts_at <= window_end,
                NewsEvent.impact == "high",
            )
        )
        events = result.scalars().all()

        for event in events:
            event_time = event.starts_at
            if event_time.tzinfo is None:
                event_time = pytz.UTC.localize(event_time)
            else:
                event_time = event_time.astimezone(pytz.UTC)

            # Per spec: 30 minutes before, 60 minutes after
            blackout_start = event_time - timedelta(minutes=NEWS_BUFFER_BEFORE)
            blackout_end = event_time + timedelta(minutes=NEWS_BUFFER_AFTER)

            if blackout_start <= effective_now <= blackout_end:
                minutes_clear = int((blackout_end - effective_now).total_seconds() / 60)
                return NewsCheckResult(
                    blocked=True,
                    reason=f"News blackout: {event.title} (30min before / 60min after)",
                    blocking_event=event.title,
                    minutes_until_clear=minutes_clear,
                )

        return NewsCheckResult(blocked=False)
    
    except Exception as exc:
        logger.warning(f"News calendar check failed: {exc}")
        
        # Conservative mode: block during typical news times if calendar unavailable
        if enable_conservative_mode:
            sast_now = effective_now.astimezone(SAST)
            current_time = sast_now.time()
            
            # Typical news times in SAST with 30-minute windows
            typical_news_times = [
                (8, 30),  # 08:30 SAST (US CPI, employment data)
                (10, 0),  # 10:00 SAST (European data)
                (14, 0),  # 14:00 SAST (US market open data)
                (15, 30), # 15:30 SAST (US session data)
                (19, 0),  # 19:00 SAST (Fed speeches, FOMC)
            ]
            
            for hour, minute in typical_news_times:
                news_time = datetime.combine(sast_now.date(), datetime.min.time().replace(hour=hour, minute=minute))
                news_time = SAST.localize(news_time)
                
                blackout_start = news_time - timedelta(minutes=30)
                blackout_end = news_time + timedelta(minutes=30)
                
                if blackout_start <= sast_now <= blackout_end:
                    return NewsCheckResult(
                        blocked=True,
                        reason=f"Conservative mode: typical news time {hour:02d}:{minute:02d} SAST",
                        blocking_event="Calendar unavailable",
                        minutes_until_clear=int((blackout_end - sast_now).total_seconds() / 60),
                        conservative_mode=True,
                    )
        
        # If conservative mode disabled or outside typical times, allow trading
        return NewsCheckResult(blocked=False)


async def sync_forexfactory_news(db: AsyncSession) -> int:
    """
    Scrape this week's high-impact USD events from ForexFactory JSON feed.
    Returns number of events upserted.
    Runs as a scheduled background job (daily at midnight SAST).
    """
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    inserted = 0

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"ForexFactory feed returned {resp.status}")
                    return 0
                data = await resp.json(content_type=None)

        for item in data:
            # Only USD events
            if item.get("country", "").upper() != "USD":
                continue
            # Only high impact
            if item.get("impact", "").lower() not in ("high", "holiday"):
                continue

            title = item.get("title", "Unknown")
            date_str = item.get("date", "")
            time_str = item.get("time", "")

            try:
                if time_str:
                    dt_str = f"{date_str} {time_str}"
                    event_dt = datetime.strptime(dt_str, "%Y-%m-%d %I:%M%p")
                else:
                    event_dt = datetime.strptime(date_str, "%Y-%m-%d")

                # ForexFactory times are in ET
                event_utc = pytz.timezone("America/New_York").localize(event_dt).astimezone(pytz.UTC)
            except ValueError:
                logger.debug(f"Could not parse date for event: {title}")
                continue

            is_major = _is_high_impact(title)

            event = NewsEvent(
                title=title,
                country="US",
                currency="USD",
                impact="high",
                starts_at=event_utc,
                is_major=is_major,
                source="forexfactory",
                raw_payload=item,
            )
            db.add(event)
            inserted += 1

        await db.commit()
        logger.info(f"Synced {inserted} news events from ForexFactory")
    except Exception as exc:
        logger.error(f"News sync failed: {exc}")
        await db.rollback()

    return inserted


async def add_manual_news_event(
    db: AsyncSession,
    title: str,
    starts_at: datetime,
    impact: str = "high",
    is_major: bool = False,
) -> NewsEvent:
    """Allow users to manually add news events via API."""
    if starts_at.tzinfo is None:
        starts_at = pytz.UTC.localize(starts_at)

    event = NewsEvent(
        title=title,
        country="US",
        currency="USD",
        impact=impact,
        starts_at=starts_at,
        is_major=is_major,
        source="manual",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_upcoming_news(
    db: AsyncSession,
    days: int = 7,
) -> list[NewsEvent]:
    """Get upcoming high-impact news events for the next N days."""
    now = datetime.now(pytz.UTC)
    end = now + timedelta(days=days)

    result = await db.execute(
        select(NewsEvent).where(
            NewsEvent.starts_at >= now,
            NewsEvent.starts_at <= end,
            NewsEvent.impact == "high",
        ).order_by(NewsEvent.starts_at)
    )
    return list(result.scalars().all())
