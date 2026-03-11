"""
Trading Loop Router - API endpoints and WebSocket for trading loop.

Provides:
- Trading loop control (start/stop/status)
- WebSocket for real-time updates
- Settings management
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import logging

from backend.services.trading_loop import trading_loop_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading-loop", tags=["Trading Loop"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class TradingLoopStatusResponse(BaseModel):
    """Trading loop status."""
    running: bool
    loop_count: int
    signals_generated: int
    trades_executed: int
    last_run: str | None
    websocket_connections: int
    enabled_instruments: list[str]
    settings: dict
    recent_errors: list[dict]


class UpdateSettingsRequest(BaseModel):
    """Update trading loop settings."""
    core_strategy_enabled: bool | None = None
    quick_scalp_enabled: bool | None = None
    us30_enabled: bool | None = None
    nas100_enabled: bool | None = None
    xauusd_enabled: bool | None = None


# ---------------------------------------------------------------------------
# Trading Loop Control Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=TradingLoopStatusResponse, summary="Get trading loop status")
async def get_trading_loop_status():
    """
    Get current trading loop status.
    
    Returns:
    - Running state
    - Loop statistics
    - Enabled instruments
    - Settings
    - Recent errors
    """
    try:
        status = trading_loop_service.get_status()
        return TradingLoopStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting trading loop status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", summary="Start trading loop")
async def start_trading_loop():
    """
    Start the trading loop.
    
    Begins continuous market analysis and signal generation.
    """
    try:
        if trading_loop_service.running:
            return {
                "ok": False,
                "message": "Trading loop already running",
                "status": "running"
            }
        
        # Start loop in background
        import asyncio
        asyncio.create_task(trading_loop_service.start())
        
        # Give it a moment to start
        await asyncio.sleep(0.5)
        
        return {
            "ok": True,
            "message": "Trading loop started",
            "status": "running"
        }
    except Exception as e:
        logger.error(f"Error starting trading loop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", summary="Stop trading loop")
async def stop_trading_loop():
    """
    Stop the trading loop.
    
    Stops market analysis and signal generation.
    """
    try:
        if not trading_loop_service.running:
            return {
                "ok": False,
                "message": "Trading loop not running",
                "status": "stopped"
            }
        
        await trading_loop_service.stop()
        
        return {
            "ok": True,
            "message": "Trading loop stopped",
            "status": "stopped"
        }
    except Exception as e:
        logger.error(f"Error stopping trading loop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings", summary="Update trading loop settings")
async def update_trading_loop_settings(request: UpdateSettingsRequest):
    """
    Update trading loop settings.
    
    Args:
        request: Settings to update
    
    Returns:
        Updated settings
    """
    try:
        # Build settings dict from request
        settings = {}
        if request.core_strategy_enabled is not None:
            settings["core_strategy_enabled"] = request.core_strategy_enabled
        if request.quick_scalp_enabled is not None:
            settings["quick_scalp_enabled"] = request.quick_scalp_enabled
        if request.us30_enabled is not None:
            settings["us30_enabled"] = request.us30_enabled
        if request.nas100_enabled is not None:
            settings["nas100_enabled"] = request.nas100_enabled
        if request.xauusd_enabled is not None:
            settings["xauusd_enabled"] = request.xauusd_enabled
        
        # Update settings
        trading_loop_service.update_settings(settings)
        
        return {
            "ok": True,
            "message": "Settings updated",
            "settings": trading_loop_service.engine_settings
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time trading updates.
    
    Broadcasts:
    - Signal generation events
    - Trade execution events
    - Loop completion events
    - News blackout events
    - Error events
    """
    await websocket.accept()
    trading_loop_service.add_websocket(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected",
            "status": trading_loop_service.get_status()
        })
        
        # Keep connection alive
        while True:
            # Wait for messages from client (ping/pong)
            try:
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Handle status request
                elif data == "status":
                    await websocket.send_json({
                        "type": "status",
                        "status": trading_loop_service.get_status()
                    })
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        trading_loop_service.remove_websocket(websocket)
        logger.info("WebSocket disconnected")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/health", summary="Trading loop health check")
async def trading_loop_health():
    """
    Quick health check for trading loop.
    
    Returns:
        Health status
    """
    try:
        status = trading_loop_service.get_status()
        
        return {
            "ok": True,
            "service": "Trading Loop",
            "status": "healthy" if status["running"] else "stopped",
            "loop_count": status["loop_count"],
            "signals_generated": status["signals_generated"],
            "trades_executed": status["trades_executed"],
        }
    except Exception as e:
        logger.error(f"Trading loop health check failed: {e}")
        return {
            "ok": False,
            "service": "Trading Loop",
            "status": "error",
            "message": str(e)
        }
