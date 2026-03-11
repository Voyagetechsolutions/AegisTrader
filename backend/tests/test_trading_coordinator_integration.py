"""
Integration tests for Trading Coordinator.

Tests the complete end-to-end flow:
Market Data → Regime Detection → Strategy Engines → Decision Engine →
Risk Validation → Signal Routing → Execution → Performance Tracking
"""

import pytest
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
from backend.strategy.unified_signal import SignalStatus


# Mock session manager
class MockSessionManager:
    def is_signal_permitted(self, timestamp, engine):
        return True


# Mock news filter
class MockNewsFilter:
    def is_blocked(self, timestamp):
        return False


# Mock execution handler
class MockExecutionHandler:
    def __init__(self):
        self.executed_signals = []
    
    def handle(self, signal):
        self.executed_signals.append(signal)
        return True


# Mock Core Strategy Engine
class MockCoreEngine:
    def __init__(self, should_signal=True):
        self.should_signal = should_signal
    
    def analyze_setup(self, instrument, bars, regime):
        if not self.should_signal:
            return None
        
        # Generate A+ signal
        return CoreSignal(
            instrument=instrument,
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


# Mock Quick Scalp Engine
class MockScalpEngine:
    def __init__(self, should_signal=True):
        self.should_signal = should_signal
    
    def analyze_scalp_setup(self, instrument, bars, regime):
        if not self.should_signal:
            return None
        
        return ScalpSignal(
            instrument=instrument,
            direction=Direction.SHORT,
            entry_price=42000.0,
            stop_loss=42020.0,
            take_profit=41980.0,
            session=SessionType.LONDON,
            timestamp=datetime.now()
        )


def generate_test_bars(count=250, volatility=100.0, trend="up"):
    """Generate test OHLCV bars."""
    bars = []
    base_price = 42000.0
    timestamp = datetime.now() - timedelta(hours=count)
    
    for i in range(count):
        if trend == "up":
            base_price += volatility * 0.05
        elif trend == "down":
            base_price -= volatility * 0.05
        
        bars.append(OHLCVBar(
            timestamp=timestamp + timedelta(hours=i),
            open=base_price,
            high=base_price + volatility,
            low=base_price - volatility,
            close=base_price + (volatility * 0.5),
            volume=1000.0
        ))
    
    return bars


def test_coordinator_initialization():
    """Test coordinator initializes correctly."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30, Instrument.XAUUSD],
        spread_limits_global={
            Instrument.US30: 5.0,
            Instrument.XAUUSD: 3.0
        },
        spread_limits_scalp={
            Instrument.US30: 3.0,
            Instrument.XAUUSD: 2.0
        }
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter()
    )
    
    assert coordinator.config == config
    assert coordinator.regime_detector is not None
    assert coordinator.decision_engine is not None
    assert coordinator.performance_tracker is not None


def test_end_to_end_core_strategy_signal():
    """Test complete flow with Core Strategy signal."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True),
        scalp_strategy_engine=MockScalpEngine(should_signal=False)
    )
    
    # Register execution handler
    handler = MockExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    # Process market data
    bars = generate_test_bars(count=250, volatility=100.0, trend="up")
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=2.0
    )
    
    # Verify signal generated
    assert signal is not None
    assert signal.engine == EngineType.CORE_STRATEGY
    assert signal.status == SignalStatus.EXECUTED
    assert signal.instrument == Instrument.US30
    assert signal.direction == Direction.LONG
    
    # Verify execution
    assert len(handler.executed_signals) == 1
    assert handler.executed_signals[0].signal_id == signal.signal_id
    
    # Verify active signals
    active = coordinator.get_active_signals()
    assert len(active) == 1
    assert active[0].signal_id == signal.signal_id


def test_end_to_end_scalp_signal():
    """Test complete flow with Quick Scalp signal."""
    config = CoordinatorConfig(
        instruments=[Instrument.XAUUSD],
        spread_limits_global={Instrument.XAUUSD: 3.0},
        spread_limits_scalp={Instrument.XAUUSD: 2.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=False),
        scalp_strategy_engine=MockScalpEngine(should_signal=True)
    )
    
    handler = MockExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    # Generate bars with volatility spike to create HIGH volatility regime
    # Need ATR ratio between 1.5x and 2.5x for HIGH volatility
    # First 200 bars: low volatility (50.0)
    # Last 50 bars: higher volatility (100.0) - creates ATR ratio ~2.0x
    bars = []
    base_price = 42000.0
    timestamp = datetime.now() - timedelta(hours=250)
    
    for i in range(250):
        vol = 50.0 if i < 200 else 100.0  # Moderate volatility spike
        bars.append(OHLCVBar(
            timestamp=timestamp + timedelta(hours=i),
            open=base_price,
            high=base_price + vol,
            low=base_price - vol,
            close=base_price + (vol * 0.5),
            volume=1000.0
        ))
    
    signal = coordinator.process_market_data(
        instrument=Instrument.XAUUSD,
        bars=bars,
        current_spread=1.5
    )
    
    assert signal is not None
    assert signal.engine == EngineType.QUICK_SCALP
    assert signal.status == SignalStatus.EXECUTED
    assert len(handler.executed_signals) == 1


