from backend.modules.confluence_scoring import score_setup, score_from_payload, ConfluenceResult
from backend.modules.session_filter import get_active_session, is_within_session
from backend.modules.spread_filter import check_spread, record_spread, get_average_spread
from backend.modules.news_filter import check_news_blackout, sync_forexfactory_news
from backend.modules.risk_engine import check_risk, disable_auto_trading
from backend.modules.signal_engine import process_signal
from backend.modules.alert_manager import send_message, send_signal_alert, send_trade_open_alert
from backend.modules.trade_manager import open_trade, handle_tp1, handle_tp2, close_trade, close_all_trades
from backend.modules.analytics_engine import compute_strategy_stats, generate_weekly_report

__all__ = [
    "score_setup", "score_from_payload", "ConfluenceResult",
    "get_active_session", "is_within_session",
    "check_spread", "record_spread", "get_average_spread",
    "check_news_blackout", "sync_forexfactory_news",
    "check_risk", "disable_auto_trading",
    "process_signal",
    "send_message", "send_signal_alert", "send_trade_open_alert",
    "open_trade", "handle_tp1", "handle_tp2", "close_trade", "close_all_trades",
    "compute_strategy_stats", "generate_weekly_report",
]
