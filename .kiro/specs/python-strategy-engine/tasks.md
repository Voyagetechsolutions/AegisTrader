# Implementation Plan: Python Strategy Engine

## Overview

This implementation plan transforms the Python Strategy Engine from design to working code through a series of incremental development tasks. The approach prioritizes core data structures and Redis integration first, builds the market data pipeline, implements the six specialized analysis engines, and finally integrates with the existing FastAPI backend.

The implementation maintains the 500-line core target through focused, single-responsibility components while ensuring sub-5-second signal generation performance and seamless integration with existing Aegis Trader systems.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create directory structure for strategy engine components
  - Define core data classes (Candle, AnalysisResult, Signal) with proper typing
  - Set up Redis connection and configuration management
  - Configure logging and error handling infrastructure
  - _Requirements: 1.1, 13.1, 14.1_

- [x] 2. Implement Market Data Layer and Redis integration
  - [x] 2.1 Create MarketDataLayer class with MT5 integration
    - Implement fetch_latest_candle() with MT5 API connection
    - Add data validation for OHLCV integrity and timestamp accuracy
    - Implement retry logic with exponential backoff for connection failures
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [x] 2.2 Write property test for market data integrity
    - **Property 1: Market Data Integrity**
    - **Validates: Requirements 1.2**
  
  - [x] 2.3 Implement Redis storage with rolling window management
    - Create store_candle() method with 2000-candle limit enforcement
    - Implement get_historical_candles() with efficient retrieval
    - Add automatic cleanup for memory management
    - _Requirements: 1.3, 1.5_
  
  - [x] 2.4 Write property test for rolling window storage
    - **Property 2: Rolling Window Storage Limits**
    - **Validates: Requirements 1.3**

- [x] 3. Build Candle Aggregator for multi-timeframe analysis
  - [x] 3.1 Create CandleAggregator class with timeframe management
    - Implement process_new_candle() for real-time aggregation
    - Add get_timeframe_candles() for analysis engine access
    - Create session-aware daily candle boundary alignment
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [x] 3.2 Write property test for candle aggregation correctness
    - **Property 4: Candle Aggregation Mathematical Correctness**
    - **Validates: Requirements 2.5**
  
  - [x] 3.3 Write property test for session boundary alignment
    - **Property 5: Session Boundary Alignment**
    - **Validates: Requirements 2.3**
  
  - [x] 3.4 Implement analysis trigger system
    - Add event-driven analysis triggering on candle completion
    - Create timeframe-specific analysis scheduling
    - _Requirements: 2.4_

- [ ] 4. Checkpoint - Core data pipeline validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Bias Detection Engine
  - [x] 5.1 Create BiasEngine with EMA calculation
    - Implement 21-period EMA calculation for all timeframes
    - Add bias classification logic (bullish/bearish/neutral)
    - Create market structure shift detection (BOS/CHoCH)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 5.2 Write property test for EMA calculation accuracy
    - **Property 6: EMA Calculation Accuracy**
    - **Validates: Requirements 3.1**
  
  - [x] 5.3 Write property test for bias classification logic
    - **Property 7: Bias Classification Logic**
    - **Validates: Requirements 3.2, 3.3, 3.4**
  
  - [x] 5.4 Implement bias history storage
    - Store last 100 periods of bias data per timeframe
    - Add efficient retrieval for confluence analysis
    - _Requirements: 3.6_

- [x] 6. Implement Level Detection Engine
  - [x] 6.1 Create LevelEngine with key level calculation
    - Implement 250-point and 125-point level rounding
    - Add automatic level updates based on price movement
    - Create distance calculation utilities
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  
  - [x] 6.2 Write property test for key level rounding accuracy
    - **Property 8: Key Level Rounding Accuracy**
    - **Validates: Requirements 4.1, 4.2**
  
  - [x] 6.3 Write property test for distance calculation correctness
    - **Property 9: Distance Calculation Correctness**
    - **Validates: Requirements 4.5**
  
  - [x] 6.4 Implement level history management
    - Store last 20 key levels for historical reference
    - Add level change detection and logging
    - _Requirements: 4.4_

