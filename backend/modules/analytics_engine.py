"""
analytics_engine.py
Generates weekly performance statistics and Sunday market outlook reports.

Per spec: Sunday overview generator runs every Sunday.
"""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    Trade, Signal, NewsEvent, WeeklyReport,
    TradeStatus, SignalGrade, StrategyStat,
)

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")

MTF_TIMEFRAMES = ["weekly", "daily", "h4", "h1", "m15", "m5", "m1"]


async def compute_strategy_stats(
    db: AsyncSession,
    user_id: Optional[str] = None,
    setup_type: Optional[str] = None,
    session_name: Optional[str] = None,
    period_days: int = 30,
) -> StrategyStat:
    """
    Compute performance metrics for the specified filters.

    Returns StrategyStat with:
    - trades_count
    - win_rate
    - avg_rr (average risk-reward)
    - expectancy
    - max_drawdown
    """
    now = datetime.now(pytz.UTC)
    period_start = now - timedelta(days=period_days)

    # Base filter
    filters = [
        Trade.status == TradeStatus.CLOSED,
        Trade.closed_at >= period_start,
    ]

    closed_trades_q = await db.execute(
        select(Trade).where(and_(*filters))
    )
    trades = closed_trades_q.scalars().all()

    total_trades = len(trades)
    winning = [t for t in trades if (t.pnl and float(t.pnl) > 0)]
    losing = [t for t in trades if (t.pnl and float(t.pnl) < 0)]

    win_rate = (len(winning) / total_trades * 100) if total_trades else 0.0

    # Expectancy = (win_rate × avg_win) - (loss_rate × avg_loss)
    avg_win = sum(float(t.pnl) for t in winning) / len(winning) if winning else 0
    avg_loss = abs(sum(float(t.pnl) for t in losing) / len(losing)) if losing else 0
    loss_rate = (len(losing) / total_trades) if total_trades else 0
    expectancy = (win_rate / 100 * avg_win) - (loss_rate * avg_loss)

    # Average R:R (based on TP1 distance vs SL distance)
    rr_values = []
    for t in trades:
        if t.stop_loss and t.tp1 and t.entry_price:
            sl_dist = abs(float(t.entry_price) - float(t.stop_loss))
            tp_dist = abs(float(t.tp1) - float(t.entry_price))
            if sl_dist > 0:
                rr_values.append(tp_dist / sl_dist)
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0

    # Max drawdown: largest equity decline from peak
    equity = [0.0]
    for t in sorted(trades, key=lambda x: x.closed_at or x.created_at):
        equity.append(equity[-1] + (float(t.pnl) if t.pnl else 0))
    peak = equity[0]
    max_dd = 0.0
    for e in equity:
        if e > peak:
            peak = e
        dd = peak - e
        if dd > max_dd:
            max_dd = dd

    stat = StrategyStat(
        setup_type=setup_type,
        session_name=session_name,
        trades_count=total_trades,
        win_rate=round(win_rate, 2),
        avg_rr=round(avg_rr, 2),
        expectancy=round(expectancy, 2),
        max_drawdown=round(max_dd, 2),
    )
    db.add(stat)
    await db.commit()
    return stat


