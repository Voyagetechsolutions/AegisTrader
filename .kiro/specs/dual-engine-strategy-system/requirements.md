# Requirements Document

## Introduction

This document specifies requirements for rebuilding Aegis Trader with a dual-engine strategy system. The system will operate two distinct trading engines simultaneously: a Core Strategy Engine using institutional liquidity models on higher timeframes, and a Quick Scalp Engine for rapid momentum-based trades on M1 timeframes. Both engines will share common risk management infrastructure while maintaining separate risk pools and operating parameters.

## Glossary

- **Core_Strategy_Engine**: The primary trading engine that analyzes Weekly, Daily, H4, H1, and M5 timeframes using institutional liquidity models
- **Quick_Scalp_Engine**: The secondary trading engine that analyzes M1 and M5 timeframes for rapid momentum-based scalping opportunities
- **Signal_Window**: The time period from 10:00 to 22:00 SAST during which trading signals may be generated
- **HTF**: Higher timeframe (Weekly, Daily, H4, H1)
- **FVG**: Fair Value Gap - an imbalance in price action indicating institutional order flow
- **MSS**: Market Structure Shift - a break in the sequence of higher highs/lows or lower highs/lows
- **Liquidity_Sweep**: Price movement that triggers stop losses before reversing direction
- **Displacement**: Strong directional price movement indicating institutional participation
- **Confluence_Score**: A numerical rating from 0-100 points evaluating the quality of a trading setup
- **Signal_Grade**: A letter grade (A+, A, B) assigned based on confluence score thresholds
- **Momentum_Candle**: A M1 candle with body greater than 60% of its range and range exceeding the average of the last 10 candles
- **Active_Session**: Specific trading session periods (London: 10:00-13:00, NY Open: 15:30-18:00, Power Hour: 20:00-22:00 SAST)
- **Risk_Pool**: Separate risk allocation tracking for Core Strategy Engine versus Quick Scalp Engine
- **Cooldown_Period**: Minimum time interval of 2-3 minutes required between consecutive scalp trades
- **News_Event**: High-impact economic announcements (CPI, NFP, FOMC, Fed speeches) requiring trade blocking
- **Spread_Filter**: Maximum allowed bid-ask spread threshold for trade execution
- **Slippage**: The difference between expected execution price and actual fill price
- **VWAP**: Volume Weighted Average Price - a trading benchmark representing average price weighted by volume
- **ATR**: Average True Range - a volatility indicator measuring average price movement
- **Session_Manager**: Component responsible for enforcing signal window and active session rules
- **Bias_Engine**: Component that determines directional bias using HTF alignment analysis
- **Risk_Tracker**: Component that monitors and enforces risk limits separately for each engine

## Requirements

### Requirement 1: Core Strategy Engine Market Coverage

**User Story:** As a trader, I want the Core Strategy Engine to analyze US30, XAUUSD, and NAS100 markets, so that I can capture institutional liquidity opportunities across major instruments.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL analyze US30 market data
2. THE Core_Strategy_Engine SHALL analyze XAUUSD market data
3. THE Core_Strategy_Engine SHALL analyze NAS100 market data
4. THE Core_Strategy_Engine SHALL analyze Weekly timeframe data for each market
5. THE Core_Strategy_Engine SHALL analyze Daily timeframe data for each market
6. THE Core_Strategy_Engine SHALL analyze H4 timeframe data for each market
7. THE Core_Strategy_Engine SHALL analyze H1 timeframe data for each market
8. THE Core_Strategy_Engine SHALL analyze M5 timeframe data for each market

### Requirement 2: Quick Scalp Engine Market Coverage

**User Story:** As a trader, I want the Quick Scalp Engine to analyze the same markets as the Core Strategy Engine, so that I can capture rapid momentum opportunities across all instruments.

#### Acceptance Criteria

1. THE Quick_Scalp_Engine SHALL analyze US30 market data
2. THE Quick_Scalp_Engine SHALL analyze XAUUSD market data
3. THE Quick_Scalp_Engine SHALL analyze NAS100 market data
4. THE Quick_Scalp_Engine SHALL use M1 timeframe as primary analysis timeframe
5. THE Quick_Scalp_Engine SHALL use M5 timeframe as context timeframe

