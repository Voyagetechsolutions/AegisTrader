"""
trade_manager.py
Constructs, executes, and manages trade lifecycle via the MT5 bridge.

Trade lifecycle (per spec):
  IDLE → SIGNAL_RECEIVED → VALIDATING → SCORED → ALERT_SENT
  → EXECUTION_PENDING → EXECUTED → TP1_HIT → BREAKEVEN_ACTIVE
  → TP2_HIT → RUNNER_ACTIVE → CLOSED → LOGGED

Trade management (from PRD):
  TP1: close 50% → move SL to BE
  TP2: close 40%
  Runner: remaining 10% with trailing stop on 5M structure
"""

from __future__ import annotations
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    Signal, Trade, TradeLog, BotSetting, LotMode,
    TradeStatus, TradeCloseReason, TradeState, SignalDirection,
)
from backend.schemas.schemas import MT5OrderRequest, MT5OrderResponse
from backend.modules import alert_manager

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")

# Trade management ratios per spec
TP1_RATIO = 0.50   # Close 50% at TP1
TP2_RATIO = 0.40   # Close 40% at TP2
RUNNER_RATIO = 0.10  # Leave 10% as runner


# ---------------------------------------------------------------------------
# State Machine Transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS = {
    TradeState.IDLE: [TradeState.SIGNAL_RECEIVED],
    TradeState.SIGNAL_RECEIVED: [TradeState.VALIDATING],
    TradeState.VALIDATING: [TradeState.SCORED, TradeState.REJECTED],
    TradeState.SCORED: [TradeState.ALERT_SENT],
    TradeState.ALERT_SENT: [TradeState.EXECUTION_PENDING, TradeState.CLOSED],
    TradeState.EXECUTION_PENDING: [TradeState.EXECUTED, TradeState.EXECUTION_FAILED],
    TradeState.EXECUTED: [TradeState.TP1_HIT, TradeState.STOPPED_OUT, TradeState.CLOSED],
    TradeState.TP1_HIT: [TradeState.BREAKEVEN_ACTIVE],
    TradeState.BREAKEVEN_ACTIVE: [TradeState.TP2_HIT, TradeState.STOPPED_OUT, TradeState.CLOSED],
    TradeState.TP2_HIT: [TradeState.RUNNER_ACTIVE],
    TradeState.RUNNER_ACTIVE: [TradeState.CLOSED, TradeState.STOPPED_OUT],
    TradeState.CLOSED: [TradeState.LOGGED],
}


def transition_state(trade: Trade, new_state: TradeState) -> bool:
    """
    Transition trade to a new state if valid.
    Returns True if transition was successful.
    """
    current = trade.state
    if current is None:
        trade.state = new_state
        return True

    valid_next = VALID_TRANSITIONS.get(current, [])
    if new_state in valid_next:
        trade.state = new_state
        return True

    logger.warning(f"Invalid state transition: {current} -> {new_state}")
    return False


