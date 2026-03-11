# Design Document: Dual-Engine Strategy System

## Overview

The dual-engine strategy system implements two independent trading engines that operate simultaneously on the same market data while maintaining separate risk pools and execution logic. The Core Strategy Engine focuses on institutional liquidity models across higher timeframes (Weekly through M5), using a comprehensive 100-point confluence scoring system to identify high-probability setups. The Quick Scalp Engine targets rapid momentum opportunities on M1 timeframes during high-liquidity sessions.

Both engines share common infrastructure components (market data feeds, session management, news filtering, spread monitoring) but maintain complete operational independence. This architecture enables the system to capture both extended institutional moves and rapid scalping opportunities without interference between strategies.

The system enforces a 10:00-22:00 SAST signal window across both engines while maintaining 24/7 market analysis. Risk management operates at two levels: global filters (news events, spreads, slippage) apply to both engines, while engine-specific limits (daily trade counts, position sizing, drawdown thresholds) operate independently.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Market Data Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │  US30    │  │  XAUUSD  │  │  NAS100  │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │             │             │                              │
│       └─────────────┴─────────────┘                              │
│                     │                                            │
└─────────────────────┼────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐         ┌────────▼────────┐
│  Shared        │         │  Shared         │
│  Infrastructure│         │  Infrastructure │
│                │         │                 │
│  • Session Mgr │         │  • News Filter  │
│  • Spread Mon  │         │  • Slippage Mon │
└───────┬────────┘         └────────┬────────┘
        │                           │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────────┐    ┌─────────▼──────────────┐
│ Core Strategy      │    │ Quick Scalp            │
│ Engine             │    │ Engine                 │
│                    │    │                        │
│ • Bias Engine      │    │ • M1 Momentum Detector │
│ • Confluence Score │    │ • Liquidity Sweep Det  │
│ • HTF Analysis     │    │ • Session Limiter      │
│ • Multi-TP Manager │    │ • Spread Filter        │
│                    │    │ • Cooldown Timer       │
└───────┬────────────┘    └─────────┬──────────────┘
        │                           │
        └─────────────┬─────────────┘
                      │
              ┌───────▼────────┐
              │  Risk Tracker  │
              │                │
              │  • Core Pool   │
              │  • Scalp Pool  │
              │  • Metrics     │
              └───────┬────────┘
                      │
              ┌───────▼────────┐
              │  Trade         │
              │  Execution     │
              └────────────────┘
```

### Component Responsibilities

**Market Data Layer**: Ingests and normalizes tick data, OHLCV bars, and volume data for US30, XAUUSD, and NAS100 across all required timeframes (Weekly, Daily, H4, H1, M5, M1).

**Session Manager**: Enforces the 10:00-22:00 SAST signal window, tracks active sessions (London, NY Open, Power Hour), and blocks signal generation outside permitted periods.

**News Filter**: Maintains economic calendar, blocks trading 30 minutes before and 60 minutes after high-impact events (CPI, NFP, FOMC, Fed speeches).

**Spread Monitor**: Tracks real-time bid-ask spreads, enforces global spread limits (US30: 5pts, NAS100: 4pts, XAUUSD: 3pts) and scalp-specific limits (US30: 3pts, NAS100: 2pts, XAUUSD: 2pts).

**Slippage Monitor**: Measures execution quality, rejects trades with slippage exceeding 10 points.

**Bias Engine**: Analyzes Weekly, Daily, H4, and H1 timeframes to determine directional bias using the 20-point HTF alignment scoring system (6pts Weekly, 6pts Daily, 4pts H4, 4pts H1).

**Core Strategy Engine**: Implements institutional liquidity model with 100-point confluence scoring, manages multi-level take-profit strategy (TP1: 40% at 1R, TP2: 40% at 2R, Runner: 20% trailing), enforces 1% risk per trade and 2-trade daily limit.

**Quick Scalp Engine**: Detects M1 momentum setups (liquidity sweep + momentum candle + volume spike + micro structure break), operates only during active sessions, enforces session-specific trade limits (London: 5, NY: 5, Power Hour: 3), uses 0.25-0.5% risk per trade with 0.8-1R single take-profit.

**Risk Tracker**: Maintains separate risk pools for each engine, tracks daily trade counts, monitors drawdown limits, calculates performance metrics (win rate, profit factor, average R:R) independently for each engine.

### Data Flow

1. **Market Data Ingestion**: Raw tick and bar data flows from broker feed into Market Data Layer
2. **Timeframe Construction**: System constructs all required timeframes (W, D, H4, H1, M5, M1) from base data
3. **Global Filtering**: Session Manager, News Filter, and Spread Monitor evaluate whether signal generation is permitted
4. **Engine-Specific Analysis**: 
   - Core Strategy Engine analyzes HTF alignment, calculates confluence scores, identifies SMC patterns
   - Quick Scalp Engine analyzes M1 momentum, detects liquidity sweeps, evaluates session constraints
5. **Signal Generation**: Each engine independently generates signals when conditions are met
6. **Risk Validation**: Risk Tracker validates that engine-specific limits are not exceeded
7. **Trade Execution**: Validated signals are sent to execution layer with appropriate stop loss and take-profit parameters
8. **Position Management**: Core Strategy Engine manages multi-level exits; Quick Scalp Engine manages single exit
9. **Performance Tracking**: Risk Tracker records trade outcomes and updates metrics

## Components and Interfaces

### Bias Engine

**Purpose**: Determines directional bias by analyzing higher timeframe alignment.

**Inputs**:
- Weekly OHLCV data
- Daily OHLCV data
- H4 OHLCV data
- H1 OHLCV data
- Trade direction (long/short)

**Outputs**:
- HTF alignment score (0-20 points)
- Breakdown by timeframe (Weekly: 0-6, Daily: 0-6, H4: 0-4, H1: 0-4)

**Algorithm**:
1. For each timeframe, identify current trend direction using market structure (higher highs/lows for uptrend, lower highs/lows for downtrend)
2. Compare trade direction against timeframe trend
3. Award points if alignment exists: Weekly (6pts), Daily (6pts), H4 (4pts), H1 (4pts)
4. Require H1 alignment (4pts minimum) for any valid signal
5. Return total score and per-timeframe breakdown

**Interface**:
```python
class BiasEngine:
    def calculate_htf_alignment(
        self,
        weekly_data: TimeframeData,
        daily_data: TimeframeData,
        h4_data: TimeframeData,
        h1_data: TimeframeData,
        trade_direction: Direction
    ) -> HTFAlignmentScore:
        """
        Returns HTF alignment score with breakdown.
        Requires H1 alignment (4pts) for valid signal.
        """
