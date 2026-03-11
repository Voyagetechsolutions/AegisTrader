export type BotMode = 'analyze' | 'trade' | 'swing';
export type BotState = 'running' | 'paused' | 'safe_mode' | 'offline';
export type AccountMode = 'demo' | 'live';
export type SignalGrade = 'A+' | 'A' | 'B';
export type SignalStatus = 'ignored' | 'alerted' | 'executed' | 'blocked';
export type TradeStatus = 'open' | 'partial' | 'closed';
export type Direction = 'long' | 'short';

// Dashboard API types
export interface DashboardStatus {
  mode: string;
  auto_trade_enabled: boolean;
  trades_today: number;
  losses_today: number;
  drawdown_today_pct: number;
  risk_limit_hit: boolean;
  news_blackout_active: boolean;
  active_session: string | null;
  open_positions: number;
  account_balance: number;
  connection_health: {
    database: boolean;
    telegram: boolean;
    mt5_node: boolean;
  };
}

// Legacy BotStatus for backward compatibility
export interface BotStatus {
  mode: BotMode;
  bot_state: BotState;
  account_mode: AccountMode;
  today_pnl: number;
  daily_drawdown_pct: number;
  trades_today: number;
  losses_today: number;
  session_name: string;
  backend_online: boolean;
  mt5_online: boolean;
  last_signal_time: string | null;
  last_trade_time: string | null;
  balance: number;
  open_positions: number;
}

export interface Signal {
  id: string;
  source: string;
  setup_type: string | null;
  direction: string | null;
  analysis_symbol: string;
  execution_symbol: string;
  entry_price: number;
  stop_loss: number;
  tp1: number;
  tp2: number;
  score: number;
  grade: string | null;
  eligible_for_auto_trade: boolean;
  session_name: string | null;
  news_blocked: boolean;
  paper_result: string | null;
  created_at: string | null;
}

export interface Trade {
  id: string;
  broker: string;
  account_type: string;
  mt5_ticket: number | null;
  symbol: string;
  direction: string | null;
  lot_size: number;
  entry_price: number;
  stop_loss: number;
  tp1: number;
  tp2: number;
  actual_entry_price: number | null;
  status: string | null;
  state: string | null;
  tp1_hit: boolean;
  tp2_hit: boolean;
  runner_active: boolean;
  breakeven_active: boolean;
  pnl: number | null;
  close_reason: string | null;
  opened_at: string | null;
  closed_at: string | null;
}

export interface SwingApproval {
  id: string;
  timestamp: string;
  direction: Direction;
  score: number;
  entry: number;
  sl: number;
  tp: number;
  expires_at: string;
}

export interface WeeklyOverview {
  weekly_bias: string;
  daily_bias: string;
  h4_bias: string;
  h1_bias: string;
  m15_bias: string;
  m5_bias: string;
  m1_bias: string;
  bullish_scenario: string;
  bearish_scenario: string;
  key_levels: number[];
  major_news: Array<{
    date: string;
    event: string;
    impact: string;
  }>;
}

// Dual-Engine System Types
export interface MarketRegime {
  instrument: string;
  volatility: string; // LOW, NORMAL, HIGH, EXTREME
  trend: string; // STRONG_TREND, WEAK_TREND, RANGING, CHOPPY
  atr_current: number;
  atr_average: number;
  atr_ratio: number;
  timestamp: string;
}

export interface EnginePerformance {
  engine: string;
  instrument: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  average_rr: number;
  profit_factor: number;
  consecutive_wins: number;
  consecutive_losses: number;
}

export interface EngineStatus {
  engine: string;
  active: boolean;
  trades_today: number;
  daily_limit: number;
  can_trade: boolean;
  block_reason: string | null;
  performance: EnginePerformance | null;
}

export interface DualEngineStatus {
  core_strategy: EngineStatus;
  quick_scalp: EngineStatus;
  market_regimes: MarketRegime[];
  active_signals: number;
  last_decision: string | null;
  timestamp: string;
}

export interface UnifiedSignal {
  signal_id: string;
  engine: string;
  instrument: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  tp1: number;
  tp2: number | null;
  risk_reward_ratio: number;
  status: string;
  grade: string | null;
  score: number | null;
  session: string | null;
  timestamp: string;
  reasons: string[];
}
