"""
EA Polling Router
Exposes endpoints for the MQL5 Expert Advisor to poll commands and report results.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from backend.config import settings
from backend.routers.mt5_bridge import mt5_bridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mt5", tags=["MT5 EA Integration"])

AUTH_HEADER = "X-MT5-Secret"

def verify_secret(x_mt5_secret: str = Header(None)):
    if x_mt5_secret != settings.mt5_node_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid secret"
        )


class EAResult(BaseModel):
    command_id: str
    status: str
    message: str = ""


@router.get("/poll")
async def poll_commands(x_mt5_secret: str = Header(None)) -> List[Dict[str, Any]]:
    """
    Endpoint for the MQL5 EA to poll for pending commands.
    Pops all commands from the queue and returns them to the EA.
    """
    verify_secret(x_mt5_secret)
    
    # Grab all queued commands and clear the queue
    commands = list(mt5_bridge.command_queue)
    mt5_bridge.command_queue.clear()
    
    if commands:
        logger.info(f"EA polled {len(commands)} commands")
        
    return commands


@router.post("/result")
async def report_result(result: EAResult, x_mt5_secret: str = Header(None)):
    """
    Endpoint for the MQL5 EA to report the result of an executed command.
    Resolves the pending asyncio Future in the bridge manager.
    """
    verify_secret(x_mt5_secret)
    
    cmd_id = result.command_id
    future = mt5_bridge.pending_results.get(cmd_id)
    
    if future and not future.done():
        # EA reports "success" string
        is_success = result.status.lower() == "success"
        
        # If it's a place_order response, the EA sends the ticket in the message field
        ticket = result.message if is_success and result.message.isdigit() else 0
        
        future.set_result({
            "success": is_success,
            "message": result.message,
            "ticket": ticket
        })
        
        # Remove from pending dictionary
        mt5_bridge.pending_results.pop(cmd_id, None)
        logger.info(f"EA reported result for command {cmd_id}: {result.status}")
        
    return {"status": "ok"}
