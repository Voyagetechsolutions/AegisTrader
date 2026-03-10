from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Get absolute path to backend directory for database
_BACKEND_DIR = Path(__file__).resolve().parent
_DEFAULT_DB_PATH = _BACKEND_DIR / "aegis_trader.db"


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    port: int = 8000
    webhook_secret: str = "changeme"
    dashboard_jwt_secret: str = "changeme_jwt"

    # Database (using SQLite for local dev with absolute path)
    database_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # MT5 Execution Node
    mt5_node_url: str = "http://localhost:8001"
    mt5_node_secret: str = "changeme_mt5"

    # Risk Defaults
    max_daily_trades: int = 2
    max_daily_losses: int = 2
    max_daily_drawdown_pct: float = 2.0
    max_spread_points: float = 5.0
    max_slippage_points: float = 10.0

    # News Filter
    news_filter_bypass: bool = False

    # Timezone
    timezone: str = "Africa/Johannesburg"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
