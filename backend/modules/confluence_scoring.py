"""
confluence_scoring.py
Scores a trading setup 0–100 based on the Technical Architecture spec.

Scoring weights:
  - HTF alignment:      20 points max
  - 250 level:          15 points max
  - 125 level:          10 points max
  - Liquidity sweep:    15 points max
  - FVG:                15 points max
  - Displacement:       10 points max
  - MSS:                10 points max
  - Session timing:      5 points max
  - Spread OK:           5 points max (deducted if spread is bad)
  --------------------------
  Total:               100 points max

Grades:
  - A+ (85-100): Auto trade eligible
  - A  (75-84):  Alert only
  - B  (<75):    Ignored (no alert)
"""

from dataclasses import dataclass
from typing import Literal, Optional

from backend.schemas.schemas import TradingViewWebhookPayload


@dataclass
class ConfluenceResult:
    score: int
    grade: Literal["A+", "A", "B"]
    breakdown: dict[str, int]
    auto_trade_eligible: bool
    setup_type: Optional[str]
    reason: str


# Bias interpretation helpers
BULLISH_TERMS = frozenset(["bull", "bullish", "buy", "bull_shift", "long"])
BEARISH_TERMS = frozenset(["bear", "bearish", "sell", "bear_shift", "short"])


def _is_bullish(bias: Optional[str]) -> bool:
    """Check if a bias string indicates bullish sentiment."""
    if not bias:
        return False
    return bias.lower() in BULLISH_TERMS


def _is_bearish(bias: Optional[str]) -> bool:
    """Check if a bias string indicates bearish sentiment."""
    if not bias:
        return False
    return bias.lower() in BEARISH_TERMS


def _is_neutral_or_bullish(bias: Optional[str]) -> bool:
    """Check if bias is not bearish (neutral or bullish)."""
    if not bias:
        return True  # No data = neutral
    return not _is_bearish(bias)


def _is_neutral_or_bearish(bias: Optional[str]) -> bool:
    """Check if bias is not bullish (neutral or bearish)."""
    if not bias:
        return True
    return not _is_bullish(bias)


def classify_setup_type(payload: TradingViewWebhookPayload) -> tuple[Optional[str], str]:
    """
    Classify the setup type based on MTF alignment and direction.

    Returns:
        tuple of (setup_type, reason)
        setup_type: continuation_long | continuation_short | swing_long | swing_short | None
    """
    direction = payload.direction.lower()
    is_long = direction in ("long", "buy")

    weekly = payload.weekly_bias
    daily = payload.daily_bias
    h4 = payload.h4_bias
    h1 = payload.h1_bias
    m5 = payload.m5_bias

    if is_long:
        # A+ Continuation Long conditions (per spec):
        # - weekly/daily/h4 not bearish
        # - h1 aligned bullish
        # - 5m MSS bullish (bull_shift)
        htf_aligned = (
            _is_neutral_or_bullish(weekly) and
            _is_neutral_or_bullish(daily) and
            _is_neutral_or_bullish(h4) and
            _is_bullish(h1)
        )
        m5_shift = _is_bullish(m5) or m5 == "bull_shift"

        if htf_aligned and m5_shift:
            return "continuation_long", "HTF aligned bullish with 5M bull shift"

        # Swing Long conditions:
        # - weekly bullish
        # - daily bullish
        # - h4 bullish
        # - h1 pullback (not bullish = retracement opportunity)
        swing_htf = _is_bullish(weekly) and _is_bullish(daily) and _is_bullish(h4)
        h1_pullback = not _is_bullish(h1)  # H1 is neutral or bearish = pullback

        if swing_htf and h1_pullback:
            return "swing_long", "Weekly/Daily/H4 bullish with H1 pullback - swing setup"

        return None, "Long setup does not meet continuation or swing criteria"

    else:  # Short
        # A+ Continuation Short conditions (mirror of long):
        # - weekly/daily/h4 not bullish
        # - h1 aligned bearish
        # - 5m MSS bearish (bear_shift)
        htf_aligned = (
            _is_neutral_or_bearish(weekly) and
            _is_neutral_or_bearish(daily) and
            _is_neutral_or_bearish(h4) and
            _is_bearish(h1)
        )
        m5_shift = _is_bearish(m5) or m5 == "bear_shift"

        if htf_aligned and m5_shift:
            return "continuation_short", "HTF aligned bearish with 5M bear shift"

        # Swing Short conditions:
        swing_htf = _is_bearish(weekly) and _is_bearish(daily) and _is_bearish(h4)
        h1_pullback = not _is_bearish(h1)

        if swing_htf and h1_pullback:
            return "swing_short", "Weekly/Daily/H4 bearish with H1 pullback - swing setup"

        return None, "Short setup does not meet continuation or swing criteria"


