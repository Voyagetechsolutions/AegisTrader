# Requirements Document

## Introduction

The Python Strategy Engine replaces TradingView webhook dependencies in Aegis Trader by implementing real-time market data analysis and signal generation natively in Python. This system transforms the current webhook-based signal processing into a continuous market monitoring engine that analyzes US30 price action across multiple timeframes, detects trading setups using existing confluence scoring logic, and generates signals internally without external dependencies.

## Glossary

- **Strategy_Engine**: The core Python system that orchestrates real-time market analysis and signal generation
- **Market_Data_Layer**: Component responsible for fetching and managing live US30 price data from MT5
- **Candle_Aggregator**: Service that builds higher timeframe candles (5M, 15M, 1H, 4H, Daily, Weekly) from 1-minute base data
- **Analysis_Engine**: Collection of specialized engines that perform technical analysis (Bias, Level, Liquidity, FVG, Displacement, Structure)
- **Confluence_Scorer**: Existing 100-point scoring system that evaluates setup quality
- **Signal_Generator**: Component that creates trading signals based on confluence analysis
- **Session_Manager**: Service that manages London/NY/Power Hour trading windows
- **Risk_Manager**: Existing risk management system with daily limits and drawdown controls
- **MT5_Bridge**: Existing Expert Advisor interface for trade execution
- **Redis_Cache**: In-memory data store for efficient multi-timeframe data management
- **Timeframe**: Market data intervals (1M, 5M, 15M, 1H, 4H, Daily, Weekly)
- **Confluence_Factor**: Technical analysis component (FVG, liquidity sweep, displacement, MSS, levels)
- **Setup_Type**: Classification of trading opportunity (continuation_long, continuation_short, swing_long, swing_short)

## Requirements

### Requirement 1: Real-Time Market Data Management

**User Story:** As a trader, I want the system to continuously fetch live US30 market data, so that I can analyze real-time price movements without depending on TradingView.

#### Acceptance Criteria

1. THE Market_Data_Layer SHALL fetch US30 1-minute OHLCV data from MT5 API every 60 seconds
2. WHEN new 1-minute data is received, THE Market_Data_Layer SHALL validate data integrity and timestamp accuracy
3. THE Market_Data_Layer SHALL store the last 2000 1-minute candles in Redis_Cache for analysis
4. IF data fetch fails, THEN THE Market_Data_Layer SHALL retry up to 3 times with exponential backoff
5. THE Market_Data_Layer SHALL log all data fetch operations with timestamps and success/failure status

### Requirement 2: Multi-Timeframe Candle Aggregation

**User Story:** As a trader, I want the system to build higher timeframe candles from 1-minute data, so that I can perform multi-timeframe analysis without external data sources.

#### Acceptance Criteria

1. WHEN new 1-minute data arrives, THE Candle_Aggregator SHALL update all higher timeframe candles (5M, 15M, 1H, 4H, Daily, Weekly)
2. THE Candle_Aggregator SHALL maintain the last 500 candles for each timeframe in Redis_Cache
3. THE Candle_Aggregator SHALL ensure candle boundaries align with market session times (00:00 UTC for daily candles)
4. WHEN a higher timeframe candle completes, THE Candle_Aggregator SHALL trigger analysis for that timeframe
5. THE Candle_Aggregator SHALL validate that aggregated OHLC values match mathematical aggregation rules

### Requirement 3: Market Bias Detection Engine

**User Story:** As a trader, I want the system to detect market bias across all timeframes using EMA analysis, so that I can identify trend direction for confluence scoring.

#### Acceptance Criteria

1. THE Analysis_Engine SHALL calculate 21-period EMA for each timeframe (1M, 5M, 15M, 1H, 4H, Daily, Weekly)
2. WHEN price closes above EMA, THE Analysis_Engine SHALL classify bias as "bullish" for that timeframe
3. WHEN price closes below EMA, THE Analysis_Engine SHALL classify bias as "bearish" for that timeframe
4. WHEN price is within 10 points of EMA, THE Analysis_Engine SHALL classify bias as "neutral"
5. THE Analysis_Engine SHALL detect market structure shifts (BOS/CHoCH) and update bias to "bull_shift" or "bear_shift"
6. THE Analysis_Engine SHALL store bias history for the last 100 periods per timeframe

