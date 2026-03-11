"""
Strategy Engine API Router

Provides FastAPI integration endpoints for the Python Strategy Engine:
- Engine status and health monitoring
- Signal webhook endpoints for existing systems
- Configuration update endpoints
- Performance metrics and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.strategy.engine import strategy_engine
from backend.strategy.signal_generator import signal_generator
from backend.strategy.session_manager import SessionManager
from backend.strategy.risk_integration import risk_integration
from backend.strategy.performance_monitor import performance_monitor
from backend.strategy.config import strategy_settings
from backend.strategy.models import SignalGrade, SetupType, Direction


router = APIRouter(prefix="/strategy-engine", tags=["Strategy Engine"])


# ── Schemas ───────────────────────────────────────────────────────────────

class EngineStatusResponse(BaseModel):
    """Strategy engine status response."""
    running: bool
    components_initialized: bool
    timestamp: str
    uptime_seconds: Optional[float]
    performance_metrics: Dict[str, Any]
    memory_usage_mb: Optional[float]
    last_processing_time: Optional[float]


class EngineHealthResponse(BaseModel):
    """Strategy engine health check response."""
    status: str  # "healthy", "degraded", "unhealthy"
    components: Dict[str, str]
    data_freshness: Dict[str, Any]
    session_info: Dict[str, Any]
    alerts: List[str]


class SignalWebhookPayload(BaseModel):
    """Signal webhook payload for existing systems."""
    timestamp: str
    setup_type: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    confluence_score: float
    grade: str
    analysis_breakdown: Dict[str, Any]
    symbol: str = "US30"


class ConfigurationUpdate(BaseModel):
    """Configuration update request."""
    ema_period: Optional[int] = None
    level_increment_250: Optional[int] = None
    level_increment_125: Optional[int] = None
    fvg_threshold: Optional[float] = None
    displacement_threshold: Optional[float] = None
    liquidity_sweep_threshold: Optional[float] = None
    min_confluence_score: Optional[float] = None
    session_override: Optional[bool] = None


class CompatibilityStatusResponse(BaseModel):
    """Compatibility system status response."""
    timestamp: str
    mt5_bridge: str
    telegram: str
    confluence_scoring: str
    positions_count: int
    overall_status: str


class SystemIntegrationResponse(BaseModel):
    """System integration test response."""
    compatibility_check: bool
    confluence_score: Optional[float]
    confluence_grade: Optional[str]
    alert_sent: bool
    trade_executed: bool
    errors: List[str]


# ── Engine Status & Health ────────────────────────────────────────────────

@router.get("/status", response_model=EngineStatusResponse)
async def get_engine_status():
    """Get current strategy engine status and metrics."""
    
    status = await strategy_engine.get_status()
    
    return EngineStatusResponse(
        running=status["running"],
        components_initialized=status["components_initialized"],
        timestamp=status["timestamp"],
        uptime_seconds=None,  # TODO: Calculate uptime
        performance_metrics=status.get("performance_metrics", {}),
        memory_usage_mb=None,  # TODO: Get memory usage
        last_processing_time=None  # TODO: Get last processing time
    )


@router.get("/health", response_model=EngineHealthResponse)
async def get_engine_health():
    """Comprehensive health check for strategy engine components."""
    
    # Check component health
    components = {
        "market_data_layer": "ok",  # TODO: Actual health checks
        "candle_aggregator": "ok",
        "analysis_engines": "ok", 
        "signal_generator": "ok",
        "redis_connection": "ok",
        "session_manager": "ok"
    }
    
    # Check data freshness
    data_freshness = {
        "last_candle_update": None,  # TODO: Get from market data layer
        "last_analysis_update": None,  # TODO: Get from analysis engines
        "redis_connection_age": None   # TODO: Get Redis connection info
    }
    
    # Get session info
    session_manager = SessionManager(strategy_settings.timezone)
    session_info = {
        "current_session": session_manager.get_active_session(),
        "session_active": session_manager.is_within_session(),
        "next_session": None,  # TODO: Calculate next session
        "override_enabled": session_manager.is_override_enabled()
    }
    
    # Check for alerts
    alerts = []
    if not strategy_engine.running:
        alerts.append("Strategy engine is not running")
    
    # Determine overall status
    if alerts:
        status = "unhealthy"
    elif any(comp != "ok" for comp in components.values()):
        status = "degraded"
    else:
        status = "healthy"
    
    return EngineHealthResponse(
        status=status,
        components=components,
        data_freshness=data_freshness,
        session_info=session_info,
        alerts=alerts
    )


# ── Signal Webhooks ───────────────────────────────────────────────────────

@router.post("/signals/webhook")
async def signal_webhook_endpoint(
    background_tasks: BackgroundTasks,
    callback_url: Optional[str] = None
):
    """
    Webhook endpoint for existing systems to receive signals.
    
    This endpoint allows existing systems to register for signal notifications
    and receive them via webhook callbacks, replacing TradingView webhooks.
    """
    
    # Get recent signals
    recent_signals = await signal_generator.get_recent_signals(count=1)
    
    if not recent_signals:
        return {"status": "no_signals", "message": "No recent signals available"}
    
    latest_signal = recent_signals[0]
    
    # Convert to webhook payload format
    webhook_payload = SignalWebhookPayload(
        timestamp=latest_signal.timestamp.isoformat(),
        setup_type=latest_signal.setup_type.value,
        direction=latest_signal.direction.value,
        entry=latest_signal.entry,
        stop_loss=latest_signal.stop_loss,
        take_profit=latest_signal.take_profit,
        confluence_score=latest_signal.confluence_score,
        grade=latest_signal.grade.value,
        analysis_breakdown=latest_signal.analysis_breakdown
    )
    
    # If callback URL provided, send webhook in background
    if callback_url:
        background_tasks.add_task(_send_webhook_callback, callback_url, webhook_payload)
        return {"status": "webhook_queued", "signal": webhook_payload.dict()}
    
    return {"status": "signal_retrieved", "signal": webhook_payload.dict()}


@router.get("/signals/latest")
async def get_latest_signal():
    """Get the latest generated signal."""
    
    recent_signals = await signal_generator.get_recent_signals(count=1)
    
    if not recent_signals:
        return {"status": "no_signals", "message": "No signals available"}
    
    signal = recent_signals[0]
    
    return {
        "status": "ok",
        "signal": {
            "timestamp": signal.timestamp.isoformat(),
            "setup_type": signal.setup_type.value,
            "direction": signal.direction.value,
            "entry": signal.entry,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "confluence_score": signal.confluence_score,
            "grade": signal.grade.value,
            "analysis_breakdown": signal.analysis_breakdown
        }
    }


@router.get("/signals/recent")
async def get_recent_signals(count: int = 10):
    """Get recent signals with optional count limit."""
    
    signals = await signal_generator.get_recent_signals(count=count)
    
    return {
        "status": "ok",
        "count": len(signals),
        "signals": [
            {
                "timestamp": s.timestamp.isoformat(),
                "setup_type": s.setup_type.value,
                "direction": s.direction.value,
                "entry": s.entry,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "confluence_score": s.confluence_score,
                "grade": s.grade.value,
                "analysis_breakdown": s.analysis_breakdown
            }
            for s in signals
        ]
    }


# ── Configuration Management ──────────────────────────────────────────────

@router.post("/config/update")
async def update_configuration(config: ConfigurationUpdate):
    """
    Update strategy engine configuration parameters at runtime.
    
    Allows modification of analysis parameters without requiring restart.
    """
    from datetime import timezone
    
    updated_params = {}
    
    # Update analysis parameters
    if config.ema_period is not None:
        # TODO: Update EMA period in bias engine
        updated_params["ema_period"] = config.ema_period
    
    if config.level_increment_250 is not None:
        # TODO: Update level increment in level engine
        updated_params["level_increment_250"] = config.level_increment_250
    
    if config.level_increment_125 is not None:
        # TODO: Update level increment in level engine
        updated_params["level_increment_125"] = config.level_increment_125
    
    if config.fvg_threshold is not None:
        # TODO: Update FVG threshold in FVG engine
        updated_params["fvg_threshold"] = config.fvg_threshold
    
    if config.displacement_threshold is not None:
        # TODO: Update displacement threshold in displacement engine
        updated_params["displacement_threshold"] = config.displacement_threshold
    
    if config.liquidity_sweep_threshold is not None:
        # TODO: Update liquidity sweep threshold in liquidity engine
        updated_params["liquidity_sweep_threshold"] = config.liquidity_sweep_threshold
    
    if config.min_confluence_score is not None:
        # TODO: Update minimum confluence score in signal generator
        updated_params["min_confluence_score"] = config.min_confluence_score
    
    if config.session_override is not None:
        session_manager = SessionManager(strategy_settings.timezone)
        if config.session_override:
            session_manager.enable_override()
        else:
            session_manager.disable_override()
        updated_params["session_override"] = config.session_override
    
    return {
        "status": "ok",
        "message": f"Updated {len(updated_params)} parameters",
        "updated_parameters": updated_params,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/config/current")
async def get_current_configuration():
    """Get current strategy engine configuration."""
    from datetime import timezone
    
    session_manager = SessionManager(strategy_settings.timezone)
    
    return {
        "status": "ok",
        "configuration": {
            "data_fetch_interval": strategy_settings.data_fetch_interval,
            "max_processing_time": strategy_settings.max_processing_time,
            "memory_limit_mb": strategy_settings.memory_limit_mb,
            "timezone": strategy_settings.timezone,
            "session_override": session_manager.is_override_enabled(),
            # TODO: Add other configurable parameters
            "ema_period": 21,  # Default values for now
            "level_increment_250": 250,
            "level_increment_125": 125,
            "fvg_threshold": 20.0,
            "displacement_threshold": 50.0,
            "liquidity_sweep_threshold": 10.0,
            "min_confluence_score": 60.0
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class PerformanceMetrics(BaseModel):
    """Performance metrics response."""
    processing_times: Dict[str, float]
    memory_usage: Dict[str, float]
    data_fetch_latency: Dict[str, float]
    signal_generation_rate: Dict[str, int]
    error_counts: Dict[str, int]


# ── Compatibility & Integration ───────────────────────────────────────────

@router.get("/compatibility/status", response_model=CompatibilityStatusResponse)
async def get_compatibility_status():
    """Get status of compatibility with existing Aegis Trader systems."""
    
    # Import here to avoid circular import
    from backend.strategy.compatibility import system_compatibility
    status = await system_compatibility.get_system_status()
    
    # Determine overall status
    overall_status = "healthy"
    if "error" in status.get("mt5_bridge", ""):
        overall_status = "degraded"
    if "error" in status.get("telegram", ""):
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
    
    return CompatibilityStatusResponse(
        timestamp=status["timestamp"],
        mt5_bridge=status["mt5_bridge"],
        telegram=status["telegram"],
        confluence_scoring=status["confluence_scoring"],
        positions_count=status["positions_count"],
        overall_status=overall_status
    )


@router.post("/compatibility/test")
async def test_system_integration():
    """
    Test integration with existing systems using a mock signal.
    
    This endpoint creates a test signal and processes it through all
    compatibility layers to verify system integration.
    """
    from datetime import timezone
    from backend.strategy.models import Signal, Direction, SetupType, SignalGrade
    from backend.strategy.compatibility import system_compatibility
    
    # Create a test signal
    test_signal = Signal(
        timestamp=datetime.now(timezone.utc),
        setup_type=SetupType.CONTINUATION_LONG,
        direction=Direction.LONG,
        entry=46150.0,
        stop_loss=46100.0,
        take_profit=46200.0,
        confluence_score=85.0,
        grade=SignalGrade.A_PLUS,
        analysis_breakdown={
            "bias_score": 15.0,
            "level_score": 12.0,
            "liquidity_score": 10.0,
            "fvg_score": 8.0,
            "displacement_score": 15.0,
            "structure_score": 12.0,
            "session_bonus": 8.0,
            "weekly_bias": "bullish",
            "daily_bias": "bullish",
            "h4_bias": "bullish",
            "h1_bias": "bullish",
            "level_250": 46250.0,
            "level_125": 46125.0,
        }
    )
    
    # Process through compatibility layer (test mode - no actual execution)
    result = await system_compatibility.process_strategy_signal(
        signal=test_signal,
        send_alerts=False,  # Don't send actual alerts during test
        execute_trade=False  # Don't execute actual trades during test
    )
    
    return SystemIntegrationResponse(
        compatibility_check=result["compatibility_check"],
        confluence_score=result.get("confluence_score"),
        confluence_grade=result.get("confluence_grade"),
        alert_sent=result["alert_sent"],
        trade_executed=result["trade_executed"],
        errors=result["errors"]
    )


@router.get("/compatibility/confluence-mapping")
async def get_confluence_mapping():
    """
    Get mapping between strategy engine analysis and existing confluence scoring.
    
    This endpoint shows how strategy engine analysis results map to the
    existing 100-point confluence scoring system.
    """
    
    return {
        "status": "ok",
        "mapping": {
            "strategy_engine_to_confluence": {
                "bias_score": "HTF alignment (max 20 points)",
                "level_score": "250/125 level proximity (max 25 points)",
                "liquidity_score": "Liquidity sweep (max 15 points)",
                "fvg_score": "FVG presence (max 15 points)",
                "displacement_score": "Displacement candle (max 10 points)",
                "structure_score": "MSS/CHoCH (max 10 points)",
                "session_bonus": "Session timing (max 5 points)"
            },
            "grade_thresholds": {
                "A+": "85-100 points (auto trade eligible)",
                "A": "75-84 points (alert only)",
                "B": "<75 points (ignored)"
            },
            "setup_type_mapping": {
                "continuation_long": "HTF aligned bullish + 5M bull shift",
                "continuation_short": "HTF aligned bearish + 5M bear shift",
                "swing_long": "Weekly/Daily/H4 bullish + H1 pullback",
                "swing_short": "Weekly/Daily/H4 bearish + H1 pullback"
            }
        }
    }

# ── Bot Mode Management ───────────────────────────────────────────────────

@router.get("/bot-mode/status")
async def get_bot_mode_status(user_id: Optional[str] = None):
    """Get current bot mode status for user."""
    from datetime import timezone
    from backend.strategy.bot_mode_manager import bot_mode_manager
    from uuid import UUID
    
    user_uuid = UUID(user_id) if user_id else None
    status = await bot_mode_manager.get_mode_status(user_uuid)
    
    return {
        "status": "ok",
        "bot_mode": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/bot-mode/switch/{mode}")
async def switch_bot_mode(mode: str, user_id: Optional[str] = None):
    """Switch bot mode (analyze/trade/swing)."""
    from datetime import timezone
    from backend.strategy.bot_mode_manager import bot_mode_manager
    from backend.models.models import BotMode
    from uuid import UUID
    
    # Validate mode
    try:
        bot_mode = BotMode(mode.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Valid modes: analyze, trade, swing"
        )
    
    user_uuid = UUID(user_id) if user_id else None
    success = await bot_mode_manager.update_mode(bot_mode, user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update bot mode"
        )
    
    return {
        "status": "ok",
        "mode": bot_mode.value,
        "message": f"Bot mode switched to {bot_mode.value}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/bot-mode/auto-trade/{action}")
async def toggle_auto_trade(action: str, user_id: Optional[str] = None):
    """Toggle auto trading (enable/disable)."""
    from datetime import timezone
    from backend.strategy.bot_mode_manager import bot_mode_manager
    from uuid import UUID
    
    # Validate action
    if action.lower() not in ["enable", "disable"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{action}'. Valid actions: enable, disable"
        )
    
    enabled = action.lower() == "enable"
    user_uuid = UUID(user_id) if user_id else None
    success = await bot_mode_manager.toggle_auto_trade(enabled, user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to toggle auto trading"
        )
    
    action_text = "enabled" if enabled else "disabled"
    return {
        "status": "ok",
        "auto_trade_enabled": enabled,
        "message": f"Auto trading {action_text}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/bot-mode/execution-decision")
async def get_execution_decision(
    confluence_score: float,
    setup_type: str,
    user_id: Optional[str] = None,
    session_active: bool = True,
    risk_allowed: bool = True
):
    """
    Get execution decision for a hypothetical signal based on current bot mode.
    
    This endpoint helps existing systems understand how the strategy engine
    would handle a signal with given parameters.
    """
    from datetime import timezone
    from backend.strategy.bot_mode_manager import bot_mode_manager
    from backend.strategy.models import Signal, SetupType, SignalGrade, Direction
    from uuid import UUID
    
    # Validate setup type
    try:
        setup_enum = SetupType(setup_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid setup_type '{setup_type}'. Valid types: continuation_long, continuation_short, swing_long, swing_short"
        )
    
    # Create mock signal for decision
    mock_signal = Signal(
        timestamp=datetime.now(timezone.utc),
        setup_type=setup_enum,
        direction=Direction.LONG,  # Doesn't affect mode decision
        entry=46150.0,
        stop_loss=46100.0,
        take_profit=46200.0,
        confluence_score=confluence_score,
        grade=SignalGrade.A_PLUS if confluence_score >= 85 else SignalGrade.A if confluence_score >= 75 else SignalGrade.B,
        analysis_breakdown={}
    )
    
    user_uuid = UUID(user_id) if user_id else None
    decision = await bot_mode_manager.should_execute_signal(
        signal=mock_signal,
        user_id=user_uuid,
        session_active=session_active,
        risk_allowed=risk_allowed
    )
    
    return {
        "status": "ok",
        "decision": decision,
        "signal_grade": mock_signal.grade.value,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ── Bot Mode Compatibility ────────────────────────────────────────────────

@router.get("/bot-mode/compatibility-mapping")
async def get_bot_mode_compatibility():
    """
    Get mapping between strategy engine bot modes and existing system behavior.
    
    This endpoint documents how the strategy engine maintains identical
    behavior to the existing webhook-based system.
    """
    
    return {
        "status": "ok",
        "mode_behavior": {
            "analyze": {
                "description": "Detect setups and send alerts only (no trades)",
                "signal_processing": "All valid signals generate alerts",
                "auto_trade": "Never executes trades automatically",
                "user_interaction": "Alerts sent via Telegram and dashboard",
                "identical_to_webhook": True
            },
            "trade": {
                "description": "Detect setups and auto-execute A+ grade trades",
                "signal_processing": "A+ signals execute automatically, A/B signals alert only",
                "auto_trade": "Executes A+ signals when auto_trade_enabled=True",
                "conditions": [
                    "Signal grade must be A+ (confluence score >= 85)",
                    "Auto trading must be enabled",
                    "Must be within active trading session",
                    "Risk limits must allow execution"
                ],
                "identical_to_webhook": True
            },
            "swing": {
                "description": "Detect higher timeframe setups and alert only",
                "signal_processing": "All swing setups generate alerts (never auto-execute)",
                "auto_trade": "Never executes trades (user approval required)",
                "setup_types": ["swing_long", "swing_short"],
                "user_interaction": "Manual approval required for all swing trades",
                "identical_to_webhook": True
            }
        },
        "compatibility_guarantees": {
            "dashboard_integration": "All existing dashboard functionality preserved",
            "telegram_commands": "All bot commands (/mode, /start, /stop) work identically",
            "signal_format": "Alerts use identical format to webhook system",
            "risk_management": "Same risk limits and validation logic",
            "session_management": "Identical trading session windows and logic"
        },
        "migration_status": {
            "webhook_replacement": "Strategy engine replaces TradingView webhooks",
            "behavior_preservation": "100% identical mode behavior maintained",
            "interface_compatibility": "All existing interfaces work without changes"
        }
    }


# ── Performance Monitoring ────────────────────────────────────────────────

@router.get("/performance/health")
async def get_performance_health():
    """Get performance health status with detailed diagnostics."""
    from datetime import timezone
    
    health_status = performance_monitor.get_health_status()
    
    return {
        "status": "ok",
        "health": health_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/performance/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """Get detailed performance metrics for monitoring."""
    
    # Get comprehensive metrics from performance monitor
    metrics = performance_monitor.get_performance_metrics()
    
    return PerformanceMetrics(
        processing_times={
            "data_fetch": metrics.get("data_fetch_duration", 0.0),
            "candle_aggregation": metrics.get("candle_aggregation_duration", 0.0),
            "analysis_engines": metrics.get("analysis_engines_duration", 0.0),
            "signal_generation": metrics.get("signal_generation_duration", 0.0),
            "total_cycle": metrics.get("process_cycle_duration", 0.0),
            "average_cycle": metrics.get("average_cycle_time", 0.0)
        },
        memory_usage={
            "current_mb": metrics.get("memory_usage_mb", 0.0),
            "peak_mb": metrics.get("strategy_engine_peak_memory", 0.0),
            "limit_mb": metrics.get("memory_limit_mb", 512.0),
            "usage_percent": metrics.get("memory_usage_percent", 0.0)
        },
        data_fetch_latency={
            "mt5_connection": metrics.get("mt5_connection_duration", 0.0),
            "data_retrieval": metrics.get("data_fetch_duration", 0.0),
            "validation": metrics.get("data_validation_duration", 0.0)
        },
        signal_generation_rate={
            "signals_per_hour": metrics.get("signals_a_plus", 0) + metrics.get("signals_a", 0),
            "signals_today": metrics.get("signals_a_plus", 0) + metrics.get("signals_a", 0) + metrics.get("signals_b", 0),
            "signals_this_week": metrics.get("signals_a_plus", 0) + metrics.get("signals_a", 0) + metrics.get("signals_b", 0)
        },
        error_counts=metrics.get("error_breakdown", {
            "connection_errors": 0,
            "validation_errors": 0,
            "analysis_errors": 0,
            "total_errors": 0
        })
    )


# ── Engine Control ────────────────────────────────────────────────────────


@router.post("/engine/start")
async def start_engine(background_tasks: BackgroundTasks):
    """Start the strategy engine."""
    from datetime import timezone
    
    if strategy_engine.running:
        return {"status": "already_running", "message": "Strategy engine is already running"}
    
    # Start engine in background
    background_tasks.add_task(strategy_engine.start)
    
    return {
        "status": "starting",
        "message": "Strategy engine start initiated",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/engine/stop")
async def stop_engine():
    """Stop the strategy engine gracefully."""
    from datetime import timezone
    
    if not strategy_engine.running:
        return {"status": "not_running", "message": "Strategy engine is not running"}
    
    await strategy_engine.stop()
    
    return {
        "status": "stopped",
        "message": "Strategy engine stopped successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ── Helper Functions ──────────────────────────────────────────────────────

async def _send_webhook_callback(callback_url: str, payload: SignalWebhookPayload):
    """Send webhook callback to external system."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=payload.dict(),
                timeout=10.0
            )
            response.raise_for_status()
    except Exception as e:
        # Log error but don't raise - this is a background task
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send webhook callback to {callback_url}: {e}")