async def log_trade_event(
    db: AsyncSession,
    trade: Trade,
    event_type: str,
    message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> TradeLog:
    """Create a trade log entry."""
    log = TradeLog(
        trade_id=trade.id,
        event_type=event_type,
        message=message,
        payload=payload,
    )
    db.add(log)
    return log


# ---------------------------------------------------------------------------
# Lot Size Calculation
# ---------------------------------------------------------------------------

def calculate_lot_size(
    settings: BotSetting,
    account_balance: float,
    stop_loss_points: float,
    min_lot: float = 0.01,
) -> float:
    """
    Calculate lot size based on settings.

    Per spec:
    - minimum_lot: Always use broker minimum (default 0.01)
    - fixed_lot: Use the configured fixed lot
    - risk_percent: Calculate based on risk % of account
    """
    if settings.lot_mode == LotMode.MINIMUM_LOT:
        return min_lot

    if settings.lot_mode == LotMode.FIXED_LOT and settings.fixed_lot:
        return float(settings.fixed_lot)

    if settings.lot_mode == LotMode.RISK_PERCENT and settings.risk_percent:
        risk_pct = float(settings.risk_percent) / 100.0
        risk_amount = account_balance * risk_pct
        # For US30: approximately $1 per point per 0.01 lot
        # Calculate lots needed for the SL distance
        if stop_loss_points > 0:
            lot_size = risk_amount / (stop_loss_points * 100)
            return max(round(lot_size, 2), min_lot)

    return min_lot


# ---------------------------------------------------------------------------
# Trade Opening
# ---------------------------------------------------------------------------

async def open_trade(
    db: AsyncSession,
    signal: Signal,
    user_id: Optional[UUID],
    mt5_bridge,
    account_balance: float = 1000.0,
    account_type: str = "demo",
) -> Optional[Trade]:
    """
    Place a trade via the MT5 bridge for a given signal.
    Persists the Trade record regardless of MT5 response.
    """
    # Get settings for lot calculation
    settings = None
    lot_size = 0.01  # Default minimum

    if user_id:
        result = await db.execute(select(BotSetting).where(BotSetting.user_id == user_id))
        settings = result.scalar_one_or_none()
    else:
        result = await db.execute(select(BotSetting).limit(1))
        settings = result.scalar_one_or_none()

    if settings:
        stop_loss_points = abs(float(signal.entry_price) - float(signal.stop_loss))
        lot_size = calculate_lot_size(settings, account_balance, stop_loss_points)

    direction = signal.direction.value if hasattr(signal.direction, "value") else str(signal.direction)
    mt5_direction = "buy" if direction == "long" else "sell"

    order_req = MT5OrderRequest(
        symbol=signal.execution_symbol,
        direction=mt5_direction,
        lot_size=lot_size,
        entry_price=float(signal.entry_price),
        sl_price=float(signal.stop_loss),
        tp1_price=float(signal.tp1),
        tp2_price=float(signal.tp2),
        signal_id=str(signal.id),
    )

    # Create trade record in pending state
    trade = Trade(
        user_id=user_id,
        signal_id=signal.id,
        account_type=account_type,
        symbol=signal.execution_symbol,
        direction=signal.direction,
        lot_size=lot_size,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        tp1=signal.tp1,
        tp2=signal.tp2,
        status=TradeStatus.PENDING,
        state=TradeState.EXECUTION_PENDING,
    )
    db.add(trade)
    await db.flush()

    await log_trade_event(db, trade, "execution_pending", "Sending order to MT5", {
        "order_request": order_req.model_dump(),
    })

    # Call MT5 execution node
    mt5_resp: MT5OrderResponse = await mt5_bridge.place_order(order_req)

    if mt5_resp.success:
        trade.mt5_ticket = mt5_resp.ticket
        trade.actual_entry_price = mt5_resp.actual_price
        trade.slippage = mt5_resp.slippage
        trade.status = TradeStatus.OPEN
        trade.opened_at = datetime.now(pytz.UTC)
        transition_state(trade, TradeState.EXECUTED)

        await log_trade_event(db, trade, "executed", "Order filled successfully", {
            "ticket": mt5_resp.ticket,
            "fill_price": mt5_resp.actual_price,
            "slippage": mt5_resp.slippage,
        })
    else:
        trade.status = TradeStatus.FAILED
        transition_state(trade, TradeState.EXECUTION_FAILED)

        await log_trade_event(db, trade, "execution_failed", f"Order failed: {mt5_resp.error}", {
            "error": mt5_resp.error,
        })
        logger.error(f"MT5 order failed: {mt5_resp.error}")

    await db.commit()

    if mt5_resp.success:
        await alert_manager.send_trade_open_alert(trade)

    return trade if mt5_resp.success else None


# ---------------------------------------------------------------------------
# TP1 Handling
# ---------------------------------------------------------------------------

async def handle_tp1(
    db: AsyncSession,
    trade: Trade,
    mt5_bridge,
) -> bool:
    """
    Process TP1 hit:
    - Close 50% of position
    - Move SL to break even
    - Enable aggressive trailing
    """
    if trade.tp1_hit:
        return False

    close_lots = round(float(trade.lot_size) * TP1_RATIO, 2)

    # Partial close via MT5
    close_ok = await mt5_bridge.close_partial(trade.mt5_ticket, close_lots, trade.symbol)

    if close_ok:
        trade.tp1_hit = True
        transition_state(trade, TradeState.TP1_HIT)

        # Move SL to entry (break even)
        be_price = float(trade.actual_entry_price or trade.entry_price)
        await mt5_bridge.modify_sl(trade.mt5_ticket, be_price)

        trade.breakeven_active = True
        trade.trailing_active = True
        trade.status = TradeStatus.PARTIAL
        transition_state(trade, TradeState.BREAKEVEN_ACTIVE)

        await log_trade_event(db, trade, "tp1_hit", "TP1 hit - 50% closed, SL moved to BE", {
            "lots_closed": close_lots,
            "be_price": be_price,
        })

        await db.commit()
        await alert_manager.send_tp1_alert(trade)
        return True

    return False


# ---------------------------------------------------------------------------
# TP2 Handling
# ---------------------------------------------------------------------------

async def handle_tp2(
    db: AsyncSession,
    trade: Trade,
    mt5_bridge,
) -> bool:
    """
    Process TP2 hit:
    - Close 40% of position
    - Leave 10% as runner
    - Continue trailing via 5M structure
    """
    if not trade.tp1_hit or trade.tp2_hit:
        return False

    close_lots = round(float(trade.lot_size) * TP2_RATIO, 2)
    close_ok = await mt5_bridge.close_partial(trade.mt5_ticket, close_lots, trade.symbol)

    if close_ok:
        trade.tp2_hit = True
        trade.runner_active = True
        transition_state(trade, TradeState.TP2_HIT)
        transition_state(trade, TradeState.RUNNER_ACTIVE)

        await log_trade_event(db, trade, "tp2_hit", "TP2 hit - 40% closed, runner active", {
            "lots_closed": close_lots,
            "runner_lots": round(float(trade.lot_size) * RUNNER_RATIO, 2),
        })

        await db.commit()
        await alert_manager.send_tp2_alert(trade)
        return True

    return False


# ---------------------------------------------------------------------------
# Stop Loss Handling
# ---------------------------------------------------------------------------

async def handle_stop_loss(
    db: AsyncSession,
    trade: Trade,
    pnl: float = 0.0,
) -> bool:
    """
    Handle stop loss hit.
    - Close full position
    - Increment daily loss count
    - Check kill switch
    """
    trade.status = TradeStatus.CLOSED
    trade.pnl = pnl
    trade.close_reason = TradeCloseReason.STOP_LOSS
    trade.closed_at = datetime.now(pytz.UTC)
    trade.runner_active = False
    transition_state(trade, TradeState.STOPPED_OUT)
    transition_state(trade, TradeState.CLOSED)

    await log_trade_event(db, trade, "stopped_out", "Stop loss hit", {
        "pnl": pnl,
    })

    await db.commit()
    await alert_manager.send_trade_close_alert(trade)
    return True


# ---------------------------------------------------------------------------
# Trade Closing
# ---------------------------------------------------------------------------

async def close_trade(
    db: AsyncSession,
    trade: Trade,
    mt5_bridge,
    reason: TradeCloseReason,
    pnl: float = 0.0,
) -> bool:
    """Fully close a trade and mark it in the DB."""
    # Calculate remaining lots based on what's been closed
    if trade.tp2_hit:
        remaining_lots = round(float(trade.lot_size) * RUNNER_RATIO, 2)
    elif trade.tp1_hit:
        remaining_lots = round(float(trade.lot_size) * (TP2_RATIO + RUNNER_RATIO), 2)
    else:
        remaining_lots = float(trade.lot_size)

    close_ok = await mt5_bridge.close_partial(trade.mt5_ticket, remaining_lots, trade.symbol)

    if close_ok:
        trade.status = TradeStatus.CLOSED
        trade.pnl = pnl
        trade.close_reason = reason
        trade.closed_at = datetime.now(pytz.UTC)
        trade.runner_active = False
        transition_state(trade, TradeState.CLOSED)

        await log_trade_event(db, trade, "trade_closed", f"Trade closed: {reason.value}", {
            "reason": reason.value,
            "pnl": pnl,
            "lots_closed": remaining_lots,
        })

        await db.commit()
        await alert_manager.send_trade_close_alert(trade)
        return True

    return False


# ---------------------------------------------------------------------------
# Close All Trades
# ---------------------------------------------------------------------------

async def close_all_trades(
    db: AsyncSession,
    user_id: Optional[UUID],
    mt5_bridge,
    reason: TradeCloseReason = TradeCloseReason.MANUAL,
) -> int:
    """Close all open trades for a user. Returns count closed."""
    query = select(Trade).where(
        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIAL]),
    )
    if user_id:
        query = query.where(Trade.user_id == user_id)

    result = await db.execute(query)
    trades = result.scalars().all()

    closed = 0
    for trade in trades:
        success = await close_trade(db, trade, mt5_bridge, reason)
        if success:
            closed += 1

    return closed


