# Current Trading Strategy - Complete Runthrough

## Overview: Dual-Engine Architecture

Aegis Trader now uses a **dual-engine system** where two independent trading strategies operate simultaneously with intelligent coordination:

1. **Core Strategy Engine** - High-probability institutional setups
2. **Quick Scalp Engine** - Rapid M1 momentum trades

Both engines share infrastructure but maintain separate risk pools and operate independently.

---

## 🎯 Engine 1: Core Strategy (Institutional SMC)

### Philosophy
Waits for high-confluence institutional setups using Smart Money Concepts. Quality over quantity.

### Entry Requirements

**100-Point Confluence Scoring System:**

| Component | Max Points | What It Checks |
|-----------|-----------|----------------|
| HTF Alignment | 20 | Weekly, Daily, H4, H1 all aligned |
| Key Level | 15 | Near 250pt or 125pt levels |
| Liquidity Sweep | 15 | Stops triggered above/below swing |
| FVG (Fair Value Gap) | 15 | Imbalance zone present |
| Displacement | 10 | Strong directional move |
| MSS (Market Structure Shift) | 10 | Break of structure confirmed |
| VWAP | 5 | Price within 0.1% of VWAP |
| Volume Spike | 5 | Volume > 1.5× average |
| ATR | 5 | Normal volatility range |
| HTF Target | 5 | Liquidity pool within 3R |
| Session | 5 | Active session (London/NY/Power) |
| Spread | 5 | Spread within limits |

**Signal Grading:**
- **A+ (85-100 points)**: Auto-execute immediately
- **A (75-84 points)**: Alert only, manual review
- **B (<75 points)**: Suppressed, not shown

### Trade Management

**Position Sizing:**
- Risk: 1% of account per trade
- Calculated based on stop loss distance

**Multi-Level Take Profits:**
- **TP1 at 1R**: Close 40% of position
- **TP2 at 2R**: Close 40% of position
- **Runner (20%)**: Trailing stop after TP1 hit

**Stop Loss:**
- Placed below/above structure
- Moved to breakeven after TP1

### Risk Limits

**Daily Limits:**
- Maximum 2 trades per day
- Maximum 2 losses per day
- Maximum 2% daily drawdown

**Session Limits:**
- Trades only during active sessions
- No trading outside 10:00-22:00 SAST

### Example Core Strategy Trade

```
Setup: US30 LONG
Confluence Score: 87 (A+)
- HTF Alignment: 20 ✓ (W, D, H4, H1 all bullish)
- Key Level: 15 ✓ (Near 42,000 level)
- Liquidity Sweep: 15 ✓ (Swept lows at 41,950)
- FVG: 15 ✓ (Gap at 41,980-42,000)
- Displacement: 10 ✓ (Strong move from 41,950)
- MSS: 10 ✓ (Break above 42,020)
- VWAP: 0 (Price 0.3% away)
- Volume: 5 ✓ (2.1× average)
- ATR: 5 ✓ (Normal range)
- HTF Target: 0 (No pool within 3R)
- Session: 5 ✓ (London active)
- Spread: 5 ✓ (2pts < 5pts limit)

Entry: 42,000
Stop Loss: 41,900 (100pts = 1R)
TP1: 42,100 (100pts = 1R) → Close 40%
TP2: 42,200 (200pts = 2R) → Close 40%
Runner: 20% with trailing stop

Risk: 1% of account
Expected R:R: 2:1 minimum
```

---

## ⚡ Engine 2: Quick Scalp (M1 Momentum)

### Philosophy
Capitalize on rapid M1 momentum moves during high volatility. Quantity with tight risk.

### Entry Requirements

**All conditions must be met:**

1. **Liquidity Sweep on M1**
   - Price triggers stops above/below swing high/low
   - Reversal candle forms

2. **Momentum Candle**
   - Body > 60% of total range
   - Range > average of last 10 candles
   - Volume > average of last 20 candles

3. **Volume Spike**
   - Current volume > 1.5× average

4. **Micro Structure Break**
   - Breaks previous M1 swing high/low

5. **High Volatility Regime**
   - ATR > instrument threshold
   - Detected by regime detector

6. **Active Session**
   - London, NY Open, or Power Hour

7. **Tight Spread**
   - US30: < 3pts
   - XAUUSD: < 2pts
   - NASDAQ: < 2pts

8. **Cooldown Elapsed**
   - 2-3 minutes since last scalp trade

### Trade Management