### Requirement 3: Signal Window Enforcement

**User Story:** As a trader, I want both engines to generate signals only during 10:00-22:00 SAST, so that I avoid trading during low-liquidity periods while maintaining 24/7 market analysis.

#### Acceptance Criteria

1. THE Session_Manager SHALL analyze market data continuously across all hours
2. WHEN the current time is between 10:00 and 22:00 SAST, THE Session_Manager SHALL permit signal generation
3. WHEN the current time is outside 10:00-22:00 SAST, THE Session_Manager SHALL block signal generation
4. THE Session_Manager SHALL apply signal window enforcement to Core_Strategy_Engine
5. THE Session_Manager SHALL apply signal window enforcement to Quick_Scalp_Engine

### Requirement 4: Core Strategy Confluence Scoring System

**User Story:** As a trader, I want the Core Strategy Engine to score setups using a 100-point confluence system, so that I can objectively evaluate trade quality.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL calculate HTF alignment score with maximum 20 points
2. WHEN Weekly timeframe aligns with trade direction, THE Core_Strategy_Engine SHALL award 6 points
3. WHEN Daily timeframe aligns with trade direction, THE Core_Strategy_Engine SHALL award 6 points
4. WHEN H4 timeframe aligns with trade direction, THE Core_Strategy_Engine SHALL award 4 points
5. WHEN H1 timeframe aligns with trade direction, THE Core_Strategy_Engine SHALL award 4 points
6. THE Core_Strategy_Engine SHALL require H1 alignment for any valid signal
7. THE Core_Strategy_Engine SHALL calculate key level proximity score with maximum 15 points
8. THE Core_Strategy_Engine SHALL calculate liquidity sweep score with maximum 15 points
9. THE Core_Strategy_Engine SHALL calculate FVG score with maximum 15 points
10. THE Core_Strategy_Engine SHALL calculate displacement score with maximum 10 points
11. THE Core_Strategy_Engine SHALL calculate MSS score with maximum 10 points
12. THE Core_Strategy_Engine SHALL calculate VWAP alignment score with maximum 5 points
13. THE Core_Strategy_Engine SHALL calculate volume spike score with maximum 5 points
14. THE Core_Strategy_Engine SHALL calculate ATR volatility score with maximum 5 points
15. THE Core_Strategy_Engine SHALL calculate HTF liquidity target score with maximum 5 points
16. THE Core_Strategy_Engine SHALL calculate session score with maximum 5 points
17. THE Core_Strategy_Engine SHALL calculate spread score with maximum 5 points
18. THE Core_Strategy_Engine SHALL sum all component scores to produce total Confluence_Score

### Requirement 5: Core Strategy Signal Grading

**User Story:** As a trader, I want signals graded as A+, A, or B based on confluence scores, so that I can distinguish between auto-trade setups and alerts.

#### Acceptance Criteria

1. WHEN Confluence_Score is between 85 and 100 points, THE Core_Strategy_Engine SHALL assign Signal_Grade A+
2. WHEN Confluence_Score is between 75 and 84 points, THE Core_Strategy_Engine SHALL assign Signal_Grade A
3. WHEN Confluence_Score is below 75 points, THE Core_Strategy_Engine SHALL assign Signal_Grade B
4. WHEN Signal_Grade is A+, THE Core_Strategy_Engine SHALL enable automatic trade execution
5. WHEN Signal_Grade is A, THE Core_Strategy_Engine SHALL generate alert without automatic execution
6. WHEN Signal_Grade is B, THE Core_Strategy_Engine SHALL suppress signal output

### Requirement 6: Core Strategy Trade Management

**User Story:** As a trader, I want the Core Strategy Engine to manage trades with multiple take-profit levels and a trailing runner, so that I can capture extended moves while securing profits.

#### Acceptance Criteria

