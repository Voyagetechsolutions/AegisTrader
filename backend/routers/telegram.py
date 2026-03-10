"""
telegram.py
Handles inbound Telegram Bot API updates (commands).
Registered as a webhook endpoint OR used in polling mode.

Supported commands (per spec):
  /status - Bot status
  /start - Enable auto trading
  /stop - Disable auto trading
  /mode [analyze|trade|swing] - Switch mode
  /positions - Open positions
  /closeall - Close all trades
  /overview - Weekly market overview
"""

from __future__ import annotations
import logging
import inspect

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.models import BotSetting, BotMode, Trade, TradeStatus
from backend.modules.alert_manager import send_message
from backend.routers.mt5_bridge import mt5_bridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_settings(db: AsyncSession) -> BotSetting | None:
    result = await db.execute(select(BotSetting).limit(1))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

async def handle_status(db: AsyncSession) -> str:
    """Handle /status command."""
    s = await _get_settings(db)
    if not s:
        return "Bot not configured. No settings found."

    balance = await mt5_bridge.get_account_balance()

    # Get lot size display
    lot_display = s.lot_mode.value
    if s.lot_mode.value == "fixed_lot" and s.fixed_lot:
        lot_display = f"Fixed: {float(s.fixed_lot)}"
    elif s.lot_mode.value == "risk_percent" and s.risk_percent:
        lot_display = f"Risk: {float(s.risk_percent)}%"

    # Count open positions
    pos_result = await db.execute(
        select(func.count(Trade.id)).where(
            Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIAL])
        )
    )
    open_positions = pos_result.scalar() or 0

    return (
        f"<b>Aegis Trader Status</b>\n"
        f"{'─' * 24}\n"
        f"<b>Mode:</b> {s.mode.value.upper()}\n"
        f"<b>Auto Trade:</b> {'ON' if s.auto_trade_enabled else 'OFF'}\n"
        f"<b>Lot Mode:</b> {lot_display}\n"
        f"<b>Symbol:</b> {s.execution_symbol}\n"
        f"<b>Balance:</b> ${balance:,.2f}\n"
        f"<b>Open Positions:</b> {open_positions}\n"
        f"{'─' * 24}\n"
        f"<b>Max Trades/Day:</b> {s.max_trades_per_day}\n"
        f"<b>Max Losses/Day:</b> {s.max_losses_per_day}\n"
        f"<b>Drawdown Limit:</b> {float(s.max_daily_drawdown_pct)}%"
    )


async def handle_start(db: AsyncSession) -> str:
    """Handle /start command - enable auto trading."""
    s = await _get_settings(db)
    if not s:
        return "Bot not configured."
    s.auto_trade_enabled = True
    await db.commit()
    return "<b>Auto trading ENABLED.</b>\nBot is now in active trade mode."


async def handle_stop(db: AsyncSession) -> str:
    """Handle /stop command - disable auto trading."""
    s = await _get_settings(db)
    if not s:
        return "Bot not configured."
    s.auto_trade_enabled = False
    await db.commit()
    return "<b>Auto trading DISABLED.</b>\nSignal alerts will continue."


async def handle_mode(db: AsyncSession, mode_arg: str) -> str:
    """Handle /mode command - switch bot mode."""
    mode_map = {
        "analyze": BotMode.ANALYZE,
        "trade": BotMode.TRADE,
        "swing": BotMode.SWING,
    }
    new_mode = mode_map.get(mode_arg.lower())
    if not new_mode:
        return f"Unknown mode: <code>{mode_arg}</code>\nValid: analyze | trade | swing"

    s = await _get_settings(db)
    if not s:
        return "Bot not configured."
    s.mode = new_mode
    await db.commit()
    return f"Bot mode switched to <b>{new_mode.value.upper()}</b>"


async def handle_positions() -> str:
    """Handle /positions command - list open MT5 positions."""
    positions = await mt5_bridge.get_positions()
    if not positions:
        return "<b>No open positions.</b>"

    lines = ["<b>Open Positions:</b>", "─" * 24]
    for p in positions:
        pnl_emoji = "+" if p.pnl >= 0 else ""
        lines.append(
            f"#{p.ticket} {p.symbol} {p.direction.upper()} "
            f"{p.lot_size} lots | P&L: {pnl_emoji}{p.pnl:.2f}"
        )
    return "\n".join(lines)


async def handle_closeall(db: AsyncSession) -> str:
    """Handle /closeall command - close all open trades."""
    from backend.modules.trade_manager import close_all_trades
    from backend.models.models import TradeCloseReason

    s = await _get_settings(db)
    if not s:
        return "Bot not configured."

    closed = await close_all_trades(db, s.user_id, mt5_bridge, TradeCloseReason.MANUAL)
    return f"<b>Closed {closed} position(s).</b>"


async def handle_overview(db: AsyncSession) -> str:
    """Handle /overview command - generate weekly market overview."""
    from backend.modules.analytics_engine import generate_weekly_report, format_weekly_report

    report = await generate_weekly_report(db)
    return format_weekly_report(report)


# ---------------------------------------------------------------------------
# Command Map
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "/status": handle_status,
    "/start": handle_start,
    "/stop": handle_stop,
    "/positions": handle_positions,
    "/overview": handle_overview,
    "/closeall": handle_closeall,
}


# ---------------------------------------------------------------------------
# Webhook Endpoint
# ---------------------------------------------------------------------------

@router.post("/webhook", summary="Telegram Bot webhook endpoint")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receives Telegram Bot API updates and dispatches command responses."""
    body = await request.json()
    message = body.get("message", {})
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not chat_id:
        return {"ok": True}

    # Parse command and optional argument
    parts = text.split()
    command = parts[0].lower().split("@")[0]  # handle /cmd@botname
    arg = parts[1] if len(parts) > 1 else ""

    try:
        if command == "/mode":
            reply = await handle_mode(db, arg)
        elif command in COMMAND_MAP:
            handler = COMMAND_MAP[command]
            if "db" in inspect.signature(handler).parameters:
                reply = await handler(db)
            else:
                reply = await handler()
        else:
            reply = (
                "<b>Aegis Trader Commands:</b>\n"
                "/status - Bot status\n"
                "/start - Enable auto trading\n"
                "/stop - Disable auto trading\n"
                "/mode [analyze|trade|swing] - Switch mode\n"
                "/positions - Open positions\n"
                "/closeall - Close all trades\n"
                "/overview - Weekly market overview"
            )
    except Exception as e:
        logger.error(f"Command handler error: {e}")
        reply = f"Error processing command: {e}"

    await send_message(reply, chat_id=chat_id)
    return {"ok": True}