### Requirement 4: Key Level Detection Engine

**User Story:** As a trader, I want the system to identify 250-point and 125-point key levels, so that I can score setups based on level proximity.

#### Acceptance Criteria

1. THE Analysis_Engine SHALL calculate 250-point levels by rounding current price to nearest 250-point increment
2. THE Analysis_Engine SHALL calculate 125-point levels by rounding current price to nearest 125-point increment  
3. THE Analysis_Engine SHALL update key levels every 5 minutes or when price moves more than 50 points
4. THE Analysis_Engine SHALL store the last 20 key levels for historical reference
5. THE Analysis_Engine SHALL provide distance calculation from current price to nearest levels

### Requirement 5: Liquidity Sweep Detection Engine

**User Story:** As a trader, I want the system to detect liquidity sweeps at key levels, so that I can identify high-probability reversal zones.

#### Acceptance Criteria

1. THE Analysis_Engine SHALL monitor for price wicks that extend beyond previous swing highs/lows by at least 10 points
2. WHEN a liquidity sweep occurs, THE Analysis_Engine SHALL mark the level and timestamp
3. THE Analysis_Engine SHALL track liquidity sweeps for the last 24 hours across all timeframes
4. THE Analysis_Engine SHALL classify sweeps as "buy-side" (above resistance) or "sell-side" (below support)
5. THE Analysis_Engine SHALL validate that sweeps are followed by reversal within 3 candles

### Requirement 6: Fair Value Gap Detection Engine

**User Story:** As a trader, I want the system to identify Fair Value Gaps (imbalances), so that I can score setups based on FVG retest opportunities.

#### Acceptance Criteria

1. THE Analysis_Engine SHALL detect FVGs when candle gaps exceed 20 points with no overlapping wicks
2. THE Analysis_Engine SHALL classify FVGs as "bullish" (gap up) or "bearish" (gap down)
3. THE Analysis_Engine SHALL track FVG fill status and mark as "unfilled", "partially filled", or "filled"
4. THE Analysis_Engine SHALL maintain FVG registry for the last 48 hours across 5M, 15M, and 1H timeframes
5. WHEN price retests an unfilled FVG, THE Analysis_Engine SHALL flag as "fvg_retest" opportunity

### Requirement 7: Displacement Candle Detection Engine

**User Story:** As a trader, I want the system to identify displacement candles (momentum moves), so that I can score setups based on strong directional moves.

#### Acceptance Criteria

1. THE Analysis_Engine SHALL detect displacement when a single candle moves more than 50 points in one direction
2. THE Analysis_Engine SHALL classify displacement as "bullish" (strong up move) or "bearish" (strong down move)
3. THE Analysis_Engine SHALL validate displacement candles have minimal wicks (body > 80% of total range)
4. THE Analysis_Engine SHALL track displacement events for the last 12 hours across 5M and 15M timeframes
5. THE Analysis_Engine SHALL flag recent displacement (within 10 candles) for confluence scoring

### Requirement 8: Market Structure Analysis Engine

**User Story:** As a trader, I want the system to detect market structure shifts (BOS/CHoCH), so that I can identify trend changes for confluence analysis.

#### Acceptance Criteria

1. THE Analysis_Engine SHALL identify Break of Structure (BOS) when price breaks previous swing high/low in trend direction
2. THE Analysis_Engine SHALL identify Change of Character (CHoCH) when price breaks counter-trend swing points
3. THE Analysis_Engine SHALL classify structure shifts as "bullish_bos", "bearish_bos", "bullish_choch", or "bearish_choch"
4. THE Analysis_Engine SHALL track structure shifts for the last 24 hours across 5M, 15M, and 1H timeframes
5. THE Analysis_Engine SHALL validate structure breaks with volume confirmation (if available)

### Requirement 9: Real-Time Signal Generation

**User Story:** As a trader, I want the system to generate trading signals based on confluence analysis, so that I can receive alerts without TradingView dependencies.

#### Acceptance Criteria