- [x] 7. Implement Liquidity Sweep Detection Engine
  - [x] 7.1 Create LiquidityEngine with sweep detection
    - Implement wick extension detection (10+ point threshold)
    - Add buy-side/sell-side classification logic
    - Create reversal validation within 3 candles
    - _Requirements: 5.1, 5.2, 5.4, 5.5_
  
  - [x] 7.2 Write property test for liquidity sweep detection
    - **Property 10: Liquidity Sweep Detection**
    - **Validates: Requirements 5.1, 5.4**
  
  - [x] 7.3 Implement sweep history tracking
    - Store 24-hour sweep history across all timeframes
    - Add sweep timestamp and level marking
    - _Requirements: 5.3_

- [x] 8. Implement Fair Value Gap Detection Engine
  - [x] 8.1 Create FVGEngine with gap detection
    - Implement 20+ point gap detection with no overlapping wicks
    - Add bullish/bearish FVG classification
    - Create FVG fill status tracking (unfilled/partially filled/filled)
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [x] 8.2 Write property test for FVG detection and classification
    - **Property 11: FVG Detection and Classification**
    - **Validates: Requirements 6.1, 6.2**
  
  - [x] 8.3 Write property test for FVG fill status tracking
    - **Property 12: FVG Fill Status Tracking**
    - **Validates: Requirements 6.3**
  
  - [x] 8.4 Implement FVG registry and retest detection
    - Maintain 48-hour FVG registry for 5M, 15M, 1H timeframes
    - Add retest opportunity flagging
    - _Requirements: 6.4, 6.5_

- [x] 9. Implement Displacement Candle Detection Engine
  - [x] 9.1 Create DisplacementEngine with momentum detection
    - Implement 50+ point single candle movement detection
    - Add body percentage validation (80%+ of total range)
    - Create bullish/bearish displacement classification
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 9.2 Write property test for displacement candle validation
    - **Property 13: Displacement Candle Validation**
    - **Validates: Requirements 7.1, 7.3**
  
  - [x] 9.3 Implement displacement history tracking
    - Store 12-hour displacement events for 5M and 15M timeframes
    - Add recent displacement flagging for confluence scoring
    - _Requirements: 7.4, 7.5_

- [x] 10. Implement Market Structure Analysis Engine
  - [x] 10.1 Create StructureEngine with break detection
    - Implement Break of Structure (BOS) detection for trend continuation
    - Add Change of Character (CHoCH) detection for trend reversal
    - Create directional classification (bullish_bos, bearish_bos, etc.)
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 10.2 Write property test for structure break classification
    - **Property 14: Structure Break Classification**
    - **Validates: Requirements 8.1, 8.2, 8.3**
  
  - [x] 10.3 Implement structure history and volume validation
    - Store 24-hour structure breaks for 5M, 15M, 1H timeframes
    - Add volume confirmation when available
    - _Requirements: 8.4, 8.5_

- [ ] 11. Checkpoint - All analysis engines operational
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Signal Generator and Confluence Scoring
  - [x] 12.1 Create SignalGenerator with confluence evaluation
    - Implement evaluate_setup() using existing 100-point scoring system
    - Add setup type determination (continuation_long, continuation_short, swing_long, swing_short)
    - Create trade level calculation (entry, stop loss, take profit)
    - _Requirements: 9.1, 9.2, 9.4_
  
  - [x] 12.2 Write property test for signal grade classification
    - **Property 15: Signal Grade Classification**
    - **Validates: Requirements 9.3**
  
  - [x] 12.3 Implement session-based signal filtering
    - Add London/NY/Power Hour session validation
    - Create daylight saving time handling
    - Implement session override functionality
    - _Requirements: 9.5, 10.1, 10.2, 10.3, 10.5_
  
  - [x] 12.4 Write property test for session-based filtering
    - **Property 16: Session-Based Signal Filtering**
    - **Validates: Requirements 9.5, 10.2**

- [ ] 13. Implement Session Manager and Risk Integration
  - [x] 13.1 Create SessionManager with trading window management
    - Implement active session detection with timezone handling
    - Add session status reporting for confluence scoring
    - Create session override controls
    - _Requirements: 10.1, 10.4_
  
  - [x] 13.2 Integrate existing risk management systems
    - Connect with existing Risk_Manager for daily limits
    - Maintain compatibility with drawdown controls
    - Preserve existing risk validation logic
    - _Requirements: 9.6, 11.6_

