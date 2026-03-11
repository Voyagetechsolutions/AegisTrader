"""
Tests for Unified Signal Contract.

Verifies that signal normalization, validation, and conversion work correctly.
"""

import pytest
from datetime import datetime
from backend.strategy.unified_signal import (
    UnifiedSignal,
    SignalType,
    SignalStatus,
    SignalReason,
    SignalConverter
)
from backend.strategy.dual_engine_models import (
    Instrument,
    Direction,
    EngineType,
    SignalGrade,
    CoreSignal,
    ScalpSignal,
    ConfluenceScore,
    SessionType
)


def test_unified_signal_creation():
    """Test creating a valid unified signal."""
    signal = UnifiedSignal(
        signal_id="test_001",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp1_size=0.4,
        tp2=42200.0,
        tp2_size=0.4,
        tp3=None,
        tp3_size=0.2
    )
    
    assert signal.signal_id == "test_001"
    assert signal.engine == EngineType.CORE_STRATEGY
    assert signal.instrument == Instrument.US30
    assert signal.direction == Direction.LONG
    assert signal.grade == SignalGrade.A_PLUS
    assert signal.score == 90.0
    assert signal.status == SignalStatus.PENDING


def test_long_signal_validation():
    """Test validation of long signal parameters."""
    # Valid long signal
    signal = UnifiedSignal(
        signal_id="test_002",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A,
        score=80.0,
        entry_price=42000.0,
        stop_loss=41900.0,  # Below entry
        tp1=42100.0,  # Above entry
        tp1_size=1.0
    )
    
    assert signal.entry_price > signal.stop_loss
    assert signal.tp1 > signal.entry_price


def test_short_signal_validation():
    """Test validation of short signal parameters."""
    # Valid short signal
    signal = UnifiedSignal(
        signal_id="test_003",
        engine=EngineType.QUICK_SCALP,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.XAUUSD,
        direction=Direction.SHORT,
        grade=SignalGrade.A,
        score=75.0,
        entry_price=2450.0,
        stop_loss=2452.0,  # Above entry
        tp1=2448.0,  # Below entry
        tp1_size=1.0
    )
    
    assert signal.entry_price < signal.stop_loss
    assert signal.tp1 < signal.entry_price


def test_invalid_long_signal():
    """Test that invalid long signal raises error."""
    with pytest.raises(ValueError, match="must be above stop loss"):
        UnifiedSignal(
            signal_id="test_004",
            engine=EngineType.CORE_STRATEGY,
            signal_type=SignalType.ENTRY,
            instrument=Instrument.US30,
            direction=Direction.LONG,
            grade=SignalGrade.A,
            score=80.0,
            entry_price=42000.0,
            stop_loss=42100.0,  # WRONG: above entry
            tp1=42200.0,
            tp1_size=1.0
        )


def test_invalid_short_signal():
    """Test that invalid short signal raises error."""
    with pytest.raises(ValueError, match="must be below stop loss"):
        UnifiedSignal(
            signal_id="test_005",
            engine=EngineType.QUICK_SCALP,
            signal_type=SignalType.ENTRY,
            instrument=Instrument.XAUUSD,
            direction=Direction.SHORT,
            grade=SignalGrade.A,
            score=75.0,
            entry_price=2450.0,
            stop_loss=2448.0,  # WRONG: below entry
            tp1=2452.0,
            tp1_size=1.0
        )


def test_tp_sizes_validation():
    """Test that TP sizes must sum to <= 1.0."""
    # Valid: sums to 1.0
    signal1 = UnifiedSignal(
        signal_id="test_006",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp1_size=0.4,
        tp2=42200.0,
        tp2_size=0.4,
        tp3=None,
        tp3_size=0.2
    )
    assert signal1.tp1_size + signal1.tp2_size + signal1.tp3_size == 1.0
    
    # Invalid: sums to > 1.0
    with pytest.raises(ValueError, match="must be <= 1.0"):
        UnifiedSignal(
            signal_id="test_007",
            engine=EngineType.CORE_STRATEGY,
            signal_type=SignalType.ENTRY,
            instrument=Instrument.US30,
            direction=Direction.LONG,
            grade=SignalGrade.A,
            score=80.0,
            entry_price=42000.0,
            stop_loss=41900.0,
            tp1=42100.0,
            tp1_size=0.5,
            tp2=42200.0,
            tp2_size=0.5,
            tp3=None,
            tp3_size=0.2  # Total = 1.2 > 1.0
        )


