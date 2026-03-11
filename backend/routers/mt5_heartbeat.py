"""
MT5 Heartbeat Router
Receives heartbeat messages from MT5 bridge and handles command polling
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging
from typing import Dict, Any, List

from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mt5", tags=["MT5"])

# Store last heartbeat time
last_heartbeat = None
last_heartbeat_data = None

# Command queue for EA to poll (imported from bridge)
from backend.routers.mt5_bridge import mt5_bridge


class HeartbeatData(BaseModel):
    symbol: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    positions: int
    server_time: str
    bid: float
    ask: float


@router.post("/heartbeat")
async def receive_heartbeat(
    data: HeartbeatData,
    x_mt5_secret: str = Header(None)
):
    """
    Receive heartbeat from MT5 bridge.
    
    The bridge sends this every 30 seconds with account status.
    """
    global last_heartbeat, last_heartbeat_data
    
    logger.info(f"Heartbeat request received - Secret present: {x_mt5_secret is not None}")
    
    # Verify secret
    if x_mt5_secret != settings.mt5_node_secret:
        logger.warning(f"Invalid MT5 secret - Received: '{x_mt5_secret}' (len={len(x_mt5_secret) if x_mt5_secret else 0}), Expected: '{settings.mt5_node_secret}' (len={len(settings.mt5_node_secret)})")
        raise HTTPException(status_code=401, detail="Invalid secret")
    
    # Update last heartbeat
    last_heartbeat = datetime.utcnow()
    last_heartbeat_data = data.dict()
    
    logger.info(f"MT5 Heartbeat: Balance=${data.balance:.2f}, Positions={data.positions}")
    
    return {
        "ok": True,
        "message": "Heartbeat received",
        "timestamp": last_heartbeat.isoformat()
    }


@router.get("/heartbeat/status")
async def get_heartbeat_status():
    """
    Check if MT5 is connected (has sent heartbeat recently).
    """
    if last_heartbeat is None:
        return {
            "connected": False,
            "message": "No heartbeat received yet"
        }
    
    # Check if heartbeat is recent (within last 60 seconds)
    seconds_since = (datetime.utcnow() - last_heartbeat).total_seconds()
    connected = seconds_since < 60
    
    return {
        "connected": connected,
        "last_heartbeat": last_heartbeat.isoformat(),
        "seconds_since": seconds_since,
        "data": last_heartbeat_data
    }


@router.get("/price/{symbol}")
async def get_current_price(symbol: str):
    """
    Get current bid/ask price for a symbol from the last heartbeat.
    """
    if last_heartbeat_data is None:
        raise HTTPException(status_code=503, detail="No price data available - MT5 not connected")
    
    # Check if data is recent (within last 60 seconds)
    seconds_since = (datetime.utcnow() - last_heartbeat).total_seconds()
    if seconds_since > 60:
        raise HTTPException(status_code=503, detail="Price data stale - MT5 connection lost")
    
    # Check if symbol matches
    if last_heartbeat_data.get("symbol") != symbol:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not available. Current symbol: {last_heartbeat_data.get('symbol')}")
    
    return {
        "symbol": last_heartbeat_data.get("symbol"),
        "bid": last_heartbeat_data.get("bid"),
        "ask": last_heartbeat_data.get("ask"),
        "spread": last_heartbeat_data.get("ask", 0) - last_heartbeat_data.get("bid", 0),
        "timestamp": last_heartbeat.isoformat(),
        "seconds_ago": seconds_since
    }


# ---------------------------------------------------------------------------
# Command Polling Endpoints (for EA v2)
# ---------------------------------------------------------------------------

class CommandResultData(BaseModel):
    """Result from EA command execution."""
    id: str
    success: bool
    data: Dict[str, Any] = {}
    error: str = ""


@router.post("/poll")
async def poll_commands(x_mt5_secret: str = Header(None)):
    """
    EA polls this endpoint to get pending commands.
    
    Returns list of commands to execute.
    """
    # Verify secret
    if x_mt5_secret != settings.mt5_node_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")
    
    # Get commands from bridge queue
    commands = []
    
    # Return up to 10 commands at a time
    while len(commands) < 10 and len(mt5_bridge.command_queue) > 0:
        cmd = mt5_bridge.command_queue.pop(0)
        commands.append(cmd)
    
    if commands:
        logger.debug(f"Sending {len(commands)} commands to EA")
    
    return {
        "ok": True,
        "commands": commands,
        "count": len(commands)
    }


@router.post("/result")
async def receive_command_result(
    result: CommandResultData,
    x_mt5_secret: str = Header(None)
):
    """
    EA sends command execution results here.
    
    This resolves the pending future waiting for the result.
    """
    # Verify secret
    if x_mt5_secret != settings.mt5_node_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")
    
    cmd_id = result.id
    
    logger.info(f"Received result for command {cmd_id}: success={result.success}")
    
    # Find pending future and resolve it
    future = mt5_bridge.pending_results.get(cmd_id)
    
    if future and not future.done():
        # Resolve the future with the result
        result_dict = {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            **result.data  # Flatten data into result
        }
        
        future.set_result(result_dict)
        logger.debug(f"Resolved future for command {cmd_id}")
    else:
        logger.warning(f"No pending future found for command {cmd_id}")
    
    # Clean up
    mt5_bridge.pending_results.pop(cmd_id, None)
    
    return {
        "ok": True,
        "message": "Result received"
    }
