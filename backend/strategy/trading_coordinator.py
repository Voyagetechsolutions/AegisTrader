"""
Trading Coordinator - End-to-End Integration.

Wires the complete flow:
Market Data → Regime Detection → Strategy Engines → Decision Engine → 
Risk Validation → Signal Routing → Execution → Performance Tracking

This is where all components become one coordinated machine.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
import uuid
from backend.strategy.regime_detector import RegimeDetector
from backend.strategy.auto_trade_decision_engine import (
    AutoTradeDecisionEngine,
    MarketRegime
)
from backend.strategy.performance_tracker import PerformanceTracker
from backend.strategy.unified_signal import (
    UnifiedSignal,
    SignalConverter,
    SignalValidator,
    SignalRouter,
    SignalStatus,
    SignalReason
)
from backend.strategy.dual_engine_models import (
    Instrument,
    EngineType,
    OHLCVBar,
    CoreSignal,
    ScalpSignal,
    SignalGrade
)


@dataclass
class CoordinatorConfig:
    """Configuration for trading coordinator."""
    # Instruments to trade
    instruments: List[Instrument]
    
    # Spread limits
    spread_limits_global: Dict[Instrument, float]
    spread_limits_scalp: Dict[Instrument, float]
    
    # Risk limits
    core_risk_per_trade: float = 0.01  # 1%
    scalp_risk_per_trade: float = 0.005  # 0.5%
    
    # Performance tracking
    rolling_window_size: int = 20
    
    # Regime detection
    min_bars_for_regime: int = 250


class TradingCoordinator:
    """
    Coordinates all trading components into one unified system.
    
    Flow:
    1. Receive market data
    2. Detect regime
    3. Generate signals from both engines
    4. Decision engine picks winner
    5. Validate signal
    6. Route to execution
    7. Track performance
    
    This is the brain that connects all the pieces.
    """
    
    def __init__(
        self,
        config: CoordinatorConfig,
        session_manager,
        news_filter,
        core_strategy_engine=None,
        scalp_strategy_engine=None
    ):
        """
        Initialize trading coordinator.
        
        Args:
            config: Coordinator configuration
            session_manager: Session manager instance
            news_filter: News filter instance
            core_strategy_engine: Core strategy engine (optional for testing)
            scalp_strategy_engine: Scalp strategy engine (optional for testing)
        """
        self.config = config
        self.session_manager = session_manager
        self.news_filter = news_filter
        
        # Strategy engines (to be implemented)
        self.core_engine = core_strategy_engine
        self.scalp_engine = scalp_strategy_engine
        
        # Core components
        self.regime_detector = RegimeDetector()
        self.decision_engine = AutoTradeDecisionEngine()
        self.performance_tracker = PerformanceTracker(
            rolling_window_size=config.rolling_window_size
        )
        
        # Signal processing
        self.signal_validator = SignalValidator(
            spread_limits=config.spread_limits_global,
            session_manager=session_manager,
            news_filter=news_filter
        )
        self.signal_router = SignalRouter()
        
        # State tracking
        self.current_regimes: Dict[Instrument, MarketRegime] = {}
        self.pending_signals: List[UnifiedSignal] = []
        self.active_signals: List[UnifiedSignal] = []
    
    def process_market_data(
        self,
        instrument: Instrument,
        bars: List[OHLCVBar],
        current_spread: float
    ) -> Optional[UnifiedSignal]:
        """
        Process market data through complete pipeline.
        
        This is the main entry point. Call this when new market data arrives.
        
        Args:
            instrument: Trading instrument
            bars: OHLCV bars (need at least 250 for full analysis)
            current_spread: Current bid-ask spread
        
        Returns:
            UnifiedSignal if trade approved, None otherwise
        """
        # Step 1: Detect regime
        if len(bars) < self.config.min_bars_for_regime:
            print(f"Insufficient bars for {instrument.value}: {len(bars)} < {self.config.min_bars_for_regime}")
            return None
        
        regime = self.regime_detector.detect_regime(instrument, bars)
        self.current_regimes[instrument] = regime
        
        print(f"\n{'='*60}")
        print(f"Processing {instrument.value}")
        print(f"Regime: {regime.volatility.value} volatility, {regime.trend_strength.value} trend")
        print(f"ATR: {regime.atr_current:.2f} (avg: {regime.atr_average:.2f}, ratio: {regime.atr_current/regime.atr_average:.2f}x)")
        
        # Step 2: Generate signals from both engines
        core_signal = self._generate_core_signal(instrument, bars, regime)
        scalp_signal = self._generate_scalp_signal(instrument, bars, regime)
        
        if not core_signal and not scalp_signal:
            print("No signals from either engine")
            return None
        
        if core_signal:
            print(f"Core Signal: {core_signal.grade.value} ({core_signal.confluence_score.total} points)")
        if scalp_signal:
            print(f"Scalp Signal: Valid")
        
        # Step 3: Decision engine picks winner
        core_metrics = self.performance_tracker.get_rolling_metrics(EngineType.CORE_STRATEGY)
        scalp_metrics = self.performance_tracker.get_rolling_metrics(EngineType.QUICK_SCALP)
        
        decision = self.decision_engine.decide_trade(
            instrument=instrument,
            core_signal=core_signal,
            scalp_signal=scalp_signal,
            market_regime=regime,
            core_metrics=core_metrics,
            scalp_metrics=scalp_metrics
        )
        
        print(f"\nDecision: {decision.engine.value if decision.engine else 'NO TRADE'}")
        print(f"Reason: {decision.reason}")
        if decision.blocked_engine:
            print(f"Blocked: {decision.blocked_engine.value}")
        
        if not decision.should_trade:
            return None
        
        # Step 4: Convert to unified signal
        signal_id = self._generate_signal_id(instrument, decision.engine)
        
        if decision.engine == EngineType.CORE_STRATEGY:
            unified_signal = SignalConverter.from_core_signal(
                core_signal=decision.signal,
                signal_id=signal_id,
                reasons=self._build_core_reasons(decision.signal)
            )
        else:  # QUICK_SCALP
            unified_signal = SignalConverter.from_scalp_signal(
                scalp_signal=decision.signal,
                signal_id=signal_id,
                grade=SignalGrade.A,  # Scalp signals that pass are grade A
                score=70.0,  # Scalp doesn't have scores, use A threshold default
                reasons=self._build_scalp_reasons()
            )
        
        # Step 5: Validate signal
        is_valid, rejection_reason = self.signal_validator.validate(
            unified_signal,
            current_spread
        )
        
        if not is_valid:
            print(f"Signal rejected: {rejection_reason}")
            unified_signal.status = SignalStatus.REJECTED
            return None
        
        unified_signal.status = SignalStatus.APPROVED
        print(f"\nSignal approved: {signal_id}")
        print(f"Entry: {unified_signal.entry_price:.2f}")
        print(f"Stop Loss: {unified_signal.stop_loss:.2f}")
        print(f"TP1: {unified_signal.tp1:.2f} ({unified_signal.tp1_size:.0%})")
        if unified_signal.tp2:
            print(f"TP2: {unified_signal.tp2:.2f} ({unified_signal.tp2_size:.0%})")
        print(f"R:R: {unified_signal.get_risk_reward_ratio():.2f}")
        
        # Step 6: Register position with decision engine
        self.decision_engine.register_position_opened(
            instrument=instrument,
            engine=decision.engine
        )
        
        # Step 7: Route to execution
        success = self.signal_router.route(unified_signal)
        
        if success:
            self.active_signals.append(unified_signal)
            print(f"Signal routed successfully")
        else:
            print(f"Signal routing failed")
            unified_signal.status = SignalStatus.REJECTED
            return None
        
        return unified_signal
    
    def record_trade_outcome(
        self,
        signal_id: str,
        win: bool,
        r_multiple: float,
        profit_loss: float
    ) -> None:
        """
        Record completed trade outcome.
        
        Args:
            signal_id: Signal identifier
            win: True if profitable
            r_multiple: Risk multiple achieved
            profit_loss: Actual P&L
        """
        # Find signal
        signal = None
        for sig in self.active_signals:
            if sig.signal_id == signal_id:
                signal = sig
                break
        
        if not signal:
            print(f"Warning: Signal {signal_id} not found in active signals")
            return
        
        # Record in performance tracker
        self.performance_tracker.record_trade(
            trade_id=signal_id,
            engine=signal.engine,
            instrument=signal.instrument,
            win=win,
            r_multiple=r_multiple,
            profit_loss=profit_loss
        )
        
        # Unregister position
        self.decision_engine.register_position_closed(signal.instrument)
        
        # Remove from active signals
        self.active_signals = [s for s in self.active_signals if s.signal_id != signal_id]
        
        print(f"\nTrade completed: {signal_id}")
        print(f"Result: {'WIN' if win else 'LOSS'}")
        print(f"R Multiple: {r_multiple:.2f}R")
        print(f"P&L: {profit_loss:+.2f}")
        
        # Show updated metrics
        metrics = self.performance_tracker.get_rolling_metrics(
            signal.engine,
            signal.instrument
        )
        print(f"\nUpdated {signal.engine.value} metrics for {signal.instrument.value}:")
        print(f"Win Rate: {metrics.win_rate:.1%}")
        print(f"Avg R: {metrics.average_rr:.2f}")
        print(f"Profit Factor: {metrics.profit_factor:.2f}")
        print(f"Total Trades: {metrics.total_trades}")
    
    def get_current_regime(self, instrument: Instrument) -> Optional[MarketRegime]:
        """Get current market regime for instrument."""
        return self.current_regimes.get(instrument)
    
    def get_performance_summary(self, engine: EngineType) -> Dict:
        """Get comprehensive performance summary for engine."""
        return self.performance_tracker.get_summary(engine)
    
    def get_active_signals(self) -> List[UnifiedSignal]:
        """Get list of active signals."""
        return self.active_signals.copy()
    
    def _generate_core_signal(
        self,
        instrument: Instrument,
        bars: List[OHLCVBar],
        regime: MarketRegime
    ) -> Optional[CoreSignal]:
        """
        Generate signal from Core Strategy Engine.
        
        This is a placeholder. Real implementation would call actual strategy logic.
        """
        if self.core_engine:
            return self.core_engine.analyze_setup(instrument, bars, regime)
        
        # Placeholder: return None (no signal)
        return None
    
    def _generate_scalp_signal(
        self,
        instrument: Instrument,
        bars: List[OHLCVBar],
        regime: MarketRegime
    ) -> Optional[ScalpSignal]:
        """
        Generate signal from Quick Scalp Engine.
        
        This is a placeholder. Real implementation would call actual strategy logic.
        """
        if self.scalp_engine:
            return self.scalp_engine.analyze_scalp_setup(instrument, bars, regime)
        
        # Placeholder: return None (no signal)
        return None
    
    def _generate_signal_id(self, instrument: Instrument, engine: EngineType) -> str:
        """Generate unique signal ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{engine.value}_{instrument.value}_{timestamp}_{unique_id}"
    
    def _build_core_reasons(self, signal: CoreSignal) -> SignalReason:
        """Build detailed reasons from Core Strategy signal."""
        cs = signal.confluence_score
        
        return SignalReason(
            htf_alignment=f"{cs.htf_alignment} points" if cs.htf_alignment > 0 else None,
            key_level=f"{cs.key_level} points" if cs.key_level > 0 else None,
            liquidity_sweep=f"{cs.liquidity_sweep} points" if cs.liquidity_sweep > 0 else None,
            fvg=f"{cs.fvg} points" if cs.fvg > 0 else None,
            displacement=f"{cs.displacement} points" if cs.displacement > 0 else None,
            mss=f"{cs.mss} points" if cs.mss > 0 else None,
            vwap=f"{cs.vwap} points" if cs.vwap > 0 else None,
            volume=f"{cs.volume_spike} points" if cs.volume_spike > 0 else None,
            atr=f"{cs.atr} points" if cs.atr > 0 else None,
            session=f"{cs.session} points" if cs.session > 0 else None
        )
    
    def _build_scalp_reasons(self) -> SignalReason:
        """Build reasons for Quick Scalp signal."""
        return SignalReason(
            liquidity_sweep="M1 liquidity sweep detected",
            momentum_candle="Strong momentum candle",
            micro_structure="Micro structure break confirmed",
            volume="Volume spike present"
        )
    
    def register_execution_handler(self, handler):
        """Register handler for signal execution."""
        self.signal_router.register_handler(handler)
    
    def clear_state(self):
        """Clear all state (for testing)."""
        self.current_regimes.clear()
        self.pending_signals.clear()
        self.active_signals.clear()
        self.decision_engine.clear_history()
        self.performance_tracker.clear_history()
