"""
Trading Loop Service - Continuous Market Analysis & Signal Generation

Implements the main trading loop that:
1. Fetches live market data from MT5
2. Analyzes all enabled markets in parallel
3. Generates signals via dual-engine system
4. Executes approved trades
5. Broadcasts updates via WebSocket
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import pytz

from backend.modules.mt5_manager import mt5_manager
from backend.strategy.multi_market_coordinator import MultiMarketCoordinator, MultiMarketConfig
from backend.strategy.dual_engine_models import Instrument, OHLCVBar
from backend.strategy.session_manager import SessionManager
from backend.modules.news_filter import check_news_blackout
from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class TradingLoopService:
    """
    Main trading loop service.
    
    Continuously analyzes markets and generates signals.
    """
    
    def __init__(self):
        """Initialize trading loop service."""
        self.running = False
        self.loop_interval = 60  # Check every 60 seconds
        self.session_manager = SessionManager()
        
        # Multi-market coordinator
        self.coordinator = MultiMarketCoordinator(
            config=MultiMarketConfig(),
            session_manager=self.session_manager,
            news_filter=None,  # Will use check_news_blackout directly
        )
        
        # Engine settings (would be loaded from database)
        self.engine_settings = {
            "core_strategy_enabled": True,
            "quick_scalp_enabled": True,
            "us30_enabled": True,
            "nas100_enabled": True,
            "xauusd_enabled": True,
        }
        
        # WebSocket connections (for broadcasting updates)
        self.websocket_connections = set()
        
        # Statistics
        self.loop_count = 0
        self.signals_generated = 0
        self.trades_executed = 0
        self.last_run = None
        self.errors = []
    
    async def start(self):
        """Start the trading loop."""
        if self.running:
            logger.warning("Trading loop already running")
            return
        
        self.running = True
        logger.info("🚀 Trading loop started")
        
        try:
            while self.running:
                try:
                    await self._run_iteration()
                    await asyncio.sleep(self.loop_interval)
                except Exception as e:
                    logger.error(f"Trading loop iteration error: {e}", exc_info=True)
                    self.errors.append({
                        "timestamp": datetime.now(pytz.UTC).isoformat(),
                        "error": str(e)
                    })
                    # Keep only last 10 errors
                    self.errors = self.errors[-10:]
                    await asyncio.sleep(5)  # Wait before retry
        except Exception as e:
            logger.critical(f"Trading loop crashed: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("Trading loop stopped")
    
    async def stop(self):
        """Stop the trading loop."""
        logger.info("Stopping trading loop...")
        self.running = False
    
    async def _run_iteration(self):
        """Run one iteration of the trading loop."""
        self.loop_count += 1
        self.last_run = datetime.now(pytz.UTC)
        
        logger.info(f"=== Trading Loop Iteration #{self.loop_count} ===")
        
        # Step 1: Check MT5 connection
        if not await mt5_manager.is_connected():
            logger.warning("MT5 not connected - attempting to connect")
            if not await mt5_manager.connect():
                logger.error("Failed to connect to MT5 - skipping iteration")
                return
        
        # Step 2: Check news blackout
        async with AsyncSessionLocal() as db:
            news_check = await check_news_blackout(db)
            if news_check.blocked:
                logger.warning(f"News blackout active: {news_check.reason}")
                await self._broadcast_update({
                    "type": "news_blackout",
                    "reason": news_check.reason,
                    "minutes_until_clear": news_check.minutes_until_clear
                })
                return
        
        # Step 3: Get enabled instruments
        enabled_instruments = self._get_enabled_instruments()
        if not enabled_instruments:
            logger.info("No instruments enabled - skipping iteration")
            return
        
        logger.info(f"Analyzing {len(enabled_instruments)} instruments: {[i.value for i in enabled_instruments]}")
        
        # Step 4: Fetch market data for all instruments
        market_data = await self._fetch_market_data(enabled_instruments)
        
        if not market_data:
            logger.warning("No market data available - skipping iteration")
            return
        
        # Step 5: Process all markets in parallel
        signals = await self.coordinator.process_all_markets(market_data)
        
        # Step 6: Handle generated signals
        for instrument, signal in signals.items():
            if signal:
                self.signals_generated += 1
                logger.info(f"✨ Signal generated for {instrument.value}: {signal.signal_id}")
                
                # Broadcast signal to WebSocket clients
                await self._broadcast_update({
                    "type": "signal_generated",
                    "signal": {
                        "signal_id": signal.signal_id,
                        "engine": signal.engine.value,
                        "instrument": signal.instrument.value,
                        "direction": signal.direction.value,
                        "entry_price": signal.entry_price,
                        "stop_loss": signal.stop_loss,
                        "tp1": signal.tp1,
                        "tp2": signal.tp2,
                        "risk_reward_ratio": signal.get_risk_reward_ratio(),
                        "status": signal.status.value,
                    }
                })
                
                # Execute trade if auto-trade enabled
                if self._should_execute_trade(signal):
                    success = await self._execute_trade(signal)
                    if success:
                        self.trades_executed += 1
        
        # Step 7: Broadcast status update
        await self._broadcast_update({
            "type": "loop_completed",
            "iteration": self.loop_count,
            "signals_generated": self.signals_generated,
            "trades_executed": self.trades_executed,
            "timestamp": self.last_run.isoformat()
        })
        
        logger.info(f"Iteration complete - Signals: {self.signals_generated}, Trades: {self.trades_executed}")
    
    def _get_enabled_instruments(self) -> List[Instrument]:
        """Get list of enabled instruments based on settings."""
        enabled = []
        
        if self.engine_settings.get("us30_enabled"):
            enabled.append(Instrument.US30)
        if self.engine_settings.get("nas100_enabled"):
            enabled.append(Instrument.NAS100)
        if self.engine_settings.get("xauusd_enabled"):
            enabled.append(Instrument.XAUUSD)
        
        return enabled
    
    async def _fetch_market_data(
        self,
        instruments: List[Instrument]
    ) -> Dict[Instrument, tuple[List[OHLCVBar], float]]:
        """
        Fetch market data for all instruments.
        
        Returns:
            Dict mapping instrument to (bars, current_spread)
        """
        market_data = {}
        
        for instrument in instruments:
            try:
                # Fetch OHLCV bars (300 bars for regime detection)
                bars = await mt5_manager.get_market_data(
                    instrument=instrument,
                    timeframe="M5",
                    bars=300,
                    use_cache=True
                )
                
                # Get current spread
                spread = await mt5_manager.get_current_spread(instrument)
                
                if bars and len(bars) >= 250:  # Minimum for regime detection
                    market_data[instrument] = (bars, spread)
                    logger.debug(f"Fetched {len(bars)} bars for {instrument.value}, spread: {spread}")
                else:
                    logger.warning(f"Insufficient data for {instrument.value}: {len(bars) if bars else 0} bars")
                    
            except Exception as e:
                logger.error(f"Error fetching data for {instrument.value}: {e}")
        
        return market_data
    
    def _should_execute_trade(self, signal) -> bool:
        """Check if trade should be executed."""
        # Check if engine is enabled
        if signal.engine.value == "CORE_STRATEGY":
            if not self.engine_settings.get("core_strategy_enabled"):
                logger.info(f"Core Strategy disabled - not executing {signal.signal_id}")
                return False
        elif signal.engine.value == "QUICK_SCALP":
            if not self.engine_settings.get("quick_scalp_enabled"):
                logger.info(f"Quick Scalp disabled - not executing {signal.signal_id}")
                return False
        
        # Check if signal is approved
        if signal.status.value != "APPROVED":
            logger.info(f"Signal not approved - not executing {signal.signal_id}")
            return False
        
        return True
    
    async def _execute_trade(self, signal) -> bool:
        """
        Execute trade via MT5.
        
        Returns:
            True if trade executed successfully
        """
        try:
            from backend.schemas.schemas import MT5OrderRequest
            
            # Create order request
            order = MT5OrderRequest(
                symbol=signal.instrument.value,
                action="buy" if signal.direction.value == "LONG" else "sell",
                lot_size=0.1,  # Would calculate based on risk
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.tp1,
                comment=f"{signal.engine.value}_{signal.signal_id[:8]}"
            )
            
            # Place order
            response = await mt5_manager.place_order(order)
            
            if response.success:
                logger.info(f"✅ Trade executed: {signal.signal_id} -> Ticket: {response.ticket}")
                
                # Broadcast trade execution
                await self._broadcast_update({
                    "type": "trade_executed",
                    "signal_id": signal.signal_id,
                    "ticket": response.ticket,
                    "instrument": signal.instrument.value,
                    "direction": signal.direction.value,
                    "entry_price": response.actual_price,
                })
                
                return True
            else:
                logger.error(f"❌ Trade execution failed: {response.error}")
                
                # Broadcast failure
                await self._broadcast_update({
                    "type": "trade_failed",
                    "signal_id": signal.signal_id,
                    "error": response.error,
                })
                
                return False
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return False
    
    async def _broadcast_update(self, message: dict):
        """Broadcast update to all WebSocket connections."""
        if not self.websocket_connections:
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(pytz.UTC).isoformat()
        
        # Broadcast to all connections
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected
    
    def add_websocket(self, websocket):
        """Add WebSocket connection for updates."""
        self.websocket_connections.add(websocket)
        logger.info(f"WebSocket connected - Total: {len(self.websocket_connections)}")
    
    def remove_websocket(self, websocket):
        """Remove WebSocket connection."""
        self.websocket_connections.discard(websocket)
        logger.info(f"WebSocket disconnected - Total: {len(self.websocket_connections)}")
    
    def update_settings(self, settings: dict):
        """Update engine settings."""
        self.engine_settings.update(settings)
        logger.info(f"Settings updated: {settings}")
    
    def get_status(self) -> dict:
        """Get trading loop status."""
        return {
            "running": self.running,
            "loop_count": self.loop_count,
            "signals_generated": self.signals_generated,
            "trades_executed": self.trades_executed,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "websocket_connections": len(self.websocket_connections),
            "enabled_instruments": [i.value for i in self._get_enabled_instruments()],
            "settings": self.engine_settings,
            "recent_errors": self.errors[-5:] if self.errors else [],
        }


# Global singleton instance
trading_loop_service = TradingLoopService()
