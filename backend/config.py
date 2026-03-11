from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from pathlib import Path
import secrets

# Get absolute path to backend directory for database
_BACKEND_DIR = Path(__file__).resolve().parent
_DEFAULT_DB_PATH = _BACKEND_DIR / "aegis_trader.db"
_PROJECT_ROOT = _BACKEND_DIR.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    port: int = 8000
    # Generate secure random secret if not provided (for cloud deployment)
    dashboard_jwt_secret: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        min_length=32,
        description="JWT signing secret"
    )

    # Database (using SQLite for local dev, PostgreSQL for cloud)
    # Cloud platforms like Render provide DATABASE_URL env var automatically
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}",
        description="Database connection URL"
    )

    @field_validator('database_url')
    @classmethod
    def convert_database_url(cls, v: str) -> str:
        """Convert postgres:// to postgresql+asyncpg:// for async support"""
        if v.startswith('postgres://'):
            return v.replace('postgres://', 'postgresql+asyncpg://', 1)
        elif v.startswith('postgresql://'):
            return v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return v

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # MT5 Execution Node
    mt5_node_url: str = "http://localhost:8001"
    # Generate secure random secret if not provided (for cloud deployment)
    mt5_node_secret: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16),
        min_length=16,
        description="MT5 node authentication secret"
    )

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

    @field_validator('dashboard_jwt_secret', 'mt5_node_secret')
    @classmethod
    def validate_secrets(cls, v: str, info) -> str:
        # Only validate if explicitly set to weak values
        # Auto-generated secrets from default_factory are secure
        if v and v in ('changeme', 'changeme_jwt', 'changeme_mt5', 'test', 'secret'):
            raise ValueError(f"{info.field_name} must not use default/weak values")
        return v

    class Config:
        # Only use .env file if it exists (not available in cloud)
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else None
        case_sensitive = False
        extra = 'ignore'  # Ignore extra environment variables


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