**Position Sizing:**
- Risk: 0.25-0.5% of account per trade
- Smaller risk due to higher frequency

**Single Take Profit:**
- TP at 0.8-1R distance
- Close 100% of position (no runners)
- No trailing stops

**Stop Loss (Instrument-Specific):**
- US30: 15-30 points
- NASDAQ: 10-25 points
- XAUUSD: 0.80-2.00 dollars

### Risk Limits

**Session Limits:**
- London: 5 trades max
- NY Open: 5 trades max
- Power Hour: 3 trades max
- Total: 15 trades per day max

**Cooldown:**
- Minimum 2 minutes between scalp trades
- Prevents overtrading

**Spread Protection:**
- Stricter limits than Core Strategy
- Rejects if spread widens

### Example Quick Scalp Trade

```
Setup: US30 SHORT
Regime: HIGH volatility, RANGING trend
ATR: 150 (avg: 100, ratio: 1.5×)

Conditions Met:
✓ Liquidity sweep at 42,050 (swing high)
✓ Momentum candle: 80% body, 2.3× avg range
✓ Volume spike: 1.8× average
✓ Broke M1 structure at 42,045
✓ High volatility regime
✓ London session active
✓ Spread: 2pts (< 3pts limit)
✓ Cooldown: 3 minutes since last trade

Entry: 42,040
Stop Loss: 42,060 (20pts)
Take Profit: 42,020 (20pts = 1R)

Risk: 0.5% of account
Expected R:R: 1:1
Close: 100% at TP (no runner)
```

---

## 🧠 Auto-Trade Decision Engine (The Traffic Cop)

### Purpose
Prevents both engines from trading the same instrument simultaneously and resolves conflicts.

### Priority Rules

**1. Core Strategy A+ Always Wins**
```
If Core A+ signal + Scalp signal on same instrument:
  → Execute Core A+
  → Block Scalp
```

**2. One Engine Per Instrument**
```
If Core has open position on US30:
  → Block all Scalp signals on US30
  → Allow Scalp on XAUUSD, NASDAQ
```

**3. Regime-Based Selection**
```
If both engines signal different instruments:
  → Use market regime to decide
  → High volatility + ranging → Favor Scalp
  → Normal volatility + trending → Favor Core
```

**4. Performance-Based Tiebreaker**
```
If equal priority:
  → Check recent performance (last 20 trades)
  → Select engine with better win rate
  → If tied, select Core Strategy
```

### Decision Flow

```
Market Data Arrives
    ↓
Regime Detection
    ↓
Both Engines Analyze
    ↓
Core Signal?  Scalp Signal?
    ↓              ↓
Decision Engine Evaluates
    ↓
Priority Check
    ↓
Position Conflict Check
    ↓
Regime Suitability Check
    ↓
Performance Tiebreaker
    ↓
Execute Selected Signal
    ↓
Block Other Engine for Instrument
```

---

## 📊 Market Regime Detection (The Eyes)

### Purpose
Classifies market conditions to help decision engine select appropriate strategy.

### Volatility Classification

**Uses ATR (Average True Range):**

```
ATR Ratio = Current ATR / 50-period ATR Average

LOW:      Ratio < 0.8×    (Gray)
NORMAL:   0.8× < Ratio < 1.5×    (Green)
HIGH:     1.5× < Ratio < 2.5×    (Orange)
EXTREME:  Ratio > 2.5×    (Red)
```

**Engine Preferences:**
- LOW/NORMAL → Core Strategy preferred
- HIGH → Quick Scalp preferred
- EXTREME → Both engines cautious

### Trend Classification

**Uses EMA + Swing Structure:**

```
EMA50 vs EMA200:
- Separation > 0.5% → Strong trend
- Separation > 0.2% → Weak trend
- Separation < 0.2% → Ranging

Swing Structure:
- Higher highs + higher lows → Uptrend
- Lower highs + lower lows → Downtrend
- Mixed → Choppy

STRONG_TREND:  Clear direction + EMA separation (Green)
WEAK_TREND:    Mild direction + small EMA separation (Blue)
RANGING:       Sideways + tight EMAs (Orange)
CHOPPY:        Erratic + no clear pattern (Red)
```

**Engine Preferences:**
- STRONG_TREND → Core Strategy preferred
- WEAK_TREND → Core Strategy preferred
- RANGING + HIGH volatility → Quick Scalp preferred
- CHOPPY → Both engines cautious

---

## 📈 Performance Tracking (The Memory)

### Purpose
Tracks each engine's performance to inform decision engine tiebreakers.

