"""Initial Aegis Trader schema

Revision ID: 001
Revises:
Create Date: 2026-03-10

Creates all tables for Aegis Trader per Technical Architecture spec.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types (PostgreSQL only, SQLite handles these differently)
    # Note: These are created implicitly by SQLAlchemy for SQLite

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=True),
        sa.Column('telegram_chat_id', sa.String(length=64), nullable=True),
        sa.Column('whatsapp_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('telegram_chat_id')
    )

    # Bot Settings table
    op.create_table(
        'bot_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('analysis_symbol', sa.String(length=32), nullable=True, default='TVC:DJI'),
        sa.Column('execution_symbol', sa.String(length=32), nullable=True, default='US30'),
        sa.Column('mode', sa.String(length=16), nullable=False, default='analyze'),
        sa.Column('auto_trade_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('sessions', sa.JSON(), nullable=True),
        sa.Column('spread_max_points', sa.Numeric(precision=6, scale=2), nullable=True, default=5.0),
        sa.Column('spread_multiplier', sa.Numeric(precision=4, scale=2), nullable=True, default=2.0),
        sa.Column('news_block_standard_mins', sa.Integer(), nullable=True, default=15),
        sa.Column('news_block_major_mins', sa.Integer(), nullable=True, default=30),
        sa.Column('max_trades_per_day', sa.Integer(), nullable=True, default=2),
        sa.Column('max_losses_per_day', sa.Integer(), nullable=True, default=2),
        sa.Column('max_daily_drawdown_pct', sa.Numeric(precision=5, scale=2), nullable=True, default=2.0),
        sa.Column('lot_mode', sa.String(length=16), nullable=True, default='minimum_lot'),
        sa.Column('fixed_lot', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('risk_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('max_slippage_points', sa.Numeric(precision=6, scale=2), nullable=True, default=10.0),
        sa.Column('swing_alert_only', sa.Boolean(), nullable=True, default=True),
        sa.Column('use_one_minute_refinement', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('source', sa.String(length=32), nullable=True, default='tradingview'),
        sa.Column('setup_type', sa.String(length=32), nullable=True),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('analysis_symbol', sa.String(length=32), nullable=True, default='TVC:DJI'),
        sa.Column('execution_symbol', sa.String(length=32), nullable=True, default='US30'),
        sa.Column('timeframe_entry', sa.String(length=8), nullable=True, default='5m'),
        sa.Column('weekly_bias', sa.String(length=16), nullable=True),
        sa.Column('daily_bias', sa.String(length=16), nullable=True),
        sa.Column('h4_bias', sa.String(length=16), nullable=True),
        sa.Column('h1_bias', sa.String(length=16), nullable=True),
        sa.Column('m15_bias', sa.String(length=16), nullable=True),
        sa.Column('m5_bias', sa.String(length=16), nullable=True),
        sa.Column('m1_bias', sa.String(length=16), nullable=True),
        sa.Column('level_250', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('level_125', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('fvg_present', sa.Boolean(), nullable=True, default=False),
        sa.Column('liquidity_sweep', sa.Boolean(), nullable=True, default=False),
        sa.Column('displacement_present', sa.Boolean(), nullable=True, default=False),
        sa.Column('mss_present', sa.Boolean(), nullable=True, default=False),
        sa.Column('entry_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('stop_loss', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tp1', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tp2', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('session_name', sa.String(length=32), nullable=True),
        sa.Column('spread_points', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('news_blocked', sa.Boolean(), nullable=True, default=False),
        sa.Column('score', sa.Integer(), nullable=False, default=0),
        sa.Column('grade', sa.String(length=8), nullable=True),
        sa.Column('eligible_for_auto_trade', sa.Boolean(), nullable=True, default=False),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=64), nullable=True),
        sa.Column('paper_result', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signals_created_at', 'signals', ['created_at'])
    op.create_index('ix_signals_grade', 'signals', ['grade'])
    op.create_index('ix_signals_idempotency_key', 'signals', ['idempotency_key'], unique=True)

    # Trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('signal_id', sa.UUID(), nullable=True),
        sa.Column('broker', sa.String(length=64), nullable=True),
        sa.Column('account_type', sa.String(length=16), nullable=True, default='demo'),
        sa.Column('mt5_ticket', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=32), nullable=True, default='US30'),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('lot_size', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('stop_loss', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tp1', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tp2', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('actual_entry_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('slippage', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('tp1_hit', sa.Boolean(), nullable=True, default=False),
        sa.Column('tp2_hit', sa.Boolean(), nullable=True, default=False),
        sa.Column('runner_active', sa.Boolean(), nullable=True, default=False),
        sa.Column('breakeven_active', sa.Boolean(), nullable=True, default=False),
        sa.Column('trailing_active', sa.Boolean(), nullable=True, default=False),
        sa.Column('status', sa.String(length=16), nullable=True, default='pending'),
        sa.Column('state', sa.String(length=32), nullable=True, default='idle'),
        sa.Column('pnl', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('close_reason', sa.String(length=32), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trades_status', 'trades', ['status'])
    op.create_index('ix_trades_opened_at', 'trades', ['opened_at'])

    # Trade Logs table
    op.create_table(
        'trade_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('trade_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # News Events table
    op.create_table(
        'news_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('country', sa.String(length=8), nullable=True, default='US'),
        sa.Column('currency', sa.String(length=8), nullable=True, default='USD'),
        sa.Column('impact', sa.String(length=16), nullable=True, default='high'),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_major', sa.Boolean(), nullable=True, default=False),
        sa.Column('source', sa.String(length=64), nullable=True, default='forexfactory'),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_news_events_starts_at', 'news_events', ['starts_at'])

    # Spread Samples table
    op.create_table(
        'spread_samples',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=True, default='US30'),
        sa.Column('bid', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('ask', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('spread_points', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('sampled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_spread_samples_symbol_sampled_at', 'spread_samples', ['symbol', 'sampled_at'])

    # Weekly Reports table
    op.create_table(
        'weekly_reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('week_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('weekly_bias', sa.String(length=16), nullable=True),
        sa.Column('daily_bias', sa.String(length=16), nullable=True),
        sa.Column('h4_bias', sa.String(length=16), nullable=True),
        sa.Column('h1_bias', sa.String(length=16), nullable=True),
        sa.Column('m15_bias', sa.String(length=16), nullable=True),
        sa.Column('m5_bias', sa.String(length=16), nullable=True),
        sa.Column('m1_bias', sa.String(length=16), nullable=True),
        sa.Column('bullish_scenario', sa.Text(), nullable=True),
        sa.Column('bearish_scenario', sa.Text(), nullable=True),
        sa.Column('key_levels', sa.JSON(), nullable=True),
        sa.Column('news_summary', sa.JSON(), nullable=True),
        sa.Column('report_text', sa.Text(), nullable=True),
        sa.Column('sent_to_telegram', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Strategy Stats table
    op.create_table(
        'strategy_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('setup_type', sa.String(length=32), nullable=True),
        sa.Column('session_name', sa.String(length=32), nullable=True),
        sa.Column('trades_count', sa.Integer(), nullable=True, default=0),
        sa.Column('win_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('avg_rr', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('expectancy', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('strategy_stats')
    op.drop_table('weekly_reports')
    op.drop_index('ix_spread_samples_symbol_sampled_at', table_name='spread_samples')
    op.drop_table('spread_samples')
    op.drop_index('ix_news_events_starts_at', table_name='news_events')
    op.drop_table('news_events')
    op.drop_table('trade_logs')
    op.drop_index('ix_trades_opened_at', table_name='trades')
    op.drop_index('ix_trades_status', table_name='trades')
    op.drop_table('trades')
    op.drop_index('ix_signals_idempotency_key', table_name='signals')
    op.drop_index('ix_signals_grade', table_name='signals')
    op.drop_index('ix_signals_created_at', table_name='signals')
    op.drop_table('signals')
    op.drop_table('bot_settings')
    op.drop_table('users')
