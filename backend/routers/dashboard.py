"""
dashboard.py
REST API endpoints for the mobile-first dashboard.

Provides:
- Status (bot mode, risk status, open positions)
- Signals list
- Trades list
- Settings management
- Mode switching
- Weekly overview

Per spec: GET /dashboard/status
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.models import (
    Signal, Trade, BotSetting, BotMode, LotMode, TradeStatus,
    WeeklyReport,
)
from backend.schemas.schemas import (
    SignalOut, TradeOut, BotSettingOut, BotSettingUpdate, DashboardStatus,
    WeeklyOverviewOut,
)
from backend.modules.risk_engine import get_daily_stats
from backend.modules.news_filter import check_news_blackout
from backend.modules.session_filter import get_active_session
from backend.routers.mt5_bridge import mt5_bridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

SAST = pytz.timezone("Africa/Johannesburg")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_settings(bot_settings: Optional[BotSetting]) -> BotSetting:
    if not bot_settings:
        raise HTTPException(
            status_code=404,
            detail="Bot settings not found. Create a user first."
        )
    return bot_settings


async def _get_default_settings(db: AsyncSession) -> Optional[BotSetting]:
    result = await db.execute(select(BotSetting).limit(1))
    return result.scalar_one_or_none()


async def _check_connection_health() -> dict[str, bool]:
    """Check health of external connections."""
    health = {
        "database": True,  # If we got here, DB is working
        "telegram": False,
        "mt5_node": False,
    }

    # Check MT5 node via heartbeat
    try:
        from backend.routers.mt5_heartbeat import last_heartbeat
        from datetime import datetime
        
        if last_heartbeat is not None:
            seconds_since = (datetime.utcnow() - last_heartbeat).total_seconds()
            health["mt5_node"] = seconds_since < 60  # Connected if heartbeat within 60s
        else:
            health["mt5_node"] = False
    except Exception as e:
        logger.error(f"Error checking MT5 health: {e}")
        health["mt5_node"] = False

    # Telegram check would require a test message - skip for now
    from backend.config import settings
    health["telegram"] = bool(settings.telegram_bot_token and settings.telegram_chat_id)

    return health


# ---------------------------------------------------------------------------
# Status (per spec)
# ---------------------------------------------------------------------------

@router.get("/status", response_model=DashboardStatus, summary="Get live bot status")
async def get_status(db: AsyncSession = Depends(get_db)):
    """
    Returns current bot status per spec:
    - current mode
    - bot status
    - open positions
    - daily stats
    - connection health
    """
    bot_settings = await _get_default_settings(db)
    _require_settings(bot_settings)

    user_id = bot_settings.user_id
    account_balance = await mt5_bridge.get_account_balance()

    # Risk stats
    trades_today, losses_today, abs_loss = await get_daily_stats(db, user_id)
    drawdown_pct = (abs_loss / account_balance * 100) if account_balance else 0.0

    max_trades = int(bot_settings.max_trades_per_day)
    max_losses = int(bot_settings.max_losses_per_day)
    max_drawdown = float(bot_settings.max_daily_drawdown_pct)

    risk_hit = (
        trades_today >= max_trades
        or losses_today >= max_losses
        or drawdown_pct >= max_drawdown
    )

    # News blackout
    news_result = await check_news_blackout(db)

    # Active session
    active_session = get_active_session(bot_settings.sessions)

    # Open positions count
    pos_result = await db.execute(
        select(func.count(Trade.id)).where(
            Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIAL]),
        )
    )
    open_positions = pos_result.scalar() or 0

    # Connection health
    connection_health = await _check_connection_health()

    return DashboardStatus(
        mode=bot_settings.mode.value,
        auto_trade_enabled=bot_settings.auto_trade_enabled,
        trades_today=trades_today,
        losses_today=losses_today,
        drawdown_today_pct=round(drawdown_pct, 2),
        risk_limit_hit=risk_hit,
        news_blackout_active=news_result.blocked,
        active_session=active_session,
        open_positions=open_positions,
        account_balance=account_balance,
        connection_health=connection_health,
    )


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@router.get("/signals", summary="List recent signals")
async def list_signals(
    limit: int = Query(default=20, le=100),
    grade: Optional[str] = Query(default=None, description="Filter by grade: A+, A, B"),
    db: AsyncSession = Depends(get_db),
):
    """List recent signals with optional grade filter."""
    query = select(Signal).order_by(desc(Signal.created_at)).limit(limit)

    if grade:
        from backend.models.models import SignalGrade
        grade_map = {"A+": SignalGrade.A_PLUS, "A": SignalGrade.A, "B": SignalGrade.B}
        if grade in grade_map:
            query = query.where(Signal.grade == grade_map[grade])

    result = await db.execute(query)
    signals = result.scalars().all()

    # Convert to response format
    return [
        {
            "id": str(s.id),
            "source": s.source,
            "setup_type": s.setup_type.value if s.setup_type else None,
            "direction": s.direction.value if s.direction else None,
            "analysis_symbol": s.analysis_symbol,
            "execution_symbol": s.execution_symbol,
            "entry_price": float(s.entry_price),
            "stop_loss": float(s.stop_loss),
            "tp1": float(s.tp1),
            "tp2": float(s.tp2),
            "score": s.score,
            "grade": s.grade.value if s.grade else None,
            "eligible_for_auto_trade": s.eligible_for_auto_trade,
            "session_name": s.session_name,
            "news_blocked": s.news_blocked,
            "paper_result": s.paper_result,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

@router.get("/trades", summary="List recent trades")
async def list_trades(
    limit: int = Query(default=20, le=100),
    status_filter: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List recent trades with optional status filter."""
    query = select(Trade).order_by(desc(Trade.created_at)).limit(limit)

    if status_filter:
        try:
            query = query.where(Trade.status == TradeStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    result = await db.execute(query)
    trades = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "broker": t.broker,
            "account_type": t.account_type,
            "mt5_ticket": t.mt5_ticket,
            "symbol": t.symbol,
            "direction": t.direction.value if t.direction else None,
            "lot_size": float(t.lot_size),
            "entry_price": float(t.entry_price),
            "stop_loss": float(t.stop_loss),
            "tp1": float(t.tp1),
            "tp2": float(t.tp2),
            "actual_entry_price": float(t.actual_entry_price) if t.actual_entry_price else None,
            "status": t.status.value if t.status else None,
            "state": t.state.value if t.state else None,
            "tp1_hit": t.tp1_hit,
            "tp2_hit": t.tp2_hit,
            "runner_active": t.runner_active,
            "breakeven_active": t.breakeven_active,
            "pnl": float(t.pnl) if t.pnl else None,
            "close_reason": t.close_reason.value if t.close_reason else None,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


@router.get("/positions", summary="Get live MT5 open positions")
async def get_live_positions():
    """Fetch real-time open positions directly from the MT5 node."""
    positions = await mt5_bridge.get_positions()
    return [p.model_dump() for p in positions]


@router.post("/closeall", summary="Close all open positions")
async def close_all(db: AsyncSession = Depends(get_db)):
    """Emergency close all open trades."""
    from backend.modules.trade_manager import close_all_trades
    from backend.models.models import TradeCloseReason

    bot_settings = await _get_default_settings(db)
    _require_settings(bot_settings)

    closed = await close_all_trades(
        db,
        bot_settings.user_id,
        mt5_bridge,
        TradeCloseReason.FORCE_CLOSED
    )
    return {"ok": True, "closed": closed}


# ---------------------------------------------------------------------------
# Settings (per spec: POST /settings/update)
# ---------------------------------------------------------------------------

@router.get("/settings", response_model=BotSettingOut, summary="Get bot settings")
async def get_settings_route(db: AsyncSession = Depends(get_db)):
    """Get current bot settings."""
    bot_settings = await _get_default_settings(db)
    settings = _require_settings(bot_settings)

    return BotSettingOut(
        analysis_symbol=settings.analysis_symbol,
        execution_symbol=settings.execution_symbol,
        mode=settings.mode.value,
        auto_trade_enabled=settings.auto_trade_enabled,
        sessions=settings.sessions,
        spread_max_points=float(settings.spread_max_points),
        spread_multiplier=float(settings.spread_multiplier),
        news_block_standard_mins=settings.news_block_standard_mins,
        news_block_major_mins=settings.news_block_major_mins,
        max_trades_per_day=settings.max_trades_per_day,
        max_losses_per_day=settings.max_losses_per_day,
        max_daily_drawdown_pct=float(settings.max_daily_drawdown_pct),
        lot_mode=settings.lot_mode.value,
        fixed_lot=float(settings.fixed_lot) if settings.fixed_lot else None,
        risk_percent=float(settings.risk_percent) if settings.risk_percent else None,
        max_slippage_points=float(settings.max_slippage_points),
        swing_alert_only=settings.swing_alert_only,
        use_one_minute_refinement=settings.use_one_minute_refinement,
    )


@router.post("/settings/update", response_model=BotSettingOut, summary="Update bot settings")
async def update_settings(
    updates: BotSettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update bot settings per spec.

    Updatable fields:
    - sessions
    - lot mode
    - symbol mapping
    - auto trade on/off
    - spread threshold
    - risk rules
    """
    bot_settings = await _get_default_settings(db)
    _require_settings(bot_settings)

    for field, value in updates.model_dump(exclude_none=True).items():
        if field == "mode":
            try:
                setattr(bot_settings, field, BotMode(value))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid mode: {value}")
        elif field == "lot_mode":
            try:
                setattr(bot_settings, field, LotMode(value))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid lot_mode: {value}")
        else:
            setattr(bot_settings, field, value)

    await db.commit()
    await db.refresh(bot_settings)

    return BotSettingOut(
        analysis_symbol=bot_settings.analysis_symbol,
        execution_symbol=bot_settings.execution_symbol,
        mode=bot_settings.mode.value,
        auto_trade_enabled=bot_settings.auto_trade_enabled,
        sessions=bot_settings.sessions,
        spread_max_points=float(bot_settings.spread_max_points),
        spread_multiplier=float(bot_settings.spread_multiplier),
        news_block_standard_mins=bot_settings.news_block_standard_mins,
        news_block_major_mins=bot_settings.news_block_major_mins,
        max_trades_per_day=bot_settings.max_trades_per_day,
        max_losses_per_day=bot_settings.max_losses_per_day,
        max_daily_drawdown_pct=float(bot_settings.max_daily_drawdown_pct),
        lot_mode=bot_settings.lot_mode.value,
        fixed_lot=float(bot_settings.fixed_lot) if bot_settings.fixed_lot else None,
        risk_percent=float(bot_settings.risk_percent) if bot_settings.risk_percent else None,
        max_slippage_points=float(bot_settings.max_slippage_points),
        swing_alert_only=bot_settings.swing_alert_only,
        use_one_minute_refinement=bot_settings.use_one_minute_refinement,
    )


# Keep backward compatibility
@router.patch("/settings", response_model=BotSettingOut, summary="Update bot settings (legacy)")
async def update_settings_legacy(
    updates: BotSettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Legacy PATCH endpoint - redirects to POST /settings/update."""
    return await update_settings(updates, db)


@router.post("/mode/{mode}", summary="Switch bot mode")
async def switch_mode(mode: str, db: AsyncSession = Depends(get_db)):
    """Quick mode switch: analyze | trade | swing"""
    try:
        new_mode = BotMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Valid: analyze, trade, swing"
        )

    bot_settings = await _get_default_settings(db)
    _require_settings(bot_settings)

    bot_settings.mode = new_mode
    await db.commit()

    return {
        "ok": True,
        "mode": new_mode.value,
        "message": f"Bot switched to {new_mode.value} mode"
    }


# ---------------------------------------------------------------------------
# Weekly Overview
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=WeeklyOverviewOut, summary="Get latest weekly overview")
async def get_weekly_overview(db: AsyncSession = Depends(get_db)):
    """Get the latest weekly market overview."""
    result = await db.execute(
        select(WeeklyReport).order_by(desc(WeeklyReport.created_at)).limit(1)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No weekly overview generated yet. Run /overview command."
        )

    return WeeklyOverviewOut(
        weekly_bias=report.weekly_bias,
        daily_bias=report.daily_bias,
        h4_bias=report.h4_bias,
        h1_bias=report.h1_bias,
        m15_bias=report.m15_bias,
        m5_bias=report.m5_bias,
        m1_bias=report.m1_bias,
        bullish_scenario=report.bullish_scenario,
        bearish_scenario=report.bearish_scenario,
        key_levels=report.key_levels,
        major_news=report.news_summary,
    )


