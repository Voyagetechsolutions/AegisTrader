# Aegis Trader Strategy & Confirmations

## Strategy Overview

Aegis Trader uses a **Multi-Timeframe Smart Money Concepts (SMC)** strategy with a 100-point confluence scoring system. The strategy identifies institutional order flow and market structure to find high-probability trade setups.

---

## Core Methodology

### 1. Smart Money Concepts (SMC)
The strategy is built on institutional trading principles:
- **Market Structure Shifts (MSS)** - Identifies trend changes
- **Fair Value Gaps (FVG)** - Price imbalances that act as magnets
- **Liquidity Sweeps** - Stop hunts before reversals
- **Displacement** - Strong institutional moves
- **Order Blocks** - Institutional supply/demand zones

### 2. Multi-Timeframe Analysis
Analyzes 7 timeframes for confluence:
- **Weekly** - Overall market direction
- **Daily** - Primary trend
- **H4** - Intermediate trend
- **H1** - Entry timeframe trend
- **M15** - Refinement
- **M5** - Execution trigger
- **M1** - Precision entry (optional)

---

## Confluence Scoring System (100 Points Max)

### HTF Alignment (20 points max)
- **Weekly aligned**: 6 points (3 if neutral)
- **Daily aligned**: 5 points (2 if neutral)
- **H4 aligned**: 4 points (2 if neutral)
- **H1 aligned**: 3 points (1 if neutral)
- **M15 aligned**: 2 points (bonus)

### Key Levels (25 points max)
- **250-point level**: 15 points max
  - Within 50 points: 15 points
  - Within 100 points: 10 points
  - Within 150 points: 5 points
- **125-point level**: 10 points max
  - Within 30 points: 10 points
  - Within 60 points: 7 points
  - Within 100 points: 3 points

### SMC Confirmations (50 points)
- **Liquidity Sweep**: 15 points (stop hunt confirmed)
- **FVG Present**: 15 points (price imbalance)
- **Displacement**: 10 points (strong institutional move)
- **MSS Present**: 10 points (structure break)

### Execution Conditions (10 points)
- **Session Active**: 5 points (London/NY/Power Hour)
- **Spread OK**: 5 points (spread within limits)

---

## Setup Types

### 1. Continuation Setup (A+ Auto-Trade Eligible)
**Requirements:**
- HTF alignment (Weekly/Daily/H4 not opposing, H1 aligned)
- M5 Market Structure Shift (bull_shift or bear_shift)
- All 4 SMC confirmations present:
  - ✓ Liquidity sweep
  - ✓ FVG present
  - ✓ Displacement
  - ✓ MSS
- Score ≥ 85 points
- Spread within limits
- Active trading session

**Example Long:**
- Weekly: Bullish or Neutral
- Daily: Bullish or Neutral
- H4: Bullish or Neutral
- H1: Bullish
- M5: Bull shift (structure break to upside)
- Liquidity sweep below recent low
- FVG above current price
- Strong displacement candle
- MSS confirmed

### 2. Swing Setup (Alert Only)
**Requirements:**
- Weekly/Daily/H4 strongly aligned
- H1 showing pullback (counter-trend)
- Score ≥ 75 points
- Requires manual approval

**Example Long:**
- Weekly: Bullish
- Daily: Bullish
- H4: Bullish
- H1: Bearish or Neutral (pullback)
- Waiting for H1 to shift bullish for entry

---

## Signal Grades

### A+ Grade (85-100 points)
- **Auto-trade eligible** if continuation setup
- All key confirmations present
- Highest probability setups
- Automatic execution in "trade" mode

### A Grade (75-84 points)
- **Alert only** - requires manual review
- Strong setup but missing some confluence
- Good for swing trades
- Manual approval needed

### B Grade (<75 points)
- **Ignored** - insufficient confluence
- No alert generated
- Setup does not meet minimum criteria

---

## Trade Management

### Entry
- **Continuation**: Immediate entry on M5 structure break
- **Swing**: Wait for H1 pullback completion

### Stop Loss
- Below/above recent liquidity sweep
- Typically 50-100 points on US30

### Take Profit Strategy
1. **TP1 (50%)**: 1:1 Risk-Reward
   - Close 50% of position
   - Move SL to breakeven