1. WHEN a Core Strategy trade is opened, THE Core_Strategy_Engine SHALL set TP1 at 1R distance
2. WHEN TP1 is reached, THE Core_Strategy_Engine SHALL close 40% of position size
3. WHEN a Core Strategy trade is opened, THE Core_Strategy_Engine SHALL set TP2 at 2R distance
4. WHEN TP2 is reached, THE Core_Strategy_Engine SHALL close 40% of position size
5. WHEN TP1 is reached, THE Core_Strategy_Engine SHALL activate trailing stop on remaining 20% position
6. THE Core_Strategy_Engine SHALL maintain trailing stop on runner position until stopped out

### Requirement 7: Core Strategy Risk Management

**User Story:** As a trader, I want the Core Strategy Engine to enforce strict risk limits, so that I protect my account from excessive drawdown.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL risk 1% of account balance per trade
2. THE Core_Strategy_Engine SHALL limit Core Strategy trades to maximum 2 per day
3. WHEN 2 losing Core Strategy trades occur in a day, THE Core_Strategy_Engine SHALL block additional Core Strategy trades for that day
4. WHEN Core Strategy daily drawdown reaches 2%, THE Core_Strategy_Engine SHALL block additional Core Strategy trades for that day

### Requirement 8: Quick Scalp Engine Entry Conditions

**User Story:** As a trader, I want the Quick Scalp Engine to identify high-probability momentum setups, so that I can capture rapid price movements.

#### Acceptance Criteria

1. THE Quick_Scalp_Engine SHALL identify Liquidity_Sweep on M1 timeframe
2. THE Quick_Scalp_Engine SHALL identify Momentum_Candle following Liquidity_Sweep
3. WHEN a M1 candle body is greater than 60% of candle range, THE Quick_Scalp_Engine SHALL classify it as potential Momentum_Candle
4. WHEN a M1 candle range exceeds average range of last 10 candles, THE Quick_Scalp_Engine SHALL classify it as potential Momentum_Candle
5. WHEN a M1 candle volume exceeds average volume of last 20 candles, THE Quick_Scalp_Engine SHALL classify it as volume spike
6. WHEN Momentum_Candle breaks previous M1 swing high or low, THE Quick_Scalp_Engine SHALL classify it as micro structure break
7. WHEN Liquidity_Sweep AND Momentum_Candle AND volume spike AND micro structure break all occur, THE Quick_Scalp_Engine SHALL generate scalp signal

### Requirement 9: Quick Scalp Engine Session Management

**User Story:** As a trader, I want the Quick Scalp Engine to operate only during high-liquidity sessions, so that I avoid scalping during unfavorable market conditions.

#### Acceptance Criteria

1. WHEN current time is between 10:00 and 13:00 SAST, THE Quick_Scalp_Engine SHALL classify session as London Active_Session
2. WHEN current time is between 15:30 and 18:00 SAST, THE Quick_Scalp_Engine SHALL classify session as NY Open Active_Session
3. WHEN current time is between 20:00 and 22:00 SAST, THE Quick_Scalp_Engine SHALL classify session as Power Hour Active_Session
4. WHEN no Active_Session is present, THE Quick_Scalp_Engine SHALL block scalp signal generation
5. THE Quick_Scalp_Engine SHALL limit London Active_Session to maximum 5 scalp trades
6. THE Quick_Scalp_Engine SHALL limit NY Open Active_Session to maximum 5 scalp trades
7. THE Quick_Scalp_Engine SHALL limit Power Hour Active_Session to maximum 3 scalp trades

### Requirement 10: Quick Scalp Engine Stop Loss Configuration

**User Story:** As a trader, I want tight stop losses on scalp trades appropriate for each instrument, so that I minimize risk on rapid trades.

#### Acceptance Criteria

1. WHEN Quick_Scalp_Engine opens US30 trade, THE Quick_Scalp_Engine SHALL set stop loss between 15 and 30 points
2. WHEN Quick_Scalp_Engine opens NAS100 trade, THE Quick_Scalp_Engine SHALL set stop loss between 10 and 25 points
3. WHEN Quick_Scalp_Engine opens XAUUSD trade, THE Quick_Scalp_Engine SHALL set stop loss between 0.80 and 2.00 dollars

### Requirement 11: Quick Scalp Engine Take Profit Configuration

