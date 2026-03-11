# Performance Tracking Implementation - Complete

## What Was Built

The **Performance Tracker** - enables the Auto-Trade Decision Engine to learn from experience and make intelligent tiebreaker decisions.

## Files Created

1. **`backend/strategy/performance_tracker.py`** (450+ lines)
   - `PerformanceTracker` class
   - Separate tracking per engine + instrument
   - Rolling window (last 20 trades) and lifetime metrics
   - Consecutive wins/losses tracking
   - Max drawdown calculation
   - Comprehensive summary generation

2. **`backend/tests/test_performance_tracker.py`** (450+ lines)
   - 15 comprehensive tests
   - All passing ✓
   - Tests all tracking scenarios
   - Tests edge cases

## What It Tracks

### Per Engine + Instrument

Tracks separately for:
- Core Strategy + US30
- Core Strategy + XAUUSD
- Core Strategy + NAS100
- Quick Scalp + US30
- Quick Scalp + XAUUSD
- Quick Scalp + NAS100

### Metrics Tracked

**Rolling Window (last 20 trades):**
- Win rate
- Average R multiple
- Profit factor
- Total trades
- Winning trades
- Losing trades

**Lifetime (all trades):**
- Same metrics as rolling
- Never resets

**Additional Tracking:**
- Consecutive wins (current streak)
- Consecutive losses (current streak)
- Maximum drawdown
- Trade count

## Usage Example

```python
from backend.strategy.performance_tracker import PerformanceTracker
from backend.strategy.dual_engine_models import EngineType, Instrument

# Initialize tracker
tracker = PerformanceTracker(rolling_window_size=20)

# Record a trade
tracker.record_trade(
    trade_id="trade_001",
    engine=EngineType.CORE_STRATEGY,
    instrument=Instrument.US30,
    win=True,
    r_multiple=2.0,
    profit_loss=200.0
)

# Get rolling metrics (last 20 trades)
rolling_metrics = tracker.get_rolling_metrics(
    engine=EngineType.CORE_STRATEGY,
    instrument=Instrument.US30  # Optional: None = all instruments
)

print(f"Win Rate: {rolling_metrics.win_rate:.1%}")
print(f"Avg R: {rolling_metrics.average_rr:.2f}")
print(f"Profit Factor: {rolling_metrics.profit_factor:.2f}")
print(f"Total Trades: {rolling_metrics.total_trades}")

# Get lifetime metrics
lifetime_metrics = tracker.get_lifetime_metrics(
    engine=EngineType.CORE_STRATEGY
)

# Get consecutive streaks
consecutive_wins = tracker.get_consecutive_wins(
    EngineType.CORE_STRATEGY,
    Instrument.US30
)

consecutive_losses = tracker.get_consecutive_losses(
    EngineType.CORE_STRATEGY,
    Instrument.US30
)

# Get max drawdown
max_dd = tracker.get_max_drawdown(
    EngineType.CORE_STRATEGY,
    Instrument.US30
)
```

## Integration with Decision Engine

The performance tracker feeds directly into the Auto-Trade Decision Engine's tiebreaker logic:

```python
from backend.strategy.performance_tracker import PerformanceTracker
from backend.strategy.auto_trade_decision_engine import AutoTradeDecisionEngine

# Initialize both
tracker = PerformanceTracker()
decision_engine = AutoTradeDecisionEngine()

# ... record trades as they complete ...

# When making decisions, pass performance metrics
core_metrics = tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
scalp_metrics = tracker.get_rolling_metrics(EngineType.QUICK_SCALP)

decision = decision_engine.decide_trade(
    instrument=Instrument.US30,
    core_signal=core_signal,
    scalp_signal=scalp_signal,
    market_regime=regime,
    core_metrics=core_metrics,  # <-- Performance feeds here
    scalp_metrics=scalp_metrics  # <-- Performance feeds here
)
```

## How Tiebreaker Works

When both engines are suitable for the regime, the decision engine calculates performance scores:

```python
core_score = (
    core_metrics.win_rate * 0.4 +
    min(core_metrics.profit_factor / 3.0, 1.0) * 0.3 +
    min(core_metrics.average_rr / 2.0, 1.0) * 0.3
)

scalp_score = (
    scalp_metrics.win_rate * 0.4 +
    min(scalp_metrics.profit_factor / 2.0, 1.0) * 0.3 +
    min(scalp_metrics.average_rr / 1.0, 1.0) * 0.3
)

# Scalp must score >10% higher to override Core default
if scalp_score > core_score * 1.1:
    return QUICK_SCALP
else:
    return CORE_STRATEGY
```

## Real-World Example

```python
# After 20 trades, Core Strategy metrics:
core_metrics = PerformanceMetrics(
    win_rate=0.45,
    profit_factor=2.1,
    average_rr=2.0,
    total_trades=20,
    winning_trades=9,
    losing_trades=11
)

# After 50 trades, Quick Scalp metrics:
scalp_metrics = PerformanceMetrics(
    win_rate=0.62,
    profit_factor=1.6,
    average_rr=0.9,
    total_trades=50,
    winning_trades=31,
    losing_trades=19
)

# Decision engine calculates:
# core_score = (0.45 * 0.4) + (0.7 * 0.3) + (1.0 * 0.3) = 0.69
# scalp_score = (0.62 * 0.4) + (0.8 * 0.3) + (0.9 * 0.3) = 0.76

# scalp_score (0.76) > core_score (0.69) * 1.1 (0.76)?
# 0.76 > 0.76? No, equal
# → Decision: Core Strategy (default when close)
```

## Comprehensive Summary

Get full summary for an engine:

```python
summary = tracker.get_summary(EngineType.CORE_STRATEGY)

# Returns:
{
    "engine": "CORE_STRATEGY",
    "rolling": {
        "win_rate": 0.55,
        "profit_factor": 2.1,
        "average_rr": 1.8,
        "total_trades": 20,
        "winning_trades": 11,
        "losing_trades": 9
    },
    "lifetime": {
        "win_rate": 0.52,
        "profit_factor": 1.9,
        "average_rr": 1.7,
        "total_trades": 45,
        "winning_trades": 23,
        "losing_trades": 22
    },
    "by_instrument": {
        "US30": {
            "rolling": {...},
            "lifetime": {...},
            "consecutive_wins": 2,
            "consecutive_losses": 0,
            "max_drawdown": 350.0
        },
        "XAUUSD": {...},
        "NAS100": {...}
    }
}
```

## Test Results

All 15 tests passing:

```
✓ test_empty_history
✓ test_only_wins
✓ test_only_losses
✓ test_mixed_results
✓ test_rolling_window_updates
✓ test_per_instrument_separation
✓ test_per_engine_separation
✓ test_consecutive_wins_tracking
✓ test_consecutive_losses_tracking
✓ test_max_drawdown_tracking
✓ test_trade_count
✓ test_clear_history
✓ test_summary_generation
✓ test_timestamp_ordering
✓ test_multiple_instruments_combined
```

## Key Features

1. **Separate Tracking**: Each engine+instrument combination tracked independently
2. **Rolling Window**: Last 20 trades for recent performance
3. **Lifetime Stats**: All-time performance never resets
4. **Streak Tracking**: Consecutive wins/losses for risk management
5. **Drawdown Monitoring**: Maximum drawdown per engine+instrument
6. **Efficient Storage**: Uses deque for automatic rolling window management

## What's Next

Performance tracking is complete. Next steps:

1. ✓ **Regime Detection** - DONE
2. ✓ **Performance Tracking** - DONE
3. **Signal Contract** - Normalize Core + Scalp outputs
4. **Integration** - Wire everything together
5. **Replay Tests** - Real scenario testing

## Production Readiness

The performance tracker is production-ready:

- ✓ All tests passing
- ✓ Handles edge cases (empty history, only wins, only losses)
- ✓ Efficient rolling window (deque with maxlen)
- ✓ Separate tracking per engine + instrument
- ✓ Clear, documented API
- ✓ Comprehensive summary generation

The decision engine can now learn from experience. It has eyes (regime detection) and memory (performance tracking).

Next: Normalize signal contracts so both engines speak the same language.
