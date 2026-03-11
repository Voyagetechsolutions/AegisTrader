# Implementation Plan: Dual-Engine Strategy System

## Overview

This implementation plan rebuilds Aegis Trader with a dual-engine architecture: a Core Strategy Engine using institutional liquidity models with 100-point confluence scoring, and a Quick Scalp Engine for rapid M1 momentum trades. Both engines operate independently with separate risk pools while sharing common infrastructure (session management, news filtering, spread monitoring).

The implementation follows a bottom-up approach: foundation (data models, configuration), shared infrastructure, confluence components, engine-specific logic, risk management, coordination, comprehensive testing (33 property-based tests), and integration.

## Tasks

- [ ] 1. Foundation - Data Models and Configuration
  - [x] 1.1 Create core data models and enums
    - Implement Instrument, Direction, EngineType, SessionType, SignalGrade enums
    - Implement OHLCVBar, TimeframeData dataclasses
    - Implement HTFAlignmentScore, ConfluenceScore dataclasses
    - Implement CoreSignal, ScalpSignal, Position dataclasses
    - Implement TradeOutcome, PerformanceMetrics, RiskPoolStatus dataclasses
    - Implement Configuration dataclass with all engine parameters
    - _Requirements: 27.1, 27.5_
  
  - [x] 1.2 Write property test for Configuration round-trip
    - **Property 30: Configuration Round-Trip**
    - **Validates: Requirements 27.1, 27.3, 27.4**
    - Generate random valid Configuration objects
    - Verify serialize → parse → serialize produces equivalent object
  
  - [x] 1.3 Write property test for Configuration validation
    - **Property 31: Configuration Validation**
    - **Validates: Requirements 27.2, 27.5-27.7**
    - Generate configurations with missing fields and out-of-range values
    - Verify descriptive error messages returned
  
  - [x] 1.4 Create signal parser and serializer
    - Implement Signal_Parser for CoreSignal and ScalpSignal
    - Implement Signal_Serializer with ISO 8601 timestamp formatting
    - Validate required fields: instrument, direction, entry, stop loss, take profit
    - _Requirements: 28.1, 28.2, 28.5_
  
  - [ ] 1.5 Write property test for Signal round-trip
    - **Property 32: Signal Round-Trip**
    - **Validates: Requirements 28.1-28.6**
    - Generate random valid Signal objects
    - Verify serialize → parse → serialize preserves all fields including timestamps
  
  - [ ] 1.6 Write property test for Signal validation
    - **Property 33: Signal Validation**
    - **Validates: Requirements 28.2, 28.5**
    - Generate signals with missing required fields
    - Verify descriptive error messages returned

- [ ] 2. Shared Infrastructure - Session Manager
  - [x] 2.1 Implement Session Manager core logic
    - Implement signal window enforcement (10:00-22:00 SAST)
    - Implement session classification (London, NY Open, Power Hour)
    - Implement session trade limit tracking
    - Track current time in SAST timezone
    - _Requirements: 3.1-3.5, 9.1-9.7_
  
  - [ ] 2.2 Write property test for signal window enforcement
    - **Property 1: Signal Window Enforcement**
    - **Validates: Requirements 3.2, 3.3**
    - Generate random times outside 10:00-22:00 SAST
    - Verify both engines blocked from signal generation
  
  - [ ] 2.3 Write property test for signal window permission
    - **Property 2: Signal Window Permission**
    - **Validates: Requirements 3.2**
    - Generate random times within 10:00-22:00 SAST
    - Verify signal generation permitted (subject to other filters)
  
  - [ ] 2.4 Write property test for session time classification
    - **Property 12: Session Time Classification**
    - **Validates: Requirements 9.1-9.4**
    - Generate random times across 24-hour period
    - Verify correct session classification (London/NY/Power Hour/None)
  
  - [ ] 2.5 Write property test for session trade limits
    - **Property 13: Session Trade Limits**
    - **Validates: Requirements 9.5-9.7**
    - Generate trade sequences within sessions
    - Verify limits enforced: London (5), NY (5), Power Hour (3)