**User Story:** As a trader, I want scalp trades to exit completely at 0.8R-1R, so that I capture quick profits without holding for extended moves.

#### Acceptance Criteria

1. WHEN Quick_Scalp_Engine opens a trade, THE Quick_Scalp_Engine SHALL set take profit between 0.8R and 1R distance
2. WHEN scalp take profit is reached, THE Quick_Scalp_Engine SHALL close 100% of position size
3. THE Quick_Scalp_Engine SHALL NOT use trailing stops on scalp positions

### Requirement 12: Quick Scalp Engine Spread Filtering

**User Story:** As a trader, I want the Quick Scalp Engine to trade only when spreads are tight, so that transaction costs do not erode scalping profits.

#### Acceptance Criteria

1. WHEN US30 spread exceeds 3 points, THE Quick_Scalp_Engine SHALL block US30 scalp signals
2. WHEN NAS100 spread exceeds 2 points, THE Quick_Scalp_Engine SHALL block NAS100 scalp signals
3. WHEN XAUUSD spread exceeds 2 points, THE Quick_Scalp_Engine SHALL block XAUUSD scalp signals

### Requirement 13: Quick Scalp Engine Cooldown Period

**User Story:** As a trader, I want a cooldown period between scalp trades, so that I avoid overtrading and allow market conditions to reset.

#### Acceptance Criteria

1. WHEN a scalp trade is closed, THE Quick_Scalp_Engine SHALL record trade completion timestamp
2. WHEN time since last scalp trade completion is less than 2 minutes, THE Quick_Scalp_Engine SHALL block new scalp signals
3. THE Quick_Scalp_Engine SHALL permit new scalp signals when 2 to 3 minutes have elapsed since last trade completion

### Requirement 14: Quick Scalp Engine Risk Management

**User Story:** As a trader, I want the Quick Scalp Engine to use smaller position sizes than the Core Strategy Engine, so that rapid trades carry proportionally lower risk.

#### Acceptance Criteria

1. THE Quick_Scalp_Engine SHALL risk between 0.25% and 0.5% of account balance per scalp trade
2. THE Risk_Tracker SHALL track Quick Scalp Engine risk separately from Core Strategy Engine risk

### Requirement 15: Dual Engine Coordination

**User Story:** As a trader, I want both engines to operate simultaneously without interference, so that I can capture opportunities across different timeframes and styles.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL operate independently of Quick_Scalp_Engine state
2. THE Quick_Scalp_Engine SHALL operate independently of Core_Strategy_Engine state
3. THE Risk_Tracker SHALL maintain separate Risk_Pool for Core_Strategy_Engine
4. THE Risk_Tracker SHALL maintain separate Risk_Pool for Quick_Scalp_Engine
5. WHEN Core_Strategy_Engine reaches daily trade limit, THE Quick_Scalp_Engine SHALL continue operating
6. WHEN Quick_Scalp_Engine reaches session trade limit, THE Core_Strategy_Engine SHALL continue operating

### Requirement 16: Engine Activation Logic

**User Story:** As a trader, I want each engine to activate based on its specific market conditions, so that trades are taken only when appropriate setups exist.

#### Acceptance Criteria

1. WHEN high volatility is present AND Active_Session is present AND spread passes Spread_Filter, THE Quick_Scalp_Engine SHALL activate scalp signal generation
2. WHEN full SMC setup is present AND Confluence_Score is 85 or greater, THE Core_Strategy_Engine SHALL activate signal generation
3. THE Quick_Scalp_Engine SHALL measure volatility using ATR indicator
4. WHEN ATR exceeds instrument-specific threshold, THE Quick_Scalp_Engine SHALL classify market as high volatility

### Requirement 17: News Event Filtering

**User Story:** As a trader, I want both engines to avoid trading around high-impact news events, so that I avoid unpredictable volatility spikes.

#### Acceptance Criteria

