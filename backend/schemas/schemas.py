"""Pydantic v2 schemas for Aegis Trader API requests and responses.

Matches the Technical Architecture API specification.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# TradingView Webhook Payload (per spec)
# ---------------------------------------------------------------------------

class TradingViewWebhookPayload(BaseModel):
    """Payload sent from TradingView Pine Script alert - matches spec exactly."""

    # Authentication
    secret: str

    # Symbol info
    symbol: str = Field(default="TVC:DJI", description="TradingView symbol")

    # Signal details
    direction: str  # "long" | "short"
    setup_type: str = Field(default="continuation_long", description="Setup classification")
    timeframe: str = Field(default="5", description="Entry timeframe in minutes")

    # Prices
    entry: float
    stop_loss: float
    tp1: float
    tp2: float

    # Multi-timeframe bias (per spec)
    weekly_bias: str = Field(default="neutral", description="bull / bear / neutral")
    daily_bias: str = Field(default="neutral", description="buy / sell / neutral")
    h4_bias: str = Field(default="neutral")
    h1_bias: str = Field(default="neutral")
    m15_bias: str = Field(default="neutral")
    m5_bias: str = Field(default="neutral", description="bull_shift / bear_shift / neutral")
    m1_bias: str = Field(default="neutral")

    # Key levels
    level_250: Optional[float] = None
    level_125: Optional[float] = None

    # Confluence factors (boolean per spec)
    fvg_present: bool = False
    liquidity_sweep: bool = False
    displacement_present: bool = False
    mss_present: bool = False

    # Context
    session_name: str = Field(default="", description="Active session name")
    spread: Optional[float] = Field(default=None, description="Current spread in points")

    # TradingView timestamp
    tv_timestamp: Optional[str] = None

    # Raw payload capture
    raw_payload: Optional[dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def capture_raw(cls, values: dict) -> dict:
        values["raw_payload"] = dict(values)
        return values


# ---------------------------------------------------------------------------
# Webhook Response (per spec)
# ---------------------------------------------------------------------------

class WebhookResponse(BaseModel):
    """Response from POST /webhooks/tradingview."""
    ok: bool
    signal_id: Optional[str] = None
    score: Optional[int] = None
    grade: Optional[str] = None
    auto_trade_eligible: bool = False
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Signal Response
# ---------------------------------------------------------------------------

class SignalOut(BaseModel):
    id: UUID
    source: str
    setup_type: Optional[str]
    direction: str
    analysis_symbol: str
    execution_symbol: str
    timeframe_entry: str

    # MTF bias
    weekly_bias: Optional[str]
    daily_bias: Optional[str]
    h4_bias: Optional[str]
    h1_bias: Optional[str]
    m15_bias: Optional[str]
    m5_bias: Optional[str]
    m1_bias: Optional[str]

    # Levels
    level_250: Optional[float]
    level_125: Optional[float]

    # Confluence
    fvg_present: bool
    liquidity_sweep: bool
    displacement_present: bool
    mss_present: bool

    # Prices
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float

    # Context
    session_name: Optional[str]
    spread_points: Optional[float]
    news_blocked: bool

    # Scoring
    score: int
    grade: Optional[str]
    eligible_for_auto_trade: bool

    # Paper trade
    paper_result: Optional[str]

    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Trade Response
# ---------------------------------------------------------------------------

class TradeOut(BaseModel):
    id: UUID
    broker: Optional[str]
    account_type: str
    mt5_ticket: Optional[int]
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    actual_entry_price: Optional[float]
    slippage: Optional[float]
    status: str
    state: str
    tp1_hit: bool
    tp2_hit: bool
    runner_active: bool
    breakeven_active: bool
    trailing_active: bool
    pnl: Optional[float]
    pnl_pct: Optional[float]
    close_reason: Optional[str]
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Bot Settings (per spec)
# ---------------------------------------------------------------------------

class BotSettingOut(BaseModel):
    analysis_symbol: str
    execution_symbol: str
    mode: str
    auto_trade_enabled: bool
    sessions: dict[str, Any]
    spread_max_points: float
    spread_multiplier: float
    news_block_standard_mins: int
    news_block_major_mins: int
    max_trades_per_day: int
    max_losses_per_day: int
    max_daily_drawdown_pct: float
    lot_mode: str
    fixed_lot: Optional[float]
    risk_percent: Optional[float]
    max_slippage_points: float
    swing_alert_only: bool
    use_one_minute_refinement: bool

    model_config = {"from_attributes": True}


class BotSettingUpdate(BaseModel):
    """Settings update payload - all fields optional."""
    analysis_symbol: Optional[str] = None
    execution_symbol: Optional[str] = None
    mode: Optional[str] = None
    auto_trade_enabled: Optional[bool] = None
    sessions: Optional[dict[str, Any]] = None
    spread_max_points: Optional[float] = Field(default=None, gt=0)
    spread_multiplier: Optional[float] = Field(default=None, gt=0)
    news_block_standard_mins: Optional[int] = Field(default=None, ge=0)
    news_block_major_mins: Optional[int] = Field(default=None, ge=0)
    max_trades_per_day: Optional[int] = Field(default=None, ge=1)
    max_losses_per_day: Optional[int] = Field(default=None, ge=1)
    max_daily_drawdown_pct: Optional[float] = Field(default=None, gt=0)
    lot_mode: Optional[str] = None
    fixed_lot: Optional[float] = Field(default=None, gt=0)
    risk_percent: Optional[float] = Field(default=None, gt=0, le=10)
    max_slippage_points: Optional[float] = Field(default=None, gt=0)
    swing_alert_only: Optional[bool] = None
    use_one_minute_refinement: Optional[bool] = None


# ---------------------------------------------------------------------------
# Dashboard Status (per spec)
# ---------------------------------------------------------------------------

class DashboardStatus(BaseModel):
    mode: str
    auto_trade_enabled: bool
    trades_today: int
    losses_today: int
    drawdown_today_pct: float
    risk_limit_hit: bool
    news_blackout_active: bool
    active_session: Optional[str]
    open_positions: int
    account_balance: float = 0.0
    connection_health: dict[str, bool] = Field(default_factory=lambda: {
        "database": True,
        "telegram": True,
        "mt5_node": True,
    })


# ---------------------------------------------------------------------------
# MT5 Execution Request (per spec)
# ---------------------------------------------------------------------------

class ExecutionRequest(BaseModel):
    """Internal endpoint from backend to MT5 agent - POST /execution/request."""
    trade_id: str
    symbol: str
    direction: str  # "buy" | "sell"
    lot_size: float
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    max_slippage_points: float = 10.0
    account_type: str = "demo"


class ExecutionCallback(BaseModel):
    """MT5 agent returns status - POST /execution/callback."""
    trade_id: str
    status: str  # "executed" | "failed" | "rejected"
    broker_order_id: Optional[str] = None
    fill_price: Optional[float] = None
    slippage_points: Optional[float] = None
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# MT5 Bridge Schemas (internal)
# ---------------------------------------------------------------------------

class MT5OrderRequest(BaseModel):
    symbol: str
    direction: str  # "buy" | "sell"
    lot_size: float
    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    slippage_points: float = 10.0
    comment: str = "AegisTrader"
    signal_id: Optional[str] = None


class MT5OrderResponse(BaseModel):
    success: bool
    ticket: Optional[int] = None
    actual_price: Optional[float] = None
    slippage: Optional[float] = None
    error: Optional[str] = None


class MT5CloseRequest(BaseModel):
    ticket: int
    lot_size: float
    symbol: str


class MT5ModifyRequest(BaseModel):
    ticket: int
    sl_price: float


class MT5Position(BaseModel):
    ticket: int
    symbol: str
    direction: str
    lot_size: float
    open_price: float
    current_sl: float
    current_price: float
    pnl: float
    comment: str


# ---------------------------------------------------------------------------
# Telegram Webhook
# ---------------------------------------------------------------------------

class TelegramUpdate(BaseModel):
    """Simplified Telegram webhook update."""
    update_id: int
    message: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Weekly Report (per spec)
# ---------------------------------------------------------------------------

class WeeklyOverviewOut(BaseModel):
    weekly_bias: Optional[str]
    daily_bias: Optional[str]
    h4_bias: Optional[str]
    h1_bias: Optional[str]
    m15_bias: Optional[str]
    m5_bias: Optional[str]
    m1_bias: Optional[str]
    bullish_scenario: Optional[str]
    bearish_scenario: Optional[str]
    key_levels: Optional[list[float]]
    major_news: Optional[list[str]]


# ---------------------------------------------------------------------------
# News Event
# ---------------------------------------------------------------------------

class NewsEventOut(BaseModel):
    id: int
    title: str
    country: str
    currency: str
    impact: str
    starts_at: datetime
    is_major: bool

    model_config = {"from_attributes": True}


class NewsEventCreate(BaseModel):
    title: str
    starts_at: datetime
    impact: str = "high"
    is_major: bool = False
