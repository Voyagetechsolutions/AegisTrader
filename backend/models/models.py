"""SQLAlchemy ORM models for Aegis Trader.

All tables are defined here and imported in database.py so that
create_tables() picks them up automatically.

Schema matches the Technical Architecture spec.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, Enum, JSON, func, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class BotMode(str, PyEnum):
    ANALYZE = "analyze"
    TRADE = "trade"
    SWING = "swing"


class SignalDirection(str, PyEnum):
    LONG = "long"
    SHORT = "short"


class SignalGrade(str, PyEnum):
    A_PLUS = "A+"
    A = "A"
    B = "B"


class SetupType(str, PyEnum):
    CONTINUATION_LONG = "continuation_long"
    CONTINUATION_SHORT = "continuation_short"
    SWING_LONG = "swing_long"
    SWING_SHORT = "swing_short"


class TradeStatus(str, PyEnum):
    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"
    REJECTED = "rejected"
    FAILED = "failed"


class TradeCloseReason(str, PyEnum):
    TP1 = "tp1"
    TP2 = "tp2"
    RUNNER = "runner"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"
    RISK_LIMIT = "risk_limit"
    NEWS = "news"
    FORCE_CLOSED = "force_closed"


class LotMode(str, PyEnum):
    MINIMUM_LOT = "minimum_lot"
    FIXED_LOT = "fixed_lot"
    RISK_PERCENT = "risk_percent"


class TradeState(str, PyEnum):
    """Trade lifecycle state machine states."""
    IDLE = "idle"
    SIGNAL_RECEIVED = "signal_received"
    VALIDATING = "validating"
    SCORED = "scored"
    ALERT_SENT = "alert_sent"
    EXECUTION_PENDING = "execution_pending"
    EXECUTED = "executed"
    TP1_HIT = "tp1_hit"
    BREAKEVEN_ACTIVE = "breakeven_active"
    TP2_HIT = "tp2_hit"
    RUNNER_ACTIVE = "runner_active"
    CLOSED = "closed"
    LOGGED = "logged"
    # Failure states
    REJECTED = "rejected"
    EXECUTION_FAILED = "execution_failed"
    STOPPED_OUT = "stopped_out"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(256), unique=True, nullable=True)
    telegram_chat_id = Column(String(64), unique=True, nullable=True)
    whatsapp_enabled = Column(Boolean, default=False)  # Feature flag - disabled
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    settings = relationship("BotSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user")
    signals = relationship("Signal", back_populates="user")


# ---------------------------------------------------------------------------
# Bot Settings (per spec)
# ---------------------------------------------------------------------------

class BotSetting(Base):
    __tablename__ = "bot_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Symbol configuration
    analysis_symbol = Column(String(32), default="TVC:DJI")  # TradingView symbol for analysis
    execution_symbol = Column(String(32), default="US30")    # Broker symbol for execution

    # Mode
    mode = Column(Enum(BotMode), default=BotMode.ANALYZE, nullable=False)
    auto_trade_enabled = Column(Boolean, default=False)

    # Session windows (stored as JSON: {"london": {"start": "10:00", "end": "13:00"}, ...})
    sessions = Column(JSON, default=lambda: {
        "london": {"start": "10:00", "end": "13:00"},
        "new_york": {"start": "15:30", "end": "17:30"},
        "power_hour": {"start": "20:00", "end": "22:00"},
    })

    # Spread configuration
    spread_max_points = Column(Numeric(6, 2), default=5.0)
    spread_multiplier = Column(Numeric(4, 2), default=2.0)  # current <= avg * multiplier

    # News blackout configuration
    news_block_standard_mins = Column(Integer, default=15)
    news_block_major_mins = Column(Integer, default=30)

    # Risk rules
    max_trades_per_day = Column(Integer, default=2)
    max_losses_per_day = Column(Integer, default=2)
    max_daily_drawdown_pct = Column(Numeric(5, 2), default=2.0)

    # Lot sizing
    lot_mode = Column(Enum(LotMode), default=LotMode.MINIMUM_LOT)
    fixed_lot = Column(Numeric(8, 4), nullable=True)
    risk_percent = Column(Numeric(5, 2), nullable=True)

    # Execution settings
    max_slippage_points = Column(Numeric(6, 2), default=10.0)

    # Swing mode
    swing_alert_only = Column(Boolean, default=True)  # Swing never auto-trades

    # Refinement
    use_one_minute_refinement = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="settings")


# ---------------------------------------------------------------------------
# Signals (per spec)
# ---------------------------------------------------------------------------

class Signal(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Source
    source = Column(String(32), default="tradingview")

    # Setup classification
    setup_type = Column(Enum(SetupType), nullable=True)
    direction = Column(Enum(SignalDirection), nullable=False)

    # Symbols
    analysis_symbol = Column(String(32), default="TVC:DJI")
    execution_symbol = Column(String(32), default="US30")

    # Timeframe
    timeframe_entry = Column(String(8), default="5m")

    # Multi-timeframe bias (per spec)
    weekly_bias = Column(String(16), nullable=True)   # bull / bear / neutral
    daily_bias = Column(String(16), nullable=True)    # buy / sell / neutral
    h4_bias = Column(String(16), nullable=True)
    h1_bias = Column(String(16), nullable=True)
    m15_bias = Column(String(16), nullable=True)
    m5_bias = Column(String(16), nullable=True)       # bull_shift / bear_shift / neutral
    m1_bias = Column(String(16), nullable=True)

    # Key levels
    level_250 = Column(Numeric(12, 2), nullable=True)
    level_125 = Column(Numeric(12, 2), nullable=True)

    # Confluence factors (boolean per spec)
    fvg_present = Column(Boolean, default=False)
    liquidity_sweep = Column(Boolean, default=False)
    displacement_present = Column(Boolean, default=False)
    mss_present = Column(Boolean, default=False)

    # Prices
    entry_price = Column(Numeric(12, 2), nullable=False)
    stop_loss = Column(Numeric(12, 2), nullable=False)
    tp1 = Column(Numeric(12, 2), nullable=False)
    tp2 = Column(Numeric(12, 2), nullable=False)

    # Session and spread context
    session_name = Column(String(32), nullable=True)
    spread_points = Column(Numeric(6, 2), nullable=True)

    # News
    news_blocked = Column(Boolean, default=False)

    # Scoring
    score = Column(Integer, nullable=False, default=0)
    grade = Column(Enum(SignalGrade), nullable=True)
    eligible_for_auto_trade = Column(Boolean, default=False)

    # Raw payload for debugging
    raw_payload = Column(JSON, nullable=True)

    # Idempotency key (hash of key fields to prevent duplicates)
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)

    # Paper trade tracking
    paper_result = Column(String(16), nullable=True)  # win / loss / open

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="signals")
    trade = relationship("Trade", back_populates="signal", uselist=False)

    __table_args__ = (
        Index('ix_signals_created_at', 'created_at'),
        Index('ix_signals_grade', 'grade'),
    )


# ---------------------------------------------------------------------------
# Trades (per spec)
# ---------------------------------------------------------------------------

class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("signals.id", ondelete="SET NULL"), nullable=True)

    # Broker info
    broker = Column(String(64), nullable=True)
    account_type = Column(String(16), default="demo")  # demo | live
    mt5_ticket = Column(Integer, nullable=True)

    # Symbol and direction
    symbol = Column(String(32), default="US30")
    direction = Column(Enum(SignalDirection), nullable=False)
    lot_size = Column(Numeric(8, 4), nullable=False)

    # Prices
    entry_price = Column(Numeric(12, 2), nullable=False)
    stop_loss = Column(Numeric(12, 2), nullable=False)
    tp1 = Column(Numeric(12, 2), nullable=False)
    tp2 = Column(Numeric(12, 2), nullable=False)
    actual_entry_price = Column(Numeric(12, 2), nullable=True)
    slippage = Column(Numeric(6, 2), nullable=True)

    # Trade management state
    tp1_hit = Column(Boolean, default=False)
    tp2_hit = Column(Boolean, default=False)
    runner_active = Column(Boolean, default=False)
    breakeven_active = Column(Boolean, default=False)
    trailing_active = Column(Boolean, default=False)

    # Status
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING)
    state = Column(Enum(TradeState), default=TradeState.IDLE)

    # Results
    pnl = Column(Numeric(12, 2), nullable=True)
    pnl_pct = Column(Numeric(8, 4), nullable=True)
    close_reason = Column(Enum(TradeCloseReason), nullable=True)

    # Timestamps
    opened_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="trades")
    signal = relationship("Signal", back_populates="trade")
    logs = relationship("TradeLog", back_populates="trade", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_trades_status', 'status'),
        Index('ix_trades_opened_at', 'opened_at'),
    )


# ---------------------------------------------------------------------------
# Trade Logs
# ---------------------------------------------------------------------------

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(64), nullable=False)
    message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trade = relationship("Trade", back_populates="logs")


# ---------------------------------------------------------------------------
# News Events (per spec)
# ---------------------------------------------------------------------------

class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    country = Column(String(8), default="US")
    currency = Column(String(8), default="USD")
    impact = Column(String(16), default="high")  # high | medium | low
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    is_major = Column(Boolean, default=False)  # CPI, NFP, FOMC etc
    source = Column(String(64), default="forexfactory")
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_news_events_starts_at', 'starts_at'),
    )


# ---------------------------------------------------------------------------
# Spread Samples
# ---------------------------------------------------------------------------

class SpreadSample(Base):
    __tablename__ = "spread_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), default="US30")
    bid = Column(Numeric(12, 2), nullable=True)
    ask = Column(Numeric(12, 2), nullable=True)
    spread_points = Column(Numeric(6, 2), nullable=False)
    sampled_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_spread_samples_symbol_sampled_at', 'symbol', 'sampled_at'),
    )


# ---------------------------------------------------------------------------
# Weekly Reports (per spec)
# ---------------------------------------------------------------------------

class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    week_start = Column(DateTime(timezone=True), nullable=False)

    # MTF bias (per spec)
    weekly_bias = Column(String(16), nullable=True)
    daily_bias = Column(String(16), nullable=True)
    h4_bias = Column(String(16), nullable=True)
    h1_bias = Column(String(16), nullable=True)
    m15_bias = Column(String(16), nullable=True)
    m5_bias = Column(String(16), nullable=True)
    m1_bias = Column(String(16), nullable=True)

    # Scenarios
    bullish_scenario = Column(Text, nullable=True)
    bearish_scenario = Column(Text, nullable=True)

    # Key levels (JSON array)
    key_levels = Column(JSON, nullable=True)

    # News summary (JSON array)
    news_summary = Column(JSON, nullable=True)

    # Full report text for Telegram
    report_text = Column(Text, nullable=True)

    sent_to_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Strategy Stats (per spec)
# ---------------------------------------------------------------------------

class StrategyStat(Base):
    __tablename__ = "strategy_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Breakdown dimensions
    setup_type = Column(String(32), nullable=True)
    session_name = Column(String(32), nullable=True)

    # Metrics
    trades_count = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 2), nullable=True)
    avg_rr = Column(Numeric(6, 2), nullable=True)
    expectancy = Column(Numeric(8, 2), nullable=True)
    max_drawdown = Column(Numeric(8, 2), nullable=True)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