- [ ] 14. Integrate with existing FastAPI backend
  - [x] 14.1 Create FastAPI integration endpoints
    - Add strategy engine status and health check endpoints
    - Implement signal webhook endpoints for existing systems
    - Create configuration update endpoints
    - _Requirements: 11.1, 14.2, 14.5_
  
  - [x] 14.2 Maintain existing system compatibility
    - Preserve existing Confluence_Scorer integration
    - Maintain MT5_Bridge compatibility for trade execution
    - Keep Telegram alert functionality intact
    - _Requirements: 11.2, 11.3, 11.4_
  
  - [x] 14.3 Support existing bot modes
    - Implement Analyze, Trade, and Swing mode compatibility
    - Maintain identical behavior to webhook-based system
    - Preserve existing dashboard integration
    - _Requirements: 11.5_

- [ ] 15. Implement performance optimization and monitoring
  - [x] 15.1 Add performance monitoring and metrics
    - Implement processing time tracking for sub-5-second requirement
    - Add memory usage monitoring for 512MB VPS limit
    - Create data fetch latency and analysis processing metrics
    - _Requirements: 12.1, 12.4, 14.4_
  
  - [x] 15.2 Write property test for processing time performance
    - **Property 17: Processing Time Performance**
    - **Validates: Requirements 12.1**
  
  - [x] 15.3 Implement error recovery and degraded mode
    - Add graceful error handling with immediate Telegram alerts
    - Create degraded mode operation for critical errors
    - Implement automatic reconnection for MT5 and Redis failures
    - _Requirements: 12.3, 12.5_
  
  - [x] 15.4 Write property test for error recovery
    - **Property 18: Error Recovery and Degraded Mode**
    - **Validates: Requirements 12.5**

- [ ] 16. Implement data persistence and recovery
  - [ ] 16.1 Create PostgreSQL persistence layer
    - Implement hourly market data persistence to database
    - Add system restart recovery with 2-hour data reload
    - Create Redis backup snapshots every 30 minutes
    - _Requirements: 13.1, 13.2, 13.3_
  
  - [x] 16.2 Write property test for data persistence round trip
    - **Property 19: Data Persistence Round Trip**
    - **Validates: Requirements 13.1, 13.2**
  
  - [ ] 16.3 Implement recovery state management
    - Add incomplete candle aggregation recovery
    - Create signal generation state preservation
    - Implement 60-second resume target after restart
    - _Requirements: 13.4, 13.5_

- [ ] 17. Add configuration management and logging
  - [ ] 17.1 Implement environment-based configuration
    - Add configurable analysis parameters (EMA periods, thresholds)
    - Create runtime parameter update capability
    - Implement configuration validation and defaults
    - _Requirements: 14.1, 14.5_
  
  - [x] 17.2 Write property test for configuration parameter application
    - **Property 20: Configuration Parameter Application**
    - **Validates: Requirements 14.1, 14.5**
  
  - [ ] 17.3 Add comprehensive logging and monitoring
    - Implement detailed signal generation logging with confluence breakdowns
    - Add health check endpoints for data freshness and analysis status
    - Create signal generation rate and system health metrics
    - _Requirements: 14.3, 14.4_

- [ ] 18. Final integration and system testing
  - [ ] 18.1 Wire all components together
    - Connect Market Data Layer → Candle Aggregator → Analysis Engines → Signal Generator
    - Integrate with existing FastAPI backend and MT5 Bridge
    - Ensure seamless operation with existing Telegram and dashboard systems
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ] 18.2 Write integration tests for end-to-end pipeline
    - Test complete data flow from MT5 to signal generation
    - Validate session management and risk integration
    - Test error recovery and degraded mode scenarios
    - _Requirements: 12.2, 12.3, 12.5_
  
  - [ ] 18.3 Performance validation and optimization
    - Validate sub-5-second processing requirement under load
    - Confirm 512MB memory limit compliance
    - Test 99.5% uptime target with simulated failures
    - _Requirements: 12.1, 12.2, 12.4_

- [ ] 19. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and early error detection
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation maintains the 500-line core target through focused, single-responsibility components
- All components integrate seamlessly with existing Aegis Trader infrastructure
- Performance targets (sub-5-second processing, 512MB memory) are validated throughout development