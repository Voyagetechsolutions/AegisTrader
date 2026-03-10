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

    async def get_account_balance(self) -> float:
        """Get current account balance (stubbed for now)."""
        return 1000.0  


# Singleton instance used throughout the backend
mt5_bridge = MT5BridgeManager()