async def generate_weekly_report(
    db: AsyncSession,
    week_start: Optional[datetime] = None,
    mtf_bias: Optional[dict] = None,
) -> WeeklyReport:
    """
    Generate a Sunday market overview report per spec.

    Output format:
    {
        "weekly_bias": "bull",
        "daily_bias": "buy",
        "h4_bias": "buy",
        "h1_bias": "sell",
        "m15_bias": "sell",
        "m5_bias": "sell",
        "m1_bias": "neutral",
        "bullish_scenario": "...",
        "bearish_scenario": "...",
        "key_levels": [46000, 46125, 46250],
        "major_news": ["CPI Wednesday", "NFP Friday"]
    }
    """
    if week_start is None:
        now = datetime.now(SAST)
        # Snap to the most recent Sunday
        days_since_sunday = (now.weekday() + 1) % 7
        week_start = (now - timedelta(days=days_since_sunday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Placeholder MTF bias if not provided
    # In production, this would come from a TradingView webhook or manual input
    if mtf_bias is None:
        mtf_bias = {
            "weekly": "neutral",
            "daily": "neutral",
            "h4": "neutral",
            "h1": "neutral",
            "m15": "neutral",
            "m5": "neutral",
            "m1": "neutral",
        }

    # Fetch upcoming high-impact news events (next 7 days)
    news_q = await db.execute(
        select(NewsEvent).where(
            and_(
                NewsEvent.starts_at >= datetime.now(pytz.UTC),
                NewsEvent.starts_at <= datetime.now(pytz.UTC) + timedelta(days=7),
                NewsEvent.impact == "high",
            )
        ).order_by(NewsEvent.starts_at)
    )
    news_events = news_q.scalars().all()
    major_news = [e.title for e in news_events[:10]]

    # Key levels (generated around a reference price)
    # In production this would be fetched from MT5 or the latest signal
    reference_price = 46000
    key_levels = [
        reference_price - 250,
        reference_price - 125,
        reference_price,
        reference_price + 125,
        reference_price + 250,
    ]

    # Determine scenarios from bias
    daily_bias = mtf_bias.get("daily", "neutral").lower()
    if daily_bias in ("bull", "bullish", "buy"):
        bullish_scenario = (
            f"Wait for retracement into {reference_price + 125:,} with bullish shift "
            f"for continuation toward {reference_price + 250:,}."
        )
        bearish_scenario = (
            f"Only valid if daily structure breaks and {reference_price:,} fails."
        )
    elif daily_bias in ("bear", "bearish", "sell"):
        bullish_scenario = (
            f"Only valid if {reference_price:,} reclaims with displacement."
        )
        bearish_scenario = (
            f"Wait for retracement into {reference_price - 125:,} with bearish shift "
            f"for continuation toward {reference_price - 250:,}."
        )
    else:
        bullish_scenario = (
            f"Wait for bullish confirmation at {reference_price + 125:,} level."
        )
        bearish_scenario = (
            f"Wait for bearish confirmation at {reference_price - 125:,} level."
        )

    report = WeeklyReport(
        week_start=week_start,
        weekly_bias=mtf_bias.get("weekly", "neutral"),
        daily_bias=mtf_bias.get("daily", "neutral"),
        h4_bias=mtf_bias.get("h4", "neutral"),
        h1_bias=mtf_bias.get("h1", "neutral"),
        m15_bias=mtf_bias.get("m15", "neutral"),
        m5_bias=mtf_bias.get("m5", "neutral"),
        m1_bias=mtf_bias.get("m1", "neutral"),
        bullish_scenario=bullish_scenario,
        bearish_scenario=bearish_scenario,
        key_levels=key_levels,
        news_summary=major_news,
        sent_to_telegram=False,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


def format_weekly_report(report: WeeklyReport) -> str:
    """
    Format a WeeklyReport into a Telegram message string per spec format.

    US30 Weekly Overview

    Weekly: Bull
    Daily: Buy
    4H: Buy
    1H: Sell
    15M: Sell
    5M: Sell
    1M: Neutral

    Key levels:
    46000
    46125
    46250

    Bullish scenario:
    Wait for retracement into 46125 and bullish 5M confirmation.

    Bearish scenario:
    Valid only if 46000 breaks with displacement.

    Major news:
    CPI Wednesday
    NFP Friday
    """
    lines = [
        "<b>US30 Weekly Overview</b>",
        "",
        f"<b>Weekly:</b> {(report.weekly_bias or 'Neutral').title()}",
        f"<b>Daily:</b> {(report.daily_bias or 'Neutral').title()}",
        f"<b>4H:</b> {(report.h4_bias or 'Neutral').title()}",
        f"<b>1H:</b> {(report.h1_bias or 'Neutral').title()}",
        f"<b>15M:</b> {(report.m15_bias or 'Neutral').title()}",
        f"<b>5M:</b> {(report.m5_bias or 'Neutral').title()}",
        f"<b>1M:</b> {(report.m1_bias or 'Neutral').title()}",
        "",
        "<b>Key levels:</b>",
    ]

    if report.key_levels:
        for level in report.key_levels:
            lines.append(f"{int(level):,}")
    else:
        lines.append("None identified")

    lines.extend([
        "",
        "<b>Bullish scenario:</b>",
        report.bullish_scenario or "Not specified",
        "",
        "<b>Bearish scenario:</b>",
        report.bearish_scenario or "Not specified",
        "",
        "<b>Major news:</b>",
    ])

    if report.news_summary:
        for news in report.news_summary[:5]:
            lines.append(news)
    else:
        lines.append("None this week")

    return "\n".join(lines)