def test_score_validation():
    """Test that score must be 0-100."""
    # Valid score
    signal1 = UnifiedSignal(
        signal_id="test_008",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=100.0,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp1_size=1.0
    )
    assert 0 <= signal1.score <= 100
    
    # Invalid score
    with pytest.raises(ValueError, match="Score must be 0-100"):
        UnifiedSignal(
            signal_id="test_009",
            engine=EngineType.CORE_STRATEGY,
            signal_type=SignalType.ENTRY,
            instrument=Instrument.US30,
            direction=Direction.LONG,
            grade=SignalGrade.A,
            score=150.0,  # WRONG: > 100
            entry_price=42000.0,
            stop_loss=41900.0,
            tp1=42100.0,
            tp1_size=1.0
        )


def test_risk_reward_calculation():
    """Test R:R ratio calculation."""
    signal = UnifiedSignal(
        signal_id="test_010",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,  # Risk = 100
        tp1=42200.0,  # Reward = 200
        tp1_size=1.0
    )
    
    rr = signal.get_risk_reward_ratio()
    assert rr == 2.0  # 200 / 100


def test_total_risk_reward_calculation():
    """Test weighted average R:R across multiple TPs."""
    signal = UnifiedSignal(
        signal_id="test_011",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,  # Risk = 100
        tp1=42100.0,  # 1R, 40%
        tp1_size=0.4,
        tp2=42200.0,  # 2R, 40%
        tp2_size=0.4,
        tp3=42300.0,  # 3R, 20%
        tp3_size=0.2
    )
    
    total_rr = signal.get_total_risk_reward()
    # (1R * 0.4) + (2R * 0.4) + (3R * 0.2) = 0.4 + 0.8 + 0.6 = 1.8R
    assert abs(total_rr - 1.8) < 0.01


def test_signal_reason():
    """Test signal reasoning."""
    reason = SignalReason(
        htf_alignment="Weekly + Daily + H4 + H1 bullish",
        liquidity_sweep="Swept previous day low",
        fvg="FVG at 41950",
        displacement="Strong bullish candle",
        mss="Break of structure confirmed"
    )
    
    reason_dict = reason.to_dict()
    assert "htf_alignment" in reason_dict
    assert "liquidity_sweep" in reason_dict
    assert "vwap" not in reason_dict  # None values excluded
    
    reason_str = reason.to_string()
    assert "htf_alignment" in reason_str
    assert "liquidity_sweep" in reason_str


def test_signal_to_dict():
    """Test signal serialization to dict."""
    signal = UnifiedSignal(
        signal_id="test_012",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp1_size=0.4,
        tp2=42200.0,
        tp2_size=0.4,
        tp3=None,
        tp3_size=0.2
    )
    
    signal_dict = signal.to_dict()
    
    assert signal_dict["signal_id"] == "test_012"
    assert signal_dict["engine"] == "CORE_STRATEGY"
    assert signal_dict["instrument"] == "US30"
    assert signal_dict["direction"] == "LONG"
    assert signal_dict["grade"] == "A+"
    assert signal_dict["score"] == 90.0
    assert "risk_reward_ratio" in signal_dict
    assert "total_risk_reward" in signal_dict