- [ ] 3. Shared Infrastructure - News Filter, Spread Monitor, Slippage Monitor
  - [x] 3.1 Implement News Filter
    - Maintain economic calendar for CPI, NFP, FOMC, Fed speeches
    - Block trading 30 minutes before news events
    - Block trading 60 minutes after news events
    - Handle calendar unavailability with conservative mode
    - _Requirements: 17.1-17.7_
  
  - [ ] 3.2 Write property test for news event buffer blocking
    - **Property 21: News Event Buffer Blocking**
    - **Validates: Requirements 17.2, 17.3**
    - Generate random times relative to news events
    - Verify blocking 30min before and 60min after
  
  - [ ] 3.3 Implement Spread Monitor
    - Track real-time bid-ask spreads for US30, XAUUSD, NAS100
    - Enforce global spread limits (US30: 5pts, NAS100: 4pts, XAUUSD: 3pts)
    - Enforce scalp-specific limits (US30: 3pts, NAS100: 2pts, XAUUSD: 2pts)
    - _Requirements: 12.1-12.3, 18.1-18.3_
  
  - [ ] 3.4 Write property test for comprehensive spread filtering
    - **Property 16: Comprehensive Spread Filtering**
    - **Validates: Requirements 12.1-12.3, 18.1-18.3**
    - Generate random spread values for each instrument
    - Verify scalp-specific and global limits enforced correctly
  
  - [ ] 3.5 Implement Slippage Monitor
    - Measure slippage between expected and actual fill price
    - Reject trades when slippage exceeds 10 points
    - Log rejection details with timestamp and slippage amount
    - _Requirements: 19.1-19.5_
  
  - [ ] 3.6 Write property test for slippage protection
    - **Property 22: Slippage Protection**
    - **Validates: Requirements 19.1-19.5**
    - Generate random expected vs actual fill prices
    - Verify rejection when slippage > 10 points and logging occurs

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Confluence Components - Bias Engine and VWAP Calculator
  - [ ] 5.1 Implement Bias Engine HTF alignment scoring
    - Analyze Weekly, Daily, H4, H1 timeframes for trend direction
    - Award points: Weekly (6), Daily (6), H4 (4), H1 (4)
    - Require H1 alignment (4pts minimum) for valid signals
    - Identify market structure (higher highs/lows vs lower highs/lows)
    - _Requirements: 20.1-20.6, 4.1-4.6_
  
  - [ ] 5.2 Write property test for HTF alignment scoring
    - **Property 23: HTF Alignment Scoring**
    - **Validates: Requirements 20.1-20.6**
    - Generate random market data across W, D, H4, H1 timeframes
    - Verify correct point allocation and H1 requirement
  
  - [ ] 5.3 Implement VWAP Calculator
    - Calculate VWAP as cumulative (price × volume) / cumulative volume
    - Detect alignment when price within 0.1% of VWAP
    - Award 5 confluence points when aligned in trade direction
    - _Requirements: 21.1-21.3_
  
  - [ ] 5.4 Write property test for VWAP alignment detection
    - **Property 24: VWAP Alignment Detection**
    - **Validates: Requirements 21.1-21.3**
    - Generate random intraday OHLCV data
    - Verify VWAP calculation and 0.1% alignment threshold

- [ ] 6. Confluence Components - Volume Spike Detector and ATR Filter
  - [ ] 6.1 Implement Volume Spike Detector
    - Calculate average volume over last 20 candles
    - Classify spike when current volume > 1.5× average
    - Award 5 confluence points when spike in trade direction
    - _Requirements: 22.1-22.3_
  
  - [ ] 6.2 Write property test for volume spike detection
    - **Property 25: Volume Spike Detection**
    - **Validates: Requirements 22.1-22.3**
    - Generate random candle data with varying volume
    - Verify 1.5× threshold and directional alignment
  
  - [ ] 6.3 Implement ATR Filter
    - Calculate 14-period ATR and 50-period ATR average
    - Classify normal range: 0.8× avg < ATR < 1.5× avg
    - Award 5 confluence points when within normal range
    - Support Quick Scalp Engine volatility detection (ATR > threshold)
    - _Requirements: 23.1-23.3, 16.3_
  
  - [ ] 6.4 Write property test for ATR volatility filtering
    - **Property 26: ATR Volatility Filtering**
    - **Validates: Requirements 23.1-23.3**
    - Generate random OHLC data
    - Verify ATR calculation and normal range classification

