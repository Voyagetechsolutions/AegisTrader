"""
Tests for Performance Tracking Module.

Verifies that performance metrics are correctly calculated and tracked
separately by engine and instrument, with both rolling and lifetime windows.
"""

import pytest
from datetime import datetime, timedelta
from backend.strategy.performance_tracker import PerformanceTracker
from backend.strategy.dual_engine_models import (
    Instrument,
    EngineType,
    PerformanceMetrics
)


def test_empty_history():
    """Test that empty history returns zero metrics."""
    tracker = PerformanceTracker()
    
    metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    
    assert metrics.win_rate == 0.0
    assert metrics.profit_factor == 0.0
    assert metrics.average_rr == 0.0
    assert metrics.total_trades == 0
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 0


def test_only_wins():
    """Test metrics with only winning trades."""
    tracker = PerformanceTracker()
    
    # Record 5 winning trades
    for i in range(5):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    
    assert metrics.win_rate == 1.0  # 100%
    assert metrics.total_trades == 5
    assert metrics.winning_trades == 5
    assert metrics.losing_trades == 0
    assert metrics.average_rr == 2.0
    assert metrics.profit_factor == float('inf')  # No losses


def test_only_losses():
    """Test metrics with only losing trades."""
    tracker = PerformanceTracker()
    
    # Record 5 losing trades
    for i in range(5):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.QUICK_SCALP,
            instrument=Instrument.XAUUSD,
            win=False,
            r_multiple=-1.0,
            profit_loss=-100.0
        )
    
    metrics = tracker.get_rolling_metrics(EngineType.QUICK_SCALP)
    
    assert metrics.win_rate == 0.0  # 0%
    assert metrics.total_trades == 5
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 5
    assert metrics.average_rr == -1.0
    assert metrics.profit_factor == 0.0  # No wins


def test_mixed_results():
    """Test metrics with mixed winning and losing trades."""
    tracker = PerformanceTracker()
    
    # Record mixed trades: 6 wins, 4 losses
    trades = [
        (True, 2.0, 200.0),
        (False, -1.0, -100.0),
        (True, 1.5, 150.0),
        (True, 2.5, 250.0),
        (False, -1.0, -100.0),
        (True, 1.8, 180.0),
        (False, -0.8, -80.0),
        (True, 2.2, 220.0),
        (False, -1.0, -100.0),
        (True, 1.9, 190.0),
    ]
    
    for i, (win, r_mult, pnl) in enumerate(trades):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=win,
            r_multiple=r_mult,
            profit_loss=pnl
        )
    
    metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    
    assert metrics.win_rate == 0.6  # 60%
    assert metrics.total_trades == 10
    assert metrics.winning_trades == 6
    assert metrics.losing_trades == 4
    
    # Average R = (2.0 - 1.0 + 1.5 + 2.5 - 1.0 + 1.8 - 0.8 + 2.2 - 1.0 + 1.9) / 10
    expected_avg_r = (2.0 - 1.0 + 1.5 + 2.5 - 1.0 + 1.8 - 0.8 + 2.2 - 1.0 + 1.9) / 10
    assert abs(metrics.average_rr - expected_avg_r) < 0.01
    
    # Profit factor = gross profit / gross loss
    gross_profit = 200 + 150 + 250 + 180 + 220 + 190  # 1190
    gross_loss = 100 + 100 + 80 + 100  # 380
    expected_pf = gross_profit / gross_loss
    assert abs(metrics.profit_factor - expected_pf) < 0.01


def test_rolling_window_updates():
    """Test that rolling window correctly limits to last N trades."""
    tracker = PerformanceTracker(rolling_window_size=5)
    
    # Record 10 trades (more than window size)
    for i in range(10):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=(i % 2 == 0),  # Alternate wins/losses
            r_multiple=1.0 if (i % 2 == 0) else -1.0,
            profit_loss=100.0 if (i % 2 == 0) else -100.0
        )
    
    # Rolling should only have last 5 trades
    rolling_metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    assert rolling_metrics.total_trades == 5
    
    # Lifetime should have all 10 trades
    lifetime_metrics = tracker.get_lifetime_metrics(EngineType.CORE_STRATEGY)
    assert lifetime_metrics.total_trades == 10