```

### VWAP Calculator

**Purpose**: Calculates Volume Weighted Average Price and determines alignment with current price.

**Inputs**:
- Intraday OHLCV data with volume
- Current price

**Outputs**:
- VWAP value
- Alignment status (within 0.1% threshold)
- Confluence points (0 or 5)

**Algorithm**:
1. Calculate cumulative (price × volume) from session start
2. Calculate cumulative volume from session start
3. VWAP = cumulative (price × volume) / cumulative volume
4. If |current_price - VWAP| / VWAP < 0.001, mark as aligned
5. Award 5 points if aligned in trade direction

**Interface**:
```python
class VWAPCalculator:
    def calculate_vwap(
        self,
        intraday_data: List[OHLCVBar],
        current_price: float,
        trade_direction: Direction
    ) -> VWAPScore:
        """
        Returns VWAP value, alignment status, and confluence points.
        """
```

### Volume Spike Detector

**Purpose**: Identifies abnormal volume indicating institutional participation.

**Inputs**:
- Recent OHLCV data (20-bar lookback)
- Current bar volume

**Outputs**:
- Volume spike detected (boolean)
- Confluence points (0 or 5)

**Algorithm**:
1. Calculate average volume over last 20 bars
2. If current_volume > 1.5 × average_volume, classify as spike
3. Award 5 points if spike occurs in trade direction

**Interface**:
```python
class VolumeSpikeDetector:
    def detect_spike(
        self,
        recent_bars: List[OHLCVBar],
        trade_direction: Direction
    ) -> VolumeSpikeScore:
        """
        Returns spike detection status and confluence points.
        """
```

### ATR Filter

**Purpose**: Evaluates volatility to avoid abnormal market conditions.

**Inputs**:
- OHLC data (14-period for current ATR, 50-period for average)

**Outputs**:
- Current ATR value
- Normal range status (boolean)
- Confluence points (0 or 5)

**Algorithm**:
1. Calculate 14-period ATR
2. Calculate 50-period ATR average
3. Define normal range: 0.8 × avg_ATR < current_ATR < 1.5 × avg_ATR
4. Award 5 points if within normal range
5. Quick Scalp Engine uses ATR > threshold to detect high volatility for activation

**Interface**:
```python
class ATRFilter:
    def evaluate_volatility(
        self,
        ohlc_data: List[OHLCBar],
        instrument: Instrument
    ) -> ATRScore:
        """
        Returns ATR value, normal range status, and confluence points.
        """
```

### HTF Liquidity Target Identifier

**Purpose**: Identifies liquidity pools on higher timeframes to assess profit potential.

**Inputs**:
- Weekly OHLC data
- Daily OHLC data
- H4 OHLC data
- Trade direction
- Entry price
- Risk amount (R)

**Outputs**:
- Liquidity targets (list of price levels)
- Target within 3R (boolean)
- Confluence points (0 or 5)

**Algorithm**:
1. Identify swing highs and swing lows on each HTF
2. Cluster nearby levels (within 0.5% of each other) into liquidity pools
3. Calculate distance from entry to each pool in R multiples
4. Award 5 points if any pool exists within 3R in trade direction

**Interface**:
```python
class HTFLiquidityIdentifier:
    def identify_targets(
        self,
        weekly_data: TimeframeData,
        daily_data: TimeframeData,
        h4_data: TimeframeData,
        trade_direction: Direction,
        entry_price: float,
        risk_amount: float
    ) -> LiquidityTargetScore:
        """
        Returns liquidity targets and confluence points.
        """
```

### Key Level Detector

**Purpose**: Scores proximity to psychological price levels (250-point and 125-point levels).

**Inputs**:
- Current price
- Instrument type

**Outputs**:
- Nearest key levels (250pt and 125pt)
- Proximity distances
- Confluence points (0-15)

**Algorithm**:
1. For US30/NAS100: Calculate nearest 250-point level (e.g., 40000, 40250, 40500)
2. For US30/NAS100: Calculate nearest 125-point level (e.g., 40125, 40250, 40375)
3. For XAUUSD: Use equivalent round numbers (e.g., 2000, 2050, 2100)
4. Scoring:
   - Within 20 points of 250pt level: 15 points
   - Within 10 points of 125pt level: 10 points
   - Within 30 points (but not 20) of 250pt level: 8 points

**Interface**:
```python
class KeyLevelDetector:
    def score_proximity(
        self,
        current_price: float,
        instrument: Instrument
    ) -> KeyLevelScore:
        """
        Returns key levels, distances, and confluence points.
        """