# ---------------------------------------------------------------------------
# Paper Trades & Reports
# ---------------------------------------------------------------------------

@router.get("/paper-trades/stats", summary="Get paper trade statistics")
async def get_paper_trade_stats(db: AsyncSession = Depends(get_db)):
    """
    Get performance statistics for paper trades.

    Returns breakdown by:
    - Overall win rate
    - By grade (A+, A, B)
    - By session (london, new_york, power_hour)
    - By setup type (continuation, swing)
    """
    from backend.modules.paper_trade import get_paper_trade_stats

    stats = await get_paper_trade_stats(db)
    return stats


@router.post("/paper-trades/update", summary="Update paper trade results")
async def update_paper_trades(
    current_price: float,
    symbol: str = "US30",
    db: AsyncSession = Depends(get_db),
):
    """
    Update all open paper trades with the current price.
    Call this when you have new price data to check if any paper trades
    have hit TP or SL.
    """
    from backend.modules.paper_trade import batch_update_paper_trades

    result = await batch_update_paper_trades(db, current_price, symbol)
    return {"ok": True, "updated": result}


@router.get("/reports/performance", summary="Get performance report")
async def get_performance_report(
    days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trading performance report for the specified period.

    Includes:
    - Win rate
    - Expectancy
    - Max drawdown
    - Average R:R
    - Breakdown by session and setup type
    """
    from backend.modules.analytics_engine import compute_strategy_stats

    stats = await compute_strategy_stats(db, period_days=days)

    return {
        "period_days": days,
        "trades_count": stats.trades_count,
        "win_rate": float(stats.win_rate) if stats.win_rate else 0,
        "avg_rr": float(stats.avg_rr) if stats.avg_rr else 0,
        "expectancy": float(stats.expectancy) if stats.expectancy else 0,
        "max_drawdown": float(stats.max_drawdown) if stats.max_drawdown else 0,
    }


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/health", summary="Health check endpoint")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check health of all system components."""
    health = await _check_connection_health()
    all_healthy = all(health.values())

    return {
        "ok": all_healthy,
        "components": health,
        "timestamp": datetime.now(pytz.UTC).isoformat(),
    }



# ---------------------------------------------------------------------------
# Emergency Stop
# ---------------------------------------------------------------------------

@router.post("/emergency-stop", summary="Activate emergency stop")
async def activate_emergency_stop_endpoint(
    reason: str,
    close_positions: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    🚨 EMERGENCY STOP - Immediately halt all trading.
    
    Args:
        reason: Reason for emergency stop
        close_positions: If true, close all open positions
    """
    from backend.modules.emergency_stop import activate_emergency_stop
    
    result = await activate_emergency_stop(
        db,
        reason=reason,
        close_positions=close_positions,
        mt5_bridge=mt5_bridge,
    )
    
    return result


@router.post("/emergency-stop/deactivate", summary="Deactivate emergency stop")
async def deactivate_emergency_stop_endpoint(
    authorized_by: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate emergency stop - allow trading to resume.
    
    Note: Auto-trading will remain disabled and must be manually re-enabled.
    """
    from backend.modules.emergency_stop import deactivate_emergency_stop
    
    result = await deactivate_emergency_stop(db, authorized_by=authorized_by)
    
    return result


@router.get("/emergency-stop/status", summary="Get emergency stop status")
async def get_emergency_stop_status_endpoint():
    """Get current emergency stop status."""
    from backend.modules.emergency_stop import get_emergency_stop_status
    
    return get_emergency_stop_status()
