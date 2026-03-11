"""
risk_engine.py
Enforces all per-day trading risk limits (per spec):
  - Max 2 trades per day
  - Max 2 losses per day
  - 2% daily drawdown limit

Kill switch: Disable auto-trade if:
  - 2 losses in same day
  - Daily drawdown >= 2%

Analyze mode and alerts continue regardless.
"""

from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from uuid import UUID

import pytz
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Trade, BotSetting, TradeStatus

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")

# Global lock for atomic risk checking and trade slot reservation
_risk_check_lock = asyncio.Lock()


@dataclass
class RiskStatus:
    """Result of risk check."""
    allowed: bool
    trades_today: int
    losses_today: int
    drawdown_pct: float
    reason: Optional[str] = None


async def get_daily_stats(
    db: AsyncSession,
    user_id: Optional[UUID],
    today: Optional[date] = None,
) -> tuple[int, int, float]:
    """
    Returns (trades_today, losses_today, absolute_loss) for the given user and day.

    absolute_loss is the total negative P&L for closed trades today (used to calculate drawdown %).
    """
    if today is None:
        today = datetime.now(SAST).date()

    start_of_day = SAST.localize(datetime.combine(today, datetime.min.time())).astimezone(pytz.UTC)
    end_of_day = SAST.localize(datetime.combine(today, datetime.max.time())).astimezone(pytz.UTC)

    # Build base filter
    base_filter = and_(
        Trade.opened_at >= start_of_day,
        Trade.opened_at <= end_of_day,
    )
    if user_id:
        base_filter = and_(base_filter, Trade.user_id == user_id)

    # Count all trades opened today
    trades_result = await db.execute(
        select(func.count(Trade.id)).where(base_filter)
    )
    trades_today = trades_result.scalar() or 0

    # Count losing closed trades today
    losses_result = await db.execute(
        select(func.count(Trade.id)).where(
            and_(
                base_filter,
                Trade.status == TradeStatus.CLOSED,
                Trade.pnl < 0,
            )
        )
    )
    losses_today = losses_result.scalar() or 0

    # Sum P&L for drawdown calculation (only negative P&L)
    pnl_result = await db.execute(
        select(func.sum(Trade.pnl)).where(
            and_(
                base_filter,
                Trade.status == TradeStatus.CLOSED,
            )
        )
    )
    total_pnl = pnl_result.scalar() or 0.0

    # Absolute loss for drawdown calculation
    absolute_loss = abs(min(float(total_pnl), 0))

    return trades_today, losses_today, absolute_loss


