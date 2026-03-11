# Signal Grading Scale Update

## Problem Identified

The original grading scale was detached from reality:
- **Old Scale**: A+ = 85+, A = 75-84, B = 65-74, C = <65
- **Reality**: Live signals clustering around 60-65
- **Result**: System rarely produced tradeable signals, missing opportunities

The scale assumed markets would regularly produce near-perfect confluence, but actual market conditions don't work that way.

## New Grading Scale

### Reality-Based Thresholds

```
A+ (80-100)  → Auto trade, highest confidence, full allowed risk
A  (70-79)   → Auto trade, standard confidence, standard risk  
B  (60-69)   → Alert only, no execution
C  (<60)     → Ignore, insufficient quality
```

### Why This Works

1. **More Trading Opportunities**: 70+ scores are achievable in real markets
2. **Clear Separation**: Each grade has distinct behavior
3. **Matches Reality**: Aligns with actual signal distribution (60-65 typical)
4. **Different Execution**: A+ vs A have different risk profiles

## Critical Language Change

### Removed: "Aggressive"

The word "aggressive" was removed from all descriptions because it causes dangerous thinking:
- Bigger lot sizes
- Looser standards
- More exposure
- Overconfidence

### Replaced With: "Full Allowed Risk" vs "Standard Risk"

This is precise and safe:
- **A+ (80+)**: Full allowed risk for that mode (still within limits)
- **A (70-79)**: Standard risk, monitor more closely

## Safety Guardrails Remain Mandatory

Even an 82-score A+ trade is blocked if:
- Spread too wide
- News blackout active
- Session inactive
- Daily risk limit hit
- Emergency stop triggered

**Score does not override safety.**

## Implementation Details

### Files Updated

1. **backend/strategy/dual_engine_models.py**
   - Updated `SignalGrade` enum documentation
   - Added Grade C: `C = "C"  # <60: Ignore`
   - Added note about scale adjustment and language removal
   - Changed thresholds: A+ (80+), A (70-79), B (60-69), C (<60)

2. **backend/strategy/models.py**
   - Added Grade C to SignalGrade enum: `C = "C"`

3. **backend/models/models.py** (Database models)
   - Added Grade C to SignalGrade enum: `C = "C"`

4. **backend/strategy/auto_trade_decision_engine.py**
   - Updated threshold from 85 to 80 for A+
   - Added explicit thresholds: `grade_a_plus_threshold = 80`, `grade_a_threshold = 70`, `grade_b_threshold = 60`
   - Updated all decision reasons to include score ranges
   - Clarified language: "highest confidence, full allowed risk" vs "standard confidence, standard risk"

5. **backend/strategy/config.py**
   - Added grading configuration section
   - Documented thresholds with clear comments

6. **backend/strategy/signal_generator.py**
   - Updated `classify_signal_grade()` function
   - Changed thresholds: A+ >= 80, A >= 70, B >= 60, C < 60
   - Added Grade C handling

7. **backend/routers/strategy_engine.py**
   - Updated inline grading logic
   - Changed documentation from >= 85 to >= 80 for A+

8. **backend/routers/dual_engine.py**
   - Updated min_confluence_score from 85 to 80

9. **backend/strategy/trading_coordinator.py**
   - Updated scalp signal default score from 75.0 to 70.0

10. **backend/tests/test_auto_trade_decision_engine.py**
    - Updated test signal generation strategy
    - Changed score ranges: A+ (80-100), A (70-79), B (60-69), C (0-59)

11. **backend/tests/test_signal_generator.py**
    - Updated all property-based tests
    - Changed boundary tests to match new thresholds
    - Added Grade C test coverage
    - Test verified passing ✓

### Next Steps

You should now define the execution behavior difference between A+ and A:

**A+ Execution (80+ score)**:
- Use full allowed risk percentage (e.g., 1% for Core Strategy)
- Less monitoring required
- Can trade during slightly less favorable conditions

**A Execution (70-79 score)**:
- Use standard risk percentage (e.g., 0.75% for Core Strategy)
- Monitor more closely
- Require more favorable regime conditions (already implemented)

This ensures the system knows exactly what "highest confidence" and "standard confidence" mean in practice.

## Testing Required

1. Run existing tests to ensure grading logic still works
2. Verify A+ signals (80+) get highest priority in conflicts
3. Verify A signals (70-79) are validated against regime
4. Verify B signals (60-69) are suppressed (alert only)
5. Verify C signals (<60) are ignored

## Benefits

- System will generate more tradeable signals
- Clear behavioral differences between grades
- No dangerous "aggressive" language
- Safety filters still prevent bad trades
- Matches real market conditions
