"""
Example usage of Auto-Trade Decision Engine.

This demonstrates how to integrate the decision engine into your trading system
to coordinate Core Strategy and Quick Scalp engines intelligently.
"""

from datetime import datetime
from backend.strategy.auto_trade_decision_engine import (
    AutoTradeDecisionEngine,
    VolatilityRegime,
    TrendStrength,
    MarketRegime
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


def example_1_core_a_plus_priority():
    """
    Example 1: Core Strategy A+ signal gets priority over scalp signal.
    
    This is the most common scenario - when you have a high-quality Core Strategy
    setup, it should always take priority because of its higher R:R potential.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Core Strategy A+ Priority")
    print("="*80)
    
    engine = AutoTradeDecisionEngine()
    
    # Market regime: High volatility, trending (both engines suitable)
    regime = MarketRegime(
        instrument=Instrument.US30,
        volatility=VolatilityRegime.HIGH,
        trend_strength=TrendStrength.STRONG_TREND,
        atr_current=200.0,
        atr_average=100.0,
        timestamp=datetime.now()
    )
    
    # Core Strategy A+ signal (90 points)
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
    
    # Quick Scalp signal
    scalp_signal = ScalpSignal(
        instrument=Instrument.US30,
        direction=Direction.LONG,
        entry_price=42000.0,
        stop_loss=41980.0,
        take_profit=42020.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    # Make decision
    decision = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    print(f"\nMarket: {regime.instrument.value}")
    print(f"Volatility: {regime.volatility.value}")
    print(f"Trend: {regime.trend_strength.value}")
    print(f"\nCore Signal: A+ (90 points)")
    print(f"Scalp Signal: Valid")
    print(f"\n{'='*40}")
    print(f"DECISION: {decision.engine.value if decision.engine else 'NO TRADE'}")
    print(f"Reason: {decision.reason}")
    print(f"Blocked: {decision.blocked_engine.value if decision.blocked_engine else 'None'}")
    print(f"{'='*40}")


def example_2_regime_based_selection():
    """
    Example 2: Regime-based engine selection.
    
    When only one engine has a signal, the decision engine validates it
    against the current market regime.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Regime-Based Selection")
    print("="*80)
    
    engine = AutoTradeDecisionEngine()
    
    # Scenario A: High volatility, ranging - good for scalping
    print("\n--- Scenario A: High Volatility + Ranging ---")
    
    regime_a = MarketRegime(
        instrument=Instrument.XAUUSD,
        volatility=VolatilityRegime.HIGH,
        trend_strength=TrendStrength.RANGING,
        atr_current=8.0,
        atr_average=4.0,
        timestamp=datetime.now()
    )
    
    scalp_signal = ScalpSignal(
        instrument=Instrument.XAUUSD,
        direction=Direction.SHORT,
        entry_price=2450.0,
        stop_loss=2451.5,
        take_profit=2449.0,
        session=SessionType.NY_OPEN,
        timestamp=datetime.now()
    )
    
    decision_a = engine.decide_trade(
        instrument=Instrument.XAUUSD,
        core_signal=None,
        scalp_signal=scalp_signal,
        market_regime=regime_a,
        core_metrics=None,
        scalp_metrics=None
    )
    
    print(f"Volatility: {regime_a.volatility.value}")
    print(f"Trend: {regime_a.trend_strength.value}")
    print(f"Signal: Quick Scalp")
    print(f"Decision: {decision_a.engine.value if decision_a.engine else 'NO TRADE'}")
    print(f"Reason: {decision_a.reason}")
    
    # Scenario B: Normal volatility, trending - good for Core Strategy
    print("\n--- Scenario B: Normal Volatility + Trending ---")
    
    regime_b = MarketRegime(
        instrument=Instrument.NAS100,
        volatility=VolatilityRegime.NORMAL,
        trend_strength=TrendStrength.STRONG_TREND,
        atr_current=120.0,
        atr_average=100.0,
        timestamp=datetime.now()
    )
    
    core_signal = CoreSignal(
        instrument=Instrument.NAS100,
        direction=Direction.LONG,
        entry_price=18000.0,
        stop_loss=17950.0,
        tp1=18050.0,
        tp2=18100.0,
        confluence_score=ConfluenceScore(
            total=88,
            htf_alignment=20,
            key_level=15,
            liquidity_sweep=15,
            fvg=15,
            displacement=10,
            mss=8,
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
    
    decision_b = engine.decide_trade(
        instrument=Instrument.NAS100,
        core_signal=core_signal,
        scalp_signal=None,
        market_regime=regime_b,
        core_metrics=None,
        scalp_metrics=None
    )
    
    print(f"Volatility: {regime_b.volatility.value}")
    print(f"Trend: {regime_b.trend_strength.value}")
    print(f"Signal: Core Strategy A+")
    print(f"Decision: {decision_b.engine.value if decision_b.engine else 'NO TRADE'}")
    print(f"Reason: {decision_b.reason}")


def example_3_performance_tiebreaker():
    """
    Example 3: Performance-based tiebreaker.
    
    When both engines are suitable for the regime, recent performance
    metrics are used to break the tie.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Performance Tiebreaker")
    print("="*80)
    
    engine = AutoTradeDecisionEngine()
    
    # Both engines suitable regime
    regime = MarketRegime(
        instrument=Instrument.US30,
        volatility=VolatilityRegime.HIGH,
        trend_strength=TrendStrength.WEAK_TREND,
        atr_current=180.0,
        atr_average=100.0,
        timestamp=datetime.now()
    )
    
    # Core Strategy A signal (not A+, so tiebreaker applies)
    core_signal = CoreSignal(
        instrument=Instrument.US30,
        direction=Direction.LONG,
        entry_price=42000.0,
        stop_loss=41900.0,
        tp1=42100.0,
        tp2=42200.0,
        confluence_score=ConfluenceScore(
            total=78,
            htf_alignment=18,
            key_level=15,
            liquidity_sweep=15,
            fvg=15,
            displacement=10,
            mss=5,
            vwap=0,
            volume_spike=0,
            atr=0,
            htf_target=0,
            session=0,
            spread=0
        ),
        grade=SignalGrade.A,
        timestamp=datetime.now()
    )
    
    scalp_signal = ScalpSignal(
        instrument=Instrument.US30,
        direction=Direction.LONG,
        entry_price=42000.0,
        stop_loss=41980.0,
        take_profit=42020.0,
        session=SessionType.LONDON,
        timestamp=datetime.now()
    )
    
    # Scenario A: Scalp outperforming
    print("\n--- Scenario A: Scalp Outperforming ---")
    
    core_metrics_poor = PerformanceMetrics(
        win_rate=0.40,
        profit_factor=1.2,
        average_rr=1.5,
        total_trades=20,
        winning_trades=8,
        losing_trades=12
    )
    
    scalp_metrics_good = PerformanceMetrics(
        win_rate=0.65,
        profit_factor=1.8,
        average_rr=1.0,
        total_trades=50,
        winning_trades=32,
        losing_trades=18
    )
    
    decision_a = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=core_metrics_poor,
        scalp_metrics=scalp_metrics_good
    )
    
    print(f"Core Performance: {core_metrics_poor.win_rate:.1%} win rate, {core_metrics_poor.profit_factor:.2f} PF")
    print(f"Scalp Performance: {scalp_metrics_good.win_rate:.1%} win rate, {scalp_metrics_good.profit_factor:.2f} PF")
    print(f"Decision: {decision_a.engine.value if decision_a.engine else 'NO TRADE'}")
    print(f"Reason: {decision_a.reason}")
    
    # Scenario B: Core performing better
    print("\n--- Scenario B: Core Performing Better ---")
    
    core_metrics_good = PerformanceMetrics(
        win_rate=0.55,
        profit_factor=2.1,
        average_rr=2.0,
        total_trades=20,
        winning_trades=11,
        losing_trades=9
    )
    
    scalp_metrics_ok = PerformanceMetrics(
        win_rate=0.58,
        profit_factor=1.4,
        average_rr=0.9,
        total_trades=50,
        winning_trades=29,
        losing_trades=21
    )
    
    decision_b = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=scalp_signal,
        market_regime=regime,
        core_metrics=core_metrics_good,
        scalp_metrics=scalp_metrics_ok
    )
    
    print(f"Core Performance: {core_metrics_good.win_rate:.1%} win rate, {core_metrics_good.profit_factor:.2f} PF")
    print(f"Scalp Performance: {scalp_metrics_ok.win_rate:.1%} win rate, {scalp_metrics_ok.profit_factor:.2f} PF")
    print(f"Decision: {decision_b.engine.value if decision_b.engine else 'NO TRADE'}")
    print(f"Reason: {decision_b.reason}")


def example_4_position_blocking():
    """
    Example 4: Active position blocks both engines.
    
    When an instrument already has an active position, both engines
    are blocked from trading that instrument.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Active Position Blocking")
    print("="*80)
    
    engine = AutoTradeDecisionEngine()
    
    # Register active position
    engine.register_position_opened(Instrument.US30, EngineType.CORE_STRATEGY)
    print(f"\nActive Position: US30 - Core Strategy")
    
    regime = MarketRegime(
        instrument=Instrument.US30,
        volatility=VolatilityRegime.HIGH,
        trend_strength=TrendStrength.STRONG_TREND,
        atr_current=200.0,
        atr_average=100.0,
        timestamp=datetime.now()
    )
    
    # Even with A+ signal, should be blocked
    core_signal = CoreSignal(
        instrument=Instrument.US30,
        direction=Direction.SHORT,  # Opposite direction
        entry_price=42000.0,
        stop_loss=42100.0,
        tp1=41900.0,
        tp2=41800.0,
        confluence_score=ConfluenceScore(
            total=92,
            htf_alignment=20,
            key_level=15,
            liquidity_sweep=15,
            fvg=15,
            displacement=10,
            mss=10,
            vwap=5,
            volume_spike=2,
            atr=0,
            htf_target=0,
            session=0,
            spread=0
        ),
        grade=SignalGrade.A_PLUS,
        timestamp=datetime.now()
    )
    
    decision = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=None,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    print(f"\nNew Signal: Core Strategy A+ (92 points)")
    print(f"Direction: SHORT (opposite to active position)")
    print(f"\n{'='*40}")
    print(f"DECISION: {decision.engine.value if decision.engine else 'NO TRADE'}")
    print(f"Reason: {decision.reason}")
    print(f"{'='*40}")
    
    # Close position and try again
    print("\n--- After Closing Position ---")
    engine.register_position_closed(Instrument.US30)
    print("Position Closed: US30")
    
    decision_after = engine.decide_trade(
        instrument=Instrument.US30,
        core_signal=core_signal,
        scalp_signal=None,
        market_regime=regime,
        core_metrics=None,
        scalp_metrics=None
    )
    
    print(f"\nSame Signal: Core Strategy A+ (92 points)")
    print(f"{'='*40}")
    print(f"DECISION: {decision_after.engine.value if decision_after.engine else 'NO TRADE'}")
    print(f"Reason: {decision_after.reason}")
    print(f"{'='*40}")


def example_5_engine_preference():
    """
    Example 5: Getting engine preference for monitoring.
    
    The decision engine can provide general guidance about which engine
    is preferred for the current market regime, useful for UI display.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Engine Preference for Monitoring")
    print("="*80)
    
    engine = AutoTradeDecisionEngine()
    
    regimes = [
        ("High Vol + Trending", MarketRegime(
            instrument=Instrument.US30,
            volatility=VolatilityRegime.HIGH,
            trend_strength=TrendStrength.STRONG_TREND,
            atr_current=200.0,
            atr_average=100.0,
            timestamp=datetime.now()
        )),
        ("Normal Vol + Trending", MarketRegime(
            instrument=Instrument.US30,
            volatility=VolatilityRegime.NORMAL,
            trend_strength=TrendStrength.WEAK_TREND,
            atr_current=100.0,
            atr_average=100.0,
            timestamp=datetime.now()
        )),
        ("High Vol + Ranging", MarketRegime(
            instrument=Instrument.US30,
            volatility=VolatilityRegime.HIGH,
            trend_strength=TrendStrength.RANGING,
            atr_current=200.0,
            atr_average=100.0,
            timestamp=datetime.now()
        )),
        ("Low Vol + Choppy", MarketRegime(
            instrument=Instrument.US30,
            volatility=VolatilityRegime.LOW,
            trend_strength=TrendStrength.CHOPPY,
            atr_current=50.0,
            atr_average=100.0,
            timestamp=datetime.now()
        ))
    ]
    
    for name, regime in regimes:
        preference = engine.get_engine_preference(regime)
        
        print(f"\n--- {name} ---")
        print(f"Preferred Engine: {preference.preferred_engine.value if preference.preferred_engine else 'NONE'}")
        print(f"Allow Core: {preference.allow_core_strategy}")
        print(f"Allow Scalp: {preference.allow_quick_scalp}")
        print(f"Confidence: {preference.confidence:.1%}")
        print(f"Reason: {preference.reason}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("AUTO-TRADE DECISION ENGINE - USAGE EXAMPLES")
    print("="*80)
    
    example_1_core_a_plus_priority()
    example_2_regime_based_selection()
    example_3_performance_tiebreaker()
    example_4_position_blocking()
    example_5_engine_preference()
    
    print("\n" + "="*80)
    print("EXAMPLES COMPLETE")
    print("="*80 + "\n")
