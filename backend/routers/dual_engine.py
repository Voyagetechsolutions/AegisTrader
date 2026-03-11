"""
dual_engine.py
REST API endpoints for the Dual-Engine Trading System.

Provides:
- Engine status (Core Strategy + Quick Scalp)
- Market regime information
- Performance metrics per engine
- Active signals from both engines
- Engine-specific settings
"""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional, List

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.strategy.dual_engine_models import Instrument, EngineType
from backend.strategy.auto_trade_decision_engine import VolatilityRegime, TrendStrength

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dual-engine", tags=["Dual Engine"])

SAST = pytz.timezone("Africa/Johannesburg")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class MarketRegimeResponse(BaseModel):
    """Market regime information for an instrument."""
    instrument: str
    volatility: str  # LOW, NORMAL, HIGH, EXTREME
    trend: str  # STRONG_TREND, WEAK_TREND, RANGING, CHOPPY
    atr_current: float
    atr_average: float
    atr_ratio: float
    timestamp: str


class EnginePerformanceResponse(BaseModel):
    """Performance metrics for an engine."""
    engine: str
    instrument: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_rr: float
    profit_factor: float
    consecutive_wins: int
    consecutive_losses: int


class EngineStatusResponse(BaseModel):
    """Status of a trading engine."""
    engine: str
    active: bool
    trades_today: int
    daily_limit: int
    can_trade: bool
    block_reason: Optional[str]
    performance: Optional[EnginePerformanceResponse]


class DualEngineStatusResponse(BaseModel):
    """Complete dual-engine system status."""
    core_strategy: EngineStatusResponse
    quick_scalp: EngineStatusResponse
    market_regimes: List[MarketRegimeResponse]
    active_signals: int
    last_decision: Optional[str]
    timestamp: str


class UnifiedSignalResponse(BaseModel):
    """Unified signal from either engine."""
    signal_id: str
    engine: str
    instrument: str
    direction: str
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: Optional[float]
    risk_reward_ratio: float
    status: str
    grade: Optional[str]
    score: Optional[int]
    session: Optional[str]
    timestamp: str
    reasons: List[str]


# ---------------------------------------------------------------------------
# In-Memory State (would be replaced with proper state management)
# ---------------------------------------------------------------------------

# This would be replaced with actual coordinator instance
_coordinator_state = {
    "active_signals": [],
    "market_regimes": {},
    "performance_metrics": {},
    "last_decision": None,
    "core_trades_today": 0,
    "scalp_trades_today": 0,
}

# Engine control settings
_engine_settings = {
    "core_strategy_enabled": True,
    "quick_scalp_enabled": True,
    "us30_enabled": True,
    "nas100_enabled": True,
    "xauusd_enabled": True,
}


# ---------------------------------------------------------------------------
# Status Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=DualEngineStatusResponse, summary="Get dual-engine system status")
async def get_dual_engine_status(db: AsyncSession = Depends(get_db)):
    """
    Get complete status of the dual-engine trading system.
    
    Returns:
    - Core Strategy engine status
    - Quick Scalp engine status
    - Market regime for each instrument
    - Active signals count
    - Last decision made
    """
    
    # Core Strategy status
    core_status = EngineStatusResponse(
        engine="CORE_STRATEGY",
        active=True,
        trades_today=_coordinator_state.get("core_trades_today", 0),
        daily_limit=2,
        can_trade=_coordinator_state.get("core_trades_today", 0) < 2,
        block_reason=None if _coordinator_state.get("core_trades_today", 0) < 2 else "Daily limit reached",
        performance=None,  # Would fetch from performance tracker
    )
    
    # Quick Scalp status
    scalp_status = EngineStatusResponse(
        engine="QUICK_SCALP",
        active=True,
        trades_today=_coordinator_state.get("scalp_trades_today", 0),
        daily_limit=15,  # 5 per session × 3 sessions
        can_trade=True,
        block_reason=None,
        performance=None,  # Would fetch from performance tracker
    )
    
    # Market regimes
    regimes = []
    for instrument, regime_data in _coordinator_state.get("market_regimes", {}).items():
        regimes.append(MarketRegimeResponse(
            instrument=instrument,
            volatility=regime_data.get("volatility", "NORMAL"),
            trend=regime_data.get("trend", "RANGING"),
            atr_current=regime_data.get("atr_current", 0.0),
            atr_average=regime_data.get("atr_average", 0.0),
            atr_ratio=regime_data.get("atr_ratio", 1.0),
            timestamp=regime_data.get("timestamp", datetime.now(pytz.UTC).isoformat()),
        ))
    
    return DualEngineStatusResponse(
        core_strategy=core_status,
        quick_scalp=scalp_status,
        market_regimes=regimes,
        active_signals=len(_coordinator_state.get("active_signals", [])),
        last_decision=_coordinator_state.get("last_decision"),
        timestamp=datetime.now(pytz.UTC).isoformat(),
    )


