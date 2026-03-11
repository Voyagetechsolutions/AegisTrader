"""
MT5 Manager - Centralized MT5 Connection Management

Provides high-level interface for MT5 operations with:
- Connection health monitoring
- Automatic reconnection
- Market data fetching
- Order execution
- Position management
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio

from backend.routers.mt5_bridge import mt5_bridge, MT5BridgeManager
from backend.schemas.schemas import MT5OrderRequest, MT5OrderResponse, MT5Position
from backend.strategy.dual_engine_models import Instrument, OHLCVBar

logger = logging.getLogger(__name__)


class MT5Manager:
    """
    High-level MT5 connection manager.
    
    Wraps MT5BridgeManager with additional features:
    - Multi-instrument support
    - Market data caching
    - Connection status tracking
    - Error handling and recovery
    """
    
    def __init__(self, bridge: MT5BridgeManager = None):
        """
        Initialize MT5 Manager.
        
        Args:
            bridge: MT5BridgeManager instance (uses global singleton if None)
        """
        self.bridge = bridge or mt5_bridge
        self._connection_status = "disconnected"
        self._last_connection_check = None
        self._market_data_cache: Dict[str, List[OHLCVBar]] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        
    async def connect(self) -> bool:
        """
        Establish connection to MT5.
        
        Returns:
            True if connected successfully
        """
        try:
            logger.info("Connecting to MT5...")
            
            # Check if EA is running and responding
            is_healthy = await self.bridge.health_check()
            
            if is_healthy:
                self._connection_status = "connected"
                self._last_connection_check = datetime.now()
                logger.info("MT5 connection established")
                return True
            else:
                self._connection_status = "error"
                logger.error("MT5 connection failed - EA not responding")
                return False
                
        except Exception as e:
            self._connection_status = "error"
            logger.error(f"MT5 connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MT5."""
        self._connection_status = "disconnected"
        logger.info("MT5 disconnected")
    
    async def is_connected(self) -> bool:
        """
        Check if MT5 is connected.
        
        Returns:
            True if connected and healthy
        """
        if self._connection_status != "connected":
            return False
        
        # Check if connection check is stale (>60s)
        if self._last_connection_check:
            age = (datetime.now() - self._last_connection_check).total_seconds()
            if age > 60:
                # Refresh connection status
                return await self.connect()
        
        return True
    
    async def get_connection_status(self) -> Dict:
        """
        Get detailed connection status.
        
        Returns:
            Dict with connection details
        """
        is_conn = await self.is_connected()
        
        return {
            "connected": is_conn,
            "status": self._connection_status,
            "last_check": self._last_connection_check.isoformat() if self._last_connection_check else None,
            "bridge_healthy": self.bridge._connection_healthy,
            "reconnect_attempts": self.bridge._reconnect_attempts,
        }
    
    async def get_account_info(self) -> Dict:
        """
        Get MT5 account information.
        
        Returns:
            Dict with balance, equity, margin, etc.
        """
        try:
            balance = await self.bridge.get_account_balance()
            
            # Get positions for equity calculation
            positions = await self.bridge.get_positions()
            
            return {
                "balance": balance,
                "equity": balance,  # Would calculate from positions
                "margin": 0.0,  # Would get from heartbeat
                "free_margin": balance,
                "margin_level": 0.0,
                "open_positions": len(positions),
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                "balance": 0.0,
                "equity": 0.0,
                "margin": 0.0,
                "free_margin": 0.0,
                "margin_level": 0.0,
                "open_positions": 0,
            }
    
    async def get_market_data(
        self,
        instrument: Instrument,
        timeframe: str = "M5",
        bars: int = 300,
        use_cache: bool = True
    ) -> List[OHLCVBar]:
        """
        Get market data for instrument.
        
        Args:
            instrument: Trading instrument
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
            bars: Number of bars to fetch
            use_cache: Use cached data if available
        
        Returns:
            List of OHLCV bars
        """
        cache_key = f"{instrument.value}_{timeframe}_{bars}"
        
        # Check cache
        if use_cache and cache_key in self._market_data_cache:
            expiry = self._cache_expiry.get(cache_key)
            if expiry and datetime.now() < expiry:
                logger.debug(f"Using cached market data for {cache_key}")
                return self._market_data_cache[cache_key]
        
        try:
            # Fetch from MT5 via bridge
            logger.debug(f"Fetching market data: {instrument.value} {timeframe} {bars} bars")
            
            # Request historical data from MT5
            response = await self.bridge.request_historical_data(
                symbol=instrument.value,
                timeframe=timeframe,
                bars=bars
            )
            
            if not response or not response.get("success"):
                logger.warning(f"Failed to fetch market data for {instrument.value}: {response.get('error', 'Unknown error')}")
                return []
            
            # Parse bars from response
            bars_data = response.get("bars", [])
            if not bars_data:
                logger.warning(f"No bars returned for {instrument.value}")
                return []
            
            # Convert to OHLCVBar objects
            ohlcv_bars = []
            for bar in bars_data:
                try:
                    ohlcv_bar = OHLCVBar(
                        timestamp=datetime.fromisoformat(bar["timestamp"]) if isinstance(bar["timestamp"], str) else bar["timestamp"],
                        open=float(bar["open"]),
                        high=float(bar["high"]),
                        low=float(bar["low"]),
                        close=float(bar["close"]),
                        volume=int(bar.get("volume", 0))
                    )
                    ohlcv_bars.append(ohlcv_bar)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse bar: {e}")
                    continue
            
            if not ohlcv_bars:
                logger.warning(f"No valid bars parsed for {instrument.value}")
                return []
            
            logger.info(f"Fetched {len(ohlcv_bars)} bars for {instrument.value} {timeframe}")
            
            # Cache for 1 minute
            self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=1)
            self._market_data_cache[cache_key] = ohlcv_bars
            
            return ohlcv_bars
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}", exc_info=True)
            return []
    
    async def get_current_price(self, instrument: Instrument) -> Dict:
        """
        Get current bid/ask price for instrument.
        
        Args:
            instrument: Trading instrument
        
        Returns:
            Dict with bid, ask, spread
        """
        try:
            # This would query MT5 for current price
            # For now, return placeholder
            return {
                "symbol": instrument.value,
                "bid": 0.0,
                "ask": 0.0,
                "spread": 0.0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return {
                "symbol": instrument.value,
                "bid": 0.0,
                "ask": 0.0,
                "spread": 999.0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_current_spread(self, instrument: Instrument) -> float:
        """
        Get current spread for instrument.
        
        Args:
            instrument: Trading instrument
        
        Returns:
            Current spread in points
        """
        try:
            return await self.bridge.get_current_spread(instrument.value)
        except Exception as e:
            logger.error(f"Error getting spread: {e}")
            return 999.0
    
    async def place_order(self, order: MT5OrderRequest) -> MT5OrderResponse:
        """
        Place order via MT5.
        
        Args:
            order: Order request
        
        Returns:
            Order response with ticket number
        """
        try:
            # Ensure connection
            if not await self.is_connected():
                logger.error("Cannot place order - MT5 not connected")
                return MT5OrderResponse(
                    success=False,
                    error="MT5 not connected"
                )
            
            # Place order via bridge
            response = await self.bridge.place_order(order)
            
            if response.success:
                logger.info(f"Order placed successfully: ticket={response.ticket}")
            else:
                logger.error(f"Order placement failed: {response.error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return MT5OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def get_positions(self) -> List[MT5Position]:
        """
        Get all open positions.
        
        Returns:
            List of open positions
        """
        try:
            return await self.bridge.get_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def close_position(self, ticket: int, lot_size: float, symbol: str) -> bool:
        """
        Close position (full or partial).
        
        Args:
            ticket: Position ticket
            lot_size: Lot size to close
            symbol: Symbol
        
        Returns:
            True if closed successfully
        """
        try:
            return await self.bridge.close_partial(ticket, lot_size, symbol)
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    async def modify_stop_loss(self, ticket: int, sl_price: float) -> bool:
        """
        Modify stop loss for position.
        
        Args:
            ticket: Position ticket
            sl_price: New stop loss price
        
        Returns:
            True if modified successfully
        """
        try:
            return await self.bridge.modify_sl(ticket, sl_price)
        except Exception as e:
            logger.error(f"Error modifying stop loss: {e}")
            return False
    
    def clear_cache(self):
        """Clear market data cache."""
        self._market_data_cache.clear()
        self._cache_expiry.clear()
        logger.info("Market data cache cleared")


# Global singleton instance
mt5_manager = MT5Manager()
