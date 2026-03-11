"""
MT5 Bridge Manager
Replaces the outbound HTTP client with an in-memory command queue.
The native MQL5 Expert Advisor polls this queue to execute trades.
"""

from __future__ import annotations
import logging
import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from backend.schemas.schemas import (
    MT5OrderRequest, MT5OrderResponse,
    MT5CloseRequest, MT5ModifyRequest, MT5Position,
)

logger = logging.getLogger(__name__)


class MT5BridgeManager:
    """
    Manages an in-memory queue of commands for the MQL5 EA to poll.
    Commands are queued until polled, and results are awaited.
    """

    def __init__(self):
        self.command_queue: list[Dict[str, Any]] = []
        # Store pending futures waiting for execution results
        self.pending_results: Dict[str, asyncio.Future] = {}
        # Store latest synced positions
        self.cached_positions: list[MT5Position] = []
        # Connection health tracking
        self._last_health_check: Optional[datetime] = None
        self._connection_healthy = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def health_check(self) -> bool:
        """Check if MT5 connection is healthy."""
        try:
            # Simple ping - check if we can get positions
            positions = await self.get_positions()
            self._connection_healthy = True
            self._last_health_check = datetime.now()
            self._reconnect_attempts = 0
            return True
        except Exception as e:
            logger.error(f"MT5 health check failed: {e}")
            self._connection_healthy = False
            return False

    async def ensure_connection(self) -> bool:
        """Ensure MT5 connection is active, reconnect if needed."""
        if self._connection_healthy:
            # Check if health check is stale (>60s)
            if self._last_health_check:
                age = (datetime.now() - self._last_health_check).total_seconds()
                if age < 60:
                    return True
        
        # Perform health check
        if await self.health_check():
            return True
        
        # Health check failed - attempt reconnection
        logger.warning("MT5 connection unhealthy - attempting reconnection")
        return await self.reconnect()

    async def reconnect(self) -> bool:
        """Attempt to reconnect to MT5."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.critical(f"MT5 reconnection failed after {self._max_reconnect_attempts} attempts")
            return False
        
        self._reconnect_attempts += 1
        logger.info(f"MT5 reconnection attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}")
        
        try:
            # Wait before retry (exponential backoff)
            await asyncio.sleep(2 ** self._reconnect_attempts)
            
            # Try health check again
            if await self.health_check():
                logger.info("MT5 reconnection successful")
                # Sync positions after reconnection
                await self.sync_positions_from_mt5()
                return True
            
            return False
        except Exception as e:
            logger.error(f"MT5 reconnection error: {e}")
            return False

    async def sync_positions_from_mt5(self):
        """
        Sync positions from MT5 after reconnection.
        This ensures we don't lose track of open trades.
        """
        try:
            logger.info("Syncing positions from MT5...")
            # This would query MT5 for actual open positions
            # and update cached_positions
            # Implementation depends on EA communication protocol
            pass
        except Exception as e:
            logger.error(f"Position sync failed: {e}")

    def _enqueue_command(self, action: str, payload: dict) -> str:
        cmd_id = str(uuid4())
        command = {
            "id": cmd_id,
            "action": action,
            **payload
        }
        self.command_queue.append(command)
        
        # Create a future to await the result
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_results[cmd_id] = future
        return cmd_id

    async def _await_result(self, cmd_id: str, timeout: int = 15) -> Dict[str, Any]:
        """Await the result reported back by the EA."""
        future = self.pending_results.get(cmd_id)
        if not future:
            return {"success": False, "error": "Command not found"}

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for EA result for command {cmd_id}")
            self.pending_results.pop(cmd_id, None)
            return {"success": False, "error": "Timeout waiting for MT5 EA"}
        except Exception as e:
            logger.error(f"Error waiting for EA result: {e}")
            self.pending_results.pop(cmd_id, None)
            return {"success": False, "error": str(e)}

    # --- Methods called by the backend Trade Manager ---

    async def place_order(self, order: MT5OrderRequest) -> MT5OrderResponse:
        """Queue an order and wait for the EA to execute it."""
        # Ensure connection before placing order
        if not await self.ensure_connection():
            return MT5OrderResponse(success=False, error="MT5 connection unavailable")
        
        try:
            cmd_id = self._enqueue_command("place_order", order.model_dump())
            result = await self._await_result(cmd_id)
            
            if result.get("success"):
                return MT5OrderResponse(
                    success=True, 
                    ticket=int(result.get("ticket", 0)),
                    actual_price=order.entry_price, # EA doesn't easily return actual fill price in simple JSON, use request entry
                    slippage=0.0
                )
            else:
                return MT5OrderResponse(success=False, error=result.get("message", "Unknown error"))
        except Exception as e:
            logger.error(f"MT5 place_order queue failed: {e}")
            # Attempt reconnection on failure
            await self.reconnect()
            return MT5OrderResponse(success=False, error=str(e))

    async def close_partial(self, ticket: int, lot_size: float, symbol: str) -> bool:
        """Queue a partial close and wait for the EA."""
        try:
            cmd_id = self._enqueue_command("close_partial", {
                "ticket": ticket,
                "lot_size": lot_size,
                "symbol": symbol
            })
            result = await self._await_result(cmd_id)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"MT5 close_partial queue failed: {e}")
            return False

    async def modify_sl(self, ticket: int, sl_price: float) -> bool:
        """Queue a stop loss modification and wait for the EA."""
        try:
            cmd_id = self._enqueue_command("modify_sl", {
                "ticket": ticket,
                "sl_price": sl_price
            })
            result = await self._await_result(cmd_id)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"MT5 modify_sl queue failed: {e}")
            return False

    async def get_positions(self) -> list[MT5Position]:
        """Return cached positions (the EA will sync these periodically)."""
        return self.cached_positions

    async def get_position_size(self, ticket: int) -> Optional[float]:
        """Get actual position size for a ticket (handles partial fills)."""
        try:
            positions = await self.get_positions()
            for pos in positions:
                if pos.ticket == ticket:
                    return pos.volume
            return None
        except Exception as e:
            logger.error(f"Error getting position size: {e}")
            return None

    async def get_account_balance(self) -> float:
        """Get current account balance from MT5 heartbeat."""
        from backend.routers.mt5_heartbeat import last_heartbeat_data
        import logging
        
        logger = logging.getLogger(__name__)
        
        if last_heartbeat_data:
            logger.info(f"Heartbeat data available: {last_heartbeat_data}")
            if 'balance' in last_heartbeat_data:
                balance = float(last_heartbeat_data['balance'])
                logger.info(f"Returning balance: {balance}")
                return balance
            else:
                logger.warning("Heartbeat data exists but no 'balance' field")
        else:
            logger.warning("No heartbeat data available yet")
        
        # Fallback if no heartbeat data available
        return 0.0
    
    async def get_current_spread(self, symbol: str) -> float:
        """Get current spread for symbol."""
        try:
            # This would query MT5 for current spread
            # For now, return a safe default
            return 2.0
        except Exception as e:
            logger.error(f"Error getting spread: {e}")
            return 999.0  # Return high value to trigger rejection on error
    
    async def request_historical_data(
        self,
        symbol: str,
        timeframe: str,
        bars: int
    ) -> Dict[str, Any]:
        """
        Request historical OHLCV data from MT5.
        
        Args:
            symbol: Trading symbol (US30, NAS100, XAUUSD)
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
            bars: Number of bars to fetch
        
        Returns:
            Dict with success flag and bars data
        """
        try:
            # Ensure connection before requesting data
            if not await self.ensure_connection():
                return {"success": False, "error": "MT5 connection unavailable"}
            
            cmd_id = self._enqueue_command("get_historical_data", {
                "symbol": symbol,
                "timeframe": timeframe,
                "bars": bars
            })
            
            result = await self._await_result(cmd_id, timeout=30)  # Longer timeout for data fetch
            
            if result.get("success"):
                return {
                    "success": True,
                    "bars": result.get("bars", []),
                    "symbol": symbol,
                    "timeframe": timeframe
                }
            else:
                logger.warning(f"Historical data request failed: {result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Failed to fetch historical data")
                }
                
        except Exception as e:
            logger.error(f"Error requesting historical data: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Singleton instance used throughout the backend
mt5_bridge = MT5BridgeManager()