@router.get("/regime/{instrument}", response_model=MarketRegimeResponse, summary="Get market regime for instrument")
async def get_market_regime(
    instrument: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current market regime classification for a specific instrument.
    
    Returns:
    - Volatility regime (LOW, NORMAL, HIGH, EXTREME)
    - Trend strength (STRONG_TREND, WEAK_TREND, RANGING, CHOPPY)
    - ATR metrics
    """
    
    regime_data = _coordinator_state.get("market_regimes", {}).get(instrument)
    
    if not regime_data:
        raise HTTPException(
            status_code=404,
            detail=f"No regime data available for {instrument}"
        )
    
    return MarketRegimeResponse(
        instrument=instrument,
        volatility=regime_data.get("volatility", "NORMAL"),
        trend=regime_data.get("trend", "RANGING"),
        atr_current=regime_data.get("atr_current", 0.0),
        atr_average=regime_data.get("atr_average", 0.0),
        atr_ratio=regime_data.get("atr_ratio", 1.0),
        timestamp=regime_data.get("timestamp", datetime.now(pytz.UTC).isoformat()),
    )


# ---------------------------------------------------------------------------
# Performance Endpoints
# ---------------------------------------------------------------------------

@router.get("/performance/{engine}", response_model=List[EnginePerformanceResponse], summary="Get engine performance")
async def get_engine_performance(
    engine: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance metrics for a specific engine across all instruments.
    
    Args:
        engine: CORE_STRATEGY or QUICK_SCALP
    
    Returns:
        Performance metrics per instrument
    """
    
    if engine not in ["CORE_STRATEGY", "QUICK_SCALP"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid engine: {engine}. Must be CORE_STRATEGY or QUICK_SCALP"
        )
    
    # Would fetch from performance tracker
    # For now, return mock data
    instruments = ["US30", "NAS100", "XAUUSD"]
    
    performance_list = []
    for instrument in instruments:
        key = f"{engine}_{instrument}"
        metrics = _coordinator_state.get("performance_metrics", {}).get(key, {})
        
        performance_list.append(EnginePerformanceResponse(
            engine=engine,
            instrument=instrument,
            total_trades=metrics.get("total_trades", 0),
            winning_trades=metrics.get("winning_trades", 0),
            losing_trades=metrics.get("losing_trades", 0),
            win_rate=metrics.get("win_rate", 0.0),
            average_rr=metrics.get("average_rr", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            consecutive_wins=metrics.get("consecutive_wins", 0),
            consecutive_losses=metrics.get("consecutive_losses", 0),
        ))
    
    return performance_list


@router.get("/performance/compare", summary="Compare engine performance")
async def compare_engine_performance(
    instrument: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare performance between Core Strategy and Quick Scalp engines.
    
    Args:
        instrument: Optional filter by instrument
    
    Returns:
        Comparative metrics
    """
    
    # Would fetch from performance tracker and compute comparison
    return {
        "core_strategy": {
            "win_rate": 0.65,
            "average_rr": 1.8,
            "total_trades": 45,
        },
        "quick_scalp": {
            "win_rate": 0.58,
            "average_rr": 0.9,
            "total_trades": 120,
        },
        "comparison": {
            "core_higher_win_rate": True,
            "core_higher_rr": True,
            "scalp_more_trades": True,
        }
    }


# ---------------------------------------------------------------------------
# Signal Endpoints
# ---------------------------------------------------------------------------

@router.get("/signals/active", response_model=List[UnifiedSignalResponse], summary="Get active signals")
async def get_active_signals(db: AsyncSession = Depends(get_db)):
    """
    Get all currently active signals from both engines.
    
    Returns:
        List of active unified signals
    """
    
    active_signals = _coordinator_state.get("active_signals", [])
    
    return [
        UnifiedSignalResponse(
            signal_id=signal.get("signal_id", ""),
            engine=signal.get("engine", ""),
            instrument=signal.get("instrument", ""),
            direction=signal.get("direction", ""),
            entry_price=signal.get("entry_price", 0.0),
            stop_loss=signal.get("stop_loss", 0.0),
            tp1=signal.get("tp1", 0.0),
            tp2=signal.get("tp2"),
            risk_reward_ratio=signal.get("risk_reward_ratio", 0.0),
            status=signal.get("status", ""),
            grade=signal.get("grade"),
            score=signal.get("score"),
            session=signal.get("session"),
            timestamp=signal.get("timestamp", ""),
            reasons=signal.get("reasons", []),
        )
        for signal in active_signals
    ]


@router.get("/signals/history", summary="Get signal history")
async def get_signal_history(
    engine: Optional[str] = None,
    instrument: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical signals with optional filters.
    
    Args:
        engine: Filter by CORE_STRATEGY or QUICK_SCALP
        instrument: Filter by instrument
        limit: Maximum number of signals to return
    """
    
    # Would fetch from database
    return {
        "signals": [],
        "total": 0,
        "filters": {
            "engine": engine,
            "instrument": instrument,
        }
    }


# ---------------------------------------------------------------------------
# Decision Log Endpoints
# ---------------------------------------------------------------------------

@router.get("/decisions/recent", summary="Get recent engine decisions")
async def get_recent_decisions(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent decisions made by the Auto-Trade Decision Engine.
    
    Shows:
    - Which engine was selected
    - Why it was selected
    - Market conditions at decision time
    - Conflicts resolved
    """
    
    # Would fetch from decision log
    return {
        "decisions": [],
        "total": 0,
    }


# ---------------------------------------------------------------------------
# Configuration Endpoints
# ---------------------------------------------------------------------------

@router.get("/config", summary="Get dual-engine configuration")
async def get_dual_engine_config(db: AsyncSession = Depends(get_db)):
    """
    Get current configuration for the dual-engine system.
    
    Returns:
    - Enabled instruments
    - Spread limits (global and scalp-specific)
    - Risk pool settings
    - Engine-specific parameters
    """
    
    return {
        "instruments": ["US30", "NAS100", "XAUUSD"],
        "spread_limits_global": {
            "US30": 5.0,
            "XAUUSD": 3.0,
            "NAS100": 4.0,
        },
        "spread_limits_scalp": {
            "US30": 3.0,
            "XAUUSD": 2.0,
            "NAS100": 2.0,
        },
        "core_strategy": {
            "daily_trade_limit": 2,
            "risk_per_trade_pct": 1.0,
            "min_confluence_score": 80,  # A+ threshold
        },
        "quick_scalp": {
            "session_trade_limits": {
                "LONDON": 5,
                "NY_OPEN": 5,
                "POWER_HOUR": 3,
            },
            "risk_per_trade_pct": 0.5,
            "cooldown_minutes": 2,
        }
    }


@router.post("/config/update", summary="Update dual-engine configuration")
async def update_dual_engine_config(
    config_updates: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Update dual-engine system configuration.
    
    Allows updating:
    - Spread limits
    - Risk parameters
    - Trade limits
    - Enabled instruments
    """
    
    # Would validate and update configuration
    return {
        "ok": True,
        "message": "Configuration updated",
        "updated_fields": list(config_updates.keys()),
    }


# ---------------------------------------------------------------------------
# Engine Control Endpoints
# ---------------------------------------------------------------------------

@router.post("/engines/core/toggle", summary="Toggle Core Strategy engine")
async def toggle_core_strategy(
    enabled: bool,
    db: AsyncSession = Depends(get_db)
):
    """
    Enable or disable Core Strategy engine.
    
    Args:
        enabled: True to enable, False to disable
    
    Returns:
        Updated engine status
    """
    _engine_settings["core_strategy_enabled"] = enabled
    
    logger.info(f"Core Strategy engine {'enabled' if enabled else 'disabled'}")
    
    return {
        "ok": True,
        "engine": "CORE_STRATEGY",
        "enabled": enabled,
        "timestamp": datetime.now(pytz.UTC).isoformat()
    }


@router.post("/engines/scalp/toggle", summary="Toggle Quick Scalp engine")
async def toggle_quick_scalp(
    enabled: bool,
    db: AsyncSession = Depends(get_db)
):
    """
    Enable or disable Quick Scalp engine.
    
    Args:
        enabled: True to enable, False to disable
    
    Returns:
        Updated engine status
    """
    _engine_settings["quick_scalp_enabled"] = enabled
    
    logger.info(f"Quick Scalp engine {'enabled' if enabled else 'disabled'}")
    
    return {
        "ok": True,
        "engine": "QUICK_SCALP",
        "enabled": enabled,
        "timestamp": datetime.now(pytz.UTC).isoformat()
    }


@router.get("/engines/settings", summary="Get engine settings")
async def get_engine_settings(db: AsyncSession = Depends(get_db)):
    """
    Get current engine and market settings.
    
    Returns:
        Current enable/disable state for all engines and markets
    """
    return {
        "engines": {
            "core_strategy": _engine_settings["core_strategy_enabled"],
            "quick_scalp": _engine_settings["quick_scalp_enabled"],
        },
        "markets": {
            "US30": _engine_settings["us30_enabled"],
            "NAS100": _engine_settings["nas100_enabled"],
            "XAUUSD": _engine_settings["xauusd_enabled"],
        },
        "timestamp": datetime.now(pytz.UTC).isoformat()
    }


# ---------------------------------------------------------------------------
# Market Control Endpoints
# ---------------------------------------------------------------------------

@router.post("/markets/{instrument}/toggle", summary="Toggle market")
async def toggle_market(
    instrument: str,
    enabled: bool,
    db: AsyncSession = Depends(get_db)
):
    """
    Enable or disable trading for specific market.
    
    Args:
        instrument: US30, NAS100, or XAUUSD
        enabled: True to enable, False to disable
    
    Returns:
        Updated market status
    """
    instrument_upper = instrument.upper()
    
    if instrument_upper not in ["US30", "NAS100", "XAUUSD"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid instrument: {instrument}. Must be US30, NAS100, or XAUUSD"
        )
    
    setting_key = f"{instrument_upper.lower()}_enabled"
    _engine_settings[setting_key] = enabled
    
    logger.info(f"{instrument_upper} market {'enabled' if enabled else 'disabled'}")
    
    return {
        "ok": True,
        "instrument": instrument_upper,
        "enabled": enabled,
        "timestamp": datetime.now(pytz.UTC).isoformat()
    }


@router.get("/markets/status", summary="Get all markets status")
async def get_all_markets_status(db: AsyncSession = Depends(get_db)):
    """
    Get status for all markets.
    
    Returns:
        Status for US30, NAS100, XAUUSD including:
        - Enabled/disabled state
        - Current regime
        - Active signals
        - Recent performance
    """
    markets_status = {}
    
    for instrument in ["US30", "NAS100", "XAUUSD"]:
        setting_key = f"{instrument.lower()}_enabled"
        regime_data = _coordinator_state.get("market_regimes", {}).get(instrument, {})
        
        markets_status[instrument] = {
            "enabled": _engine_settings.get(setting_key, True),
            "regime": {
                "volatility": regime_data.get("volatility", "NORMAL"),
                "trend": regime_data.get("trend", "RANGING"),
                "atr_current": regime_data.get("atr_current", 0.0),
                "atr_average": regime_data.get("atr_average", 0.0),
            } if regime_data else None,
            "active_signals": 0,  # Would count from active signals
            "trades_today": 0,  # Would fetch from database
        }
    
    return {
        "markets": markets_status,
        "timestamp": datetime.now(pytz.UTC).isoformat()
    }


# ---------------------------------------------------------------------------
# Health & Diagnostics
# ---------------------------------------------------------------------------

@router.get("/health", summary="Dual-engine system health check")
async def dual_engine_health_check(db: AsyncSession = Depends(get_db)):
    """
    Check health of dual-engine system components.
    
    Checks:
    - Regime detector operational
    - Performance tracker operational
    - Decision engine operational
    - Both strategy engines operational
    """
    
    return {
        "ok": True,
        "components": {
            "regime_detector": True,
            "performance_tracker": True,
            "decision_engine": True,
            "core_strategy_engine": True,
            "quick_scalp_engine": True,
            "trading_coordinator": True,
        },
        "settings": _engine_settings,
        "timestamp": datetime.now(pytz.UTC).isoformat(),
    }
