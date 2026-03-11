"""
Auto-Trade Decision Engine for Dual-Engine Strategy System.

This module implements the intelligent decision logic that determines which engine
should trade when both have valid setups. It prevents chaotic trading by:
- Prioritizing Core Strategy A+ signals over scalp opportunities
- Preventing both engines from trading the same instrument simultaneously
- Using volatility regime detection to favor the appropriate engine
- Tracking engine performance to dynamically adjust preferences

The decision engine is the critical component that transforms two independent
engines into a coordinated trading system.

Requirements: 15.1-15.6, 16.1-16.4
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List
from backend.strategy.dual_engine_models import (
    Instrument,
    EngineType,
    CoreSignal,
    ScalpSignal,
    SignalGrade,
    PerformanceMetrics
)


class VolatilityRegime(Enum):
    """Market volatility regime classification."""
    LOW = "LOW"           # ATR < 0.8 × average
    NORMAL = "NORMAL"     # 0.8 × average <= ATR <= 1.5 × average
    HIGH = "HIGH"         # 1.5 × average < ATR <= 2.5 × average
    EXTREME = "EXTREME"   # ATR > 2.5 × average


class TrendStrength(Enum):
    """Market trend strength classification."""
    STRONG_TREND = "STRONG_TREND"       # Clear directional bias across HTFs
    WEAK_TREND = "WEAK_TREND"           # Some HTF alignment but not strong
    RANGING = "RANGING"                 # No clear directional bias
    CHOPPY = "CHOPPY"                   # Conflicting signals across timeframes


@dataclass
class MarketRegime:
    """Current market regime for an instrument."""
    instrument: Instrument
    volatility: VolatilityRegime
    trend_strength: TrendStrength
    atr_current: float
    atr_average: float
    timestamp: datetime


@dataclass
class EnginePreference:
    """Engine preference decision with reasoning."""
    preferred_engine: Optional[EngineType]
    allow_core_strategy: bool
    allow_quick_scalp: bool
    reason: str
    confidence: float  # 0.0 to 1.0


@dataclass
class TradeDecision:
    """Final trade decision from Auto-Trade Decision Engine."""
    should_trade: bool
    engine: Optional[EngineType]
    signal: Optional[CoreSignal | ScalpSignal]
    reason: str
    blocked_engine: Optional[EngineType]  # Which engine was blocked, if any


class AutoTradeDecisionEngine:
    """
    Intelligent decision engine that coordinates Core Strategy and Quick Scalp engines.
    
    The engine prevents chaotic trading by:
    1. Ensuring only one engine trades per instrument at a time
    2. Prioritizing high-quality Core Strategy signals
    3. Favoring appropriate engine based on market regime
    4. Tracking performance to adjust preferences dynamically
    """
    
    def __init__(self):
        """Initialize the Auto-Trade Decision Engine."""
        # Track active positions per instrument
        self.active_positions: Dict[Instrument, EngineType] = {}
        
        # Track recent decisions to prevent flip-flopping
        self.recent_decisions: List[TradeDecision] = []
        
        # Performance tracking for dynamic adjustment
        self.core_performance: Optional[PerformanceMetrics] = None
        self.scalp_performance: Optional[PerformanceMetrics] = None
        
        # Configuration - Grading thresholds
        # A+ (80+): Auto trade, highest confidence, full allowed risk
        # A (70-79): Auto trade, standard confidence, standard risk
        # B (60-69): Alert only, no execution
        # C (<60): Ignore
        self.grade_a_plus_threshold = 80
        self.grade_a_threshold = 70
        self.grade_b_threshold = 60
        self.performance_lookback_trades = 20  # Recent trades for performance calc
        self.decision_cooldown_seconds = 30  # Prevent rapid switching
    
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
        
        Decision hierarchy:
        1. Check if instrument already has active position
        2. If both signals present, resolve conflict
        3. If only one signal present, validate against market regime
        4. Apply performance-based adjustments
        
        Args:
            instrument: Trading instrument
            core_signal: Core Strategy signal (if any)
            scalp_signal: Quick Scalp signal (if any)
            market_regime: Current market regime
            core_metrics: Recent Core Strategy performance
            scalp_metrics: Recent Quick Scalp performance
        
        Returns:
            TradeDecision with final verdict
        """
        # Update performance tracking
        self.core_performance = core_metrics
        self.scalp_performance = scalp_metrics
        
        # Rule 1: Check for active position on this instrument
        if instrument in self.active_positions:
            active_engine = self.active_positions[instrument]
            return TradeDecision(
                should_trade=False,
                engine=None,
                signal=None,
                reason=f"Instrument already has active {active_engine.value} position",
                blocked_engine=EngineType.CORE_STRATEGY if core_signal else EngineType.QUICK_SCALP
            )
        
        # Rule 2: No signals - nothing to decide
        if not core_signal and not scalp_signal:
            return TradeDecision(
                should_trade=False,
                engine=None,
                signal=None,
                reason="No valid signals from either engine",
                blocked_engine=None
            )
        
        # Rule 3: Only one signal present
        if core_signal and not scalp_signal:
            return self._validate_core_signal(core_signal, market_regime)
        
        if scalp_signal and not core_signal:
            return self._validate_scalp_signal(scalp_signal, market_regime)
        
        # Rule 4: Both signals present - resolve conflict
        return self._resolve_conflict(
            instrument,
            core_signal,
            scalp_signal,
            market_regime
        )
    
    def _validate_core_signal(
        self,
        signal: CoreSignal,
        regime: MarketRegime
    ) -> TradeDecision:
        """
        Validate Core Strategy signal against market regime.
        
        Core Strategy works best in:
        - Normal to high volatility (not extreme)
        - Strong to weak trends (not ranging/choppy)
        """
        # A+ signals always get approved (80+ score, highest confidence)
        if signal.grade == SignalGrade.A_PLUS:
            return TradeDecision(
                should_trade=True,
                engine=EngineType.CORE_STRATEGY,
                signal=signal,
                reason="Core Strategy A+ signal (80+) - highest confidence, full allowed risk",
                blocked_engine=None
            )
        
        # A signals (70-79 score) need favorable regime
        if signal.grade == SignalGrade.A:
            # Check volatility
            if regime.volatility == VolatilityRegime.EXTREME:
                return TradeDecision(
                    should_trade=False,
                    engine=None,
                    signal=None,
                    reason="Core Strategy A signal (70-79) blocked - extreme volatility unfavorable",
                    blocked_engine=EngineType.CORE_STRATEGY
                )
            
            # Check trend strength
            if regime.trend_strength in [TrendStrength.RANGING, TrendStrength.CHOPPY]:
                return TradeDecision(
                    should_trade=False,
                    engine=None,
                    signal=None,
                    reason="Core Strategy A signal (70-79) blocked - ranging/choppy market unfavorable",
                    blocked_engine=EngineType.CORE_STRATEGY
                )
            
            return TradeDecision(
                should_trade=True,
                engine=EngineType.CORE_STRATEGY,
                signal=signal,
                reason="Core Strategy A signal (70-79) approved - standard confidence, favorable regime",
                blocked_engine=None
            )
        
        # B signals (60-69 score) should not reach here (alert only, suppressed by Core Engine)
        return TradeDecision(
            should_trade=False,
            engine=None,
            signal=None,
            reason="Core Strategy B signal (60-69) - alert only, should be suppressed",
            blocked_engine=EngineType.CORE_STRATEGY
        )
    
    def _validate_scalp_signal(
        self,
        signal: ScalpSignal,
        regime: MarketRegime
    ) -> TradeDecision:
        """
        Validate Quick Scalp signal against market regime.
        
        Quick Scalp works best in:
        - High volatility (momentum bursts)
        - Any trend strength (captures micro moves)
        """
        # Scalp needs high volatility
        if regime.volatility in [VolatilityRegime.LOW, VolatilityRegime.NORMAL]:
            return TradeDecision(
                should_trade=False,
                engine=None,
                signal=None,
                reason="Quick Scalp signal blocked - insufficient volatility",
                blocked_engine=EngineType.QUICK_SCALP
            )
        
        # Extreme volatility is risky even for scalping
        if regime.volatility == VolatilityRegime.EXTREME:
            # Check recent scalp performance
            if self.scalp_performance and self.scalp_performance.win_rate < 0.50:
                return TradeDecision(
                    should_trade=False,
                    engine=None,
                    signal=None,
                    reason="Quick Scalp signal blocked - extreme volatility + poor recent performance",
                    blocked_engine=EngineType.QUICK_SCALP
                )
        
        return TradeDecision(
            should_trade=True,
            engine=EngineType.QUICK_SCALP,
            signal=signal,
            reason="Quick Scalp signal approved - favorable volatility",
            blocked_engine=None
        )
    
    def _resolve_conflict(
        self,
        instrument: Instrument,
        core_signal: CoreSignal,
        scalp_signal: ScalpSignal,
        regime: MarketRegime
    ) -> TradeDecision:
        """
        Resolve conflict when both engines have valid signals.
        
        Priority rules:
        1. Core Strategy A+ always wins
        2. If Core Strategy is A, compare regime suitability
        3. Use performance metrics as tiebreaker
        4. Default to Core Strategy (higher R:R potential)
        """
        # Rule 1: Core Strategy A+ (80+) has absolute priority
        if core_signal.grade == SignalGrade.A_PLUS:
            return TradeDecision(
                should_trade=True,
                engine=EngineType.CORE_STRATEGY,
                signal=core_signal,
                reason="Core Strategy A+ signal (80+) wins conflict - highest confidence, full allowed risk",
                blocked_engine=EngineType.QUICK_SCALP
            )
        
        # Rule 2: Core Strategy A - evaluate regime suitability
        if core_signal.grade == SignalGrade.A:
            core_suitable = self._is_regime_suitable_for_core(regime)
            scalp_suitable = self._is_regime_suitable_for_scalp(regime)
            
            # Both suitable - use performance tiebreaker
            if core_suitable and scalp_suitable:
                return self._performance_tiebreaker(core_signal, scalp_signal)
            
            # Only core suitable
            if core_suitable and not scalp_suitable:
                return TradeDecision(
                    should_trade=True,
                    engine=EngineType.CORE_STRATEGY,
                    signal=core_signal,
                    reason="Core Strategy wins - regime favorable for core, unfavorable for scalp",
                    blocked_engine=EngineType.QUICK_SCALP
                )
            
            # Only scalp suitable
            if not core_suitable and scalp_suitable:
                return TradeDecision(
                    should_trade=True,
                    engine=EngineType.QUICK_SCALP,
                    signal=scalp_signal,
                    reason="Quick Scalp wins - regime unfavorable for core, favorable for scalp",
                    blocked_engine=EngineType.CORE_STRATEGY
                )
            
            # Neither suitable - block both
            return TradeDecision(
                should_trade=False,
                engine=None,
                signal=None,
                reason="Both signals blocked - regime unfavorable for both engines",
                blocked_engine=None
            )
        
        # Rule 3: Core Strategy B should not reach here
        return TradeDecision(
            should_trade=False,
            engine=None,
            signal=None,
            reason="Invalid conflict - Core Strategy B signal should be suppressed",
            blocked_engine=None
        )
    
    def _is_regime_suitable_for_core(self, regime: MarketRegime) -> bool:
        """Check if market regime is suitable for Core Strategy."""
        volatility_ok = regime.volatility in [
            VolatilityRegime.NORMAL,
            VolatilityRegime.HIGH
        ]
        trend_ok = regime.trend_strength in [
            TrendStrength.STRONG_TREND,
            TrendStrength.WEAK_TREND
        ]
        return volatility_ok and trend_ok
    
    def _is_regime_suitable_for_scalp(self, regime: MarketRegime) -> bool:
        """Check if market regime is suitable for Quick Scalp."""
        return regime.volatility in [
            VolatilityRegime.HIGH,
            VolatilityRegime.EXTREME
        ]
    
    def _performance_tiebreaker(
        self,
        core_signal: CoreSignal,
        scalp_signal: ScalpSignal
    ) -> TradeDecision:
        """
        Use recent performance metrics to break tie.
        
        Compares:
        - Win rate
        - Profit factor
        - Average R:R
        
        If no clear winner, defaults to Core Strategy (higher R:R potential).
        """
        # No performance data - default to Core Strategy
        if not self.core_performance or not self.scalp_performance:
            return TradeDecision(
                should_trade=True,
                engine=EngineType.CORE_STRATEGY,
                signal=core_signal,
                reason="Core Strategy wins tiebreaker - no performance data, default to higher R:R",
                blocked_engine=EngineType.QUICK_SCALP
            )
        
        # Calculate performance scores
        core_score = (
            self.core_performance.win_rate * 0.4 +
            min(self.core_performance.profit_factor / 3.0, 1.0) * 0.3 +
            min(self.core_performance.average_rr / 2.0, 1.0) * 0.3
        )
        
        scalp_score = (
            self.scalp_performance.win_rate * 0.4 +
            min(self.scalp_performance.profit_factor / 2.0, 1.0) * 0.3 +
            min(self.scalp_performance.average_rr / 1.0, 1.0) * 0.3
        )
        
        # Require significant difference (>10%) to override Core Strategy default
        if scalp_score > core_score * 1.1:
            return TradeDecision(
                should_trade=True,
                engine=EngineType.QUICK_SCALP,
                signal=scalp_signal,
                reason=f"Quick Scalp wins tiebreaker - better recent performance (score: {scalp_score:.2f} vs {core_score:.2f})",
                blocked_engine=EngineType.CORE_STRATEGY
            )
        
        return TradeDecision(
            should_trade=True,
            engine=EngineType.CORE_STRATEGY,
            signal=core_signal,
            reason=f"Core Strategy wins tiebreaker - comparable performance, higher R:R potential (score: {core_score:.2f} vs {scalp_score:.2f})",
            blocked_engine=EngineType.QUICK_SCALP
        )
    
    def register_position_opened(
        self,
        instrument: Instrument,
        engine: EngineType
    ) -> None:
        """
        Register that an engine has opened a position on an instrument.
        
        This prevents the other engine from trading the same instrument.
        """
        self.active_positions[instrument] = engine
    
    def register_position_closed(
        self,
        instrument: Instrument
    ) -> None:
        """
        Register that a position has been closed on an instrument.
        
        This allows either engine to trade the instrument again.
        """
        if instrument in self.active_positions:
            del self.active_positions[instrument]
    
    def get_engine_preference(
        self,
        regime: MarketRegime
    ) -> EnginePreference:
        """
        Get general engine preference for current market regime.
        
        This provides guidance without specific signals.
        Useful for UI display and monitoring.
        """
        core_suitable = self._is_regime_suitable_for_core(regime)
        scalp_suitable = self._is_regime_suitable_for_scalp(regime)
        
        # Both suitable
        if core_suitable and scalp_suitable:
            return EnginePreference(
                preferred_engine=EngineType.CORE_STRATEGY,
                allow_core_strategy=True,
                allow_quick_scalp=True,
                reason="Both engines suitable - Core Strategy preferred for higher R:R",
                confidence=0.6
            )
        
        # Only core suitable
        if core_suitable:
            return EnginePreference(
                preferred_engine=EngineType.CORE_STRATEGY,
                allow_core_strategy=True,
                allow_quick_scalp=False,
                reason="Core Strategy preferred - trending market with normal volatility",
                confidence=0.8
            )
        
        # Only scalp suitable
        if scalp_suitable:
            return EnginePreference(
                preferred_engine=EngineType.QUICK_SCALP,
                allow_core_strategy=False,
                allow_quick_scalp=True,
                reason="Quick Scalp preferred - high volatility momentum environment",
                confidence=0.8
            )
        
        # Neither suitable
        return EnginePreference(
            preferred_engine=None,
            allow_core_strategy=False,
            allow_quick_scalp=False,
            reason="No engine suitable - unfavorable market conditions",
            confidence=0.9
        )
    
    def clear_history(self) -> None:
        """Clear decision history and active positions. Used for testing and daily reset."""
        self.active_positions.clear()
        self.recent_decisions.clear()