```

### Momentum Candle Detector

**Purpose**: Identifies M1 candles indicating strong directional momentum for scalp engine.

**Inputs**:
- Current M1 candle
- Last 10 M1 candles (for range comparison)
- Last 20 M1 candles (for volume comparison)

**Outputs**:
- Momentum candle detected (boolean)
- Body percentage
- Range ratio
- Volume ratio

**Algorithm**:
1. Calculate body_percentage = |close - open| / (high - low)
2. Calculate avg_range = average(high - low) over last 10 candles
3. Calculate current_range = high - low
4. Calculate avg_volume = average(volume) over last 20 candles
5. Classify as momentum candle if:
   - body_percentage > 0.6 AND
   - current_range > avg_range AND
   - volume > avg_volume

**Interface**:
```python
class MomentumCandleDetector:
    def detect_momentum(
        self,
        current_candle: OHLCVBar,
        recent_candles: List[OHLCVBar]
    ) -> MomentumDetection:
        """
        Returns momentum detection status and metrics.
        """
```

### Risk Tracker

**Purpose**: Maintains separate risk pools and enforces limits for each engine.

**Inputs**:
- Trade requests (engine type, instrument, position size, risk amount)
- Trade outcomes (win/loss, R multiple achieved)
- Account balance

**Outputs**:
- Trade approval/rejection
- Current risk pool status
- Performance metrics

**State**:
- Core Strategy Pool:
  - Daily trade count (max 2)
  - Daily drawdown (max 2%)
  - Consecutive losses (max 2)
  - Trade history
- Quick Scalp Pool:
  - Session trade counts (London: max 5, NY: max 5, Power Hour: max 3)
  - Last trade timestamp (for cooldown)
  - Trade history

**Algorithm**:
1. On trade request:
   - Check engine-specific limits
   - Validate position size matches risk rules (Core: 1%, Scalp: 0.25-0.5%)
   - Approve or reject
2. On trade outcome:
   - Update trade counts
   - Update drawdown calculations
   - Record metrics (win/loss, R multiple)
3. On metrics query:
   - Calculate win rate, profit factor, average R:R per engine

**Interface**:
```python
class RiskTracker:
    def validate_trade(
        self,
        engine: EngineType,
        instrument: Instrument,
        position_size: float,
        risk_amount: float
    ) -> TradeValidation:
        """
        Returns approval/rejection with reason.
        """
    
    def record_outcome(
        self,
        engine: EngineType,
        trade_id: str,
        outcome: TradeOutcome
    ) -> None:
        """
        Updates risk pools and metrics.
        """
    
    def get_metrics(
        self,
        engine: EngineType
    ) -> PerformanceMetrics:
        """
        Returns win rate, profit factor, avg R:R for specified engine.
        """
```

### Core Strategy Engine

**Purpose**: Implements institutional liquidity model with 100-point confluence scoring.

**Inputs**:
- Multi-timeframe market data (W, D, H4, H1, M5)
- HTF alignment score from Bias Engine
- Scores from all confluence components
- Global filter status (session, news, spread)

**Outputs**:
- Trade signals with grade (A+, A, B)
- Entry price, stop loss, TP1, TP2
- Confluence score breakdown

**Confluence Scoring Components** (100 points total):
- HTF Alignment: 20 points (from Bias Engine)
- Key Level Proximity: 15 points (from Key Level Detector)
- Liquidity Sweep: 15 points (SMC pattern detection)
- FVG: 15 points (Fair Value Gap detection)
- Displacement: 10 points (strong directional move)
- MSS: 10 points (Market Structure Shift)
- VWAP Alignment: 5 points (from VWAP Calculator)
- Volume Spike: 5 points (from Volume Spike Detector)
- ATR Volatility: 5 points (from ATR Filter)
- HTF Liquidity Target: 5 points (from HTF Liquidity Identifier)
- Session: 5 points (active session bonus)
- Spread: 5 points (tight spread bonus)

**Signal Grading**:
- 85-100 points: A+ (auto-execute)
- 75-84 points: A (alert only)
- <75 points: B (suppress)

**Trade Management**:
- TP1: 40% position at 1R
- TP2: 40% position at 2R
- Runner: 20% position with trailing stop (activated after TP1)

**Interface**:
```python
class CoreStrategyEngine:
    def analyze_setup(
        self,
        market_data: MultiTimeframeData,
        instrument: Instrument
    ) -> Optional[CoreSignal]:
        """
        Returns signal with confluence breakdown if score >= 75.
        """
    
    def manage_position(
        self,
        position: Position,
        current_price: float
    ) -> List[OrderModification]:
        """
        Returns order modifications for TP1/TP2/trailing stop.
        """
```

### Quick Scalp Engine

**Purpose**: Captures rapid M1 momentum opportunities during high-liquidity sessions.

**Inputs**:
- M1 market data
- M5 context data
- Active session status
- Spread status
- Last trade timestamp

**Outputs**:
- Scalp signals (when all conditions met)
- Entry price, stop loss, take profit (0.8-1R)

**Entry Conditions** (all required):
1. Liquidity sweep on M1
2. Momentum candle (body > 60% range, range > avg, volume > avg)
3. Volume spike (volume > 1.5× avg)
4. Micro structure break (breaks previous M1 swing)
5. Active session (London/NY/Power Hour)
6. Spread within limits (US30: 3pts, NAS100: 2pts, XAUUSD: 2pts)
7. Cooldown elapsed (2-3 minutes since last trade)
8. Session trade limit not reached

**Stop Loss Configuration**:
- US30: 15-30 points
- NAS100: 10-25 points
- XAUUSD: 0.80-2.00 dollars

**Trade Management**:
- Single take profit at 0.8-1R
- 100% position close at TP
- No trailing stops

**Interface**:
```python
class QuickScalpEngine:
    def analyze_scalp_setup(
        self,
        m1_data: TimeframeData,
        m5_data: TimeframeData,
        instrument: Instrument
    ) -> Optional[ScalpSignal]:
        """
        Returns scalp signal if all conditions met.
        """
    
    def check_cooldown(
        self,
        last_trade_time: datetime
    ) -> bool:
        """
        Returns True if 2-3 minutes elapsed since last trade.
        """