# ---------------------------------------------------------------------------
# Execution Callback Handler
# ---------------------------------------------------------------------------

async def handle_execution_callback(
    db: AsyncSession,
    trade_id: str,
    status: str,
    broker_order_id: Optional[str] = None,
    fill_price: Optional[float] = None,
    slippage_points: Optional[float] = None,
    message: Optional[str] = None,
) -> Optional[Trade]:
    """
    Handle callback from MT5 execution node.
    Updates trade with execution results.
    """
    from uuid import UUID as UUIDType

    try:
        trade_uuid = UUIDType(trade_id)
    except ValueError:
        logger.error(f"Invalid trade_id format: {trade_id}")
        return None

    result = await db.execute(select(Trade).where(Trade.id == trade_uuid))
    trade = result.scalar_one_or_none()

    if not trade:
        logger.error(f"Trade not found for callback: {trade_id}")
        return None

    if status == "executed":
        trade.status = TradeStatus.OPEN
        trade.opened_at = datetime.now(pytz.UTC)
        if broker_order_id:
            trade.mt5_ticket = int(broker_order_id)
        if fill_price:
            trade.actual_entry_price = fill_price
        if slippage_points:
            trade.slippage = slippage_points
        transition_state(trade, TradeState.EXECUTED)

        await log_trade_event(db, trade, "execution_callback", message or "Order executed", {
            "broker_order_id": broker_order_id,
            "fill_price": fill_price,
            "slippage_points": slippage_points,
        })

    elif status in ("failed", "rejected"):
        trade.status = TradeStatus.FAILED if status == "failed" else TradeStatus.REJECTED
        transition_state(trade, TradeState.EXECUTION_FAILED if status == "failed" else TradeState.REJECTED)

        await log_trade_event(db, trade, f"execution_{status}", message or f"Order {status}", {
            "error": message,
        })

    await db.commit()
    return trade
