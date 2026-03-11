"""
Main Strategy Engine orchestrator.

Coordinates all strategy engine components and manages the real-time
market analysis pipeline from data ingestion to signal generation.
Maintains full compatibility with existing Aegis Trader systems.
"""

from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from backend.strategy.config import strategy_settings, redis_manager
from backend.strategy.logging_config import get_component_logger, performance_logger
from backend.strategy.performance_monitor import performance_monitor
from backend.strategy.error_recovery import error_recovery_manager, connection_manager, EngineMode
from backend.strategy.exceptions import StrategyEngineError
from backend.strategy.models import Timeframe, Signal


class StrategyEngine:
    """
    Main orchestrator for the Python Strategy Engine.
    
    Manages the complete pipeline from market data ingestion through
    analysis to signal generation, replacing TradingView dependencies.
    """
    
    def __init__(self):
        self.logger = get_component_logger("engine")
        self.running = False
        self.components_initialized = False
        
        # Import components
        from backend.strategy.market_data import market_data_layer
        from backend.strategy.candle_aggregator import candle_aggregator
        from backend.strategy.engines.bias_engine import bias_engine
        from backend.strategy.engines.level_engine import level_engine
        from backend.strategy.engines.fvg_engine import fvg_engine
        from backend.strategy.engines.liquidity_engine import liquidity_engine
        from backend.strategy.engines.displacement_engine import displacement_engine
        from backend.strategy.engines.structure_engine import structure_engine
        from backend.strategy.signal_generator import signal_generator
        
        self.market_data = market_data_layer
        self.aggregator = candle_aggregator
        self.bias_engine = bias_engine
        self.level_engine = level_engine
        self.fvg_engine = fvg_engine
        self.liquidity_engine = liquidity_engine
        self.displacement_engine = displacement_engine
        self.structure_engine = structure_engine
        self.signal_generator = signal_generator
        
    async def initialize(self):
        """Initialize all strategy engine components."""
        try:
            self.logger.info("Initializing Python Strategy Engine...")
            
            redis = await redis_manager.get_redis()
            await redis.ping()
            self.logger.info("Redis connection established")
            
            await self.market_data.initialize_mt5()
            self.logger.info("Strategy engine components initialized")
            self.components_initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize strategy engine: {e}")
            raise StrategyEngineError(f"Initialization failed: {e}")
    
    async def start(self):
        """Start the strategy engine main loop."""
        if not self.components_initialized:
            await self.initialize()
        
        self.running = True
        self.logger.info("Starting Python Strategy Engine main loop")
        
        try:
            while self.running:
                # Main processing loop (placeholder)
                await self._process_cycle()
                await asyncio.sleep(strategy_settings.data_fetch_interval)
                
        except Exception as e:
            self.logger.error(f"Strategy engine error: {e}")
            await self._handle_error(e)
    
    async def stop(self):
        """Stop the strategy engine gracefully."""
        self.logger.info("Stopping Python Strategy Engine...")
        self.running = False
        
        # Close Redis connection
        await redis_manager.close()
        self.logger.info("Strategy engine stopped")
    
    async def _process_cycle(self):
        """Execute one complete processing cycle."""
        from backend.strategy.models import AnalysisResult
        from datetime import timezone
        
        try:
            with performance_monitor.track_operation("process_cycle"):
                # 1. Fetch latest 1M candle
                candle = await self.market_data.fetch_latest_candle()
                if not candle:
                    return
                
                await self.market_data.store_candle(candle)
                
                # 2. Aggregate to higher timeframes
                await self.aggregator.process_new_candle(candle)
                
                # 3. Get candles for analysis
                candles_5m = await self.aggregator.get_timeframe_candles(Timeframe.M5, 100)
                candles_1h = await self.aggregator.get_timeframe_candles(Timeframe.H1, 50)
                candles_4h = await self.aggregator.get_timeframe_candles(Timeframe.H4, 30)
                
                if len(candles_5m) < 50:
                    return
                
                # 4. Run analysis engines
                bias = await self.bias_engine.analyze(candles_5m, Timeframe.M5)
                levels = await self.level_engine.analyze(candles_5m)
                liquidity = await self.liquidity_engine.analyze(candles_5m, Timeframe.M5)
                fvg = await self.fvg_engine.analyze(candles_5m, Timeframe.M5)
                displacement = await self.displacement_engine.analyze(candles_5m, Timeframe.M5)
                structure = await self.structure_engine.analyze(candles_5m, Timeframe.M5)
                
                analysis = AnalysisResult(
                    timestamp=datetime.now(timezone.utc),
                    timeframe=Timeframe.M5,
                    bias=bias,
                    levels=levels,
                    liquidity=liquidity,
                    fvg=fvg,
                    displacement=displacement,
                    structure=structure
                )
                
                # 5. Generate signal if conditions met
                signal = await self.signal_generator.evaluate_setup(
                    analysis=analysis,
                    current_price=candles_5m[0].close
                )
                
                if signal:
                    self.logger.info(f"Signal: {signal.grade.value} {signal.setup_type.value} @ {signal.entry}")
            
        except Exception as e:
            self.logger.error(f"Processing cycle failed: {e}")
            performance_logger.log_error("engine", "processing_cycle_failed")
    
    async def _handle_error(self, error: Exception):
        """Handle strategy engine errors with graceful degradation."""
        self.logger.error(f"Entering error recovery mode: {error}")
        
        # TODO: Implement error recovery strategies
        # - Send Telegram alerts
        # - Switch to degraded mode
        # - Attempt component restart
        
        # For now, just log and continue
        await asyncio.sleep(5)  # Brief pause before retry
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current strategy engine status."""
        from datetime import timezone
        # Import here to avoid circular import
        try:
            from backend.strategy.compatibility import system_compatibility
            compatibility_status = await system_compatibility.get_system_status()
        except ImportError:
            compatibility_status = {"error": "Compatibility module not available"}
        
        # Get performance metrics
        performance_metrics = performance_monitor.get_performance_metrics()
        health_status = performance_monitor.get_health_status()
        
        return {
            "running": self.running,
            "components_initialized": self.components_initialized,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": performance_metrics.get("uptime_seconds"),
            "uptime_formatted": performance_metrics.get("uptime_formatted"),
            "settings": {
                "data_fetch_interval": strategy_settings.data_fetch_interval,
                "max_processing_time": strategy_settings.max_processing_time,
                "memory_limit_mb": strategy_settings.memory_limit_mb
            },
            "performance_metrics": performance_metrics,
            "health_status": health_status,
            "compatibility_status": compatibility_status
        }


# Global strategy engine instance
strategy_engine = StrategyEngine()