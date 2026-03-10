-- ============================================================
-- Aegis Trader – PostgreSQL Database Schema
-- Run this to initialise your database.
-- Compatible with Supabase + standard PostgreSQL 15+
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Enums ─────────────────────────────────────────────────

CREATE TYPE bot_mode AS ENUM ('analyze', 'trade', 'swing', 'sunday_overview');
CREATE TYPE signal_direction AS ENUM ('long', 'short');
CREATE TYPE signal_grade AS ENUM ('A+', 'A', 'B');
CREATE TYPE trade_status AS ENUM ('open', 'closed', 'cancelled', 'partial');
CREATE TYPE trade_close_reason AS ENUM ('tp1', 'tp2', 'runner', 'stop_loss', 'manual', 'risk_limit', 'news');

-- ─── Users ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_chat_id   VARCHAR(64)  UNIQUE,
    username           VARCHAR(128),
    email              VARCHAR(256) UNIQUE,
    is_active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─── Bot Settings ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS bot_settings (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID         NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    mode                   bot_mode     NOT NULL DEFAULT 'analyze',
    auto_trade_enabled     BOOLEAN      NOT NULL DEFAULT FALSE,
    lot_size               FLOAT        NOT NULL DEFAULT 0.01,
    max_daily_trades       INTEGER      NOT NULL DEFAULT 2,
    max_daily_losses       INTEGER      NOT NULL DEFAULT 2,
    max_daily_drawdown_pct FLOAT        NOT NULL DEFAULT 2.0,
    max_spread_points      FLOAT        NOT NULL DEFAULT 5.0,
    max_slippage_points    FLOAT        NOT NULL DEFAULT 10.0,
    sessions               JSONB        NOT NULL DEFAULT '{"london":{"start":"10:00","end":"13:00"},"new_york":{"start":"15:30","end":"17:30"},"power_hour":{"start":"20:00","end":"22:00"}}',
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─── Symbols ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS symbols (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(32)  NOT NULL UNIQUE,
    description     VARCHAR(256),
    point_value     FLOAT        NOT NULL DEFAULT 1.0,
    level_interval  INTEGER      NOT NULL DEFAULT 250,
    mid_interval    INTEGER      NOT NULL DEFAULT 125,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

INSERT INTO symbols (name, description) VALUES ('US30', 'Dow Jones Industrial Average CFD')
    ON CONFLICT (name) DO NOTHING;

-- ─── Signals ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS signals (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID             REFERENCES users(id) ON DELETE SET NULL,
    symbol             VARCHAR(32)      NOT NULL DEFAULT 'US30',
    direction          signal_direction NOT NULL,
    timeframe          VARCHAR(8)       NOT NULL DEFAULT '5M',
    level_price        NUMERIC(12,2)    NOT NULL,
    entry_price        NUMERIC(12,2)    NOT NULL,
    sl_price           NUMERIC(12,2)    NOT NULL,
    tp1_price          NUMERIC(12,2)    NOT NULL,
    tp2_price          NUMERIC(12,2)    NOT NULL,
    score              INTEGER          NOT NULL CHECK (score >= 0 AND score <= 100),
    grade              signal_grade     NOT NULL,
    htf_alignment      INTEGER          NOT NULL DEFAULT 0,
    level_250          INTEGER          NOT NULL DEFAULT 0,
    level_125          INTEGER          NOT NULL DEFAULT 0,
    liquidity_sweep    INTEGER          NOT NULL DEFAULT 0,
    fvg_retest         INTEGER          NOT NULL DEFAULT 0,
    displacement       INTEGER          NOT NULL DEFAULT 0,
    mss                INTEGER          NOT NULL DEFAULT 0,
    session_timing     INTEGER          NOT NULL DEFAULT 0,
    spread_ok          INTEGER          NOT NULL DEFAULT 0,
    session            VARCHAR(32),
    spread_at_signal   FLOAT,
    news_clear         BOOLEAN          NOT NULL DEFAULT TRUE,
    paper_result       VARCHAR(16),
    raw_payload        JSONB,
    created_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_created_at  ON signals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_grade        ON signals (grade);
CREATE INDEX IF NOT EXISTS idx_signals_user_id      ON signals (user_id);

-- ─── Trades ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS trades (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID              REFERENCES users(id) ON DELETE SET NULL,
    signal_id           UUID              REFERENCES signals(id) ON DELETE SET NULL,
    mt5_ticket          INTEGER,
    symbol              VARCHAR(32)       NOT NULL DEFAULT 'US30',
    direction           signal_direction  NOT NULL,
    lot_size            FLOAT             NOT NULL,
    entry_price         NUMERIC(12,2)     NOT NULL,
    sl_price            NUMERIC(12,2)     NOT NULL,
    tp1_price           NUMERIC(12,2)     NOT NULL,
    tp2_price           NUMERIC(12,2)     NOT NULL,
    actual_entry_price  NUMERIC(12,2),
    slippage            FLOAT,
    status              trade_status      NOT NULL DEFAULT 'open',
    tp1_hit             BOOLEAN           NOT NULL DEFAULT FALSE,
    tp2_hit             BOOLEAN           NOT NULL DEFAULT FALSE,
    be_moved            BOOLEAN           NOT NULL DEFAULT FALSE,
    runner_active       BOOLEAN           NOT NULL DEFAULT FALSE,
    pnl                 FLOAT,
    pips                FLOAT,
    close_reason        trade_close_reason,
    opened_at           TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trades_user_id   ON trades (user_id);
CREATE INDEX IF NOT EXISTS idx_trades_status    ON trades (status);
CREATE INDEX IF NOT EXISTS idx_trades_opened_at ON trades (opened_at DESC);

-- ─── Trade Logs ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS trade_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id    UUID         NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    event       VARCHAR(64)  NOT NULL,
    details     JSONB,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trade_logs_trade_id ON trade_logs (trade_id);

-- ─── News Events ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS news_events (
    id                        SERIAL PRIMARY KEY,
    title                     VARCHAR(256) NOT NULL,
    currency                  VARCHAR(8)   NOT NULL DEFAULT 'USD',
    impact                    VARCHAR(16)  NOT NULL DEFAULT 'high',
    event_time                TIMESTAMPTZ  NOT NULL,
    blackout_before_minutes   INTEGER      NOT NULL DEFAULT 15,
    blackout_after_minutes    INTEGER      NOT NULL DEFAULT 15,
    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_event_time ON news_events (event_time);
CREATE INDEX IF NOT EXISTS idx_news_impact     ON news_events (impact);

-- ─── Spread Samples ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS spread_samples (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(32)  NOT NULL DEFAULT 'US30',
    spread_points   FLOAT        NOT NULL,
    sampled_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spread_sampled_at ON spread_samples (sampled_at DESC);

-- ─── Weekly Reports ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS weekly_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start          TIMESTAMPTZ  NOT NULL,
    mtf_bias            JSONB,
    key_levels_250      JSONB,
    key_levels_125      JSONB,
    bullish_scenario    TEXT,
    bearish_scenario    TEXT,
    upcoming_news       JSONB,
    sent_to_telegram    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─── Strategy Stats ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS strategy_stats (
    id                SERIAL PRIMARY KEY,
    period_start      TIMESTAMPTZ  NOT NULL,
    period_end        TIMESTAMPTZ  NOT NULL,
    total_signals     INTEGER      NOT NULL DEFAULT 0,
    a_plus_signals    INTEGER      NOT NULL DEFAULT 0,
    a_signals         INTEGER      NOT NULL DEFAULT 0,
    total_trades      INTEGER      NOT NULL DEFAULT 0,
    winning_trades    INTEGER      NOT NULL DEFAULT 0,
    losing_trades     INTEGER      NOT NULL DEFAULT 0,
    win_rate          FLOAT,
    expectancy        FLOAT,
    max_drawdown      FLOAT,
    avg_spread        FLOAT,
    session_breakdown JSONB,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─── Helpful Views ───────────────────────────────────────────

CREATE OR REPLACE VIEW today_summary AS
SELECT
    COUNT(*) FILTER (WHERE status IN ('open', 'partial'))                AS open_trades,
    COUNT(*) FILTER (WHERE DATE(opened_at AT TIME ZONE 'Africa/Johannesburg') = CURRENT_DATE)
                                                                          AS trades_today,
    COUNT(*) FILTER (WHERE DATE(opened_at AT TIME ZONE 'Africa/Johannesburg') = CURRENT_DATE
                     AND status = 'closed' AND pnl < 0)                  AS losses_today,
    COALESCE(SUM(pnl) FILTER (WHERE DATE(opened_at AT TIME ZONE 'Africa/Johannesburg') = CURRENT_DATE
                              AND status = 'closed'), 0)                  AS pnl_today
FROM trades;