def score_htf_alignment(payload: TradingViewWebhookPayload) -> int:
    """
    Score HTF alignment (max 20 points).

    Points breakdown:
    - Weekly aligned: 6 points
    - Daily aligned: 5 points
    - H4 aligned: 4 points
    - H1 aligned: 3 points
    - M15 aligned: 2 points (bonus)
    """
    direction = payload.direction.lower()
    is_long = direction in ("long", "buy")
    score = 0

    def aligned(bias: Optional[str]) -> bool:
        if is_long:
            return _is_bullish(bias) or (bias and bias.lower() == "neutral")
        else:
            return _is_bearish(bias) or (bias and bias.lower() == "neutral")

    def strongly_aligned(bias: Optional[str]) -> bool:
        if is_long:
            return _is_bullish(bias)
        else:
            return _is_bearish(bias)

    # Weekly (6 points)
    if strongly_aligned(payload.weekly_bias):
        score += 6
    elif aligned(payload.weekly_bias):
        score += 3

    # Daily (5 points)
    if strongly_aligned(payload.daily_bias):
        score += 5
    elif aligned(payload.daily_bias):
        score += 2

    # H4 (4 points)
    if strongly_aligned(payload.h4_bias):
        score += 4
    elif aligned(payload.h4_bias):
        score += 2

    # H1 (3 points)
    if strongly_aligned(payload.h1_bias):
        score += 3
    elif aligned(payload.h1_bias):
        score += 1

    # M15 bonus (2 points)
    if strongly_aligned(payload.m15_bias):
        score += 2

    return min(score, 20)


def score_levels(payload: TradingViewWebhookPayload) -> tuple[int, int]:
    """
    Score level interactions.
    Returns (level_250_score, level_125_score).

    250 level: max 15 points
    125 level: max 10 points
    """
    level_250_score = 0
    level_125_score = 0

    entry = payload.entry

    # Check if entry is near 250 level
    if payload.level_250:
        distance = abs(entry - payload.level_250)
        if distance <= 50:  # Within 50 points of level
            level_250_score = 15
        elif distance <= 100:
            level_250_score = 10
        elif distance <= 150:
            level_250_score = 5

    # Check if entry is near 125 level
    if payload.level_125:
        distance = abs(entry - payload.level_125)
        if distance <= 30:
            level_125_score = 10
        elif distance <= 60:
            level_125_score = 7
        elif distance <= 100:
            level_125_score = 3

    return level_250_score, level_125_score


def score_setup(
    payload: TradingViewWebhookPayload,
    spread_ok: bool = True,
    session_active: bool = True,
) -> ConfluenceResult:
    """
    Calculate confluence score from webhook payload.

    Args:
        payload: TradingView webhook data
        spread_ok: Whether spread is within acceptable range
        session_active: Whether we're in an active trading session

    Returns:
        ConfluenceResult with score, grade, breakdown, and eligibility
    """
    # Classify setup type first
    setup_type, setup_reason = classify_setup_type(payload)

    # Score individual factors
    htf_score = score_htf_alignment(payload)
    level_250_score, level_125_score = score_levels(payload)

    # Boolean factors
    liquidity_score = 15 if payload.liquidity_sweep else 0
    fvg_score = 15 if payload.fvg_present else 0
    displacement_score = 10 if payload.displacement_present else 0
    mss_score = 10 if payload.mss_present else 0
    session_score = 5 if session_active else 0
    spread_score = 5 if spread_ok else 0

    breakdown = {
        "htf_alignment": htf_score,
        "level_250": level_250_score,
        "level_125": level_125_score,
        "liquidity_sweep": liquidity_score,
        "fvg": fvg_score,
        "displacement": displacement_score,
        "mss": mss_score,
        "session": session_score,
        "spread": spread_score,
    }

    total = sum(breakdown.values())

    # Determine grade
    if total >= 85:
        grade: Literal["A+", "A", "B"] = "A+"
    elif total >= 75:
        grade = "A"
    else:
        grade = "B"

    # Auto trade eligibility (per spec):
    # - Must be A+ grade
    # - Must be continuation setup (not swing)
    # - Must have all key confluence factors
    is_continuation = setup_type in ("continuation_long", "continuation_short")
    has_key_factors = (
        payload.liquidity_sweep and
        payload.fvg_present and
        payload.displacement_present and
        payload.mss_present
    )

    auto_eligible = (
        grade == "A+" and
        is_continuation and
        has_key_factors and
        spread_ok and
        session_active
    )

    reason = setup_reason
    if grade == "A+" and not auto_eligible:
        if not is_continuation:
            reason = f"A+ grade but swing setup - alert only"
        elif not has_key_factors:
            missing = []
            if not payload.liquidity_sweep:
                missing.append("liquidity sweep")
            if not payload.fvg_present:
                missing.append("FVG")
            if not payload.displacement_present:
                missing.append("displacement")
            if not payload.mss_present:
                missing.append("MSS")
            reason = f"A+ grade but missing: {', '.join(missing)}"
        elif not spread_ok:
            reason = "A+ grade but spread too wide"
        elif not session_active:
            reason = "A+ grade but outside session"

    return ConfluenceResult(
        score=total,
        grade=grade,
        breakdown=breakdown,
        auto_trade_eligible=auto_eligible,
        setup_type=setup_type,
        reason=reason,
    )


def score_from_payload(
    payload: TradingViewWebhookPayload,
    spread_ok: bool = True,
    session_active: bool = True,
) -> ConfluenceResult:
    """
    Convenience wrapper: score a webhook payload.
    """
    return score_setup(payload, spread_ok=spread_ok, session_active=session_active)