```

### Auto-Trade Decision Engine

**Purpose**: Intelligently coordinates Core Strategy and Quick Scalp engines to prevent chaotic trading.

**Inputs**:
- Core Strategy signal (if any)
- Quick Scalp signal (if any)
- Market regime (volatility + trend strength)
- Recent performance metrics for both engines
- Active positions per instrument

**Outputs**:
- Trade decision (which engine should trade, if any)
- Reasoning for decision
- Blocked engine (if conflict resolved)

**Decision Hierarchy**:
1. Check if instrument already has active position → block both engines
2. If no signals → no decision needed
3. If only one signal → validate against market regime
4. If both signals → resolve conflict using priority rules

**Conflict Resolution Priority**:
1. Core Strategy A+ signals always win (highest priority)
2. Core Strategy A signals evaluated against regime suitability
3. If both engines suitable for regime → use performance tiebreaker
4. If only one engine suitable → that engine wins
5. If neither suitable → block both

**Market Regime Classification**:

Volatility Regimes:
- LOW: ATR < 0.8 × average
- NORMAL: 0.8 × average ≤ ATR ≤ 1.5 × average
- HIGH: 1.5 × average < ATR ≤ 2.5 × average
- EXTREME: ATR > 2.5 × average

Trend Strength:
- STRONG_TREND: Clear directional bias across HTFs
- WEAK_TREND: Some HTF alignment but not strong
- RANGING: No clear directional bias
- CHOPPY: Conflicting signals across timeframes

**Engine Suitability Rules**:

Core Strategy suitable when:
- Volatility: NORMAL or HIGH (not LOW or EXTREME)
- Trend: STRONG_TREND or WEAK_TREND (not RANGING or CHOPPY)

Quick Scalp suitable when:
- Volatility: HIGH or EXTREME (not LOW or NORMAL)
- Trend: Any (scalps work in all trend conditions)

**Performance Tiebreaker**:

When both engines suitable for regime, calculate performance score:
```
score = (win_rate × 0.4) + (profit_factor_normalized × 0.3) + (avg_rr_normalized × 0.3)
```

Scalp must score >10% higher than Core to override default Core preference.

**Position Tracking**:
- Track which engine has active position on each instrument
- Block both engines from trading instrument with active position
- Clear tracking when position closes

**Interface**:
```python
class AutoTradeDecisionEngine:
    def decide_trade(
        self,
        instrument: Instrument,
        core_signal: Optional[CoreSignal],
        scalp_signal: Optional[ScalpSignal],
        market_regime: MarketRegime,
        core_metrics: Optional[PerformanceMetrics],
        scalp_metrics: Optional[PerformanceMetrics]
    ) -> TradeDecision:
        """
        Make intelligent decision about which engine should trade.
        Returns TradeDecision with verdict and reasoning.
        """
    
    def register_position_opened(
        self,
        instrument: Instrument,
        engine: EngineType
    ) -> None:
        """
        Register that engine opened position on instrument.
        Prevents other engine from trading same instrument.
        """
    
    def register_position_closed(
        self,
        instrument: Instrument
    ) -> None:
        """
        Register that position closed on instrument.
        Allows either engine to trade instrument again.
        """
    
    def get_engine_preference(
        self,
        regime: MarketRegime
    ) -> EnginePreference:
        """
        Get general engine preference for current regime.
        Useful for UI display and monitoring.
        """
```

### Session Manager

**Purpose**: Enforces signal window and tracks active sessions.

**Inputs**:
- Current time (SAST)
- Engine type

**Outputs**:
- Signal generation permitted (boolean)
- Active session type (London/NY/Power Hour/None)
- Session trade count

**Signal Window**: 10:00-22:00 SAST (both engines)

**Active Sessions**:
- London: 10:00-13:00 SAST (max 5 scalp trades)
- NY Open: 15:30-18:00 SAST (max 5 scalp trades)
- Power Hour: 20:00-22:00 SAST (max 3 scalp trades)

**Interface**:
```python
class SessionManager:
    def is_signal_permitted(
        self,
        current_time: datetime,
        engine: EngineType
    ) -> bool:
        """
        Returns True if within signal window.
        """
    
    def get_active_session(
        self,
        current_time: datetime
    ) -> Optional[SessionType]:
        """
        Returns active session type or None.
        """
    
    def check_session_limit(
        self,
        session: SessionType,
        current_count: int
    ) -> bool:
        """
        Returns True if session trade limit not exceeded.
        """