def test_signal_to_string():
    """Test signal human-readable string."""
    signal = UnifiedSignal(
        signal_id="test_013",
        engine=EngineType.QUICK_SCALP,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.XAUUSD,
        direction=Direction.SHORT,
        grade=SignalGrade.A,
        score=75.0,
        entry_price=2450.0,
        stop_loss=2452.0,
        tp1=2448.0,
        tp1_size=1.0
    )
    
    signal_str = signal.to_string()
    
    assert "test_013" in signal_str
    assert "QUICK_SCALP" in signal_str
    assert "XAUUSD" in signal_str
    assert "SHORT" in signal_str
    assert "2450.00" in signal_str


def test_convert_core_signal():
    """Test conversion from CoreSignal to UnifiedSignal."""
    core_signal = CoreSignal(
        instrument=Instrument.US30,
        direction=Direction.LONG,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp2=42200.0,
        confluence_score=ConfluenceScore(
            total=90,
            htf_alignment=20,
            key_level=15,
            liquidity_sweep=15,
            fvg=15,
            displacement=10,
            mss=10,
            vwap=5,
            volume_spike=0,
            atr=0,
            htf_target=0,
            session=0,
            spread=0
        ),
        grade=SignalGrade.A_PLUS,
        timestamp=datetime.now()
    )
    
    unified = SignalConverter.from_core_signal(
        core_signal,
        signal_id="core_001"
    )
    
    assert unified.signal_id == "core_001"
    assert unified.engine == EngineType.CORE_STRATEGY
    assert unified.instrument == Instrument.US30
    assert unified.direction == Direction.LONG
    assert unified.grade == SignalGrade.A_PLUS
    assert unified.score == 90.0
    assert unified.entry_price == 42000.0
    assert unified.stop_loss == 41900.0
    assert unified.tp1 == 42100.0
    assert unified.tp1_size == 0.4
    assert unified.tp2 == 42200.0
    assert unified.tp2_size == 0.4
    assert unified.tp3_size == 0.2


def test_convert_scalp_signal():
    """Test conversion from ScalpSignal to UnifiedSignal."""
    scalp_signal = ScalpSignal(
        instrument=Instrument.XAUUSD,
        direction=Direction.SHORT,
        entry_price=2450.0,
        stop_loss=2452.0,
        take_profit=2448.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    unified = SignalConverter.from_scalp_signal(
        scalp_signal,
        signal_id="scalp_001",
        grade=SignalGrade.A,
        score=75.0
    )
    
    assert unified.signal_id == "scalp_001"
    assert unified.engine == EngineType.QUICK_SCALP
    assert unified.instrument == Instrument.XAUUSD
    assert unified.direction == Direction.SHORT
    assert unified.grade == SignalGrade.A
    assert unified.score == 75.0
    assert unified.entry_price == 2450.0
    assert unified.stop_loss == 2452.0
    assert unified.tp1 == 2448.0
    assert unified.tp1_size == 1.0  # 100% at single TP
    assert unified.tp2 is None
    assert unified.tp3 is None


def test_signal_status_transitions():
    """Test signal status transitions."""
    signal = UnifiedSignal(
        signal_id="test_014",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp1_size=1.0
    )
    
    # Initial status
    assert signal.status == SignalStatus.PENDING
    
    # Approve
    signal.status = SignalStatus.APPROVED
    assert signal.status == SignalStatus.APPROVED
    
    # Execute
    signal.status = SignalStatus.EXECUTED
    assert signal.status == SignalStatus.EXECUTED


def test_signal_checks():
    """Test signal validation checks."""
    signal = UnifiedSignal(
        signal_id="test_015",
        engine=EngineType.CORE_STRATEGY,
        signal_type=SignalType.ENTRY,
        instrument=Instrument.US30,
        direction=Direction.LONG,
        grade=SignalGrade.A_PLUS,
        score=90.0,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp1_size=1.0
    )
    
    # Initial checks should be False
    assert signal.spread_check is False
    assert signal.session_check is False
    assert signal.news_check is False
    
    # Set checks
    signal.spread_check = True
    signal.session_check = True
    signal.news_check = True
    
    assert signal.spread_check is True
    assert signal.session_check is True
    assert signal.news_check is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