- [ ] 7. Confluence Components - HTF Liquidity Target Identifier and Key Level Detector
  - [ ] 7.1 Implement HTF Liquidity Target Identifier
    - Identify swing highs and lows on Weekly, Daily, H4 timeframes
    - Cluster nearby levels (within 0.5%) into liquidity pools
    - Calculate distance to pools in R multiples
    - Award 5 confluence points when pool within 3R in trade direction
    - _Requirements: 24.1-24.5_
  
  - [ ] 7.2 Write property test for HTF liquidity target identification
    - **Property 27: HTF Liquidity Target Identification**
    - **Validates: Requirements 24.1-24.5**
    - Generate random HTF market data with swing points
    - Verify pool clustering and 3R distance calculation
  
  - [ ] 7.3 Implement Key Level Detector
    - Identify 250-point and 125-point key levels for US30/NAS100
    - Identify equivalent round number levels for XAUUSD
    - Score proximity: 15pts (within 20pts of 250pt), 10pts (within 10pts of 125pt), 8pts (within 30pts of 250pt)
    - _Requirements: 25.1-25.6_
  
  - [ ] 7.4 Write property test for key level proximity scoring
    - **Property 28: Key Level Proximity Scoring**
    - **Validates: Requirements 25.1-25.6**
    - Generate random prices for each instrument
    - Verify correct key level identification and proximity scoring

- [ ] 8. Core Strategy Engine - Confluence Scoring and Signal Grading
  - [ ] 8.1 Implement Core Strategy Engine confluence scoring system
    - Integrate all confluence components (HTF, key level, liquidity sweep, FVG, displacement, MSS, VWAP, volume, ATR, HTF target, session, spread)
    - Calculate total score (0-100 points) as sum of components
    - Ensure each component stays within defined maximum
    - _Requirements: 4.1-4.18_
  
  - [ ] 8.2 Write property test for confluence score calculation
    - **Property 3: Confluence Score Calculation**
    - **Validates: Requirements 4.1-4.18**
    - Generate random market data across all timeframes
    - Verify total score equals sum of components and falls within 0-100
  
  - [ ] 8.3 Write property test for confluence score component ranges
    - **Property 4: Confluence Score Components Range**
    - **Validates: Requirements 4.1-4.18**
    - Generate random confluence calculations
    - Verify each component within its maximum: HTF (20), key level (15), liquidity sweep (15), FVG (15), displacement (10), MSS (10), VWAP (5), volume (5), ATR (5), HTF target (5), session (5), spread (5)
  
  - [ ] 8.4 Implement signal grading and action logic
    - Assign grade A+ (85-100 points) with auto-execution
    - Assign grade A (75-84 points) with alert-only
    - Assign grade B (<75 points) with suppression
    - _Requirements: 5.1-5.6_
  
  - [ ] 8.5 Write property test for signal grade assignment and action
    - **Property 5: Signal Grade Assignment and Action**
    - **Validates: Requirements 5.1-5.6**
    - Generate random confluence scores 0-100
    - Verify correct grade and action for each score range

- [ ] 9. Core Strategy Engine - Trade Management
  - [ ] 9.1 Implement multi-level take profit configuration
    - Set TP1 at 1R distance from entry
    - Set TP2 at 2R distance from entry
    - Calculate R based on stop loss distance
    - _Requirements: 6.1, 6.3_
  
  - [ ] 9.2 Write property test for multi-level TP configuration
    - **Property 6: Core Strategy Multi-Level Take Profit Configuration**
    - **Validates: Requirements 6.1, 6.3**
    - Generate random Core Strategy trades
    - Verify TP1 at 1R and TP2 at 2R
  
  - [ ] 9.3 Implement partial position close logic
    - Close 40% of position when TP1 reached
    - Close additional 40% when TP2 reached
    - Maintain 20% runner position
    - _Requirements: 6.2, 6.4_
  
  - [ ] 9.4 Write property test for partial position closes
    - **Property 7: Core Strategy Partial Position Closes**
    - **Validates: Requirements 6.2, 6.4**
    - Generate random position sizes and TP hits
    - Verify 40% close at TP1, 40% close at TP2
  
  - [ ] 9.5 Implement trailing stop activation
    - Activate trailing stop on 20% runner after TP1 hit
    - Maintain trailing stop until stopped out
    - _Requirements: 6.5, 6.6_
  
  - [ ] 9.6 Write property test for trailing stop activation
    - **Property 8: Core Strategy Trailing Stop Activation**
    - **Validates: Requirements 6.5**
    - Generate random Core Strategy positions
    - Verify trailing stop activates after TP1 on 20% runner

