"""
paper_trade.py
Simulates trade outcomes for signals in analyze mode.

Paper trades track what would have happened if a signal was executed,
allowing performance analysis without risking real capital.

This module:
1. Creates paper trade records from signals
2. Updates paper trade status based on price movements
3. Calculates hypothetical P&L
"""

from __future__ import annotations
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

import pytz
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Signal, SignalGrade

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")


async def update_paper_trade_result(
    db: AsyncSession,
    signal: Signal,
    current_price: float,
) -> Optional[str]:
    """
    Update the paper trade result for a signal based on current price.

    Returns the result: "win" | "loss" | "open" | None (if not eligible)
    """
    if signal.paper_result and signal.paper_result != "open":
        # Already resolved
        return signal.paper_result

    entry = float(signal.entry_price)
    sl = float(signal.stop_loss)
    tp1 = float(signal.tp1)
    tp2 = float(signal.tp2)

    is_long = signal.direction.value == "long"

    # Check if SL hit
    if is_long:
        sl_hit = current_price <= sl
        tp1_hit = current_price >= tp1
        tp2_hit = current_price >= tp2
    else:
        sl_hit = current_price >= sl
        tp1_hit = current_price <= tp1
        tp2_hit = current_price <= tp2

    if sl_hit:
        signal.paper_result = "loss"
        await db.commit()
        logger.info(f"Paper trade {signal.id}: LOSS (SL hit at {current_price})")
        return "loss"

    if tp1_hit:
        # For paper trades, we consider TP1 hit as a win
        # In reality, TP2 and runner would continue
        signal.paper_result = "win"
        await db.commit()
        logger.info(f"Paper trade {signal.id}: WIN (TP1 hit at {current_price})")
        return "win"

    # Still open
    if signal.paper_result != "open":
        signal.paper_result = "open"
        await db.commit()

    return "open"


async def initialize_paper_trade(
    db: AsyncSession,
    signal: Signal,
) -> bool:
    """
    Initialize a signal for paper trade tracking.
    Called when a signal is created in analyze mode.
    """
    if signal.paper_result:
        return False

    signal.paper_result = "open"
    await db.commit()
    logger.info(f"Paper trade initialized for signal {signal.id}")
    return True


async def get_paper_trade_stats(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    grade_filter: Optional[str] = None,
) -> dict:
    """
    Calculate paper trade performance statistics.

    Returns:
    {
        "total": 100,
        "wins": 65,
        "losses": 25,
        "open": 10,
        "win_rate": 72.2,
        "by_grade": {
            "A+": {"total": 50, "wins": 40, "losses": 8, "win_rate": 83.3},
            "A": {"total": 50, "wins": 25, "losses": 17, "win_rate": 59.5}
        },
        "by_session": {...},
        "by_setup_type": {...}
    }
    """
    # Build base query
    filters = [Signal.paper_result.isnot(None)]
    if user_id:
        filters.append(Signal.user_id == user_id)

    result = await db.execute(
        select(Signal).where(and_(*filters))
    )
    signals = result.scalars().all()

    total = len(signals)
    wins = sum(1 for s in signals if s.paper_result == "win")
    losses = sum(1 for s in signals if s.paper_result == "loss")
    open_trades = sum(1 for s in signals if s.paper_result == "open")

    resolved = wins + losses
    win_rate = (wins / resolved * 100) if resolved > 0 else 0.0

    # By grade breakdown
    by_grade = {}
    for grade in [SignalGrade.A_PLUS, SignalGrade.A, SignalGrade.B]:
        grade_signals = [s for s in signals if s.grade == grade]
        g_total = len(grade_signals)
        g_wins = sum(1 for s in grade_signals if s.paper_result == "win")
        g_losses = sum(1 for s in grade_signals if s.paper_result == "loss")
        g_resolved = g_wins + g_losses
        by_grade[grade.value] = {
            "total": g_total,
            "wins": g_wins,
            "losses": g_losses,
            "win_rate": (g_wins / g_resolved * 100) if g_resolved > 0 else 0.0,
        }

    # By session breakdown
    by_session = {}
    sessions = set(s.session_name for s in signals if s.session_name)
    for session in sessions:
        session_signals = [s for s in signals if s.session_name == session]
        s_total = len(session_signals)
        s_wins = sum(1 for s in session_signals if s.paper_result == "win")
        s_losses = sum(1 for s in session_signals if s.paper_result == "loss")
        s_resolved = s_wins + s_losses
        by_session[session] = {
            "total": s_total,
            "wins": s_wins,
            "losses": s_losses,
            "win_rate": (s_wins / s_resolved * 100) if s_resolved > 0 else 0.0,
        }

    # By setup type breakdown
    by_setup_type = {}
    setup_types = set(s.setup_type.value for s in signals if s.setup_type)
    for setup in setup_types:
        setup_signals = [s for s in signals if s.setup_type and s.setup_type.value == setup]
        st_total = len(setup_signals)
        st_wins = sum(1 for s in setup_signals if s.paper_result == "win")
        st_losses = sum(1 for s in setup_signals if s.paper_result == "loss")
        st_resolved = st_wins + st_losses
        by_setup_type[setup] = {
            "total": st_total,
            "wins": st_wins,
            "losses": st_losses,
            "win_rate": (st_wins / st_resolved * 100) if st_resolved > 0 else 0.0,
        }

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "open": open_trades,
        "win_rate": round(win_rate, 1),
        "by_grade": by_grade,
        "by_session": by_session,
        "by_setup_type": by_setup_type,
    }


async def batch_update_paper_trades(
    db: AsyncSession,
    current_price: float,
    symbol: str = "US30",
) -> dict:
    """
    Update all open paper trades with the current price.
    Called periodically or when price data is received.

    Returns summary of updates.
    """
    result = await db.execute(
        select(Signal).where(
            and_(
                Signal.paper_result == "open",
                Signal.execution_symbol == symbol,
            )
        )
    )
    signals = result.scalars().all()

    updated = {"wins": 0, "losses": 0, "still_open": 0}

    for signal in signals:
        outcome = await update_paper_trade_result(db, signal, current_price)
        if outcome == "win":
            updated["wins"] += 1
        elif outcome == "loss":
            updated["losses"] += 1
        else:
            updated["still_open"] += 1

    logger.info(f"Paper trade batch update: {updated}")
    return updated