### Metrics Tracked

**Per Engine + Per Instrument:**

```
Rolling Window (Last 20 Trades):
- Win Rate: Winning trades / Total trades
- Average R:R: Sum of R multiples / Trade count
- Profit Factor: Gross profit / Gross loss
- Max Drawdown: Largest peak-to-trough decline
- Consecutive Wins: Current win streak
- Consecutive Losses: Current loss streak

Lifetime Stats:
- Total trades
- Total wins/losses
- Total P&L
- Best trade
- Worst trade
```

**Example:**
```
Core Strategy - US30 (Last 20 Trades):
- Win Rate: 65%
- Average R:R: 1.8R
- Profit Factor: 2.1
- Max Drawdown: -3.2%
- Consecutive Wins: 3
- Total Trades: 20

Quick Scalp - US30 (Last 20 Trades):
- Win Rate: 58%
- Average R:R: 0.9R
- Profit Factor: 1.4
- Max Drawdown: -1.8%
- Consecutive Losses: 2
- Total Trades: 20
```

---

## 🔄 Complete Trade Flow

### Step-by-Step Process

**1. Market Data Ingestion**
```
MT5 → Market data (OHLCV bars)
    → W, D, H4, H1, M5, M1 timeframes
    → US30, XAUUSD, NASDAQ
```

**2. Regime Detection**
```
Calculate ATR → Classify volatility
Calculate EMA → Classify trend
Store regime per instrument
```

**3. Strategy Analysis**
```
Core Strategy:
  → Analyze HTF alignment
  → Calculate confluence score
  → Generate signal if score ≥ 85

Quick Scalp:
  → Check volatility regime
  → Analyze M1 momentum
  → Generate signal if all conditions met
```

**4. Decision Engine**
```
Receive signals from both engines
Apply priority rules:
  1. Core A+ wins
  2. Check position conflicts
  3. Check regime suitability
  4. Performance tiebreaker
Select winning signal
```

**5. Risk Validation**
```
Check daily limits
Check session limits
Check spread limits
Check cooldown (scalp)
Approve or reject
```

**6. Signal Routing**
```
Convert to unified signal format
Validate all fields
Route to execution handler
```

**7. Execution**
```
Send to MT5 via MQL5 bridge
Send notification to Telegram
Log to database
Track in performance tracker
```

**8. Position Management**
```
Monitor for TP/SL hits
Update position state
Move to breakeven (Core)
Activate trailing stop (Core)
Close partials (Core)
```

**9. Performance Recording**
```
Record trade outcome
Update win rate
Update average R:R
Update profit factor
Update consecutive wins/losses
Feed back to decision engine
```

---

## 🛡️ Risk Management

### Global Filters (Apply to Both Engines)

**1. Session Manager**
```
Signal Window: 10:00-22:00 SAST
Active Sessions:
  - London: 10:00-13:00
  - NY Open: 15:30-17:30
  - Power Hour: 20:00-22:00
Blocks signals outside windows
```

**2. News Filter**
```
Blocks trading:
  - 30 minutes before high-impact news
  - 60 minutes after high-impact news
Events: CPI, NFP, FOMC, Fed speeches
Conservative mode if calendar unavailable
```

**3. Spread Monitor**
```
Global Limits:
  - US30: 5 points
  - XAUUSD: 3 points
  - NASDAQ: 4 points

Scalp Limits (Stricter):
  - US30: 3 points
  - XAUUSD: 2 points
  - NASDAQ: 2 points
```

**4. Slippage Protection**
```
Reject if slippage > 10 points
Log rejection with details
Alert user
```

### Separate Risk Pools

**Core Strategy Pool:**
- Daily trade limit: 2
- Daily loss limit: 2
- Daily drawdown limit: 2%
- Risk per trade: 1%

**Quick Scalp Pool:**
- Session limits: 5/5/3
- Daily trade limit: 15
- Cooldown: 2-3 minutes
- Risk per trade: 0.25-0.5%

**Independence:**
```
If Core hits daily limit:
  → Core blocked
  → Scalp continues operating

If Scalp hits session limit:
  → Scalp blocked for that session
  → Core continues operating
```

---

## 📱 Mobile App Integration

### Real-Time Monitoring

