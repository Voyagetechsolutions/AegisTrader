"""
signal_engine.py
Orchestrates the full inbound signal pipeline:
  1. Check idempotency (prevent duplicate signals)
  2. Validate webhook payload
  3. Check session window
  4. Validate spread
  5. Check news blackout
  6. Score confluence and classify setup
  7. Persist signal to DB
  8. Dispatch action (alert / execute / ignore)
"""

from __future__ import annotations
import hashlib
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    Signal, BotSetting, BotMode, SignalDirection, SignalGrade, SetupType,
)
from backend.schemas.schemas import TradingViewWebhookPayload
from backend.modules.confluence_scoring import score_from_payload, ConfluenceResult
from backend.modules.session_filter import get_active_session
from backend.modules.spread_filter import check_spread
from backend.modules.news_filter import check_news_blackout
from backend.modules.risk_engine import check_risk, disable_auto_trading

logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")


class SignalPipelineResult:
    """Result of the signal processing pipeline."""

    def __init__(
        self,
        signal: Optional[Signal],
        action: str,  # "executed" | "alerted" | "ignored" | "blocked" | "duplicate"
        reason: Optional[str] = None,
        score_result: Optional[ConfluenceResult] = None,
    ):
        self.signal = signal
        self.action = action
        self.reason = reason
        self.score_result = score_result

    def __repr__(self):
        return f"<SignalPipelineResult action={self.action} reason={self.reason}>"