1. WHEN all confluence factors align, THE Signal_Generator SHALL create a trading signal with entry, stop loss, and take profit levels
2. THE Signal_Generator SHALL use the existing Confluence_Scorer to evaluate setup quality (0-100 points)
3. THE Signal_Generator SHALL classify signals as A+ (≥85), A (75-84), or B (<75) grades
4. THE Signal_Generator SHALL determine setup type (continuation_long, continuation_short, swing_long, swing_short)
5. THE Signal_Generator SHALL generate signals only during active trading sessions (London/NY/Power Hour)
6. THE Signal_Generator SHALL apply existing risk management rules before signal creation

### Requirement 10: Session-Based Signal Filtering

**User Story:** As a trader, I want signals generated only during active trading sessions, so that I avoid low-probability setups outside optimal trading hours.

#### Acceptance Criteria

1. THE Session_Manager SHALL monitor current time against London (10:00-13:00 SAST), NY (15:30-17:30 SAST), and Power Hour (20:00-22:00 SAST) windows
2. WHEN outside active sessions, THE Signal_Generator SHALL suppress signal creation
3. THE Session_Manager SHALL account for daylight saving time changes in London and New York
4. THE Session_Manager SHALL provide session status to the Analysis_Engine for confluence scoring
5. WHERE session override is enabled, THE Signal_Generator SHALL create signals with reduced confluence scores

### Requirement 11: Integration with Existing Systems

**User Story:** As a trader, I want the new strategy engine to work seamlessly with existing Aegis Trader components, so that I maintain all current functionality while eliminating TradingView dependency.

#### Acceptance Criteria

1. THE Strategy_Engine SHALL integrate with the existing FastAPI backend without breaking current API endpoints
2. THE Strategy_Engine SHALL use the existing Confluence_Scorer logic for signal evaluation
3. THE Strategy_Engine SHALL maintain compatibility with the existing MT5_Bridge for trade execution
4. THE Strategy_Engine SHALL preserve existing Telegram alert functionality and dashboard integration
5. THE Strategy_Engine SHALL support existing bot modes (Analyze, Trade, Swing) with identical behavior
6. THE Strategy_Engine SHALL maintain existing risk management limits and drawdown controls

### Requirement 12: Performance and Reliability

**User Story:** As a trader, I want the strategy engine to operate reliably with minimal latency, so that I don't miss trading opportunities due to system delays.

#### Acceptance Criteria

1. THE Strategy_Engine SHALL process new market data and generate signals within 5 seconds of data arrival
2. THE Strategy_Engine SHALL maintain 99.5% uptime during market hours (Sunday 22:00 - Friday 22:00 GMT)
3. THE Strategy_Engine SHALL handle MT5 connection failures gracefully with automatic reconnection
4. THE Strategy_Engine SHALL limit memory usage to under 512MB for efficient VPS operation
5. IF critical errors occur, THEN THE Strategy_Engine SHALL send immediate alerts via Telegram and continue operation in degraded mode

### Requirement 13: Data Persistence and Recovery

**User Story:** As a trader, I want the system to persist critical data and recover gracefully from restarts, so that I don't lose important market analysis during system maintenance.

#### Acceptance Criteria

1. THE Strategy_Engine SHALL persist the last 24 hours of market data to PostgreSQL database every hour
2. WHEN the system restarts, THE Strategy_Engine SHALL reload the last 2 hours of market data from database
3. THE Strategy_Engine SHALL maintain Redis_Cache backup snapshots every 30 minutes
4. THE Strategy_Engine SHALL recover incomplete candle aggregations after restart
5. THE Strategy_Engine SHALL preserve signal generation state and resume analysis within 60 seconds of restart

### Requirement 14: Configuration and Monitoring

**User Story:** As a trader, I want to configure strategy parameters and monitor system health, so that I can optimize performance and troubleshoot issues.

#### Acceptance Criteria

1. THE Strategy_Engine SHALL support configuration of analysis parameters (EMA periods, level increments, gap thresholds) via environment variables
2. THE Strategy_Engine SHALL provide health check endpoints for monitoring data freshness and analysis status
3. THE Strategy_Engine SHALL log all signal generation events with detailed confluence breakdowns
4. THE Strategy_Engine SHALL expose metrics for data fetch latency, analysis processing time, and signal generation rate
5. THE Strategy_Engine SHALL support runtime parameter updates without requiring system restart