1. THE Session_Manager SHALL maintain calendar of News_Event occurrences
2. WHEN current time is within 30 minutes before a News_Event, THE Session_Manager SHALL block signal generation for both engines
3. WHEN current time is within 60 minutes after a News_Event, THE Session_Manager SHALL block signal generation for both engines
4. THE Session_Manager SHALL classify CPI announcements as News_Event
5. THE Session_Manager SHALL classify NFP announcements as News_Event
6. THE Session_Manager SHALL classify FOMC announcements as News_Event
7. THE Session_Manager SHALL classify Fed speeches as News_Event

### Requirement 18: Global Spread Filtering

**User Story:** As a trader, I want maximum spread thresholds enforced across both engines, so that I avoid trading during poor liquidity conditions.

#### Acceptance Criteria

1. WHEN US30 spread exceeds 5 points, THE Session_Manager SHALL block US30 signals for both engines
2. WHEN NAS100 spread exceeds 4 points, THE Session_Manager SHALL block NAS100 signals for both engines
3. WHEN XAUUSD spread exceeds 3 points, THE Session_Manager SHALL block XAUUSD signals for both engines

### Requirement 19: Slippage Protection

**User Story:** As a trader, I want trades rejected if slippage exceeds acceptable limits, so that I avoid poor execution quality.

#### Acceptance Criteria

1. WHEN a trade execution is requested, THE Core_Strategy_Engine SHALL measure Slippage between expected price and fill price
2. WHEN a trade execution is requested, THE Quick_Scalp_Engine SHALL measure Slippage between expected price and fill price
3. WHEN Slippage exceeds 10 points, THE Core_Strategy_Engine SHALL reject trade execution
4. WHEN Slippage exceeds 10 points, THE Quick_Scalp_Engine SHALL reject trade execution
5. WHEN trade is rejected due to Slippage, THE system SHALL log rejection reason with timestamp and slippage amount

### Requirement 20: Bias Engine Reconstruction

**User Story:** As a trader, I want the Bias Engine to use the new 20-point HTF alignment scoring system, so that directional bias reflects the updated confluence model.

#### Acceptance Criteria

1. THE Bias_Engine SHALL analyze Weekly timeframe for directional alignment
2. THE Bias_Engine SHALL analyze Daily timeframe for directional alignment
3. THE Bias_Engine SHALL analyze H4 timeframe for directional alignment
4. THE Bias_Engine SHALL analyze H1 timeframe for directional alignment
5. THE Bias_Engine SHALL calculate HTF alignment score using 6 points for Weekly, 6 points for Daily, 4 points for H4, and 4 points for H1
6. THE Bias_Engine SHALL provide HTF alignment score to Core_Strategy_Engine for inclusion in Confluence_Score

### Requirement 21: VWAP Alignment Detection

**User Story:** As a trader, I want the system to detect when price aligns with VWAP, so that I can incorporate this confluence factor into trade scoring.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL calculate VWAP for current trading day
2. WHEN price is within 0.1% of VWAP value, THE Core_Strategy_Engine SHALL classify price as aligned with VWAP
3. WHEN price aligns with VWAP in direction of trade signal, THE Core_Strategy_Engine SHALL award 5 points to Confluence_Score

### Requirement 22: Volume Spike Detection

**User Story:** As a trader, I want the system to detect volume spikes, so that I can identify institutional participation in price moves.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL calculate average volume over last 20 candles
2. WHEN current candle volume exceeds 1.5 times average volume, THE Core_Strategy_Engine SHALL classify current candle as volume spike
3. WHEN volume spike occurs in direction of trade signal, THE Core_Strategy_Engine SHALL award 5 points to Confluence_Score

### Requirement 23: ATR Volatility Filtering

**User Story:** As a trader, I want the system to evaluate volatility using ATR, so that I can avoid trading during abnormally low or high volatility periods.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL calculate ATR with 14-period lookback
2. WHEN ATR is within normal range for instrument, THE Core_Strategy_Engine SHALL award 5 points to Confluence_Score
3. THE Core_Strategy_Engine SHALL define normal ATR range as between 0.8 and 1.5 times the 50-period ATR average

### Requirement 24: HTF Liquidity Target Identification