2. **TP2 (30%)**: 2:1 Risk-Reward
   - Close 30% of position
   - Trail remaining 20%
3. **Runner (20%)**: Trail to major levels
   - Let it run to next major structure
   - Trail with 250/125 levels

### Breakeven Rules
- Move SL to breakeven when TP1 is hit
- Protects capital on winning trades
- Allows runner to capture extended moves

---

## Risk Management

### Daily Limits
- **Max trades per day**: 2
- **Max losses per day**: 2
- **Max daily drawdown**: 2%

### Position Sizing
- **Fixed lot mode**: User-defined lot size
- **Risk % mode**: Calculate lot size based on account risk %

### Kill Switch Triggers
- Daily loss limit reached
- Daily trade limit reached
- Drawdown limit exceeded
- Emergency stop activated

---

## Filters & Protections

### 1. Session Filter
- **London**: 10:00-13:00 SAST
- **New York**: 15:30-17:30 SAST
- **Power Hour**: 20:00-22:00 SAST
- **Override enabled**: 24/7 trading (sessions tracked but don't block)

### 2. News Filter
- Blocks trading around high-impact news
- **Standard news**: 30 min before/after
- **Major news**: 60 min before/after
- Prevents whipsaw during volatility spikes

### 3. Spread Filter
- Max spread: 5 points (configurable)
- Spread multiplier: 2x (for dynamic adjustment)
- Rejects trades during spread spikes

### 4. Slippage Protection
- Max slippage: 10 points
- Validates actual fill price
- Rejects if slippage exceeds limit

### 5. Duplicate Signal Protection
- Prevents multiple entries on same setup
- 5-minute cooldown between signals
- Race condition protection with asyncio locks

---

## Execution Flow

1. **TradingView Alert** → Webhook to backend
2. **Analysis Engines** → Process all timeframes
3. **Confluence Scoring** → Calculate 100-point score
4. **Grade Assignment** → A+, A, or B
5. **Setup Classification** → Continuation or Swing
6. **Filter Checks** → Session, News, Spread
7. **Risk Authorization** → Check daily limits
8. **Auto-Trade Decision**:
   - A+ Continuation + All filters pass → **Execute**
   - A+ Swing or A grade → **Alert only**
   - B grade → **Ignore**
9. **MT5 Execution** → Place order via bridge
10. **Trade Management** → Monitor TP1/TP2/Runner

---

## Key Advantages

1. **Objective Scoring** - No emotion, pure math
2. **Multi-Timeframe Confluence** - Higher probability
3. **Institutional Flow** - Follow smart money
4. **Risk-First Approach** - Capital preservation priority
5. **Automated Execution** - No hesitation on A+ setups
6. **Partial Profit Taking** - Secure gains while letting winners run
7. **Comprehensive Filters** - Avoid bad market conditions

---

## Example A+ Setup (Long)

**Confluence Breakdown:**
- HTF Alignment: 18/20 (Weekly/Daily/H4/H1 bullish, M15 bullish)
- 250 Level: 15/15 (Entry within 50 points of level)
- 125 Level: 10/10 (Entry within 30 points of level)
- Liquidity Sweep: 15/15 ✓
- FVG: 15/15 ✓
- Displacement: 10/10 ✓
- MSS: 10/10 ✓
- Session: 5/5 ✓ (London session)
- Spread: 5/5 ✓ (2 points)

**Total: 98/100 points → A+ Grade**

**Setup Type:** Continuation Long
**Auto-Trade:** ✓ Eligible
**Action:** Execute immediately

**Trade Details:**
- Entry: 42,850
- SL: 42,800 (50 points)
- TP1: 42,900 (50 points, 1:1 RR)
- TP2: 42,950 (100 points, 2:1 RR)
- Runner: Trail to 43,000+

---

## Monitoring & Analytics

### Real-Time Tracking
- Open positions
- Daily P&L
- Drawdown %
- Trades/losses count

### Performance Metrics
- Win rate by grade
- Win rate by session
- Win rate by setup type
- Average R:R achieved
- Expectancy per trade

### Paper Trading
- All signals tracked
- Virtual P&L calculated
- Strategy validation
- No capital risk

---

This strategy combines institutional trading concepts with quantitative scoring to identify high-probability setups while maintaining strict risk management.