def test_both_engines_signal_core_wins():
    """Test that Core Strategy A+ wins when both engines signal."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True),
        scalp_strategy_engine=MockScalpEngine(should_signal=True)
    )
    
    handler = MockExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    bars = generate_test_bars(count=250)
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=2.0
    )
    
    # Core Strategy should win
    assert signal is not None
    assert signal.engine == EngineType.CORE_STRATEGY


def test_spread_rejection():
    """Test that signal is rejected when spread too wide."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True)
    )
    
    handler = MockExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    bars = generate_test_bars(count=250)
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=10.0  # Too wide
    )
    
    # Signal should be rejected
    assert signal is None
    assert len(handler.executed_signals) == 0


def test_performance_tracking():
    """Test that trade outcomes are tracked correctly."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True)
    )
    
    handler = MockExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    # Generate signal
    bars = generate_test_bars(count=250)
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=2.0
    )
    
    assert signal is not None
    
    # Record trade outcome
    coordinator.record_trade_outcome(
        signal_id=signal.signal_id,
        win=True,
        r_multiple=2.0,
        profit_loss=200.0
    )
    
    # Verify performance tracked
    metrics = coordinator.performance_tracker.get_rolling_metrics(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    
    assert metrics.total_trades == 1
    assert metrics.winning_trades == 1
    assert metrics.win_rate == 1.0
    assert metrics.average_rr == 2.0
    
    # Verify position closed
    assert len(coordinator.get_active_signals()) == 0


def test_regime_detection():
    """Test that regime is detected and stored."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True)
    )
    
    bars = generate_test_bars(count=250, volatility=100.0, trend="up")
    coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=2.0
    )
    
    # Verify regime detected
    regime = coordinator.get_current_regime(Instrument.US30)
    assert regime is not None
    assert regime.instrument == Instrument.US30
    assert regime.atr_current > 0
    assert regime.atr_average > 0


def test_insufficient_bars():
    """Test that insufficient bars returns None."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True)
    )
    
    # Only 50 bars (need 250)
    bars = generate_test_bars(count=50)
    signal = coordinator.process_market_data(
        instrument=Instrument.US30,
        bars=bars,
        current_spread=2.0
    )
    
    assert signal is None


def test_multiple_trades_performance():
    """Test performance tracking across multiple trades."""
    config = CoordinatorConfig(
        instruments=[Instrument.US30],
        spread_limits_global={Instrument.US30: 5.0},
        spread_limits_scalp={Instrument.US30: 3.0}
    )
    
    coordinator = TradingCoordinator(
        config=config,
        session_manager=MockSessionManager(),
        news_filter=MockNewsFilter(),
        core_strategy_engine=MockCoreEngine(should_signal=True)
    )
    
    handler = MockExecutionHandler()
    coordinator.register_execution_handler(handler)
    
    bars = generate_test_bars(count=250)
    
    # Trade 1: Win
    signal1 = coordinator.process_market_data(Instrument.US30, bars, 2.0)
    coordinator.record_trade_outcome(signal1.signal_id, win=True, r_multiple=2.0, profit_loss=200.0)
    
    # Trade 2: Loss
    signal2 = coordinator.process_market_data(Instrument.US30, bars, 2.0)
    coordinator.record_trade_outcome(signal2.signal_id, win=False, r_multiple=-1.0, profit_loss=-100.0)
    
    # Trade 3: Win
    signal3 = coordinator.process_market_data(Instrument.US30, bars, 2.0)
    coordinator.record_trade_outcome(signal3.signal_id, win=True, r_multiple=1.5, profit_loss=150.0)
    
    # Check metrics
    metrics = coordinator.performance_tracker.get_rolling_metrics(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    
    assert metrics.total_trades == 3
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert abs(metrics.win_rate - 0.667) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