def generate_idempotency_key(payload: TradingViewWebhookPayload) -> str:
    """
    Generate a unique key for the signal to prevent duplicates.

    Uses: symbol + direction + entry + sl + tp1 + tp2 + 5-minute time bucket
    """
    now = datetime.now(pytz.UTC)
    # Round to 5-minute bucket to catch rapid duplicate alerts
    time_bucket = now.replace(second=0, microsecond=0)
    time_bucket = time_bucket.replace(minute=(time_bucket.minute // 5) * 5)

    key_parts = [
        payload.symbol,
        payload.direction,
        f"{payload.entry:.2f}",
        f"{payload.stop_loss:.2f}",
        f"{payload.tp1:.2f}",
        f"{payload.tp2:.2f}",
        time_bucket.isoformat(),
    ]
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:64]


async def check_duplicate(db: AsyncSession, idempotency_key: str) -> Optional[Signal]:
    """Check if a signal with this idempotency key already exists."""
    result = await db.execute(
        select(Signal).where(Signal.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def process_signal(
    db: AsyncSession,
    payload: TradingViewWebhookPayload,
    user_id: Optional[UUID] = None,
    account_balance: float = 1000.0,
) -> SignalPipelineResult:
    """
    Full pipeline: validate -> filter -> score -> persist -> dispatch.

    Args:
        db: async database session
        payload: parsed TradingView webhook payload
        user_id: UUID of the associated user (None = system default)
        account_balance: current MT5 account balance for drawdown calculation

    Returns:
        SignalPipelineResult describing what action was taken
    """

    # ── 0. Idempotency check ──────────────────────────────────────────────
    idempotency_key = generate_idempotency_key(payload)
    existing_signal = await check_duplicate(db, idempotency_key)
    if existing_signal:
        logger.info(f"Duplicate signal detected: {existing_signal.id}")
        return SignalPipelineResult(
            existing_signal,
            "duplicate",
            f"Duplicate signal (existing: {existing_signal.id})"
        )

    # ── 1. Load bot settings ──────────────────────────────────────────────
    bot_mode = BotMode.ANALYZE
    sessions = None
    auto_trade = False
    spread_max = 5.0
    spread_multiplier = 2.0
    execution_symbol = "US30"

    bot_settings = None
    if user_id:
        result = await db.execute(select(BotSetting).where(BotSetting.user_id == user_id))
        bot_settings = result.scalar_one_or_none()
    else:
        # Get default settings (first one)
        result = await db.execute(select(BotSetting).limit(1))
        bot_settings = result.scalar_one_or_none()

    if bot_settings:
        bot_mode = bot_settings.mode
        sessions = bot_settings.sessions
        auto_trade = bot_settings.auto_trade_enabled
        spread_max = float(bot_settings.spread_max_points)
        spread_multiplier = float(bot_settings.spread_multiplier)
        execution_symbol = bot_settings.execution_symbol

    # ── 2. Session filter ─────────────────────────────────────────────────
    active_session = get_active_session(sessions=sessions)
    session_active = active_session is not None

    if not session_active:
        logger.info("Signal outside session windows - will score but not execute")

    # ── 3. Spread filter ──────────────────────────────────────────────────
    spread_ok = True
    current_spread = payload.spread or 0.0

    if current_spread > 0:
        spread_result = await check_spread(
            db,
            current_spread,
            symbol=execution_symbol,
            hard_cap=spread_max,
        )
        spread_ok = spread_result.allowed
        if not spread_ok:
            logger.warning(f"Spread rejected: {spread_result.reason}")

    # ── 4. Score confluence and classify setup ────────────────────────────
    score_result = score_from_payload(
        payload,
        spread_ok=spread_ok,
        session_active=session_active,
    )

    grade_map = {"A+": SignalGrade.A_PLUS, "A": SignalGrade.A, "B": SignalGrade.B}
    grade = grade_map[score_result.grade]

    setup_type_map = {
        "continuation_long": SetupType.CONTINUATION_LONG,
        "continuation_short": SetupType.CONTINUATION_SHORT,
        "swing_long": SetupType.SWING_LONG,
        "swing_short": SetupType.SWING_SHORT,
    }
    setup_type = setup_type_map.get(score_result.setup_type) if score_result.setup_type else None

    # ── 5. Check news blackout ────────────────────────────────────────────
    news_result = await check_news_blackout(db)
    news_blocked = news_result.blocked

    # ── 6. Persist signal ─────────────────────────────────────────────────
    direction = SignalDirection.LONG if payload.direction.lower() in ("long", "buy") else SignalDirection.SHORT

    signal = Signal(
        user_id=user_id,
        source="tradingview",
        setup_type=setup_type,
        direction=direction,
        analysis_symbol=payload.symbol,
        execution_symbol=execution_symbol,
        timeframe_entry=f"{payload.timeframe}m",

        # MTF bias
        weekly_bias=payload.weekly_bias,
        daily_bias=payload.daily_bias,
        h4_bias=payload.h4_bias,
        h1_bias=payload.h1_bias,
        m15_bias=payload.m15_bias,
        m5_bias=payload.m5_bias,
        m1_bias=payload.m1_bias,

        # Levels
        level_250=payload.level_250,
        level_125=payload.level_125,

        # Confluence factors
        fvg_present=payload.fvg_present,
        liquidity_sweep=payload.liquidity_sweep,
        displacement_present=payload.displacement_present,
        mss_present=payload.mss_present,

        # Prices
        entry_price=payload.entry,
        stop_loss=payload.stop_loss,
        tp1=payload.tp1,
        tp2=payload.tp2,

        # Context
        session_name=active_session,
        spread_points=current_spread or None,
        news_blocked=news_blocked,

        # Scoring
        score=score_result.score,
        grade=grade,
        eligible_for_auto_trade=score_result.auto_trade_eligible,

        # Idempotency
        idempotency_key=idempotency_key,

        # Raw payload
        raw_payload=payload.raw_payload,
    )

    db.add(signal)
    await db.flush()  # get signal.id without committing

    # ── 7. Grade filter ───────────────────────────────────────────────────
    if grade == SignalGrade.B:
        await db.commit()
        logger.info(f"Signal {signal.id} graded B - ignored (score {score_result.score})")
        return SignalPipelineResult(
            signal,
            "ignored",
            f"Grade B (score {score_result.score})",
            score_result,
        )

    # ── 8. News blackout handling ─────────────────────────────────────────
    if news_blocked:
        await db.commit()
        logger.info(f"Signal {signal.id} blocked by news: {news_result.reason}")
        return SignalPipelineResult(
            signal,
            "alerted",
            f"News blackout: {news_result.reason}",
            score_result,
        )

    await db.commit()

    # ── 9. Dispatch based on mode and eligibility ─────────────────────────

    # Check if setup is swing type - always alert only
    is_swing = score_result.setup_type in ("swing_long", "swing_short")

    if bot_mode == BotMode.ANALYZE:
        return SignalPipelineResult(
            signal,
            "alerted",
            "Analyze mode - alert only",
            score_result,
        )

    if bot_mode == BotMode.SWING or is_swing:
        return SignalPipelineResult(
            signal,
            "alerted",
            "Swing setup - user approval required",
            score_result,
        )

    if bot_mode == BotMode.TRADE and score_result.auto_trade_eligible and auto_trade:
        # Check risk limits before executing
        if user_id:
            risk = await check_risk(db, user_id, account_balance)
            if not risk.allowed:
                await disable_auto_trading(db, user_id, risk.reason or "Risk limit")
                return SignalPipelineResult(
                    signal,
                    "alerted",
                    f"Risk limit: {risk.reason}",
                    score_result,
                )

        return SignalPipelineResult(
            signal,
            "executed",
            "A+ grade in Trade mode - executing",
            score_result,
        )

    # Default: alert only
    reason = score_result.reason if not score_result.auto_trade_eligible else f"Grade {score_result.grade} - alert only"
    if not auto_trade:
        reason = "Auto trading disabled - alert only"

    return SignalPipelineResult(
        signal,
        "alerted",
        reason,
        score_result,
    )