**Engines Tab (⚡):**
```
Engine Status:
  🎯 Core Strategy: ACTIVE (1/2 trades)
  ⚡ Quick Scalp: ACTIVE (8/15 trades)

Market Regimes:
  US30: NORMAL volatility, WEAK_TREND
  XAUUSD: HIGH volatility, RANGING
  NASDAQ: NORMAL volatility, STRONG_TREND

Active Signals:
  🎯 Core - US30 LONG @ 42,000 (2.0R)
  ⚡ Scalp - XAUUSD SHORT @ 2,050 (1.0R)

Last Decision:
  "Core Strategy A+ signal - highest priority"
```

**Auto-Refresh:**
- Updates every 30 seconds
- Pull-to-refresh available
- Color-coded indicators

---

## 🎯 Strategy Comparison

| Aspect | Core Strategy | Quick Scalp |
|--------|--------------|-------------|
| **Timeframe** | H1-H4 analysis | M1 execution |
| **Frequency** | 1-2 trades/day | 5-15 trades/day |
| **Win Rate Target** | 60-70% | 55-65% |
| **R:R Target** | 2:1 minimum | 0.8-1:1 |
| **Risk Per Trade** | 1% | 0.25-0.5% |
| **Hold Time** | Hours to days | Minutes |
| **Take Profits** | Multi-level (TP1, TP2, runner) | Single TP |
| **Trailing Stop** | Yes (on runner) | No |
| **Best Conditions** | Trending, normal volatility | Ranging, high volatility |
| **Complexity** | High (100pt confluence) | Medium (5 conditions) |
| **Automation** | A+ only | All signals |

---

## 🔧 Current Implementation Status

### ✅ Fully Implemented

**Backend:**
- Auto-Trade Decision Engine (600+ lines, 9 tests)
- Regime Detector (20 tests)
- Performance Tracker (15 tests)
- Unified Signal Contract (16 tests)
- Trading Coordinator (9 integration tests)
- API endpoints (/dual-engine/*)

**Mobile:**
- Engines tab with real-time monitoring
- Market regime visualization
- Active signals display
- Performance metrics

**Total:** 69 tests passing

### ⚠️ Not Yet Wired to Live Trading

**What's Missing:**
1. Real market data feed (currently mock data)
2. Actual Core Strategy engine implementation
3. Actual Quick Scalp engine implementation
4. Live MT5 execution integration
5. Real-time regime calculation from live data

**Current State:**
- Infrastructure is complete
- Coordination logic is working
- API endpoints are functional
- Mobile app can display data
- **BUT:** Using mock/example engines, not real strategy logic

---

## 🚀 Next Steps to Go Live

### 1. Implement Real Core Strategy Engine
```python
class RealCoreStrategyEngine:
    def analyze_setup(self, instrument, bars, regime):
        # Real HTF alignment analysis
        # Real confluence scoring
        # Real signal generation
        return CoreSignal(...)
```

### 2. Implement Real Quick Scalp Engine
```python
class RealQuickScalpEngine:
    def analyze_scalp_setup(self, instrument, bars, regime):
        # Real M1 momentum detection
        # Real liquidity sweep detection
        # Real signal generation
        return ScalpSignal(...)
```

### 3. Wire to Live Market Data
```python
# Replace mock data with real MT5 feed
coordinator = TradingCoordinator(
    config=config,
    core_strategy_engine=RealCoreStrategyEngine(),
    scalp_strategy_engine=RealQuickScalpEngine()
)

# Process real market data
for bar in mt5_data_stream:
    signal = coordinator.process_market_data(
        instrument=bar.instrument,
        bars=bar.history,
        current_spread=bar.spread
    )
```

### 4. Connect to MT5 Execution
```python
# Wire execution handler to MT5 bridge
def execute_on_mt5(signal):
    mt5_bridge.place_order(
        symbol=signal.instrument,
        direction=signal.direction,
        entry=signal.entry_price,
        sl=signal.stop_loss,
        tp1=signal.tp1,
        tp2=signal.tp2
    )

coordinator.register_execution_handler(execute_on_mt5)
```

---

## 📊 Summary

**Current Strategy:** Dual-engine system with intelligent coordination

**Engine 1 (Core):** High-probability institutional setups, 1-2 trades/day, 2:1 R:R
**Engine 2 (Scalp):** Rapid M1 momentum, 5-15 trades/day, 1:1 R:R

**Coordination:** Auto-Trade Decision Engine prevents conflicts, uses regime detection and performance tracking

**Infrastructure:** Complete and tested (69 tests passing)
**Live Trading:** Not yet connected (needs real strategy engines and market data)

**Mobile App:** Fully integrated with real-time monitoring of both engines

The system is architecturally sound and ready for the real strategy implementations to be plugged in!
