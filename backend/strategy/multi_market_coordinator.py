"""
Multi-Market Coordinator - Parallel Processing for US30, NAS100, XAUUSD.

Manages multiple TradingCoordinator instances, one per instrument.
Processes all markets in parallel and aggregates results.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from backend.strategy.dual_engine_models import Instrument, OHLCVBar
from backend.strategy.trading_coordinator import TradingCoordinator, CoordinatorConfig
from backend.strategy.unified_signal import UnifiedSignal

logger = logging.getLogger(__name__)


@dataclass
class MultiMarketConfig:
    """Configuration for multi-market coordinator."""
    # Instruments to trade
    instruments: List[Instrument] = None
    
    # Per-instrument spread limits
    spread_limits_global: Dict[Instrument, float] = None
    spread_limits_scalp: Dict[Instrument, float] = None
    
    # Risk settings
    core_risk_per_trade: float = 0.01  # 1%
    scalp_risk_per_trade: float = 0.005  # 0.5%
    
    # Performance tracking
    rolling_window_size: int = 20
    
    # Regime detection
    min_bars_for_regime: int = 250
    
    def __post_init__(self):
        """Set defaults if not provided."""
        if self.instruments is None:
            self.instruments = [
                Instrument.US30,
                Instrument.NAS100,
                Instrument.XAUUSD
            ]
        
        if self.spread_limits_global is None:
            self.spread_limits_global = {
                Instrument.US30: 5.0,
                Instrument.NAS100: 4.0,
                Instrument.XAUUSD: 3.0,
            }
        
        if self.spread_limits_scalp is None:
            self.spread_limits_scalp = {
                Instrument.US30: 3.0,
                Instrument.NAS100: 2.0,
                Instrument.XAUUSD: 2.0,
            }


class MultiMarketCoordinator:
    """
    Coordinates trading across multiple instruments simultaneously.
    
    Each instrument gets its own TradingCoordinator instance.
    Processes all markets in parallel for maximum efficiency.
    """
    
    def __init__(
        self,
        config: MultiMarketConfig,
        session_manager,
        news_filter,
        core_strategy_engine=None,
        scalp_strategy_engine=None
    ):
        """
        Initialize multi-market coordinator.
        
        Args:
            config: Multi-market configuration
            session_manager: Session manager instance
            news_filter: News filter instance
            core_strategy_engine: Core strategy engine (optional)
            scalp_strategy_engine: Scalp strategy engine (optional)
        """
        self.config = config
        self.session_manager = session_manager
        self.news_filter = news_filter
        self.core_engine = core_strategy_engine
        self.scalp_engine = scalp_strategy_engine
        
        # Create coordinator for each instrument
        self.coordinators: Dict[Instrument, TradingCoordinator] = {}
        
        for instrument in config.instruments:
            coordinator_config = CoordinatorConfig(
                instruments=[instrument],
                spread_limits_global=config.spread_limits_global,
                spread_limits_scalp=config.spread_limits_scalp,
                core_risk_per_trade=config.core_risk_per_trade,
                scalp_risk_per_trade=config.scalp_risk_per_trade,
                rolling_window_size=config.rolling_window_size,
                min_bars_for_regime=config.min_bars_for_regime
            )
            
            self.coordinators[instrument] = TradingCoordinator(
                config=coordinator_config,
                session_manager=session_manager,
                news_filter=news_filter,
                core_strategy_engine=core_strategy_engine,
                scalp_strategy_engine=scalp_strategy_engine
            )
        
        logger.info(f"MultiMarketCoordinator initialized for {len(config.instruments)} instruments")
    
    async def process_all_markets(
        self,
        market_data: Dict[Instrument, tuple[List[OHLCVBar], float]]
    ) -> Dict[Instrument, Optional[UnifiedSignal]]:
        """
        Process all markets in parallel.
        
        Args:
            market_data: Dict mapping instrument to (bars, current_spread)
        
        Returns:
            Dict mapping instrument to generated signal (or None)
        """
        tasks = []
        instruments = []
        
        for instrument, (bars, spread) in market_data.items():
            if instrument not in self.coordinators:
                logger.warning(f"No coordinator for {instrument.value}, skipping")
                continue
            
            task = asyncio.create_task(
                self._process_market_async(instrument, bars, spread)
            )
            tasks.append(task)
            instruments.append(instrument)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results back to instruments
        signals = {}
        for instrument, result in zip(instruments, results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {instrument.value}: {result}")
                signals[instrument] = None
            else:
                signals[instrument] = result
        
        return signals
    
    async def _process_market_async(
        self,
        instrument: Instrument,
        bars: List[OHLCVBar],
        current_spread: float
    ) -> Optional[UnifiedSignal]:
        """
        Process single market asynchronously.
        
        Wraps synchronous coordinator.process_market_data() in async context.
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        coordinator = self.coordinators[instrument]
        
        signal = await loop.run_in_executor(
            None,
            coordinator.process_market_data,
            instrument,
            bars,
            current_spread
        )
        
        return signal
    
    def process_market_sync(
        self,
        instrument: Instrument,
        bars: List[OHLCVBar],
        current_spread: float
    ) -> Optional[UnifiedSignal]:
        """
        Process single market synchronously.
        
        Args:
            instrument: Trading instrument
            bars: OHLCV bars
            current_spread: Current bid-ask spread
        
        Returns:
            UnifiedSignal if trade approved, None otherwise
        """
        if instrument not in self.coordinators:
            logger.warning(f"No coordinator for {instrument.value}")
            return None
        
        coordinator = self.coordinators[instrument]
        return coordinator.process_market_data(instrument, bars, current_spread)
    
    def get_all_active_signals(self) -> Dict[Instrument, List[UnifiedSignal]]:
        """Get active signals for all instruments."""
        return {
            instrument: coordinator.get_active_signals()
            for instrument, coordinator in self.coordinators.items()
        }
    
    def get_all_regimes(self) -> Dict[Instrument, dict]:
        """Get current market regime for all instruments."""
        regimes = {}
        for instrument, coordinator in self.coordinators.items():
            regime = coordinator.get_current_regime(instrument)
            if regime:
                regimes[instrument] = {
                    "volatility": regime.volatility.value,
                    "trend": regime.trend_strength.value,
                    "atr_current": regime.atr_current,
                    "atr_average": regime.atr_average,
                    "atr_ratio": regime.atr_current / regime.atr_average if regime.atr_average > 0 else 0,
                    "timestamp": datetime.now().isoformat()
                }
        return regimes
    
    def get_coordinator(self, instrument: Instrument) -> Optional[TradingCoordinator]:
        """Get coordinator for specific instrument."""
        return self.coordinators.get(instrument)
    
    def record_trade_outcome(
        self,
        instrument: Instrument,
        signal_id: str,
        win: bool,
        r_multiple: float,
        profit_loss: float
    ) -> None:
        """
        Record trade outcome for specific instrument.
        
        Args:
            instrument: Trading instrument
            signal_id: Signal identifier
            win: True if profitable
            r_multiple: Risk multiple achieved
            profit_loss: Actual P&L
        """
        coordinator = self.coordinators.get(instrument)
        if coordinator:
            coordinator.record_trade_outcome(signal_id, win, r_multiple, profit_loss)
        else:
            logger.warning(f"No coordinator for {instrument.value}")
    
    def clear_all_state(self):
        """Clear state for all coordinators (for testing)."""
        for coordinator in self.coordinators.values():
            coordinator.clear_state()
