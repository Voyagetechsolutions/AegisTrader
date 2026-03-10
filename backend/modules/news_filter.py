"""
news_filter.py
Checks for high-impact economic news blackout windows.

Standard blackout: 15 min before / 15 min after event.
Extended blackout (CPI, NFP, FOMC, rate decisions): 30 min before / 30 min after.

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

# Events requiring extended blackout windows (per spec)
EXTENDED_BLACKOUT_EVENTS = frozenset([
    "cpi", "nfp", "non-farm", "fomc", "federal", "interest rate",
    "rate decision", "inflation", "gdp", "employment",
])

STANDARD_BEFORE = 15   # minutes
STANDARD_AFTER = 15
EXTENDED_BEFORE = 30
EXTENDED_AFTER = 30


@dataclass
class NewsCheckResult:
    blocked: bool
    reason: Optional[str] = None
    blocking_event: Optional[str] = None
    minutes_until_clear: Optional[int] = None


def _is_extended(title: str) -> bool:
    """Return True if event title matches an extended-blackout keyword."""
    lower = title.lower()
    return any(kw in lower for kw in EXTENDED_BLACKOUT_EVENTS)


async def check_news_blackout(
    db: AsyncSession,
    now: Optional[datetime] = None,
    standard_mins: int = STANDARD_BEFORE,
    major_mins: int = EXTENDED_BEFORE,
) -> NewsCheckResult:
    """
    Check if auto trading is currently blocked by a news blackout.
    Returns NewsCheckResult with blocked=True if trading should be paused.

    Args:
        db: Database session
        now: Current time (defaults to UTC now)
        standard_mins: Blackout minutes for standard events
        major_mins: Blackout minutes for major events (CPI, NFP, etc.)
    """
    if settings.news_filter_bypass:
        return NewsCheckResult(blocked=False, reason="News filter bypassed (dev mode)")

    if now is None:
        now = datetime.now(pytz.UTC)
    elif now.tzinfo is None:
        now = pytz.UTC.localize(now)

    # Fetch events from DB within the relevant window
    window_start = now - timedelta(minutes=major_mins)
    window_end = now + timedelta(minutes=major_mins)

    result = await db.execute(
        select(NewsEvent).where(
            NewsEvent.starts_at >= window_start,
            NewsEvent.starts_at <= window_end,
            NewsEvent.impact == "high",
        )
    )
    events = result.scalars().all()

    for event in events:
        # Determine blackout window based on event type
        if event.is_major:
            before = major_mins
            after = major_mins
        else:
            before = standard_mins
            after = standard_mins

        event_time = event.starts_at
        if event_time.tzinfo is None:
            event_time = pytz.UTC.localize(event_time)

        blackout_start = event_time - timedelta(minutes=before)
        blackout_end = event_time + timedelta(minutes=after)

        if blackout_start <= now <= blackout_end:
            minutes_clear = int((blackout_end - now).total_seconds() / 60)
            return NewsCheckResult(
                blocked=True,
                reason=f"News blackout: {event.title}",
                blocking_event=event.title,
                minutes_until_clear=minutes_clear,
            )

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

            is_major = _is_extended(title)

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