- [ ] 10. Core Strategy Engine - Risk Management
  - [ ] 10.1 Implement Core Strategy position sizing
    - Calculate position size to risk exactly 1% of account balance
    - Account for instrument-specific pip values and lot sizes
    - _Requirements: 7.1_
  
  - [ ] 10.2 Write property test for Core Strategy position sizing
    - **Property 9: Core Strategy Position Sizing**
    - **Validates: Requirements 7.1**
    - Generate random account balances and stop loss distances
    - Verify position size risks exactly 1% of balance
  
  - [ ] 10.3 Implement Core Strategy daily trade limit
    - Track daily trade count for Core Strategy Engine
    - Block trades after 2 trades executed (regardless of outcome)
    - Reset counter at start of trading day (00:00 SAST)
    - _Requirements: 7.2_
  
  - [ ] 10.4 Write property test for Core Strategy daily trade limit
    - **Property 10: Core Strategy Daily Trade Limit**
    - **Validates: Requirements 7.2**
    - Generate trade sequences across multiple days
    - Verify blocking after 2 trades per day

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Quick Scalp Engine - Entry Conditions
  - [ ] 12.1 Implement Momentum Candle Detector
    - Calculate body percentage: |close - open| / (high - low)
    - Calculate range ratio: current range / average of last 10 candles
    - Calculate volume ratio: current volume / average of last 20 candles
    - Classify as momentum candle when body > 60% AND range > avg AND volume > avg
    - _Requirements: 8.3-8.5_
  
  - [ ] 12.2 Implement liquidity sweep detection on M1
    - Identify when price triggers stops above/below swing highs/lows
    - Detect reversal after sweep
    - _Requirements: 8.1_
  
  - [ ] 12.3 Implement micro structure break detection
    - Identify previous M1 swing high/low
    - Detect when momentum candle breaks swing level
    - _Requirements: 8.6_
  
  - [ ] 12.4 Integrate all Quick Scalp entry conditions
    - Require all conditions: liquidity sweep, momentum candle, volume spike, micro structure break
    - Require active session (London/NY/Power Hour)
    - Require spread within scalp limits
    - Require cooldown elapsed
    - _Requirements: 8.1-8.7_
  
  - [ ] 12.5 Write property test for Quick Scalp entry conditions
    - **Property 11: Quick Scalp Entry Conditions**
    - **Validates: Requirements 8.1-8.7**
    - Generate random M1 data with varying condition combinations
    - Verify signals only when ALL conditions met

- [ ] 13. Quick Scalp Engine - Trade Management
  - [ ] 13.1 Implement instrument-specific stop loss configuration
    - Set US30 stop loss between 15-30 points
    - Set NAS100 stop loss between 10-25 points
    - Set XAUUSD stop loss between 0.80-2.00 dollars
    - _Requirements: 10.1-10.3_
  
  - [ ] 13.2 Write property test for instrument-specific stop loss ranges
    - **Property 14: Instrument-Specific Stop Loss Ranges**
    - **Validates: Requirements 10.1-10.3**
    - Generate random Quick Scalp trades for each instrument
    - Verify stop loss within correct range
  
  - [ ] 13.3 Implement single take profit configuration
    - Set take profit between 0.8R and 1R distance
    - Close 100% of position when TP reached
    - Never activate trailing stops on scalp positions
    - _Requirements: 11.1-11.3_
  
  - [ ] 13.4 Write property test for scalp single take profit
    - **Property 15: Scalp Single Take Profit**
    - **Validates: Requirements 11.1-11.3**
    - Generate random scalp trades
    - Verify single TP at 0.8-1R, 100% close, no trailing stops

