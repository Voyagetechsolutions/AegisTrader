"""
alert_manager.py
Sends formatted Telegram messages for all system events.
Uses python-telegram-bot in async mode.
"""

from __future__ import annotations
import logging
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from backend.config import settings
from backend.models.models import Signal, Trade, NewsEvent

logger = logging.getLogger(__name__)

_bot: Optional[Bot] = None


def get_bot() -> Bot:
    """Lazily initialise the Telegram bot singleton."""
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


async def send_message(text: str, chat_id: Optional[str] = None) -> bool:
    """Low-level message sender. Returns True on success."""
    target = chat_id or settings.telegram_chat_id
    if not target or not settings.telegram_bot_token:
        logger.warning("Telegram not configured - skipping alert")
        return False
    try:
        await get_bot().send_message(
            chat_id=target,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return True
    except TelegramError as e:
        logger.error(f"Telegram send failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grade_emoji(grade: str) -> str:
    return {"A+": "🟢", "A": "🟡", "B": "🔴"}.get(grade, "⚪")


def _direction_emoji(direction: str) -> str:
    return "📈" if direction.lower() in ("long", "buy") else "📉"


def _setup_type_label(setup_type: Optional[str]) -> str:
    if not setup_type:
        return "Unknown"
    labels = {
        "continuation_long": "Continuation Long",
        "continuation_short": "Continuation Short",
        "swing_long": "Swing Long",
        "swing_short": "Swing Short",
    }
    return labels.get(setup_type, setup_type.replace("_", " ").title())


def _bias_emoji(bias: Optional[str]) -> str:
    if not bias:
        return "⚪"
    lower = bias.lower()
    if lower in ("bull", "bullish", "buy", "bull_shift"):
        return "🟢"
    elif lower in ("bear", "bearish", "sell", "bear_shift"):
        return "🔴"
    return "⚪"


# ---------------------------------------------------------------------------
# Signal Alert (per spec format)
# ---------------------------------------------------------------------------

async def send_signal_alert(signal: Signal) -> bool:
    """Send a formatted signal alert to Telegram."""
    grade = signal.grade.value if hasattr(signal.grade, "value") else str(signal.grade)
    direction = signal.direction.value if hasattr(signal.direction, "value") else str(signal.direction)
    setup_type = signal.setup_type.value if signal.setup_type and hasattr(signal.setup_type, "value") else str(signal.setup_type or "")

    # Build MTF bias line
    biases = []
    if signal.weekly_bias:
        biases.append(f"W:{_bias_emoji(signal.weekly_bias)}")
    if signal.daily_bias:
        biases.append(f"D:{_bias_emoji(signal.daily_bias)}")
    if signal.h4_bias:
        biases.append(f"4H:{_bias_emoji(signal.h4_bias)}")
    if signal.h1_bias:
        biases.append(f"1H:{_bias_emoji(signal.h1_bias)}")
    bias_line = " ".join(biases) if biases else "N/A"

    # Confluence factors
    factors = []
    if signal.liquidity_sweep:
        factors.append("Liq Sweep")
    if signal.fvg_present:
        factors.append("FVG")
    if signal.displacement_present:
        factors.append("Displacement")
    if signal.mss_present:
        factors.append("MSS")
    factors_line = ", ".join(factors) if factors else "None"

    # Key levels
    levels = []
    if signal.level_250:
        levels.append(f"250: {float(signal.level_250):,.0f}")
    if signal.level_125:
        levels.append(f"125: {float(signal.level_125):,.0f}")
    levels_line = " | ".join(levels) if levels else "N/A"

    spread_ok = signal.spread_points and float(signal.spread_points) <= 5
    auto_label = "Auto Trade" if signal.eligible_for_auto_trade else "Alert Only"

    text = (
        f"{_direction_emoji(direction)} <b>{signal.execution_symbol} Setup Detected</b>\n"
        f"{'─' * 28}\n"
        f"<b>Type:</b> {_setup_type_label(setup_type)}\n"
        f"<b>Direction:</b> {direction.upper()}\n"
        f"<b>Entry:</b> {float(signal.entry_price):,.0f}\n"
        f"<b>SL:</b> {float(signal.stop_loss):,.0f}\n"
        f"<b>TP1:</b> {float(signal.tp1):,.0f}\n"
        f"<b>TP2:</b> {float(signal.tp2):,.0f}\n"
        f"{'─' * 28}\n"
        f"<b>MTF Bias:</b> {bias_line}\n"
        f"<b>Levels:</b> {levels_line}\n"
        f"<b>Confluence:</b> {factors_line}\n"
        f"{'─' * 28}\n"
        f"<b>Score:</b> {signal.score} ({_grade_emoji(grade)} {grade})\n"
        f"<b>Session:</b> {(signal.session_name or 'N/A').replace('_', ' ').title()}\n"
        f"<b>Spread:</b> {'OK ✅' if spread_ok else 'Wide ⚠️'}\n"
        f"<b>News:</b> {'Blackout ⛔' if signal.news_blocked else 'Clear ✅'}\n"
        f"{'─' * 28}\n"
        f"<b>Action:</b> {auto_label}"
    )
    return await send_message(text)


# ---------------------------------------------------------------------------
# Trade Execution Alerts
# ---------------------------------------------------------------------------

async def send_trade_open_alert(trade: Trade) -> bool:
    """Notify that a trade has been executed."""
    direction = trade.direction.value if hasattr(trade.direction, "value") else str(trade.direction)

    entry_price = float(trade.actual_entry_price or trade.entry_price)
    slippage_text = ""
    if trade.slippage:
        slippage_text = f" (slip: {float(trade.slippage):+.1f})"

    text = (
        f"⚡ <b>Trade Executed</b>\n"
        f"{'─' * 28}\n"
        f"<b>Symbol:</b> {trade.symbol}\n"
        f"<b>Direction:</b> {direction.upper()}\n"
        f"<b>Lots:</b> {float(trade.lot_size):.2f}\n"
        f"<b>Entry:</b> {entry_price:,.0f}{slippage_text}\n"
        f"<b>SL:</b> {float(trade.stop_loss):,.0f}\n"
        f"<b>TP1:</b> {float(trade.tp1):,.0f}\n"
        f"<b>TP2:</b> {float(trade.tp2):,.0f}\n"
        f"<b>Ticket:</b> #{trade.mt5_ticket or 'N/A'}\n"
        f"<b>Account:</b> {trade.account_type.upper()}"
    )
    return await send_message(text)


async def send_tp1_alert(trade: Trade) -> bool:
    """Notify TP1 hit - 50% closed, SL moved to BE."""
    text = (
        f"🎯 <b>TP1 Hit</b> - {trade.symbol}\n"
        f"{'─' * 28}\n"
        f"50% closed at <b>{float(trade.tp1):,.0f}</b>\n"
        f"Stop moved to <b>Break Even</b> ✅\n"
        f"Trailing stop now <b>active</b>\n"
        f"Ticket: #{trade.mt5_ticket}"
    )
    return await send_message(text)


async def send_tp2_alert(trade: Trade) -> bool:
    """Notify TP2 hit - 40% closed, runner active."""
    text = (
        f"🎯🎯 <b>TP2 Hit</b> - {trade.symbol}\n"
        f"{'─' * 28}\n"
        f"40% closed at <b>{float(trade.tp2):,.0f}</b>\n"
        f"Runner (10%) still active 🏃\n"
        f"Trailing on 5M structure\n"
        f"Ticket: #{trade.mt5_ticket}"
    )
    return await send_message(text)


async def send_trade_close_alert(trade: Trade) -> bool:
    """Notify trade closed."""
    pnl = float(trade.pnl) if trade.pnl else 0.0
    emoji = "✅" if pnl >= 0 else "❌"
    reason = trade.close_reason.value if trade.close_reason else "manual"

    text = (
        f"{emoji} <b>Trade Closed</b> - {trade.symbol}\n"
        f"{'─' * 28}\n"
        f"<b>P&L:</b> {'+' if pnl >= 0 else ''}{pnl:.2f}\n"
        f"<b>Reason:</b> {reason.replace('_', ' ').title()}\n"
        f"Ticket: #{trade.mt5_ticket}"
    )
    return await send_message(text)


# ---------------------------------------------------------------------------
# Risk / System Alerts
# ---------------------------------------------------------------------------

async def send_risk_alert(reason: str) -> bool:
    """Notify risk limit reached - auto trading disabled."""
    text = (
        f"🚨 <b>Risk Limit Reached</b>\n"
        f"{'─' * 28}\n"
        f"{reason}\n"
        f"<i>Auto trading disabled for today.</i>\n"
        f"<i>Alerts will continue.</i>"
    )
    return await send_message(text)


async def send_spread_alert(symbol: str, spread: float, cap: float) -> bool:
    """Notify spread too wide - trade rejected."""
    text = (
        f"⚠️ <b>Spread Alert</b> - {symbol}\n"
        f"{'─' * 28}\n"
        f"Current spread: <b>{spread:.1f} pts</b>\n"
        f"Max allowed: <b>{cap:.1f} pts</b>\n"
        f"<i>Trade rejected.</i>"
    )
    return await send_message(text)


async def send_news_alert(event: NewsEvent) -> bool:
    """Notify news blackout active."""
    text = (
        f"📰 <b>News Blackout Active</b>\n"
        f"{'─' * 28}\n"
        f"<b>Event:</b> {event.title}\n"
        f"<b>Impact:</b> {'🔴 HIGH' if event.is_major else '🟠 High'}\n"
        f"<i>Auto trading paused.</i>\n"
        f"<i>Alerts will continue.</i>"
    )
    return await send_message(text)


# ---------------------------------------------------------------------------
# Weekly Overview Alert (per spec format)
# ---------------------------------------------------------------------------

async def send_weekly_overview(
    weekly_bias: str,
    daily_bias: str,
    h4_bias: str,
    h1_bias: str,
    m15_bias: str,
    m5_bias: str,
    m1_bias: str,
    bullish_scenario: str,
    bearish_scenario: str,
    key_levels: list[float],
    major_news: list[str],
) -> bool:
    """
    Send Sunday market overview message per spec format.

    Example output:
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
    levels_text = "\n".join(f"{int(lvl):,}" for lvl in key_levels) if key_levels else "None identified"
    news_text = "\n".join(major_news) if major_news else "None this week"

    text = (
        f"📊 <b>US30 Weekly Overview</b>\n"
        f"{'─' * 28}\n"
        f"<b>Weekly:</b> {weekly_bias.title()}\n"
        f"<b>Daily:</b> {daily_bias.title()}\n"
        f"<b>4H:</b> {h4_bias.title()}\n"
        f"<b>1H:</b> {h1_bias.title()}\n"
        f"<b>15M:</b> {m15_bias.title()}\n"
        f"<b>5M:</b> {m5_bias.title()}\n"
        f"<b>1M:</b> {m1_bias.title()}\n"
        f"{'─' * 28}\n"
        f"<b>Key levels:</b>\n{levels_text}\n"
        f"{'─' * 28}\n"
        f"<b>Bullish scenario:</b>\n{bullish_scenario}\n"
        f"{'─' * 28}\n"
        f"<b>Bearish scenario:</b>\n{bearish_scenario}\n"
        f"{'─' * 28}\n"
        f"<b>Major news:</b>\n{news_text}"
    )
    return await send_message(text)