**User Story:** As a trader, I want the system to identify liquidity targets on higher timeframes, so that I can assess whether sufficient profit potential exists.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL identify liquidity pools on Weekly timeframe
2. THE Core_Strategy_Engine SHALL identify liquidity pools on Daily timeframe
3. THE Core_Strategy_Engine SHALL identify liquidity pools on H4 timeframe
4. WHEN a liquidity pool exists in trade direction within 3R distance, THE Core_Strategy_Engine SHALL award 5 points to Confluence_Score
5. THE Core_Strategy_Engine SHALL define liquidity pools as clusters of swing highs or swing lows

### Requirement 25: Key Level Proximity Scoring

**User Story:** As a trader, I want the system to score proximity to 250-point and 125-point key levels, so that I can incorporate psychological price levels into trade decisions.

#### Acceptance Criteria

1. THE Core_Strategy_Engine SHALL identify 250-point key levels for US30 and NAS100
2. THE Core_Strategy_Engine SHALL identify 125-point key levels for US30 and NAS100
3. THE Core_Strategy_Engine SHALL identify equivalent key levels for XAUUSD based on round numbers
4. WHEN price is within 20 points of a 250-point level, THE Core_Strategy_Engine SHALL award 15 points to Confluence_Score
5. WHEN price is within 10 points of a 125-point level, THE Core_Strategy_Engine SHALL award 10 points to Confluence_Score
6. WHEN price is within 30 points of a 250-point level but not within 20 points, THE Core_Strategy_Engine SHALL award 8 points to Confluence_Score

### Requirement 26: Performance Monitoring

**User Story:** As a trader, I want the system to track performance metrics separately for each engine, so that I can evaluate the effectiveness of each strategy.

#### Acceptance Criteria

1. THE Risk_Tracker SHALL calculate win rate for Core_Strategy_Engine trades
2. THE Risk_Tracker SHALL calculate win rate for Quick_Scalp_Engine trades
3. THE Risk_Tracker SHALL calculate average risk-reward ratio for Core_Strategy_Engine trades
4. THE Risk_Tracker SHALL calculate average risk-reward ratio for Quick_Scalp_Engine trades
5. THE Risk_Tracker SHALL calculate profit factor for Core_Strategy_Engine trades
6. THE Risk_Tracker SHALL calculate profit factor for Quick_Scalp_Engine trades
7. THE Risk_Tracker SHALL count daily trades for Core_Strategy_Engine
8. THE Risk_Tracker SHALL count daily trades for Quick_Scalp_Engine

### Requirement 27: Configuration Parser and Serializer

**User Story:** As a developer, I want to parse and serialize engine configuration files, so that I can load and save system settings reliably.

#### Acceptance Criteria

1. WHEN a valid configuration file is provided, THE Configuration_Parser SHALL parse it into a Configuration object
2. WHEN an invalid configuration file is provided, THE Configuration_Parser SHALL return a descriptive error message
3. THE Configuration_Serializer SHALL format Configuration objects into valid configuration files
4. FOR ALL valid Configuration objects, THE system SHALL satisfy the round-trip property: parsing then serializing then parsing SHALL produce an equivalent Configuration object
5. THE Configuration_Parser SHALL validate that all required fields are present
6. THE Configuration_Parser SHALL validate that numeric values are within acceptable ranges
7. THE Configuration_Serializer SHALL format configuration files with human-readable indentation

### Requirement 28: Trade Signal Parser and Serializer

**User Story:** As a developer, I want to parse and serialize trade signals, so that I can reliably communicate signals between system components.

#### Acceptance Criteria

1. WHEN a valid trade signal is provided, THE Signal_Parser SHALL parse it into a Signal object
2. WHEN an invalid trade signal is provided, THE Signal_Parser SHALL return a descriptive error message
3. THE Signal_Serializer SHALL format Signal objects into valid signal messages
4. FOR ALL valid Signal objects, THE system SHALL satisfy the round-trip property: parsing then serializing then parsing SHALL produce an equivalent Signal object
5. THE Signal_Parser SHALL validate that signal contains required fields: instrument, direction, entry price, stop loss, take profit levels
6. THE Signal_Serializer SHALL format signals with ISO 8601 timestamps
