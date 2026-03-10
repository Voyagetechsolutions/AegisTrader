"""
spread_filter.py
Validates spread against adaptive and hard-cap rules.

Rules (from PRD):
  1. current_spread ≤ average_spread × 2
  2. current_spread ≤ max_spread (hard cap, default 5 points)

Spread samples are stored in the DB to compute a rolling average.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import SpreadSample


@dataclass
class SpreadCheckResult:
    allowed: bool
    current_spread: float
    average_spread: Optional[float]
    hard_cap: float
    reason: Optional[str] = None


async def record_spread(
    db: AsyncSession,
    spread_points: float,
    symbol: str = "US30",
) -> None:
    """Persist a spread sample for rolling average calculation."""
    sample = SpreadSample(symbol=symbol, spread_points=spread_points)
    db.add(sample)
    await db.commit()


async def get_average_spread(
    db: AsyncSession,
    symbol: str = "US30",
    last_n: int = 100,
) -> Optional[float]:
    """
    Compute average spread from the last N samples for a symbol.
    Returns None if no samples exist.
    """
    # Subquery: get IDs of last N samples
    subq = (
        select(SpreadSample.id)
        .where(SpreadSample.symbol == symbol)
        .order_by(SpreadSample.sampled_at.desc())
        .limit(last_n)
        .subquery()
    )
    result = await db.execute(
        select(func.avg(SpreadSample.spread_points)).where(
            SpreadSample.id.in_(select(subq.c.id))
        )
    )
    avg = result.scalar()
    return float(avg) if avg is not None else None


async def check_spread(
    db: AsyncSession,
    current_spread: float,
    symbol: str = "US30",
    hard_cap: float = 5.0,
) -> SpreadCheckResult:
    """
    Validate spread against adaptive (avg×2) and hard-cap rules.
    Records the sample regardless of outcome.
    """
    await record_spread(db, current_spread, symbol)
    avg = await get_average_spread(db, symbol)

    # Hard cap check
    if current_spread > hard_cap:
        return SpreadCheckResult(
            allowed=False,
            current_spread=current_spread,
            average_spread=avg,
            hard_cap=hard_cap,
            reason=f"Spread {current_spread} exceeds hard cap {hard_cap}",
        )

    # Adaptive check (only when we have enough historical data)
    if avg is not None and current_spread > avg * 2:
        return SpreadCheckResult(
            allowed=False,
            current_spread=current_spread,
            average_spread=avg,
            hard_cap=hard_cap,
            reason=f"Spread {current_spread} exceeds 2× average ({avg:.2f})",
        )

    return SpreadCheckResult(
        allowed=True,
        current_spread=current_spread,
        average_spread=avg,
        hard_cap=hard_cap,
    )
