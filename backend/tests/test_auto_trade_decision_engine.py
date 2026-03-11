"""
Property-based tests for Auto-Trade Decision Engine.

These tests verify the correctness properties of the intelligent decision logic
that coordinates Core Strategy and Quick Scalp engines.

Requirements: 15.1-15.6, 16.1-16.4
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
from backend.strategy.auto_trade_decision_engine import (
    AutoTradeDecisionEngine,
    VolatilityRegime,
    TrendStrength,
    MarketRegime,
    EnginePreference,
    TradeDecision
)
from backend.strategy.dual_engine_models import (
    Instrument,
    Direction,
    EngineType,
    SessionType,
    SignalGrade,
    CoreSignal,
    ScalpSignal,
    ConfluenceScore,
    PerformanceMetrics
)


# Strategy definitions for hypothesis
@st.composite
def confluence_score_strategy(draw, min_total=0, max_total=100):
    """Generate valid ConfluenceScore with specified total range."""
    total = draw(st.integers(min_value=min_total, max_value=max_total))
    
    # Distribute total across components respecting maximums
    htf_alignment = draw(st.integers(min_value=0, max_value=min(20, total)))
    remaining = total - htf_alignment
    
    key_level = draw(st.integers(min_value=0, max_value=min(15, remaining)))
    remaining -= key_level
    
    liquidity_sweep = draw(st.integers(min_value=0, max_value=min(15, remaining)))
    remaining -= liquidity_sweep
    
    fvg = draw(st.integers(min_value=0, max_value=min(15, remaining)))
    remaining -= fvg
    
    displacement = draw(st.integers(min_value=0, max_value=min(10, remaining)))
    remaining -= displacement
    
    mss = draw(st.integers(min_value=0, max_value=min(10, remaining)))
    remaining -= mss
    
    # Distribute remaining across 5-point components
    components_5pt = []
    for _ in range(6):  # vwap, volume_spike, atr, htf_target, session, spread
        val = draw(st.integers(min_value=0, max_value=min(5, remaining)))
        components_5pt.append(val)
        remaining -= val
    
    return ConfluenceScore(
        total=total,
        htf_alignment=htf_alignment,
        key_level=key_level,
        liquidity_sweep=liquidity_sweep,
        fvg=fvg,
        displacement=displacement,
        mss=mss,
        vwap=components_5pt[0],
        volume_spike=components_5pt[1],
        atr=components_5pt[2],
        htf_target=components_5pt[3],
        session=components_5pt[4],
        spread=components_5pt[5]
    )


@st.composite
def core_signal_strategy(draw, grade=None):
    """Generate valid CoreSignal."""
    instrument = draw(st.sampled_from(list(Instrument)))
    direction = draw(st.sampled_from(list(Direction)))
    entry_price = draw(st.floats(min_value=1000, max_value=50000))
    
    # Generate stop loss based on direction
    if direction == Direction.LONG:
        stop_loss = entry_price - draw(st.floats(min_value=10, max_value=200))
    else:
        stop_loss = entry_price + draw(st.floats(min_value=10, max_value=200))
    
    risk = abs(entry_price - stop_loss)
    
    # Calculate TPs
    if direction == Direction.LONG:
        tp1 = entry_price + risk  # 1R
        tp2 = entry_price + (risk * 2)  # 2R
    else:
        tp1 = entry_price - risk  # 1R
        tp2 = entry_price - (risk * 2)  # 2R
    
    # Determine grade from confluence score
    if grade:
        signal_grade = grade
        if grade == SignalGrade.A_PLUS:
            confluence = draw(confluence_score_strategy(min_total=85, max_total=100))
        elif grade == SignalGrade.A:
            confluence = draw(confluence_score_strategy(min_total=75, max_total=84))
        else:  # B
            confluence = draw(confluence_score_strategy(min_total=0, max_total=74))
    else:
        confluence = draw(confluence_score_strategy())
        if confluence.total >= 85:
            signal_grade = SignalGrade.A_PLUS
        elif confluence.total >= 75:
            signal_grade = SignalGrade.A
        else:
            signal_grade = SignalGrade.B
    
    return CoreSignal(
        instrument=instrument,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        confluence_score=confluence,
        grade=signal_grade,
        timestamp=datetime.now()
    )


@st.composite
def scalp_signal_strategy(draw):
    """Generate valid ScalpSignal."""
    instrument = draw(st.sampled_from(list(Instrument)))
    direction = draw(st.sampled_from(list(Direction)))
    entry_price = draw(st.floats(min_value=1000, max_value=50000))
    
    # Generate stop loss based on instrument
    if instrument == Instrument.US30:
        sl_distance = draw(st.floats(min_value=15, max_value=30))
    elif instrument == Instrument.NAS100:
        sl_distance = draw(st.floats(min_value=10, max_value=25))
    else:  # XAUUSD
        sl_distance = draw(st.floats(min_value=0.80, max_value=2.00))
    
    if direction == Direction.LONG:
        stop_loss = entry_price - sl_distance
        take_profit = entry_price + (sl_distance * draw(st.floats(min_value=0.8, max_value=1.0)))
    else:
        stop_loss = entry_price + sl_distance
        take_profit = entry_price - (sl_distance * draw(st.floats(min_value=0.8, max_value=1.0)))
    
    return ScalpSignal(
        instrument=instrument,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        session=draw(st.sampled_from(list(SessionType))),
        timestamp=datetime.now()
    )


@st.composite
def market_regime_strategy(draw):
    """Generate valid MarketRegime."""
    atr_average = draw(st.floats(min_value=10, max_value=500))
    
    # Generate ATR current based on volatility regime
    volatility = draw(st.sampled_from(list(VolatilityRegime)))
    if volatility == VolatilityRegime.LOW:
        atr_current = atr_average * draw(st.floats(min_value=0.3, max_value=0.79))
    elif volatility == VolatilityRegime.NORMAL:
        atr_current = atr_average * draw(st.floats(min_value=0.8, max_value=1.5))
    elif volatility == VolatilityRegime.HIGH:
        atr_current = atr_average * draw(st.floats(min_value=1.51, max_value=2.5))
    else:  # EXTREME
        atr_current = atr_average * draw(st.floats(min_value=2.51, max_value=5.0))
    
    return MarketRegime(
        instrument=draw(st.sampled_from(list(Instrument))),
        volatility=volatility,
        trend_strength=draw(st.sampled_from(list(TrendStrength))),
        atr_current=atr_current,
        atr_average=atr_average,
        timestamp=datetime.now()
    )


@st.composite
def performance_metrics_strategy(draw):
    """Generate valid PerformanceMetrics."""
    total_trades = draw(st.integers(min_value=1, max_value=100))
    winning_trades = draw(st.integers(min_value=0, max_value=total_trades))
    losing_trades = total_trades - winning_trades
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    profit_factor = draw(st.floats(min_value=0.5, max_value=3.0))
    average_rr = draw(st.floats(min_value=0.5, max_value=3.0))
    
    return PerformanceMetrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        average_rr=average_rr,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades
    )


# Feature: dual-engine-strategy-system, Property 34: Engine Conflict Resolution
@given(
    instrument=st.sampled_from(list(Instrument)),
    regime=market_regime_strategy()
)
def test_core_a_plus_always_wins_conflict(instrument, regime):
    """
    Property 34: Engine Conflict Resolution
    
    When both engines have valid signals, Core Strategy A+ signals
    must always take priority over scalp signals.
    """
    engine = AutoTradeDecisionEngine()
    
    # Generate A+ core signal and scalp signal
    core_signal = CoreSignal(
        instrument=instrument,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39900.0,
        tp1=40100.0,
        tp2=40200.0,
        confluence_score=ConfluenceScore(
            total=90, htf_alignment=20, key_level=15, liquidity_sweep=15,
            fvg=15, displacement=10, mss=10, vwap=5, volume_spike=0,
            atr=0, htf_target=0, session=0, spread=0
        ),
        grade=SignalGrade.A_PLUS,
        timestamp=datetime.now()
    )
    
    scalp_signal = ScalpSignal(
        instrument=instrument,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39980.0,
        take_profit=40020.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    decision = engine.decide_trade(
        instrument=instrument,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    # A+ signal must win
    assert decision.should_trade is True
    assert decision.engine == EngineType.CORE_STRATEGY
    assert decision.blocked_engine == EngineType.QUICK_SCALP
    assert "A+" in decision.reason or "highest priority" in decision.reason.lower()


# Feature: dual-engine-strategy-system, Property 34: Engine Conflict Resolution
@given(
    instrument=st.sampled_from(list(Instrument)),
    core_signal=core_signal_strategy(),
    scalp_signal=scalp_signal_strategy(),
    regime=market_regime_strategy()
)
def test_only_one_engine_trades_per_instrument(instrument, core_signal, scalp_signal, regime):
    """
    Property 34: Engine Conflict Resolution
    
    When both engines have valid signals for the same instrument,
    only one engine must be allowed to trade.
    """
    # Ensure signals are for same instrument
    core_signal.instrument = instrument
    scalp_signal.instrument = instrument
    
    engine = AutoTradeDecisionEngine()
    
    decision = engine.decide_trade(
        instrument=instrument,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    # Either one engine trades or neither trades
    if decision.should_trade:
        assert decision.engine in [EngineType.CORE_STRATEGY, EngineType.QUICK_SCALP]
        assert decision.blocked_engine in [EngineType.CORE_STRATEGY, EngineType.QUICK_SCALP, None]
        # If one trades, the other must be blocked
        if decision.blocked_engine:
            assert decision.engine != decision.blocked_engine
    else:
        # If neither trades, engine should be None
        assert decision.engine is None


# Feature: dual-engine-strategy-system, Property 34: Engine Conflict Resolution
@given(
    instrument=st.sampled_from(list(Instrument)),
    regime=market_regime_strategy()
)
def test_active_position_blocks_both_engines(instrument, regime):
    """
    Property 34: Engine Conflict Resolution
    
    When an instrument already has an active position,
    both engines must be blocked from trading that instrument.
    """
    engine = AutoTradeDecisionEngine()
    
    # Register active position
    engine.register_position_opened(instrument, EngineType.CORE_STRATEGY)
    
    # Generate signals
    core_signal = CoreSignal(
        instrument=instrument,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39900.0,
        tp1=40100.0,
        tp2=40200.0,
        confluence_score=ConfluenceScore(
            total=90, htf_alignment=20, key_level=15, liquidity_sweep=15,
            fvg=15, displacement=10, mss=10, vwap=5, volume_spike=0,
            atr=0, htf_target=0, session=0, spread=0
        ),
        grade=SignalGrade.A_PLUS,
        timestamp=datetime.now()
    )
    
    scalp_signal = ScalpSignal(
        instrument=instrument,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39980.0,
        take_profit=40020.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    # Test with core signal
    decision = engine.decide_trade(
        instrument=instrument,
        core_signal=core_signal,
        scalp_signal=None,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    assert decision.should_trade is False
    assert "active" in decision.reason.lower()
    
    # Test with scalp signal
    decision = engine.decide_trade(
        instrument=instrument,
        core_signal=None,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    assert decision.should_trade is False
    assert "active" in decision.reason.lower()


# Feature: dual-engine-strategy-system, Property 35: Volatility Regime Detection
@given(
    instrument=st.sampled_from(list(Instrument)),
    atr_average=st.floats(min_value=10, max_value=500)
)
def test_scalp_favored_in_high_volatility(instrument, atr_average):
    """
    Property 35: Volatility Regime Detection
    
    Quick Scalp engine must be favored when volatility is high.
    """
    engine = AutoTradeDecisionEngine()
    
    # Create high volatility regime
    regime = MarketRegime(
        instrument=instrument,
        volatility=VolatilityRegime.HIGH,
        trend_strength=TrendStrength.RANGING,  # Unfavorable for core
        atr_current=atr_average * 2.0,
        atr_average=atr_average,
        timestamp=datetime.now()
    )
    
    preference = engine.get_engine_preference(regime)
    
    # Scalp should be allowed in high volatility
    assert preference.allow_quick_scalp is True


# Feature: dual-engine-strategy-system, Property 35: Volatility Regime Detection
@given(
    instrument=st.sampled_from(list(Instrument)),
    atr_average=st.floats(min_value=10, max_value=500)
)
def test_core_favored_in_trending_normal_volatility(instrument, atr_average):
    """
    Property 35: Volatility Regime Detection
    
    Core Strategy engine must be favored when market is trending
    with normal volatility.
    """
    engine = AutoTradeDecisionEngine()
    
    # Create trending + normal volatility regime
    regime = MarketRegime(
        instrument=instrument,
        volatility=VolatilityRegime.NORMAL,
        trend_strength=TrendStrength.STRONG_TREND,
        atr_current=atr_average * 1.0,
        atr_average=atr_average,
        timestamp=datetime.now()
    )
    
    preference = engine.get_engine_preference(regime)
    
    # Core should be allowed in trending + normal volatility
    assert preference.allow_core_strategy is True


# Feature: dual-engine-strategy-system, Property 35: Volatility Regime Detection
@given(
    instrument=st.sampled_from(list(Instrument)),
    atr_average=st.floats(min_value=10, max_value=500)
)
def test_scalp_blocked_in_low_volatility(instrument, atr_average):
    """
    Property 35: Volatility Regime Detection
    
    Quick Scalp engine must be blocked when volatility is low.
    """
    engine = AutoTradeDecisionEngine()
    
    # Create low volatility regime
    regime = MarketRegime(
        instrument=instrument,
        volatility=VolatilityRegime.LOW,
        trend_strength=TrendStrength.WEAK_TREND,
        atr_current=atr_average * 0.5,
        atr_average=atr_average,
        timestamp=datetime.now()
    )
    
    scalp_signal = ScalpSignal(
        instrument=instrument,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39980.0,
        take_profit=40020.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    decision = engine.decide_trade(
        instrument=instrument,
        core_signal=None,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    # Scalp should be blocked in low volatility
    assert decision.should_trade is False
    assert decision.blocked_engine == EngineType.QUICK_SCALP
    assert "volatility" in decision.reason.lower()


# Feature: dual-engine-strategy-system, Property 35: Volatility Regime Detection
@given(
    instrument=st.sampled_from(list(Instrument)),
    atr_average=st.floats(min_value=10, max_value=500)
)
def test_core_blocked_in_ranging_market(instrument, atr_average):
    """
    Property 35: Volatility Regime Detection
    
    Core Strategy A signals must be blocked when market is ranging/choppy.
    """
    engine = AutoTradeDecisionEngine()
    
    # Create ranging market regime
    regime = MarketRegime(
        instrument=instrument,
        volatility=VolatilityRegime.NORMAL,
        trend_strength=TrendStrength.RANGING,
        atr_current=atr_average * 1.0,
        atr_average=atr_average,
        timestamp=datetime.now()
    )
    
    # Generate A signal (not A+, which always trades)
    core_signal = CoreSignal(
        instrument=instrument,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39900.0,
        tp1=40100.0,
        tp2=40200.0,
        confluence_score=ConfluenceScore(
            total=80, htf_alignment=20, key_level=15, liquidity_sweep=15,
            fvg=15, displacement=10, mss=5, vwap=0, volume_spike=0,
            atr=0, htf_target=0, session=0, spread=0
        ),
        grade=SignalGrade.A,
        timestamp=datetime.now()
    )
    
    decision = engine.decide_trade(
        instrument=instrument,
        core_signal=core_signal,
        scalp_signal=None,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    # Core A signal should be blocked in ranging market
    assert decision.should_trade is False
    assert decision.blocked_engine == EngineType.CORE_STRATEGY
    assert "ranging" in decision.reason.lower() or "choppy" in decision.reason.lower()


# Unit test for position tracking
def test_position_tracking():
    """Test that position tracking correctly blocks and unblocks instruments."""
    engine = AutoTradeDecisionEngine()
    
    # Initially no positions
    assert len(engine.active_positions) == 0
    
    # Register position
    engine.register_position_opened(Instrument.US30, EngineType.CORE_STRATEGY)
    assert Instrument.US30 in engine.active_positions
    assert engine.active_positions[Instrument.US30] == EngineType.CORE_STRATEGY
    
    # Close position
    engine.register_position_closed(Instrument.US30)
    assert Instrument.US30 not in engine.active_positions
    
    # Multiple instruments
    engine.register_position_opened(Instrument.US30, EngineType.CORE_STRATEGY)
    engine.register_position_opened(Instrument.XAUUSD, EngineType.QUICK_SCALP)
    assert len(engine.active_positions) == 2
    
    engine.register_position_closed(Instrument.US30)
    assert len(engine.active_positions) == 1
    assert Instrument.XAUUSD in engine.active_positions


# Unit test for performance tiebreaker
def test_performance_tiebreaker_logic():
    """Test that performance tiebreaker correctly evaluates metrics."""
    engine = AutoTradeDecisionEngine()
    
    # Use HIGH volatility so both engines are suitable
    regime = MarketRegime(
        instrument=Instrument.US30,
        volatility=VolatilityRegime.HIGH,
        trend_strength=TrendStrength.WEAK_TREND,
        atr_current=200.0,
        atr_average=100.0,
        timestamp=datetime.now()
    )
    
    core_signal = CoreSignal(
        instrument=Instrument.US30,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39900.0,
        tp1=40100.0,
        tp2=40200.0,
        confluence_score=ConfluenceScore(
            total=80, htf_alignment=20, key_level=15, liquidity_sweep=15,
            fvg=15, displacement=10, mss=5, vwap=0, volume_spike=0,
            atr=0, htf_target=0, session=0, spread=0
        ),
        grade=SignalGrade.A,
        timestamp=datetime.now()
    )
    
    scalp_signal = ScalpSignal(
        instrument=Instrument.US30,
        direction=Direction.LONG,
        entry_price=40000.0,
        stop_loss=39980.0,
        take_profit=40020.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    # Scenario 1: No performance data - defaults to Core
    decision = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    assert decision.engine == EngineType.CORE_STRATEGY
    
    # Scenario 2: Scalp significantly outperforming
    core_metrics = PerformanceMetrics(
        win_rate=0.40,
        profit_factor=1.2,
        average_rr=1.5,
        total_trades=20,
        winning_trades=8,
        losing_trades=12
    )
    
    scalp_metrics = PerformanceMetrics(
        win_rate=0.65,
        profit_factor=1.8,
        average_rr=1.0,
        total_trades=50,
        winning_trades=32,
        losing_trades=18
    )
    
    decision = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=core_metrics,
        scalp_metrics=scalp_metrics
    )
    assert decision.engine == EngineType.QUICK_SCALP
    assert "performance" in decision.reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
