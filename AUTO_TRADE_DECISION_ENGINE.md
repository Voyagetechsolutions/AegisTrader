# Auto-Trade Decision Engine

## Overview

The Auto-Trade Decision Engine is the critical component that transforms two independent trading engines (Core Strategy and Quick Scalp) into a coordinated, intelligent trading system. Without this engine, the system would be chaotic—both engines could try to trade the same instrument simultaneously, leading to overtrading, conflicting positions, and poor risk management.

## The Problem It Solves

When you have two trading strategies running simultaneously, several problems arise:

1. **Conflicting Signals**: Both engines might generate signals for the same instrument at the same time
2. **Overtrading**: Without coordination, you could end up with too many positions
3. **Poor Risk Management**: Multiple positions on the same instrument multiply risk
4. **Regime Mismatch**: Trading with the wrong strategy for current market conditions
5. **Resource Waste**: Both engines consuming resources when only one should trade

## How It Works

### Decision Hierarchy

The engine uses a clear priority system:

```
1. Active Position Check
   ↓ (if no active position)
2. Signal Availability Check
   ↓ (if signals exist)
3. Single Signal Validation
   OR
   Conflict Resolution
   ↓
4. Final Trade Decision
```

### Priority Rules for Conflicts

When both engines have valid signals:

1. **Core Strategy A+ Always Wins**
   - These are the highest quality setups (85-100 confluence points)
   - They get absolute priority over any scalp signal
   - Reason: Higher R:R potential (2R+ vs 0.8-1R)

2. **Core Strategy A Evaluated by Regime**
   - Check if market regime suits Core Strategy
   - Check if market regime suits Quick Scalp
   - Winner determined by suitability

3. **Performance Tiebreaker**
   - If both engines suitable for regime
   - Compare recent performance metrics
   - Scalp must outperform Core by >10% to win
   - Default to Core Strategy (higher R:R potential)

## Market Regime Classification

### Volatility Regimes

The engine classifies volatility into four levels:

| Regime | ATR Range | Best For |
|--------|-----------|----------|
| LOW | < 0.8 × average | Neither engine (avoid trading) |
| NORMAL | 0.8-1.5 × average | Core Strategy |
| HIGH | 1.5-2.5 × average | Both engines (Quick Scalp preferred) |
| EXTREME | > 2.5 × average | Quick Scalp only (with caution) |

### Trend Strength

The engine evaluates trend strength across timeframes:

| Strength | Description | Best For |
|----------|-------------|----------|
| STRONG_TREND | Clear directional bias across HTFs | Core Strategy |
| WEAK_TREND | Some HTF alignment | Core Strategy |
| RANGING | No clear direction | Quick Scalp only |
| CHOPPY | Conflicting signals | Neither (avoid trading) |

## Engine Suitability Matrix

### Core Strategy Suitable When:
- Volatility: NORMAL or HIGH
- Trend: STRONG_TREND or WEAK_TREND

### Quick Scalp Suitable When:
- Volatility: HIGH or EXTREME
- Trend: Any (scalps work in all conditions)

## Example Scenarios

### Scenario 1: Core A+ vs Scalp Signal

```
Market: US30
Volatility: HIGH
Trend: STRONG_TREND

Core Signal: A+ (90 points)
Scalp Signal: Valid

Decision: Core Strategy trades
Reason: A+ signals have absolute priority
Blocked: Quick Scalp
```

### Scenario 2: Core A vs Scalp in High Volatility

```
Market: XAUUSD
Volatility: HIGH
Trend: RANGING

Core Signal: A (80 points)
Scalp Signal: Valid

Decision: Quick Scalp trades
Reason: Core unsuitable (ranging), Scalp suitable (high vol)
Blocked: Core Strategy
```

### Scenario 3: Both Suitable, Performance Tiebreaker

```
Market: NAS100
Volatility: NORMAL
Trend: WEAK_TREND

Core Signal: A (78 points)
Scalp Signal: Valid

Core Performance: 45% win rate, 1.8 profit factor
Scalp Performance: 62% win rate, 1.6 profit factor

Decision: Quick Scalp trades
Reason: Scalp significantly outperforming (>10% better score)
Blocked: Core Strategy
```

### Scenario 4: Active Position Blocks Both

```
Market: US30
Active Position: Core Strategy (opened 30 minutes ago)

Core Signal: A+ (92 points)
Scalp Signal: Valid

Decision: No trade
Reason: Instrument already has active position
Blocked: Both engines
```

## Performance Scoring Formula

When both engines are suitable for the regime, the engine calculates a performance score:

```python
score = (win_rate × 0.4) + 
        (profit_factor_normalized × 0.3) + 
        (avg_rr_normalized × 0.3)
```

Where:
- `win_rate`: Percentage of winning trades (0.0 to 1.0)
- `profit_factor_normalized`: Profit factor / expected maximum (Core: 3.0, Scalp: 2.0)
- `avg_rr_normalized`: Average R:R / expected maximum (Core: 2.0, Scalp: 1.0)

Quick Scalp must score >10% higher than Core Strategy to override the default Core preference.

## Position Tracking

The engine maintains a registry of active positions:

```python
active_positions = {
    Instrument.US30: EngineType.CORE_STRATEGY,
    Instrument.XAUUSD: EngineType.QUICK_SCALP
}
```