```

## Data Models

### Core Data Structures

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

class Instrument(Enum):
    US30 = "US30"
    XAUUSD = "XAUUSD"
    NAS100 = "NAS100"

class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class EngineType(Enum):
    CORE_STRATEGY = "CORE_STRATEGY"
    QUICK_SCALP = "QUICK_SCALP"

class SessionType(Enum):
    LONDON = "LONDON"
    NY_OPEN = "NY_OPEN"
    POWER_HOUR = "POWER_HOUR"

class SignalGrade(Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"

@dataclass
class OHLCVBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class TimeframeData:
    instrument: Instrument
    timeframe: str  # "W", "D", "H4", "H1", "M5", "M1"
    bars: List[OHLCVBar]

@dataclass
class HTFAlignmentScore:
    total: int  # 0-20
    weekly: int  # 0-6
    daily: int  # 0-6
    h4: int  # 0-4
    h1: int  # 0-4

@dataclass
class ConfluenceScore:
    total: int  # 0-100
    htf_alignment: int  # 0-20
    key_level: int  # 0-15
    liquidity_sweep: int  # 0-15
    fvg: int  # 0-15
    displacement: int  # 0-10
    mss: int  # 0-10
    vwap: int  # 0-5
    volume_spike: int  # 0-5
    atr: int  # 0-5
    htf_target: int  # 0-5
    session: int  # 0-5
    spread: int  # 0-5

@dataclass
class CoreSignal:
    instrument: Instrument
    direction: Direction
    entry_price: float
    stop_loss: float
    tp1: float  # 1R
    tp2: float  # 2R
    confluence_score: ConfluenceScore
    grade: SignalGrade
    timestamp: datetime

@dataclass
class ScalpSignal:
    instrument: Instrument
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float  # 0.8-1R
    session: SessionType
    timestamp: datetime

@dataclass
class Position:
    position_id: str
    engine: EngineType
    instrument: Instrument
    direction: Direction
    entry_price: float
    stop_loss: float
    size: float
    remaining_size: float
    tp1_hit: bool
    tp2_hit: bool
    trailing_active: bool

@dataclass
class TradeOutcome:
    trade_id: str
    win: bool
    r_multiple: float
    profit_loss: float

@dataclass
class PerformanceMetrics:
    win_rate: float
    profit_factor: float
    average_rr: float
    total_trades: int
    winning_trades: int
    losing_trades: int

@dataclass
class RiskPoolStatus:
    engine: EngineType
    daily_trade_count: int
    daily_drawdown: float
    consecutive_losses: int
    session_counts: dict  # SessionType -> int

@dataclass
class Configuration:
    instruments: List[Instrument]
    signal_window_start: str  # "10:00"
    signal_window_end: str  # "22:00"
    core_risk_per_trade: float  # 0.01 (1%)
    core_max_daily_trades: int  # 2
    core_max_daily_drawdown: float  # 0.02 (2%)
    scalp_risk_per_trade_min: float  # 0.0025 (0.25%)
    scalp_risk_per_trade_max: float  # 0.005 (0.5%)
    scalp_session_limits: dict  # SessionType -> int
    spread_limits_global: dict  # Instrument -> float
    spread_limits_scalp: dict  # Instrument -> float
    slippage_limit: float  # 10 points
    news_buffer_before: int  # 30 minutes
    news_buffer_after: int  # 60 minutes
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, several redundancies were identified:

- **Signal window properties (3.2, 3.3)**: These are complementary - one tests inside window, one tests outside. Both provide unique validation value.
- **Confluence scoring (4.1-4.18)**: Rather than testing each component individually, we combine into comprehensive properties that test the scoring system as a whole.
- **Signal grading (5.1-5.3, 5.4-5.6)**: Grade assignment and grade action can be combined - if we verify correct actions for scores, we implicitly verify grading.
- **TP levels (6.1, 6.3)**: Both TP1 and TP2 placement can be tested in a single property about multi-level TP configuration.
- **TP execution (6.2, 6.4)**: Both TP1 and TP2 execution can be tested together as partial position closes.
- **Session classification (9.1-9.4)**: All session time ranges can be tested in one property about session identification.
- **Stop loss ranges (10.1-10.3)**: All instruments can be tested in one property about stop loss configuration.
- **Spread filtering (12.1-12.3, 18.1-18.3)**: Scalp-specific and global spread limits can be combined into one comprehensive spread filtering property.
- **Cooldown timing (13.2, 13.3)**: These are complementary aspects of the same cooldown mechanism.
- **News event blocking (17.2, 17.3)**: Before and after blocking can be combined into one property about news event buffers.
- **Slippage handling (19.1-19.5)**: Measurement, rejection, and logging can be combined into one comprehensive slippage protection property.
- **Configuration round-trip (27.1, 27.3, 27.4)**: The round-trip property subsumes individual parsing and serialization tests.
- **Signal round-trip (28.1, 28.3, 28.4)**: Same as configuration - round-trip subsumes individual tests.

### Property 1: Signal Window Enforcement

*For any* time outside the 10:00-22:00 SAST window, both Core Strategy Engine and Quick Scalp Engine should block signal generation regardless of market conditions.

**Validates: Requirements 3.2, 3.3**

### Property 2: Signal Window Permission

*For any* time within the 10:00-22:00 SAST window, the Session Manager should permit signal generation (subject to other filters).

**Validates: Requirements 3.2**

### Property 3: Confluence Score Calculation

*For any* valid market data across all timeframes, the Core Strategy Engine should calculate a confluence score between 0 and 100 points where the sum of all component scores equals the total score.

**Validates: Requirements 4.1-4.18**

### Property 4: Confluence Score Components Range

*For any* confluence score calculation, each component score should fall within its defined maximum: HTF alignment (0-20), key level (0-15), liquidity sweep (0-15), FVG (0-15), displacement (0-10), MSS (0-10), VWAP (0-5), volume spike (0-5), ATR (0-5), HTF target (0-5), session (0-5), spread (0-5).

**Validates: Requirements 4.1-4.18**

### Property 5: Signal Grade Assignment and Action

*For any* confluence score, the system should assign grade A+ (85-100 points) with auto-execution enabled, grade A (75-84 points) with alert-only, or grade B (<75 points) with signal suppressed.

**Validates: Requirements 5.1-5.6**

### Property 6: Core Strategy Multi-Level Take Profit Configuration

*For any* Core Strategy trade, the system should set TP1 at 1R distance and TP2 at 2R distance from entry price.

**Validates: Requirements 6.1, 6.3**

### Property 7: Core Strategy Partial Position Closes

*For any* Core Strategy position, reaching TP1 should close 40% of position size, and reaching TP2 should close an additional 40% of the remaining position.

**Validates: Requirements 6.2, 6.4**

### Property 8: Core Strategy Trailing Stop Activation

*For any* Core Strategy position, reaching TP1 should activate a trailing stop on the remaining 20% runner position.

**Validates: Requirements 6.5**

### Property 9: Core Strategy Position Sizing

*For any* Core Strategy trade, the position size should be calculated to risk exactly 1% of current account balance.

**Validates: Requirements 7.1**

### Property 10: Core Strategy Daily Trade Limit

*For any* trading day, the Core Strategy Engine should block trades after 2 trades have been executed, regardless of outcome.

**Validates: Requirements 7.2**

### Property 11: Quick Scalp Entry Conditions

*For any* M1 market data, the Quick Scalp Engine should generate a signal only when all conditions are present: liquidity sweep, momentum candle (body > 60% range, range > avg, volume > avg), volume spike, micro structure break, active session, spread within limits, and cooldown elapsed.

**Validates: Requirements 8.1-8.7**

### Property 12: Session Time Classification

*For any* time in SAST, the system should correctly classify it as London session (10:00-13:00), NY Open session (15:30-18:00), Power Hour session (20:00-22:00), or no active session.

**Validates: Requirements 9.1-9.4**

### Property 13: Session Trade Limits

*For any* active session, the Quick Scalp Engine should enforce session-specific trade limits: London (max 5), NY Open (max 5), Power Hour (max 3).

**Validates: Requirements 9.5-9.7**

### Property 14: Instrument-Specific Stop Loss Ranges

*For any* Quick Scalp trade, the stop loss should fall within instrument-specific ranges: US30 (15-30 points), NAS100 (10-25 points), XAUUSD (0.80-2.00 dollars).

**Validates: Requirements 10.1-10.3**

### Property 15: Scalp Single Take Profit

*For any* Quick Scalp trade, the system should set a single take profit between 0.8R and 1R distance, close 100% of position when reached, and never activate trailing stops.

**Validates: Requirements 11.1-11.3**

### Property 16: Comprehensive Spread Filtering

*For any* trade attempt, the system should enforce instrument-specific spread limits: scalp trades blocked when US30 > 3pts, NAS100 > 2pts, XAUUSD > 2pts; all trades blocked when US30 > 5pts, NAS100 > 4pts, XAUUSD > 3pts.

**Validates: Requirements 12.1-12.3, 18.1-18.3**

### Property 17: Scalp Cooldown Period

*For any* scalp trade attempt, the system should block the trade if less than 2 minutes have elapsed since the last scalp trade completion, and permit it if 2-3 minutes have elapsed.

**Validates: Requirements 13.1-13.3**

### Property 18: Scalp Position Sizing

*For any* Quick Scalp trade, the position size should be calculated to risk between 0.25% and 0.5% of current account balance.

**Validates: Requirements 14.1**

### Property 19: Engine Independence

*For any* state where one engine reaches its limits (Core Strategy: 2 daily trades or 2% drawdown; Quick Scalp: session trade limit), the other engine should continue operating without restriction.

**Validates: Requirements 15.1-15.6**

### Property 20: Engine Activation Conditions

*For any* market state, the Quick Scalp Engine should activate only when high volatility (ATR > threshold), active session, and tight spreads are present; the Core Strategy Engine should activate only when full SMC setup exists and confluence score >= 85.

**Validates: Requirements 16.1-16.4**

### Property 21: News Event Buffer Blocking

*For any* time within 30 minutes before or 60 minutes after a high-impact news event (CPI, NFP, FOMC, Fed speech), both engines should block all signal generation.

**Validates: Requirements 17.2, 17.3**

### Property 22: Slippage Protection

*For any* trade execution, the system should measure slippage between expected and actual fill price, reject the trade if slippage exceeds 10 points, and log rejection details including timestamp and slippage amount.

**Validates: Requirements 19.1-19.5**

### Property 23: HTF Alignment Scoring

*For any* market data across Weekly, Daily, H4, and H1 timeframes, the Bias Engine should calculate HTF alignment score using 6 points for Weekly, 6 points for Daily, 4 points for H4, and 4 points for H1, requiring H1 alignment (4pts minimum) for any valid signal.

**Validates: Requirements 20.1-20.6**

### Property 24: VWAP Alignment Detection

*For any* intraday market data, the system should calculate VWAP as cumulative (price × volume) / cumulative volume, classify price as aligned when within 0.1% of VWAP, and award 5 confluence points when aligned in trade direction.

**Validates: Requirements 21.1-21.3**

### Property 25: Volume Spike Detection

*For any* candle, the system should calculate average volume over the last 20 candles, classify current candle as volume spike when volume exceeds 1.5× average, and award 5 confluence points when spike occurs in trade direction.

**Validates: Requirements 22.1-22.3**

### Property 26: ATR Volatility Filtering

*For any* market data, the system should calculate 14-period ATR and 50-period ATR average, classify volatility as normal when 0.8× avg < current ATR < 1.5× avg, and award 5 confluence points when within normal range.

**Validates: Requirements 23.1-23.3**

### Property 27: HTF Liquidity Target Identification

*For any* market data across Weekly, Daily, and H4 timeframes, the system should identify liquidity pools as clusters of swing highs/lows, calculate distance to pools in R multiples, and award 5 confluence points when a pool exists within 3R in trade direction.

**Validates: Requirements 24.1-24.5**

### Property 28: Key Level Proximity Scoring

*For any* current price and instrument, the system should identify nearest 250-point and 125-point key levels (or equivalent for XAUUSD), and award confluence points based on proximity: 15 points within 20 points of 250pt level, 10 points within 10 points of 125pt level, 8 points within 30 points (but not 20) of 250pt level.

**Validates: Requirements 25.1-25.6**

### Property 29: Performance Metrics Calculation

*For any* trade history for an engine, the Risk Tracker should correctly calculate win rate (wins/total), profit factor (gross profit/gross loss), and average risk-reward ratio (sum of R multiples/trade count).

**Validates: Requirements 26.1-26.8**

### Property 30: Configuration Round-Trip

*For any* valid Configuration object, serializing then parsing should produce an equivalent Configuration object with all fields preserved.

**Validates: Requirements 27.1-27.7**

### Property 31: Configuration Validation

*For any* configuration file, the parser should validate that all required fields are present and numeric values fall within acceptable ranges, returning descriptive error messages for invalid configurations.

**Validates: Requirements 27.2, 27.5-27.7**

### Property 32: Signal Round-Trip

*For any* valid Signal object (Core or Scalp), serializing then parsing should produce an equivalent Signal object with all fields preserved including ISO 8601 timestamps.

**Validates: Requirements 28.1-28.6**

### Property 33: Signal Validation

*For any* trade signal, the parser should validate that required fields are present (instrument, direction, entry price, stop loss, take profit levels) and return descriptive error messages for invalid signals.

**Validates: Requirements 28.2, 28.5**

### Property 34: Engine Conflict Resolution

*For any* scenario where both Core Strategy and Quick Scalp engines have valid signals for the same instrument, the Auto-Trade Decision Engine should ensure only one engine trades, with Core Strategy A+ signals taking absolute priority.

**Validates: Requirements 15.1-15.6**

### Property 35: Volatility Regime Detection

*For any* market regime, the Auto-Trade Decision Engine should favor Quick Scalp engine in high volatility environments and Core Strategy engine in trending markets with normal volatility.

**Validates: Requirements 16.1-16.4**

## Error Handling

### Market Data Errors

**Missing Timeframe Data**: When required timeframe data is unavailable, the system should log the missing timeframe, skip analysis for that instrument, and continue processing other instruments. Core Strategy Engine requires W, D, H4, H1, M5 data; Quick Scalp Engine requires M1, M5 data.

**Stale Data**: When market data timestamp is more than 5 minutes old, the system should reject the data, log a staleness warning, and wait for fresh data before generating signals.

**Malformed OHLCV Bars**: When a bar has invalid values (high < low, close outside high-low range, negative volume), the system should log the malformed bar, exclude it from calculations, and continue with remaining valid data.

### Execution Errors

**Order Rejection**: When broker rejects an order, the system should log rejection reason, notify user via alert, and not count the attempt against daily trade limits.

**Partial Fill**: When an order is partially filled, the system should adjust position size tracking to reflect actual fill size, recalculate stop loss and take profit levels proportionally, and log the partial fill details.

**Connection Loss**: When connection to broker is lost, the system should immediately halt all new signal generation, maintain monitoring of existing positions if possible, attempt reconnection with exponential backoff (1s, 2s, 4s, 8s, max 60s), and alert user of connection status.

### Risk Management Errors

**Insufficient Margin**: When account margin is insufficient for calculated position size, the system should reduce position size to maximum allowable while maintaining risk percentage, log the margin constraint, and proceed with reduced size if still above minimum viable position.

**Daily Limit Reached**: When an engine reaches its daily trade limit or drawdown limit, the system should block further trades for that engine, log the limit breach with timestamp, continue operating the other engine normally, and reset limits at start of next trading day (00:00 SAST).

**Risk Pool Calculation Error**: When risk pool calculations produce invalid results (negative drawdown, NaN values), the system should halt trading for the affected engine, log the calculation error with input values, alert user immediately, and require manual intervention to resume.

### Configuration Errors

**Invalid Configuration File**: When configuration file cannot be parsed or contains invalid values, the system should refuse to start, display detailed error message indicating which field is invalid and why, and provide example of correct format.

**Missing Required Fields**: When configuration is missing required fields, the system should list all missing fields, refuse to start, and provide default values as suggestions.

**Out-of-Range Values**: When configuration contains values outside acceptable ranges (e.g., risk > 5%, negative spreads), the system should list all out-of-range values with their limits, refuse to start, and suggest corrected values.

### Session and Timing Errors

**Clock Skew**: When system clock differs significantly from broker server time (>60 seconds), the system should log the time difference, use broker server time for all session and news event calculations, and alert user to synchronize system clock.

**News Calendar Unavailable**: When economic calendar service is unavailable, the system should operate in conservative mode (block trading 30 minutes before and after typical news times: 08:30, 10:00, 14:00, 15:30, 19:00 SAST), log calendar unavailability, and attempt to refresh calendar every 5 minutes.

**Session Transition Edge Cases**: When a trade signal is generated within 10 seconds of session boundary (e.g., 12:59:55), the system should validate that the signal can be executed within the current session, reject the signal if execution would occur in next session, and log the boundary rejection.

## Testing Strategy

### Dual Testing Approach

The system requires both unit testing and property-based testing to achieve comprehensive coverage. Unit tests verify specific examples, edge cases, and integration points. Property-based tests verify universal properties across randomized inputs with minimum 100 iterations per test.

### Unit Testing Focus

**Specific Examples**:
- Core Strategy signal with known confluence breakdown (e.g., 87 points = A+ grade)
- Quick Scalp signal during London session with all conditions met
- Configuration file with all fields populated correctly
- Trade signal with valid ISO 8601 timestamp

**Edge Cases**:
- Confluence score exactly at grade boundaries (75, 85 points)
- Time exactly at session boundaries (10:00:00, 13:00:00, 22:00:00)
- Spread exactly at limit thresholds
- Cooldown period exactly at 2-minute boundary
- Empty market data arrays
- Single-bar timeframe data
- Zero volume bars

**Integration Points**:
- Market data flow from ingestion through both engines
- Risk Tracker coordination between engines
- Session Manager interaction with both engines
- News Filter blocking both engines simultaneously

**Error Conditions**:
- Malformed configuration files
- Invalid signal messages
- Missing required timeframe data
- Connection loss during trade execution
- Insufficient margin scenarios

### Property-Based Testing Configuration

**Library Selection**: Use `hypothesis` for Python implementation, `fast-check` for TypeScript/JavaScript, or `QuickCheck` for other languages.

**Test Configuration**: Each property test must run minimum 100 iterations with randomized inputs.

**Test Tagging**: Each property test must include a comment tag referencing the design property:
```python
# Feature: dual-engine-strategy-system, Property 1: Signal Window Enforcement
def test_signal_window_blocks_outside_hours(time):
    ...
