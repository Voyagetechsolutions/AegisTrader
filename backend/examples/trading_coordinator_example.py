"""
Trading Coordinator Example - Complete End-to-End Flow

This demonstrates the full integration:
Market Data → Regime Detection → Strategy Engines → Decision Engine →
Risk Validation → Signal Routing → Execution → Performance Tracking
"""

from datetime import datetime, timedelta
from backend.strategy.trading_coordinator import TradingCoordinator, CoordinatorConfig
from backend.strategy.dual_engine_models import (
    Instrument,
    Direction,
    EngineType,
    SignalGrade,
    CoreSignal,
    ScalpSignal,
    ConfluenceScore,
    SessionType,
    OHLCVBar
)
from backend.strategy.session_manager import SessionManager


# Simple mock for news filter (real implementation is async)
class MockNewsFilter:
    """Mock news filter for examples."""
    def is_blocked(self, timestamp):
        return False


# Example: Mock Strategy Engines
class ExampleCoreEngine:
    """Example Core Strategy Engine."""
    
    def analyze_setup(self, instrument, bars, regime):
        """Analyze for Core Strategy setup."""
        # In real implementation, this would analyze:
        # - HTF alignment
        # - Key levels
        # - Liquidity sweeps
        # - FVG
        # - Displacement
        # - MSS
        
        # Example: Generate A+ signal on strong trend + high confluence
        from backend.strategy.auto_trade_decision_engine import TrendStrength
        if regime.trend_strength in [TrendStrength.STRONG_TREND, TrendStrength.WEAK_TREND]:
            return CoreSignal(
                instrument=instrument,
                direction=Direction.LONG,
                entry_price=bars[-1].close,
                stop_loss=bars[-1].close - 100.0,
                tp1=bars[-1].close + 150.0,
                tp2=bars[-1].close + 300.0,
                confluence_score=ConfluenceScore(
                    total=85,
                    htf_alignment=20,
                    key_level=15,
                    liquidity_sweep=15,
                    fvg=15,
                    displacement=10,
                    mss=10,
                    vwap=0,
                    volume_spike=0,
                    atr=0,
                    htf_target=0,
                    session=0,
                    spread=0
                ),
                grade=SignalGrade.A_PLUS,
                timestamp=datetime.now()
            )
        
        return None


class ExampleScalpEngine:
    """Example Quick Scalp Engine."""
    
    def analyze_scalp_setup(self, instrument, bars, regime):
        """Analyze for Quick Scalp setup."""
        # In real implementation, this would analyze:
        # - Micro structure breaks
        # - Liquidity grabs
        # - Quick reversals
        # - Session volatility
        
        # Example: Generate scalp signal on high volatility + ranging
        from backend.strategy.auto_trade_decision_engine import VolatilityRegime, TrendStrength
        if (regime.volatility == VolatilityRegime.HIGH and 
            regime.trend_strength == TrendStrength.RANGING):
            return ScalpSignal(
                instrument=instrument,
                direction=Direction.SHORT,
                entry_price=bars[-1].close,
                stop_loss=bars[-1].close + 20.0,
                take_profit=bars[-1].close - 30.0,
                session=SessionType.LONDON,
                timestamp=datetime.now()
            )
        
        return None


# Example: Execution Handler
class ExampleExecutionHandler:
    """Example execution handler that routes signals to MT5/Telegram."""
    
    def __init__(self):
        self.executed_signals = []
    
    def handle(self, signal):
        """Handle signal execution."""
        print(f"\n{'='*60}")
        print(f"EXECUTING SIGNAL")
        print(f"{'='*60}")
        print(f"Engine: {signal.engine.value}")
        print(f"Instrument: {signal.instrument.value}")
        print(f"Direction: {signal.direction.value}")
        print(f"Entry: {signal.entry_price:.2f}")
        print(f"Stop Loss: {signal.stop_loss:.2f}")
        print(f"Take Profit 1: {signal.tp1:.2f}")
        if signal.tp2:
            print(f"Take Profit 2: {signal.tp2:.2f}")
        print(f"Risk/Reward: {signal.risk_reward_ratio:.2f}R")
        print(f"{'='*60}\n")
        
        self.executed_signals.append(signal)
        
        # In real implementation:
        # - Send to MT5 via MQL5 bridge
        # - Send notification to Telegram
        # - Log to database
        
        return True


def generate_market_data(instrument, volatility_level="normal", trend="ranging"):
    """Generate example market data."""
    bars = []
    base_price = 42000.0 if instrument == Instrument.US30 else 2000.0
    timestamp = datetime.now() - timedelta(hours=250)
    
    # Adjust volatility based on level
    if volatility_level == "low":
        vol_base = 20.0
        vol_recent = 25.0
    elif volatility_level == "high":
        vol_base = 50.0
        vol_recent = 100.0  # Spike for HIGH regime
    elif volatility_level == "extreme":
        vol_base = 50.0
        vol_recent = 150.0  # Spike for EXTREME regime
    else:  # normal
        vol_base = 50.0
        vol_recent = 50.0
    
    for i in range(250):
        # Use recent volatility for last 50 bars
        vol = vol_recent if i >= 200 else vol_base
        
        # Apply trend
        if trend == "up":
            base_price += vol * 0.05
        elif trend == "down":
            base_price -= vol * 0.05
        
        bars.append(OHLCVBar(
            timestamp=timestamp + timedelta(hours=i),
            open=base_price,
            high=base_price + vol,
            low=base_price - vol,
            close=base_price + (vol * 0.5),
            volume=1000.0
        ))
    
    return bars