def test_per_instrument_separation():
    """Test that metrics are tracked separately per instrument."""
    tracker = PerformanceTracker()
    
    # Record trades for US30 (all wins)
    for i in range(3):
        tracker.record_trade(
            trade_id=f"us30_trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    # Record trades for XAUUSD (all losses)
    for i in range(3):
        tracker.record_trade(
            trade_id=f"xauusd_trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.XAUUSD,
            win=False,
            r_multiple=-1.0,
            profit_loss=-100.0
        )
    
    # US30 should have 100% win rate
    us30_metrics = tracker.get_rolling_metrics(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    assert us30_metrics.win_rate == 1.0
    assert us30_metrics.total_trades == 3
    
    # XAUUSD should have 0% win rate
    xauusd_metrics = tracker.get_rolling_metrics(
        EngineType.CORE_STRATEGY,
        Instrument.XAUUSD
    )
    assert xauusd_metrics.win_rate == 0.0
    assert xauusd_metrics.total_trades == 3
    
    # Combined should have 50% win rate
    combined_metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    assert combined_metrics.win_rate == 0.5
    assert combined_metrics.total_trades == 6


def test_per_engine_separation():
    """Test that metrics are tracked separately per engine."""
    tracker = PerformanceTracker()
    
    # Core Strategy: 3 wins
    for i in range(3):
        tracker.record_trade(
            trade_id=f"core_trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    # Quick Scalp: 3 losses
    for i in range(3):
        tracker.record_trade(
            trade_id=f"scalp_trade_{i}",
            engine=EngineType.QUICK_SCALP,
            instrument=Instrument.US30,
            win=False,
            r_multiple=-1.0,
            profit_loss=-50.0
        )
    
    # Core should have 100% win rate
    core_metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    assert core_metrics.win_rate == 1.0
    assert core_metrics.total_trades == 3
    
    # Scalp should have 0% win rate
    scalp_metrics = tracker.get_rolling_metrics(EngineType.QUICK_SCALP)
    assert scalp_metrics.win_rate == 0.0
    assert scalp_metrics.total_trades == 3


def test_consecutive_wins_tracking():
    """Test consecutive wins counter."""
    tracker = PerformanceTracker()
    
    # Record 3 consecutive wins
    for i in range(3):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    consecutive_wins = tracker.get_consecutive_wins(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    assert consecutive_wins == 3
    
    # Record a loss (should reset)
    tracker.record_trade(
        trade_id="trade_loss",
        engine=EngineType.CORE_STRATEGY,
        instrument=Instrument.US30,
        win=False,
        r_multiple=-1.0,
        profit_loss=-100.0
    )
    
    consecutive_wins = tracker.get_consecutive_wins(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    assert consecutive_wins == 0


def test_consecutive_losses_tracking():
    """Test consecutive losses counter."""
    tracker = PerformanceTracker()
    
    # Record 4 consecutive losses
    for i in range(4):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.QUICK_SCALP,
            instrument=Instrument.XAUUSD,
            win=False,
            r_multiple=-1.0,
            profit_loss=-50.0
        )
    
    consecutive_losses = tracker.get_consecutive_losses(
        EngineType.QUICK_SCALP,
        Instrument.XAUUSD
    )
    assert consecutive_losses == 4
    
    # Record a win (should reset)
    tracker.record_trade(
        trade_id="trade_win",
        engine=EngineType.QUICK_SCALP,
        instrument=Instrument.XAUUSD,
        win=True,
        r_multiple=1.0,
        profit_loss=50.0
    )
    
    consecutive_losses = tracker.get_consecutive_losses(
        EngineType.QUICK_SCALP,
        Instrument.XAUUSD
    )
    assert consecutive_losses == 0


def test_max_drawdown_tracking():
    """Test maximum drawdown calculation."""
    tracker = PerformanceTracker()
    
    # Simulate trades with drawdown
    trades = [
        (True, 2.0, 200.0),   # Balance: 200
        (True, 2.0, 200.0),   # Balance: 400 (new peak)
        (False, -1.0, -100.0), # Balance: 300 (drawdown: 100)
        (False, -1.0, -100.0), # Balance: 200 (drawdown: 200)
        (True, 2.0, 200.0),   # Balance: 400 (back to peak)
    ]
    
    for i, (win, r_mult, pnl) in enumerate(trades):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=win,
            r_multiple=r_mult,
            profit_loss=pnl
        )
    
    max_dd = tracker.get_max_drawdown(
        EngineType.CORE_STRATEGY,
        Instrument.US30
    )
    assert max_dd == 200.0  # Maximum drawdown was 200


def test_trade_count():
    """Test trade count retrieval."""
    tracker = PerformanceTracker(rolling_window_size=5)
    
    # Record 10 trades
    for i in range(10):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    # Rolling count should be 5 (window size)
    rolling_count = tracker.get_trade_count(
        EngineType.CORE_STRATEGY,
        Instrument.US30,
        rolling=True
    )
    assert rolling_count == 5
    
    # Lifetime count should be 10
    lifetime_count = tracker.get_trade_count(
        EngineType.CORE_STRATEGY,
        Instrument.US30,
        rolling=False
    )
    assert lifetime_count == 10


def test_clear_history():
    """Test clearing trade history."""
    tracker = PerformanceTracker()
    
    # Record some trades
    for i in range(5):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    # Verify trades recorded
    assert tracker.get_trade_count(EngineType.CORE_STRATEGY) == 5
    
    # Clear history
    tracker.clear_history(EngineType.CORE_STRATEGY, Instrument.US30)
    
    # Verify cleared
    assert tracker.get_trade_count(EngineType.CORE_STRATEGY) == 0
    metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    assert metrics.total_trades == 0


def test_summary_generation():
    """Test comprehensive summary generation."""
    tracker = PerformanceTracker()
    
    # Record some trades
    for i in range(5):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=(i % 2 == 0),
            r_multiple=2.0 if (i % 2 == 0) else -1.0,
            profit_loss=200.0 if (i % 2 == 0) else -100.0
        )
    
    summary = tracker.get_summary(EngineType.CORE_STRATEGY)
    
    # Check structure
    assert "engine" in summary
    assert "rolling" in summary
    assert "lifetime" in summary
    assert "by_instrument" in summary
    
    # Check rolling metrics
    assert summary["rolling"]["total_trades"] == 5
    assert summary["rolling"]["win_rate"] == 0.6
    
    # Check per-instrument data
    assert "US30" in summary["by_instrument"]
    us30_data = summary["by_instrument"]["US30"]
    assert "rolling" in us30_data
    assert "lifetime" in us30_data
    assert "consecutive_wins" in us30_data
    assert "consecutive_losses" in us30_data
    assert "max_drawdown" in us30_data


def test_timestamp_ordering():
    """Test that trades are ordered by timestamp in rolling window."""
    tracker = PerformanceTracker(rolling_window_size=3)
    
    base_time = datetime.now()
    
    # Record trades with specific timestamps
    for i in range(5):
        tracker.record_trade(
            trade_id=f"trade_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0,
            timestamp=base_time + timedelta(minutes=i)
        )
    
    # Rolling window should have last 3 trades
    metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    assert metrics.total_trades == 3


def test_multiple_instruments_combined():
    """Test combined metrics across multiple instruments."""
    tracker = PerformanceTracker()
    
    # US30: 2 wins
    for i in range(2):
        tracker.record_trade(
            trade_id=f"us30_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.US30,
            win=True,
            r_multiple=2.0,
            profit_loss=200.0
        )
    
    # XAUUSD: 2 losses
    for i in range(2):
        tracker.record_trade(
            trade_id=f"xauusd_{i}",
            engine=EngineType.CORE_STRATEGY,
            instrument=Instrument.XAUUSD,
            win=False,
            r_multiple=-1.0,
            profit_loss=-100.0
        )
    
    # NAS100: 1 win
    tracker.record_trade(
        trade_id="nas100_0",
        engine=EngineType.CORE_STRATEGY,
        instrument=Instrument.NAS100,
        win=True,
        r_multiple=2.0,
        profit_loss=200.0
    )
    
    # Combined should be 3 wins, 2 losses
    combined_metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
    assert combined_metrics.total_trades == 5
    assert combined_metrics.winning_trades == 3
    assert combined_metrics.losing_trades == 2
    assert combined_metrics.win_rate == 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