- [ ] 14. Quick Scalp Engine - Risk Management and Cooldown
  - [ ] 14.1 Implement Quick Scalp position sizing
    - Calculate position size to risk between 0.25% and 0.5% of account balance
    - Use configurable risk percentage within range
    - _Requirements: 14.1_
  
  - [ ] 14.2 Write property test for scalp position sizing
    - **Property 18: Scalp Position Sizing**
    - **Validates: Requirements 14.1**
    - Generate random account balances
    - Verify position size risks 0.25-0.5% of balance
  
  - [ ] 14.3 Implement cooldown period enforcement
    - Record timestamp when scalp trade closes
    - Block new scalp signals when less than 2 minutes elapsed
    - Permit new signals when 2-3 minutes elapsed
    - _Requirements: 13.1-13.3_
  
  - [ ] 14.4 Write property test for scalp cooldown period
    - **Property 17: Scalp Cooldown Period**
    - **Validates: Requirements 13.1-13.3**
    - Generate trade sequences with varying time gaps
    - Verify blocking when < 2 minutes, permission when 2-3 minutes elapsed

- [ ] 15. Risk Tracker - Separate Risk Pools
  - [ ] 15.1 Implement Risk Tracker with separate pools
    - Create Core Strategy risk pool (daily trade count, drawdown, consecutive losses)
    - Create Quick Scalp risk pool (session trade counts, last trade timestamp)
    - Track state independently for each engine
    - _Requirements: 14.2, 15.3-15.4_
  
  - [ ] 15.2 Implement trade validation logic
    - Validate Core Strategy: check daily limit (2), drawdown (2%), consecutive losses (2)
    - Validate Quick Scalp: check session limits, cooldown, spread
    - Validate position size matches risk rules
    - Return approval/rejection with reason
    - _Requirements: 7.2-7.4, 9.5-9.7, 13.1-13.3_
  
  - [ ] 15.3 Implement trade outcome recording
    - Update trade counts for appropriate engine
    - Update drawdown calculations
    - Record win/loss and R multiple
    - Reset limits at start of trading day
    - _Requirements: 26.1-26.8_
  
  - [ ] 15.4 Write property test for engine independence
    - **Property 19: Engine Independence**
    - **Validates: Requirements 15.1-15.6**
    - Generate scenarios where one engine hits limits
    - Verify other engine continues operating independently

- [ ] 16. Risk Tracker - Performance Metrics
  - [ ] 16.1 Implement performance metrics calculation
    - Calculate win rate: winning trades / total trades
    - Calculate profit factor: gross profit / gross loss
    - Calculate average R:R: sum of R multiples / trade count
    - Maintain separate metrics for each engine
    - _Requirements: 26.1-26.8_
  
  - [ ] 16.2 Write property test for performance metrics calculation
    - **Property 29: Performance Metrics Calculation**
    - **Validates: Requirements 26.1-26.8**
    - Generate random trade histories for each engine
    - Verify correct calculation of win rate, profit factor, average R:R

- [ ] 17. Engine Coordination - Activation Logic
  - [ ] 17.1 Implement Quick Scalp Engine activation conditions
    - Check high volatility: ATR > instrument-specific threshold
    - Check active session present (London/NY/Power Hour)
    - Check spread within scalp limits
    - Activate scalp signal generation only when all conditions met
    - _Requirements: 16.1, 16.3_
  
  - [ ] 17.2 Implement Core Strategy Engine activation conditions
    - Check full SMC setup present (liquidity sweep, FVG, displacement, MSS)
    - Check confluence score >= 85 (A+ grade)
    - Activate signal generation only when conditions met
    - _Requirements: 16.2_
  
  - [ ] 17.3 Write property test for engine activation conditions
    - **Property 20: Engine Activation Conditions**
    - **Validates: Requirements 16.1-16.4**
    - Generate random market states
    - Verify Quick Scalp activates with volatility + session + spread
    - Verify Core Strategy activates with SMC setup + score >= 85