def example_1_core_strategy_signal():
    """Example 1: Core Strategy signal in trending market."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Core Strategy Signal (Trending Market)")
    print("="*60)
    
    # Configure coordinator
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=SessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=ExampleCoreEngine(),
        scalp_strategy_engine=ExampleScalpEngine()
    )
    
    # Register execution handler
    handler = ExampleExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    # Generate trending market data
    bars = generate_market_data(
        instrument=Instrument.US30,
        volatility_level="normal",
        trend="up"
    )
    
    # Process market data
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=2.0
    )
    
    if signal:
        print(f"[OK] Signal generated and executed")
        print(f"  Active signals: {len(coordinator.get_active_signals())}")
    else:
        print(f"[X] No signal generated")


def example_2_scalp_signal():
    """Example 2: Quick Scalp signal in high volatility ranging market."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Quick Scalp Signal (High Volatility + Ranging)")
    print("="*60)
    
    config = CoordinatorConfig(
        instruments=[Instrument.XAUUSD],
        spread_limits_global={Instrument.XAUUSD: 3.0},
        spread_limits_scalp={Instrument.XAUUSD: 2.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=SessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=ExampleCoreEngine(),
        scalp_strategy_engine=ExampleScalpEngine()
    )
    
    handler = ExampleExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    # Generate high volatility ranging market
    bars = generate_market_data(
        instrument=Instrument.XAUUSD,
        volatility_level="high",
        trend="ranging"
    )
    
    signal = coordinator.process_market_data(
        instrument=Instrument.XAUUSD,
        bars=bars,
        current_spread=1.5
    )
    
    if signal:
        print(f"[OK] Signal generated and executed")
    else:
        print(f"[X] No signal generated")


def example_3_spread_rejection():
    """Example 3: Signal rejected due to wide spread."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Spread Rejection")
    print("="*60)
    
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=SessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=ExampleCoreEngine(),
        scalp_strategy_engine=ExampleScalpEngine()
    )
    
    handler = ExampleExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    bars = generate_market_data(Instrument.US30, trend="up")
    
    # Try with wide spread
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=10.0  # Too wide
    )
    
    if signal:
        print(f"[X] Signal should have been rejected")
    else:
        print(f"[OK] Signal correctly rejected due to wide spread (10.0 > 5.0)")


def example_4_performance_tracking():
    """Example 4: Performance tracking across multiple trades."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Performance Tracking")
    print("="*60)
    
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=SessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=ExampleCoreEngine(),
        scalp_strategy_engine=ExampleScalpEngine()
    )
    
    handler = ExampleExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    bars = generate_market_data(Instrument.US30, trend="up")
    
    # Trade 1: Win
    signal1 = coordinator.process_market_data(Instrument.US30, bars, 2.0)
    if signal1:
        coordinator.record_trade_outcome(
            signal_id=signal1.signal_id,
            win=True,
            r_multiple=2.5,
            profit_loss=250.0
        )
        print(f"Trade 1: WIN (+2.5R, +$250)")
    
    # Trade 2: Loss
    signal2 = coordinator.process_market_data(Instrument.US30, bars, 2.0)
    if signal2:
        coordinator.record_trade_outcome(
            signal_id=signal2.signal_id,
            win=False,
            r_multiple=-1.0,
            profit_loss=-100.0
        )
        print(f"Trade 2: LOSS (-1.0R, -$100)")
    
    # Trade 3: Win
    signal3 = coordinator.process_market_data(Instrument.US30, bars, 2.0)
    if signal3:
        coordinator.record_trade_outcome(
            signal_id=signal3.signal_id,
            win=True,
            r_multiple=1.8,
            profit_loss=180.0
        )
        print(f"Trade 3: WIN (+1.8R, +$180)")
    
    # Get performance metrics
    metrics = coordinator.performance_tracker.get_rolling_metrics(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    
    print(f"\n{'='*60}")
    print(f"PERFORMANCE METRICS (Core Strategy - US30)")
    print(f"{'='*60}")
    print(f"Total Trades: {metrics.total_trades}")
    print(f"Win Rate: {metrics.win_rate*100:.1f}%")
    print(f"Average R: {metrics.average_rr:.2f}R")
    print(f"Profit Factor: {metrics.profit_factor:.2f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TRADING COORDINATOR - COMPLETE INTEGRATION EXAMPLES")
    print("="*60)
    
    # Run examples
    example_1_core_strategy_signal()
    example_2_scalp_signal()
    example_3_spread_rejection()
    example_4_performance_tracking()
    
    print("\n" + "="*60)
    print("All examples completed")
    print("="*60 + "\n")