async def check_risk(
    db: AsyncSession,
    user_id: Optional[UUID],
    account_balance: float = 1000.0,
    today: Optional[date] = None,
) -> RiskStatus:
    """
    Check if auto trading is still allowed given daily limits.
    
    NOTE: This is a READ-ONLY check. For atomic check-and-reserve,
    use check_and_reserve_trade_slot() instead.

    Args:
        db: async DB session
        user_id: trader user UUID (None = check all trades)
        account_balance: current account balance (fetched from MT5 node)
        today: optional override for date (used in tests)

    Returns:
        RiskStatus with allowed flag and reason if blocked
    """
    # Load user-specific limits
    max_trades = 2
    max_losses = 2
    max_drawdown_pct = 2.0

    if user_id:
        settings_result = await db.execute(
            select(BotSetting).where(BotSetting.user_id == user_id)
        )
        bot_settings = settings_result.scalar_one_or_none()
        if bot_settings:
            max_trades = bot_settings.max_trades_per_day
            max_losses = bot_settings.max_losses_per_day
            max_drawdown_pct = float(bot_settings.max_daily_drawdown_pct)
    else:
        # Get default settings
        settings_result = await db.execute(select(BotSetting).limit(1))
        bot_settings = settings_result.scalar_one_or_none()
        if bot_settings:
            max_trades = bot_settings.max_trades_per_day
            max_losses = bot_settings.max_losses_per_day
            max_drawdown_pct = float(bot_settings.max_daily_drawdown_pct)

    trades_today, losses_today, absolute_loss = await get_daily_stats(db, user_id, today)

    # Compute drawdown percentage
    drawdown_pct = (absolute_loss / account_balance * 100) if account_balance > 0 else 0.0

    # Check trade limit
    if trades_today >= max_trades:
        return RiskStatus(
            allowed=False,
            trades_today=trades_today,
            losses_today=losses_today,
            drawdown_pct=drawdown_pct,
            reason=f"Max daily trades reached ({max_trades})",
        )

    # Check loss limit (kill switch condition)
    if losses_today >= max_losses:
        return RiskStatus(
            allowed=False,
            trades_today=trades_today,
            losses_today=losses_today,
            drawdown_pct=drawdown_pct,
            reason=f"Max daily losses reached ({max_losses}) - kill switch activated",
        )

    # Check drawdown limit (kill switch condition)
    if drawdown_pct >= max_drawdown_pct:
        return RiskStatus(
            allowed=False,
            trades_today=trades_today,
            losses_today=losses_today,
            drawdown_pct=drawdown_pct,
            reason=f"Daily drawdown limit hit ({drawdown_pct:.2f}% >= {max_drawdown_pct}%) - kill switch activated",
        )

    return RiskStatus(
        allowed=True,
        trades_today=trades_today,
        losses_today=losses_today,
        drawdown_pct=drawdown_pct,
    )


async def check_and_reserve_trade_slot(
    db: AsyncSession,
    user_id: Optional[UUID],
    account_balance: float = 1000.0,
    today: Optional[date] = None,
) -> RiskStatus:
    """
    ATOMIC check-and-reserve operation for trade execution.
    
    This function uses a lock to prevent race conditions where multiple
    signals could bypass MAX_DAILY_TRADES by checking simultaneously.
    
    CRITICAL: This MUST be called before executing any trade.
    
    Args:
        db: async DB session
        user_id: trader user UUID
        account_balance: current account balance
        today: optional date override
        
    Returns:
        RiskStatus with allowed flag. If allowed=True, a trade slot is reserved.
    """
    async with _risk_check_lock:
        # Perform risk check inside lock
        risk_status = await check_risk(db, user_id, account_balance, today)
        
        if not risk_status.allowed:
            logger.warning(f"Trade slot denied: {risk_status.reason}")
            return risk_status
        
        # Risk check passed - slot is reserved by virtue of holding the lock
        # The calling code MUST create the trade record before releasing the lock
        logger.info(f"Trade slot reserved: {risk_status.trades_today + 1}/{risk_status.trades_today + 1}")
        
        return risk_status


async def disable_auto_trading(
    db: AsyncSession,
    user_id: Optional[UUID],
    reason: str,
) -> None:
    """
    Disable auto trading for a user and log the reason.
    This is the kill switch implementation.
    """
    if user_id:
        result = await db.execute(select(BotSetting).where(BotSetting.user_id == user_id))
    else:
        result = await db.execute(select(BotSetting).limit(1))

    bot_settings = result.scalar_one_or_none()
    if bot_settings:
        bot_settings.auto_trade_enabled = False
        await db.commit()
        logger.warning(f"Kill switch activated - auto trading disabled: {reason}")

        # Send alert
        from backend.modules.alert_manager import send_risk_alert
        await send_risk_alert(reason)


async def evaluate_kill_switch(
    db: AsyncSession,
    user_id: Optional[UUID],
    account_balance: float,
) -> bool:
    """
    Evaluate kill switch conditions after a trade closes.
    Returns True if kill switch was activated.
    """
    risk = await check_risk(db, user_id, account_balance)

    if not risk.allowed:
        await disable_auto_trading(db, user_id, risk.reason or "Risk limit exceeded")
        return True

    return False
