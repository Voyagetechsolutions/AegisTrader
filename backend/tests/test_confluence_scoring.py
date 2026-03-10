"""Unit tests for the confluence scoring module."""
import pytest
from backend.modules.confluence_scoring import score_setup, score_from_payload, ConfluenceResult


def test_a_plus_grade():
    result = score_setup(
        htf_alignment=20, level_250=15, level_125=0,
        liquidity_sweep=15, fvg_retest=15, displacement=10,
        mss=10, session_timing=5, spread_ok=5,
    )
    assert result.score == 95
    assert result.grade == "A+"


def test_a_grade():
    result = score_setup(
        htf_alignment=20, level_250=15, level_125=0,
        liquidity_sweep=15, fvg_retest=0, displacement=10,
        mss=10, session_timing=5, spread_ok=5,
    )
    assert result.score == 80
    assert result.grade == "A"


def test_b_grade_ignored():
    result = score_setup(
        htf_alignment=20, level_250=0, level_125=0,
        liquidity_sweep=15, fvg_retest=0, displacement=0,
        mss=0, session_timing=5, spread_ok=5,
    )
    assert result.score == 45
    assert result.grade == "B"


def test_max_score_clamped():
    result = score_setup(
        htf_alignment=999, level_250=999, level_125=999,
        liquidity_sweep=999, fvg_retest=999, displacement=999,
        mss=999, session_timing=999, spread_ok=999,
    )
    # Should clamp to maximums: 20+15+10+15+15+10+10+5+5 = 105... wait no, max is 95 total
    # Actually: 20+15+10+15+15+10+10+5+5 = 105 → wait let me recalculate
    # htf=20 + 250=15 + 125=10 + sweep=15 + fvg=15 + disp=10 + mss=10 + sess=5 + spread=5 = 105
    # Wait: the PRD says max is 100. Let me check: 20+15+10+15+15+10+10+5+5 = 105
    # This is a discrepancy in the PRD - the actual sum is 105.
    # We clamp each factor to its max, so total will be 105 max.
    assert result.score == 105
    assert result.grade == "A+"


def test_breakdown_keys():
    result = score_setup(htf_alignment=20)
    assert "htf_alignment" in result.breakdown
    assert len(result.breakdown) == 9


def test_from_payload():
    payload = {
        "htf_alignment": 20, "level_250": 15, "level_125": 10,
        "liquidity_sweep": 15, "fvg_retest": 15, "displacement": 10,
        "mss": 10, "session_timing": 5, "spread_ok": 5,
    }
    result = score_from_payload(payload)
    assert result.grade == "A+"


def test_zero_score():
    result = score_setup()
    assert result.score == 0
    assert result.grade == "B"


def test_exact_a_boundary():
    result = score_setup(
        htf_alignment=20, level_250=15, liquidity_sweep=15,
        fvg_retest=15, session_timing=5, spread_ok=5,
    )
    assert result.score == 75
    assert result.grade == "A"


def test_exact_a_plus_boundary():
    result = score_setup(
        htf_alignment=20, level_250=15, liquidity_sweep=15,
        fvg_retest=15, mss=10, session_timing=5, spread_ok=5,
    )
    assert result.score == 85
    assert result.grade == "A+"
