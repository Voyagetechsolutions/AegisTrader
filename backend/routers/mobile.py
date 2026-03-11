"""
Mobile API endpoints for the Aegis Trader mobile app.
Provides bot status, signals, trades, and control endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/mobile", tags=["Mobile"])


# Request/Response Models
class ModeRequest(BaseModel):
    mode: str  # analyze, trade, swing


class SafeModeRequest(BaseModel):
    enabled: bool


# Mock data for now - replace with real data later
@router.get("/status")
async def get_status():
    """Get bot status and system health."""
    # Try to get real status from strategy engine
    try:
        from backend.strategy.engine import strategy_engine
        engine_status = await strategy_engine.get_status()
        return {
            "mode": "analyze",
            "bot_state": "running" if engine_status.get("running") else "paused",
            "account_mode": "demo",
            "today_pnl": 0.0,
            "daily_drawdown_pct": 0.0,
            "trades_today": 0,
            "losses_today": 0,
            "session_name": "Outside Trading Hours",
            "backend_online": True,
            "mt5_online": engine_status.get("components_initialized", False),
            "last_signal_time": None,
            "last_trade_time": None,
            "balance": 10000.0,
            "open_positions": 0,
        }
    except Exception:
        # Fallback if strategy engine not running
        return {
            "mode": "analyze",
            "bot_state": "running",
            "account_mode": "demo",
            "today_pnl": 0.0,
            "daily_drawdown_pct": 0.0,
            "trades_today": 0,
            "losses_today": 0,
            "session_name": "Outside Trading Hours",
            "backend_online": True,
            "mt5_online": False,
            "last_signal_time": None,
            "last_trade_time": None,
            "balance": 10000.0,
            "open_positions": 0,
        }


@router.post("/mode")
async def set_mode(request: ModeRequest):
    """Switch bot mode."""
    if request.mode not in ["analyze", "trade", "swing"]:
        raise HTTPException(400, "Invalid mode")
    
    return {"success": True, "mode": request.mode}


@router.post("/safe-mode")
async def set_safe_mode(request: SafeModeRequest):
    """Enable/disable safe mode."""
    return {"success": True, "safe_mode": request.enabled}


@router.get("/signals")
async def get_signals():
    """Get recent signals."""
    return []


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: str):
    """Get signal details."""
    raise HTTPException(404, "Signal not found")


@router.get("/trades/open")
async def get_open_trades():
    """Get open positions."""
    return []


@router.get("/trades/history")
async def get_trade_history():
    """Get trade history."""
    return []


@router.post("/trades/{trade_id}/close")
async def close_trade(trade_id: str):
    """Close a specific trade."""
    return {"success": True, "trade_id": trade_id}


@router.post("/trades/close-all")
async def close_all_trades():
    """Close all open trades."""
    return {"success": True, "closed": 0}


@router.get("/swing/pending")
async def get_pending_swing():
    """Get pending swing trade approvals."""
    return []


@router.post("/swing/{swing_id}/approve")
async def approve_swing(swing_id: str):
    """Approve a swing trade."""
    return {"success": True, "swing_id": swing_id}


@router.post("/swing/{swing_id}/reject")
async def reject_swing(swing_id: str):
    """Reject a swing trade."""
    return {"success": True, "swing_id": swing_id}


@router.get("/weekly-overview")
async def get_weekly_overview():
    """Get weekly market overview."""
    return {
        "weekly_bias": "Bullish",
        "daily_bias": "Bullish",
        "h4_bias": "Bullish",
        "h1_bias": "Neutral",
        "m15_bias": "Bullish",
        "m5_bias": "Bullish",
        "m1_bias": "Bullish",
        "bullish_scenario": "System is collecting data in ANALYZE mode. Check back after 1 week for detailed analysis.",
        "bearish_scenario": "System is collecting data in ANALYZE mode. Check back after 1 week for detailed analysis.",
        "key_levels": [48000, 47500, 47000],
        "major_news": [],
    }


@router.get("/risk")
async def get_risk_settings():
    """Get risk settings."""
    return {
        "max_daily_trades": 2,
        "max_daily_losses": 2,
        "max_daily_drawdown_pct": 2.0,
        "max_spread_points": 5,
    }


@router.post("/risk")
async def update_risk_settings(settings: dict):
    """Update risk settings."""
    return {"success": True, "settings": settings}
