"""
Configuration management for the Python Strategy Engine.

Handles environment variables, Redis connection settings, and
analysis parameters for the strategy engine components.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, Any, Optional
import redis.asyncio as redis


class StrategyEngineSettings(BaseSettings):
    """Configuration settings for the Python Strategy Engine."""
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 1  # Use separate DB from main application
    redis_password: str = ""  # Load from environment variable in production
    
    # Market Data Configuration
    mt5_symbol: str = "US30"
    data_fetch_interval: int = 60  # seconds
    max_candles_1m: int = 2000
    max_candles_higher_tf: int = 500
    
    # Analysis Parameters
    ema_period: int = 21
    level_250_increment: int = 250
    level_125_increment: int = 125
    level_250_tolerance: int = 30
    level_125_tolerance: int = 20
    
    # FVG Parameters
    fvg_min_gap: int = 20  # points
    fvg_history_hours: int = 48
    
    # Liquidity Parameters
    liquidity_sweep_threshold: int = 10  # points
    liquidity_history_hours: int = 24
    
    # Displacement Parameters
    displacement_min_points: int = 50
    displacement_body_percentage: float = 0.8
    displacement_history_hours: int = 12
    
    # Structure Parameters
    structure_history_hours: int = 24
    
    # Performance Settings
    max_processing_time: int = 5  # seconds
    memory_limit_mb: int = 512
    
    # Session Configuration
    london_start: str = "10:00"
    london_end: str = "13:00"
    ny_start: str = "15:30"
    ny_end: str = "17:30"
    power_start: str = "20:00"
    power_end: str = "22:00"
    timezone: str = "Africa/Johannesburg"
    
    class Config:
        env_prefix = "STRATEGY_"
        case_sensitive = False


@lru_cache()
def get_strategy_settings() -> StrategyEngineSettings:
    """Get cached strategy engine settings."""
    return StrategyEngineSettings()


class RedisManager:
    """Redis connection and key management for the strategy engine."""
    
    def __init__(self, settings: StrategyEngineSettings):
        self.settings = settings
        self._redis: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis connection with lazy initialization."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.settings.redis_url,
                db=self.settings.redis_db,
                password=self.settings.redis_password or None,
                decode_responses=True
            )
        return self._redis
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
    
    # Key patterns for different data types
    @staticmethod
    def candle_key(timeframe: str) -> str:
        """Redis key for candle data."""
        return f"candles:{timeframe}"
    
    @staticmethod
    def analysis_key(timeframe: str) -> str:
        """Redis key for analysis results."""
        return f"analysis:{timeframe}"
    
    @staticmethod
    def signal_key() -> str:
        """Redis key for recent signals."""
        return "signals:recent"
    
    @staticmethod
    def level_key() -> str:
        """Redis key for current levels."""
        return "levels:current"
    
    @staticmethod
    def fvg_key() -> str:
        """Redis key for active FVGs."""
        return "fvg:active"
    
    @staticmethod
    def liquidity_key() -> str:
        """Redis key for liquidity sweeps."""
        return "liquidity:sweeps"


# Global instances
strategy_settings = get_strategy_settings()
redis_manager = RedisManager(strategy_settings)