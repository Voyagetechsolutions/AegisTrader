# RED TEAM AUDIT: Aegis Trader

**Mission:** Find bugs that will lose money in production. Not style issues. Not theoretical problems. Real bugs that will blow up the account.

---

## Attack Vectors

### 1. Race Conditions & Concurrency

**Scenario:** Multiple signals arrive simultaneously or trades execute while risk checks run.

**Questions:**
- What happens if 2 A+ signals arrive within 100ms?
- Can the system place 3 trades before `MAX_DAILY_TRADES=2` updates?
- What if TP1 hits while the system is placing a new trade?
- Can `/closeall` command race with automatic SL modification?
- What if MT5 connection drops mid-order?
- Can news filter be bypassed if signal arrives during news check?
- What happens if spread widens during order placement?

**Test:**
```python
# Simulate: Send 5 webhook signals in parallel
# Expected: Only 2 trades placed
# Actual: ???
```

---

### 2. Timezone Edge Cases

**Scenario:** Session boundaries, DST transitions, broker server time drift.

**Questions:**
- What happens at 09:59:59 SAST when London session starts at 10:00?
- Does the system handle DST transitions (SAST doesn't have DST, but broker might)?
- What if broker server time is 5 minutes fast/slow?
- Can a signal be marked "London session" when it's actually 09:58?
- What happens at midnight when daily counters reset mid-trade?
- Does news filter work correctly across timezone boundaries?

**Test:**
```python
# Simulate: Signal at 09:59:58 SAST
# Expected: Rejected (outside session)
# Actual: ???
```

---

### 3. Partial Fill & Slippage

**Scenario:** Order fills at worse price than expected or partially fills.

**Questions:**
- What if entry fills at 42,050 but SL calculated for 42,000 entry?
- Does the system recalculate R:R after slippage?
- What if only 0.3 lots fill instead of 1.0 lot?
- Can TP1 (50% close) fail if position size is 0.01 lots?
- What happens if SL modification fails after TP1 closes?
- Does the system track actual fill price vs intended price?

**Test:**
```python
# Simulate: Order fills 15 points worse than signal
# Expected: Reject or adjust SL/TP
# Actual: ???
```

---

### 4. MT5 Connection Failures

**Scenario:** MT5 terminal crashes, network drops, broker server restarts.

**Questions:**
- What if MT5 disconnects with 2 open positions?
- Can the system recover and resume monitoring existing trades?
- What happens if TP1 hits but system can't modify SL to breakeven?
- Does the system retry failed orders? How many times?
- What if position exists in MT5 but not in system state?
- Can the system detect "zombie trades" (MT5 has it, system doesn't)?

**Test:**
```python
# Simulate: Kill MT5 connection after trade opens
# Expected: Reconnect and resume monitoring
# Actual: ???
```

---

### 5. Risk Limit Edge Cases

**Scenario:** Limits hit exactly at boundary conditions.

**Questions:**
- What if trade #2 is placed, then trade #1 closes at breakeven (0 loss)?
- Does the system allow trade #3 since no losses occurred?
- What if 2 trades lose exactly 1% each (total 2% drawdown)?
- Can the system place a 3rd trade if it's "risk-free" (SL at breakeven)?
- What happens if daily loss is 1.99% and next trade risks 0.5%?
- Does `/start` command bypass risk limits?

**Test:**
```python
# Simulate: 2 trades, both at breakeven, signal #3 arrives
# Expected: Reject (max trades hit)
# Actual: ???
```

---

### 6. News Filter Bypass

**Scenario:** High-impact news during active trade or signal generation.

**Questions:**
- What if news event starts AFTER signal approved but BEFORE order placed?
- Does the system close existing trades during news blackout?
- What if news time changes (delayed/early release)?
- Can the system detect "surprise" news events not in calendar?
- What happens if news API is down?
- Does `NEWS_FILTER_BYPASS=true` override ALL news checks?

**Test:**
```python
# Simulate: NFP scheduled 15:30, signal arrives 15:29:50
# Expected: Reject
# Actual: ???
```

---

### 7. Spread Manipulation

**Scenario:** Broker widens spread during volatile periods.

**Questions:**
- What if spread is 3 points at signal time, 8 points at execution?
- Does the system reject the trade or execute anyway?
- Can spread check be bypassed if order is already queued?
- What if spread is acceptable but slippage pushes total cost over limit?
- Does the system track spread history to detect manipulation?

**Test:**
```python
# Simulate: Spread jumps from 2 to 12 points in 1 second
# Expected: Reject all new trades
# Actual: ???
```

---

### 8. Signal Scoring Manipulation

**Scenario:** Edge cases in confluence scoring that inflate grades.

**Questions:**
- Can a signal score 85+ (A+) without HTF alignment?
- What if price is near both 250 AND 125 level (double points)?
- Can displacement be detected on a wick-only candle?
- What if FVG exists but is only 5 points wide?
- Can session timing give points outside actual session?
- What happens if all engines return `None` or empty results?

**Test:**
```python
# Simulate: Price at 42,125 (both 250 and 125 level)
# Expected: Max 15 points (not 25)
# Actual: ???
```

---

### 9. Trade Management Failures

**Scenario:** TP1/TP2 logic fails or executes incorrectly.

**Questions:**
- What if TP1 is hit but 50% close fails (insufficient volume)?
- Does the system retry or abandon the partial close?
- What if SL modification to breakeven fails after TP1?
- Can TP2 be hit before TP1 (gap/slippage)?
- What happens if trailing stop moves in wrong direction?
- Does the system handle "runner" correctly if only 0.01 lots remain?

**Test:**
```python
# Simulate: TP1 hit, close 50% succeeds, SL modification fails
# Expected: Retry SL modification or alert
# Actual: ???
```

---

### 10. Database Failures

**Scenario:** Database connection drops or queries fail.

**Questions:**
- What if signal is approved but DB write fails?
- Can the system execute trade without recording it?
- What happens if risk counters can't be read from DB?
- Does the system default to "safe" mode or continue trading?
- Can duplicate signals be inserted if webhook retries?
- What if daily reset fails (counters stuck at yesterday's values)?

**Test:**
```python
# Simulate: DB connection drops after signal approval
# Expected: Reject trade or queue for retry
# Actual: ???
```

---

### 11. Telegram Command Injection

**Scenario:** Malicious commands or rapid command spam.

**Questions:**
- What if `/start` and `/stop` are sent simultaneously?
- Can `/closeall` be spammed to trigger multiple close attempts?
- What happens if `/mode trade` is sent during active trade?
- Can commands bypass authentication (wrong chat ID)?
- What if command arrives during system restart?
- Does the system rate-limit commands?

**Test:**
```python
# Simulate: Send `/start` 10 times in 1 second
# Expected: Process once, ignore duplicates
# Actual: ???
```

---

### 12. Candle Aggregation Errors

**Scenario:** Missing ticks, gaps in data, incorrect OHLC calculations.

**Questions:**
- What if 1M candle is missing (gap in data)?
- Does 5M aggregation fail or use stale data?
- What happens if broker sends duplicate ticks?
- Can aggregation create "phantom" candles?
- What if high < low (data corruption)?
- Does the system validate OHLC before using it?

**Test:**
```python
# Simulate: 1M candles at 10:00, 10:01, 10:03 (10:02 missing)
# Expected: Detect gap, reject analysis
# Actual: ???
```

---

### 13. Position Size Calculation

**Scenario:** Incorrect lot size due to rounding or balance errors.

**Questions:**
- What if account balance is $487.63 and risk is 2%?
- Does the system round lot size correctly (0.01 increments)?
- What if calculated lot size is 0.003 (below minimum)?
- Can position size exceed account margin?
- What happens if balance changes between calculation and execution?
- Does the system account for existing open positions?

**Test:**
```python
# Simulate: Balance $500, risk 2%, SL 50 points
# Expected: 0.20 lots (or reject if below min)
# Actual: ???
```

---

### 14. Swing Mode Approval Timeout

**Scenario:** User doesn't respond to swing approval request.

**Questions:**
- What happens if approval request times out?
- Does the signal expire or stay pending forever?
- Can multiple approval requests stack up?
- What if user approves after signal is no longer valid?
- Does the system re-check conditions before executing approved signal?
- Can user approve a signal that already hit SL level?

**Test:**
```python
# Simulate: Swing signal sent, no response for 10 minutes
# Expected: Auto-reject after timeout
# Actual: ???
```

---

### 15. Weekly Bias Conflicts

**Scenario:** HTF bias changes mid-week or conflicts between timeframes.

**Questions:**
- What if weekly bias is bullish but daily is bearish?
- Does the system reject or reduce score?
- What happens if bias changes during open trade?
- Can the system detect bias flip and close positions?
- What if 4H bias conflicts with 1H bias?
- Does the system require ALL timeframes to align for A+ grade?

**Test:**
```python
# Simulate: Weekly bullish, daily bearish, 4H bullish
# Expected: Reduced score (not A+)
# Actual: ???
```

---

### 16. Replay Engine vs Live Divergence

**Scenario:** Backtest shows profit but live trading loses money.

**Questions:**
- Does replay engine use actual spreads or assume 0?
- Are slippage and latency simulated?
- Does replay account for news blackouts?
- Can replay execute trades that would fail in live (margin, connection)?
- Does replay use look-ahead bias (future data)?
- Are session times exact or approximate in replay?

**Test:**
```python
# Simulate: Run same signal through replay and live
# Expected: Identical results
# Actual: ???
```

---

### 17. Emergency Stop Failures

**Scenario:** Emergency stop button pressed but trades continue.

**Questions:**
- What if emergency stop is pressed during order placement?
- Does the system cancel pending orders?
- Can trades execute after emergency stop if webhook was already queued?
- What happens to open positions (close or leave open)?
- Does emergency stop persist after system restart?
- Can emergency stop be bypassed by direct MT5 access?

**Test:**
```python
# Simulate: Press emergency stop while 2 orders are pending
# Expected: Cancel all pending, no new trades
# Actual: ???
```

---

### 18. Duplicate Signal Detection

**Scenario:** TradingView sends same signal twice (webhook retry).

**Questions:**
- Does the system detect duplicate signals?
- What if signal is identical but 5 seconds apart?
- Can duplicate detection be bypassed by changing timestamp?
- What if legitimate signal matches previous signal exactly?
- Does the system use signal ID or content hash for deduplication?
- How long is the deduplication window?

**Test:**
```python
# Simulate: Send identical webhook payload twice
# Expected: Process once, reject duplicate
# Actual: ???
```

---

### 19. Floating Point Precision

**Scenario:** Price calculations lose precision due to float arithmetic.

**Questions:**
- What if SL is calculated as 42,000.000000001?
- Does MT5 reject the order (invalid price)?
- Can rounding errors accumulate over multiple calculations?
- What if TP1 is 0.1 points away from entry (too tight)?
- Does the system use Decimal for money calculations?
- Can float precision cause "phantom" profit/loss?

**Test:**
```python
# Simulate: Entry 42,000.5, SL 41,950.3, calculate R
# Expected: Exact 50.2 points
# Actual: 50.199999999998 ???
```

---

### 20. System Clock Drift

**Scenario:** Server clock is out of sync with broker/market time.

**Questions:**
- What if system clock is 2 minutes fast?
- Can signals be marked as "in session" when market is closed?
- Does the system sync with NTP server?
- What happens if clock jumps backward (DST, manual adjustment)?
- Can clock drift cause duplicate daily resets?
- Does the system detect and alert on clock skew?

**Test:**
```python
# Simulate: Set system clock 5 minutes ahead
# Expected: Detect skew, reject trades or alert
# Actual: ???
```

---

## Red Team Test Suite

Run these scenarios in sequence:

```python
# 1. Concurrent signal flood
async def test_race_condition():
    signals = [generate_signal() for _ in range(10)]
    results = await asyncio.gather(*[process_signal(s) for s in signals])
    assert sum(r.executed for r in results) <= 2  # MAX_DAILY_TRADES

# 2. MT5 disconnect during trade
async def test_connection_failure():
    await place_trade()
    kill_mt5_connection()
    await asyncio.sleep(60)
    assert system_recovered()
    assert position_still_monitored()

# 3. Spread spike during execution
async def test_spread_manipulation():
    signal = generate_signal()
    approve_signal(signal)
    set_spread(15)  # Spike to 15 points
    result = await execute_trade(signal)
    assert result.rejected
    assert "spread" in result.reason.lower()

# 4. News event during signal
async def test_news_blackout():
    schedule_news("NFP", "15:30")
    signal = generate_signal(timestamp="15:29:50")
    result = await process_signal(signal)
    assert result.rejected
    assert "news" in result.reason.lower()

# 5. Partial fill scenario
async def test_partial_fill():
    signal = generate_signal(lot_size=1.0)
    result = await execute_trade(signal, fill_ratio=0.3)
    assert result.actual_lots == 0.3
    assert result.sl_adjusted  # SL should still be valid

# 6. TP1 hit but SL modification fails
async def test_tp1_failure():
    trade = await place_trade()
    hit_tp1(trade)
    fail_sl_modification()
    await asyncio.sleep(5)
    assert alert_sent("SL modification failed")
    assert retry_attempted()

# 7. Database connection drop
async def test_db_failure():
    kill_database()
    signal = generate_signal()
    result = await process_signal(signal)
    assert result.rejected
    assert "database" in result.reason.lower()

# 8. Duplicate signal detection
async def test_duplicate_signal():
    signal = generate_signal()
    result1 = await process_signal(signal)
    result2 = await process_signal(signal)  # Same signal
    assert result1.processed
    assert result2.rejected
    assert "duplicate" in result2.reason.lower()

# 9. Emergency stop during execution
async def test_emergency_stop():
    signal = generate_signal()
    asyncio.create_task(execute_trade(signal))
    await asyncio.sleep(0.1)
    emergency_stop()
    await asyncio.sleep(1)
    assert no_trades_executed()

# 10. Clock drift detection
async def test_clock_drift():
    set_system_clock_offset(minutes=5)
    signal = generate_signal()
    result = await process_signal(signal)
    assert result.rejected or alert_sent("clock drift")
```

---

## Expected Output

For each attack vector, document:

```
VECTOR: Race Conditions
STATUS: VULNERABLE / PROTECTED
EVIDENCE: [file:line] where bug exists
IMPACT: Can place 5 trades instead of 2
FIX: Add distributed lock on trade counter
PRIORITY: CRITICAL
```

---

## Success Criteria

The system passes red team audit ONLY if:

- ✅ No race conditions allow exceeding risk limits
- ✅ All timezone edge cases handled correctly
- ✅ MT5 connection failures don't lose track of positions
- ✅ Spread/slippage checks can't be bypassed
- ✅ News filter works at exact boundaries
- ✅ Trade management never leaves orphaned positions
- ✅ Database failures default to safe mode (no trading)
- ✅ Emergency stop is immediate and absolute
- ✅ Duplicate signals are detected within 60 seconds
- ✅ System clock drift is detected and alerts

---

**This is the audit that matters.** Style issues don't lose money. Race conditions do.