```

### Property Test Implementation Guidance

**Property 1-2 (Signal Window)**: Generate random times across 24-hour period, verify blocking/permission based on 10:00-22:00 window.

**Property 3-4 (Confluence Scoring)**: Generate random market data across all timeframes, verify score calculation and component ranges.

**Property 5 (Signal Grading)**: Generate random confluence scores 0-100, verify correct grade assignment and action.

**Property 6-8 (Core Strategy Trade Management)**: Generate random Core Strategy trades, verify TP levels, partial closes, and trailing stop activation.

**Property 9-10 (Core Strategy Risk)**: Generate random account balances and trade sequences, verify 1% position sizing and 2-trade daily limit.

**Property 11 (Scalp Entry)**: Generate random M1 data with varying combinations of conditions, verify signals only when all conditions met.

**Property 12-13 (Session Management)**: Generate random times and trade sequences, verify session classification and trade limits.

**Property 14-15 (Scalp Trade Management)**: Generate random scalp trades, verify stop loss ranges, single TP, and no trailing stops.

**Property 16 (Spread Filtering)**: Generate random spread values, verify correct blocking for scalp-specific and global limits.

**Property 17 (Cooldown)**: Generate random trade sequences with varying time gaps, verify cooldown enforcement.

**Property 18 (Scalp Position Sizing)**: Generate random account balances, verify 0.25-0.5% risk per scalp trade.

**Property 19 (Engine Independence)**: Generate scenarios where one engine hits limits, verify other engine continues.

**Property 20 (Engine Activation)**: Generate random market states, verify correct activation conditions for each engine.

**Property 21 (News Blocking)**: Generate random times relative to news events, verify 30-minute before and 60-minute after blocking.

**Property 22 (Slippage)**: Generate random expected vs actual fill prices, verify rejection when slippage > 10 points and logging.

**Property 23-28 (Confluence Components)**: Generate random market data, verify correct calculation of HTF alignment, VWAP, volume spikes, ATR, liquidity targets, and key levels.

**Property 29 (Performance Metrics)**: Generate random trade histories, verify correct calculation of win rate, profit factor, and average R:R.

**Property 30-33 (Parsing/Serialization)**: Generate random valid Configuration and Signal objects, verify round-trip preservation and validation error messages.

### Test Data Generation Strategies

**Market Data Generators**:
- Random OHLCV bars with valid constraints (high >= low, close within range)
- Trending data (consistent higher highs/lows or lower highs/lows)
- Ranging data (oscillating within bounds)
- Volatile data (large ATR values)
- Low-volume data (below average volume)
- High-volume data (above average volume)

**Time Generators**:
- Random times across 24-hour period
- Times clustered around session boundaries
- Times clustered around news event times
- Sequential times with varying gaps (for cooldown testing)

**Configuration Generators**:
- Valid configurations with all required fields
- Configurations with missing fields
- Configurations with out-of-range values
- Configurations with invalid types

**Trade Sequence Generators**:
- Winning trades, losing trades, mixed outcomes
- Rapid sequences (testing cooldown)
- Daily sequences (testing daily limits)
- Session sequences (testing session limits)

### Coverage Goals

- **Line Coverage**: Minimum 85% across all modules
- **Branch Coverage**: Minimum 80% for conditional logic
- **Property Coverage**: 100% of design properties implemented as property tests
- **Edge Case Coverage**: All identified edge cases covered by unit tests
- **Error Path Coverage**: All error handling paths exercised by tests

### Continuous Testing

- Run unit tests on every commit
- Run property tests (100 iterations) on every pull request
- Run extended property tests (1000 iterations) nightly
- Run integration tests against mock broker API before deployment
- Monitor test execution time; property tests should complete within 5 minutes