- [ ] 18. Integration - Market Data Flow and Error Handling
  - [ ] 18.1 Integrate market data ingestion layer
    - Ingest tick and bar data for US30, XAUUSD, NAS100
    - Construct all required timeframes (W, D, H4, H1, M5, M1)
    - Handle missing timeframe data (log and skip instrument)
    - Handle stale data (reject if > 5 minutes old)
    - Handle malformed OHLCV bars (log and exclude from calculations)
    - _Requirements: 1.1-1.8, 2.1-2.5_
  
  - [ ] 18.2 Implement global filter coordination
    - Connect Session Manager to both engines
    - Connect News Filter to both engines
    - Connect Spread Monitor to both engines
    - Ensure filters block both engines when triggered
    - _Requirements: 3.1-3.5, 17.1-17.7, 18.1-18.3_
  
  - [ ] 18.3 Implement execution error handling
    - Handle order rejection (log, alert, don't count against limits)
    - Handle partial fills (adjust position tracking, recalculate levels)
    - Handle connection loss (halt signals, maintain positions, reconnect with backoff)
    - Handle insufficient margin (reduce position size, log constraint)
    - Handle risk pool calculation errors (halt engine, log error, alert user)

- [ ] 19. Integration - End-to-End Signal Flow
  - [ ] 19.1 Wire Core Strategy Engine signal flow
    - Market data → Bias Engine → Confluence components → Core Strategy Engine
    - Core Strategy Engine → Risk Tracker validation → Trade execution
    - Position management → TP1/TP2/trailing stop → Risk Tracker outcome recording
    - _Requirements: 4.1-4.18, 5.1-5.6, 6.1-6.6, 7.1-7.4_
  
  - [ ] 19.2 Wire Quick Scalp Engine signal flow
    - M1 data → Liquidity sweep + Momentum + Volume + Structure → Quick Scalp Engine
    - Quick Scalp Engine → Session check → Spread check → Cooldown check → Risk Tracker validation
    - Trade execution → Single TP → Risk Tracker outcome recording
    - _Requirements: 8.1-8.7, 9.1-9.7, 10.1-10.3, 11.1-11.3, 12.1-12.3, 13.1-13.3_
  
  - [ ] 19.3 Implement configuration loading
    - Load configuration file at startup
    - Validate all required fields present
    - Validate numeric values within acceptable ranges
    - Refuse to start with invalid configuration
    - _Requirements: 27.1-27.7_

- [ ] 20. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 21. Testing - Unit Tests for Edge Cases
  - [ ] 21.1 Write unit tests for confluence score boundaries
    - Test score exactly at 75 points (A/B boundary)
    - Test score exactly at 85 points (A/A+ boundary)
    - Test score at 0 points (minimum)
    - Test score at 100 points (maximum)
  
  - [ ] 21.2 Write unit tests for session boundaries
    - Test time exactly at 10:00:00 (signal window start)
    - Test time exactly at 13:00:00 (London session end)
    - Test time exactly at 22:00:00 (signal window end)
    - Test time at 09:59:59 and 22:00:01 (outside window)
  
  - [ ] 21.3 Write unit tests for spread thresholds
    - Test spread exactly at scalp limits (US30: 3pts, NAS100: 2pts, XAUUSD: 2pts)
    - Test spread exactly at global limits (US30: 5pts, NAS100: 4pts, XAUUSD: 3pts)
    - Test spread at limit + 0.01 (should block)
  
  - [ ] 21.4 Write unit tests for cooldown boundary
    - Test cooldown exactly at 2 minutes (should permit)
    - Test cooldown at 1:59 (should block)
    - Test cooldown at 3 minutes (should permit)
  
  - [ ] 21.5 Write unit tests for empty and minimal data
    - Test empty market data arrays
    - Test single-bar timeframe data
    - Test zero volume bars
    - Test bars with high = low (no range)

- [ ] 22. Testing - Integration Tests
  - [ ] 22.1 Write integration test for Core Strategy full flow
    - Generate market data with known confluence breakdown (e.g., 87 points)
    - Verify signal generated with correct grade (A+)
    - Verify trade executed with correct TP1, TP2, stop loss
    - Simulate TP1 hit, verify 40% close and trailing stop activation
    - Simulate TP2 hit, verify additional 40% close
  
  - [ ] 22.2 Write integration test for Quick Scalp full flow
    - Generate M1 data with all entry conditions met during London session
    - Verify scalp signal generated
    - Verify trade executed with correct stop loss and single TP
    - Simulate TP hit, verify 100% close
    - Verify cooldown blocks next signal for 2 minutes
  
  - [ ] 22.3 Write integration test for dual engine coordination
    - Generate market conditions where both engines have valid setups
    - Verify both engines generate signals independently
    - Simulate Core Strategy hitting daily limit
    - Verify Quick Scalp continues operating
    - Simulate Quick Scalp hitting session limit
    - Verify Core Strategy continues operating
  
  - [ ] 22.4 Write integration test for global filter blocking
    - Generate valid setups for both engines
    - Trigger news event (30 min before)
    - Verify both engines blocked
    - Trigger spread limit breach
    - Verify both engines blocked
    - Trigger time outside signal window
    - Verify both engines blocked

- [x] 23. Auto-Trade Decision Engine - Intelligent Engine Selection
  - [x] 23.1 Implement Auto-Trade Decision Engine
    - Analyze market conditions to determine which engine should trade
    - Prevent both engines from trading simultaneously on same instrument
    - Prioritize Core Strategy A+ signals over scalp opportunities
    - Use volatility regime detection to favor appropriate engine
    - Implement conflict resolution when both engines have valid setups
    - Track engine performance to dynamically adjust preferences
  
  - [x] 23.2 Write property test for engine conflict resolution
    - **Property 34: Engine Conflict Resolution**
    - Generate scenarios where both engines have valid setups
    - Verify Core Strategy A+ signals take priority
    - Verify only one engine trades per instrument at a time
  
  - [x] 23.3 Write property test for volatility regime detection
    - **Property 35: Volatility Regime Detection**
    - Generate market data with varying volatility levels
    - Verify scalp engine favored in high volatility regimes
    - Verify core strategy favored in trending regimes
  
  - [x] 23.4 Implement Regime Detection Module
    - ATR-based volatility classification (LOW/NORMAL/HIGH/EXTREME)
    - EMA + swing structure trend detection (STRONG_TREND/WEAK_TREND/RANGING/CHOPPY)
    - Handles insufficient data with fallback logic
    - All 20 tests passing
  
  - [x] 23.5 Implement Performance Tracking Module
    - Tracks separately by engine + instrument
    - Rolling window (last 20 trades) + lifetime metrics
    - Metrics: win rate, avg R, profit factor, max drawdown, consecutive wins/losses
    - All 15 tests passing
  
  - [x] 23.6 Implement Unified Signal Contract
    - Created UnifiedSignal - normalized contract for both engines
    - Includes SignalConverter, SignalValidator, SignalRouter
    - Built-in validation and R:R calculations
    - All 16 tests passing
  
  - [x] 23.7 Implement Trading Coordinator (Full Integration)
    - Complete end-to-end flow: Market Data → Regime Detection → Strategy Engines → Decision Engine → Risk Validation → Signal Routing → Execution → Performance Tracking
    - All 9 integration tests passing
    - Example usage script created demonstrating complete flow
    - Files: backend/strategy/trading_coordinator.py, backend/tests/test_trading_coordinator_integration.py, backend/examples/trading_coordinator_example.py

- [ ] 24. Final Checkpoint - Production Readiness
  - Ensure all tests pass (unit, property, integration)
  - Verify all 35 properties implemented and passing
  - Verify error handling paths covered
  - Verify configuration validation working
  - Verify Auto-Trade Decision Engine prevents chaotic trading
  - Ask the user if questions arise before deployment

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties (33 total)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Checkpoints ensure incremental validation at reasonable breaks
- All property tests must run minimum 100 iterations with randomized inputs
- Property test comments must include: `# Feature: dual-engine-strategy-system, Property N: [Title]`