When a position opens:
```python
engine.register_position_opened(Instrument.US30, EngineType.CORE_STRATEGY)
```

When a position closes:
```python
engine.register_position_closed(Instrument.US30)
```

This ensures:
- Only one engine trades per instrument at a time
- No conflicting positions
- Clean risk management

## Integration with Main System

The Auto-Trade Decision Engine sits between the signal generators and trade execution:

```
┌─────────────────┐     ┌─────────────────┐
│ Core Strategy   │────▶│                 │
│ Engine          │     │  Auto-Trade     │
└─────────────────┘     │  Decision       │     ┌──────────────┐
                        │  Engine         │────▶│ Trade        │
┌─────────────────┐     │                 │     │ Execution    │
│ Quick Scalp     │────▶│                 │     └──────────────┘
│ Engine          │     └─────────────────┘
└─────────────────┘            ▲
                               │
                        ┌──────┴──────┐
                        │ Market      │
                        │ Regime      │
                        │ Detector    │
                        └─────────────┘
```

## Configuration

The engine has several configurable parameters:

```python
# Core Strategy A+ threshold (signals >= this score get priority)
core_priority_threshold = 85

# Number of recent trades to consider for performance metrics
performance_lookback_trades = 20

# Minimum time between decision changes (prevents flip-flopping)
decision_cooldown_seconds = 30
```

## Benefits

1. **Prevents Overtrading**: Only one engine trades per instrument
2. **Optimizes Strategy Selection**: Right strategy for right market conditions
3. **Prioritizes Quality**: A+ signals always get priority
4. **Adapts to Performance**: Favors better-performing engine
5. **Clear Reasoning**: Every decision includes explanation
6. **Risk Management**: Prevents conflicting positions

## Expected Behavior

### Daily Trading Pattern

A typical trading day might look like:

```
10:00-13:00 (London Session)
- Market: High volatility, ranging
- Active: Quick Scalp (3-5 trades)
- Blocked: Core Strategy (no clear trend)

15:30-18:00 (NY Open)
- Market: Normal volatility, strong trend
- Active: Core Strategy (1-2 trades)
- Blocked: Quick Scalp (insufficient volatility)

20:00-22:00 (Power Hour)
- Market: High volatility, weak trend
- Active: Both engines (regime suitable for both)
- Coordination: A+ signals prioritized, conflicts resolved
```

### Trade Distribution

Expected distribution across a week:

- Core Strategy: 5-10 trades (higher quality, lower frequency)
- Quick Scalp: 20-40 trades (lower quality, higher frequency)
- Conflicts Resolved: 3-8 times (both engines had signals)
- Blocked by Active Position: 2-5 times

## Monitoring and Debugging

The engine provides detailed reasoning for every decision:

```python
decision = engine.decide_trade(...)

print(f"Should Trade: {decision.should_trade}")
print(f"Engine: {decision.engine}")
print(f"Reason: {decision.reason}")
print(f"Blocked: {decision.blocked_engine}")
```

Example output:
```
Should Trade: True
Engine: CORE_STRATEGY
Reason: Core Strategy A+ signal wins conflict - highest priority
Blocked: QUICK_SCALP
```

## Testing

The engine includes comprehensive property-based tests:

- **Property 34**: Engine Conflict Resolution
  - Core A+ always wins
  - Only one engine trades per instrument
  - Active positions block both engines

- **Property 35**: Volatility Regime Detection
  - Scalp favored in high volatility
  - Core favored in trending + normal volatility
  - Correct blocking in unsuitable regimes

## Best Practices

1. **Monitor Regime Classification**: Ensure volatility and trend detection is accurate
2. **Track Decision Patterns**: Look for excessive blocking or conflicts
3. **Review Performance Metrics**: Update regularly for accurate tiebreaking
4. **Log All Decisions**: Keep audit trail of why trades were taken or blocked
5. **Test Regime Transitions**: Ensure smooth behavior when market changes

## Common Issues and Solutions

### Issue: Too Many Conflicts
**Symptom**: Both engines frequently generating signals simultaneously
**Solution**: Tighten signal generation criteria or adjust regime thresholds

### Issue: One Engine Dominates
**Symptom**: Only one engine trading, other always blocked
**Solution**: Review regime classification—may be stuck in one regime type

### Issue: Frequent Flip-Flopping
**Symptom**: Engine preference changes rapidly
**Solution**: Increase decision cooldown period or smooth regime detection

### Issue: Poor Performance Tiebreaker
**Symptom**: Wrong engine winning conflicts
**Solution**: Adjust performance score weights or lookback period

## Future Enhancements

Potential improvements:

1. **Time-of-Day Preferences**: Favor certain engines during specific sessions
2. **Instrument-Specific Rules**: Different priority rules per instrument
3. **Correlation Awareness**: Consider correlation between instruments
4. **Adaptive Thresholds**: Dynamically adjust regime thresholds based on performance
5. **Machine Learning**: Learn optimal engine selection from historical data

## Conclusion

The Auto-Trade Decision Engine is what makes the dual-engine system practical and profitable. Without it, you'd have chaos. With it, you have an intelligent coordinator that ensures:

- The right strategy trades at the right time
- No conflicting positions
- Quality signals get priority
- Performance drives adaptation
- Risk is properly managed

It's the difference between two strategies fighting each other and two strategies working together as a cohesive system.
