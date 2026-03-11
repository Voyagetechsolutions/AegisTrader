"""
Strategy Engine API Router

Provides endpoints for:
- Strategy engine status and health
- Recent signals
- Configuration updates
- Session management
- Bot mode compatibility (analyze, trade, swing)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from uuid import UUID

from backend.database import get_db
from backend.strategy.engine import strategy_engine
from backend.strategy.session_manager import SessionManager
from backend.strategy.signal_generator import signal_generator
from backend.strategy.risk_integration import risk_integration
from backend.strategy.config import strategy_settings
from backend.strategy.models import SignalGrade


router = APIRouter(prefix="/strategy", tags=["Strategy Engine"])


# ── Schemas ───────────────────────────────────────────────────────────────

class StrategyStatusResponse(BaseModel):
    engine_running: bool
    session_active: bool
    active_session: Optional[str]
    session_override: bool
    risk_status: Dict[str, Any]
    recent_signals_count: int


class SignalResponse(BaseModel):
    timestamp: str
    setup_type: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    confluence_score: float
    grade: str


class ConfigUpdateRequest(BaseModel):
    session_override: Optional[bool] = None
    min_grade: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/status", response_model=StrategyStatusResponse)
async def get_strategy_status(db: AsyncSession = Depends(get_db)):
    """Get current strategy engine status."""
    
    # Get risk status
    risk_status = await risk_integration.get_current_status(db=db)
    
    # Get recent signals
    recent_signals = await signal_generator.get_recent_signals(count=10)
    
    # Create session manager instance
    session_mgr = SessionManager(strategy_settings.timezone)
    
    return StrategyStatusResponse(
        engine_running=strategy_engine.running if hasattr(strategy_engine, 'running') else False,
        session_active=session_mgr.is_within_session(),
        active_session=session_mgr.get_active_session(),
        session_override=session_mgr.is_override_enabled(),
        risk_status=risk_status,
        recent_signals_count=len(recent_signals),
    )


@router.get("/signals", response_model=List[SignalResponse])
async def get_recent_signals(count: int = 10):
    """Get recent trading signals."""
    
    signals = await signal_generator.get_recent_signals(count=count)
    
    return [
        SignalResponse(
            timestamp=s.timestamp.isoformat(),
            setup_type=s.setup_type.value,
            direction=s.direction.value,
            entry=s.entry,
            stop_loss=s.stop_loss,
            take_profit=s.take_profit,
            confluence_score=s.confluence_score,
            grade=s.grade.value,
        )
        for s in signals
    ]


@router.get("/session")
async def get_session_status():
    """Get detailed session information."""
    session_mgr = SessionManager(strategy_settings.timezone)
    return session_mgr.get_session_status()


@router.post("/config")
async def update_config(config: ConfigUpdateRequest):
    """Update strategy engine configuration."""
    
    updated = {}
    session_mgr = SessionManager(strategy_settings.timezone)
    
    if config.session_override is not None:
        if config.session_override:
            session_mgr.enable_override()
            await risk_integration.enable_session_override()
        else:
            session_mgr.disable_override()
            await risk_integration.disable_session_override()
        updated["session_override"] = config.session_override
    
    if config.min_grade is not None:
        try:
            grade = SignalGrade(config.min_grade)
            await risk_integration.set_minimum_grade(grade)
            updated["min_grade"] = config.min_grade
        except ValueError:
            raise HTTPException(400, f"Invalid grade: {config.min_grade}")
    
    return {"status": "ok", "updated": updated}


@router.get("/health")
async def strategy_health():
    """Strategy engine health check."""
    
    session_mgr = SessionManager(strategy_settings.timezone)
    session_active = session_mgr.is_within_session()
    
    return {
        "status": "healthy",
        "session_active": session_active,
        "components": {
            "session_manager": "ok",
            "signal_generator": "ok",
            "risk_integration": "ok",
        }
    }
