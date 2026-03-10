"""
weekly_report.py
Scheduled service that runs every Sunday at 07:00 SAST.
Generates the weekly market overview and sends it to Telegram.
"""

from __future__ import annotations
import logging
from datetime import datetime

import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.modules.analytics_engine import generate_weekly_report, format_weekly_report
from backend.modules.alert_manager import send_message
from backend.modules.news_filter import sync_forexfactory_news

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")


async def run_weekly_report_job(mtf_bias: dict | None = None) -> None:
    """
    Main job function for the weekly report scheduler.
    Syncs news events, generates report, sends to Telegram.

    mtf_bias is optionally provided via API call (user submits it via /overview command
    or from a custom TradingView webhook). Falls back to neutral placeholders.
    """
    logger.info("Running weekly report job...")

    async with AsyncSessionLocal() as db:
        # Sync ForexFactory news for the coming week
        synced = await sync_forexfactory_news(db)
        logger.info(f"Synced {synced} news events")

        # Generate report
        report = await generate_weekly_report(db, mtf_bias=mtf_bias)
        formatted = format_weekly_report(report)

        # Send to Telegram
        sent = await send_message(formatted)

        if sent:
            report.sent_to_telegram = True
            await db.commit()
            logger.info(f"Weekly report sent. Report ID: {report.id}")
        else:
            logger.error("Failed to send weekly report to Telegram")
