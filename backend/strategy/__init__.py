"""
Python Strategy Engine for Aegis Trader

Real-time market analysis and signal generation system that replaces
TradingView webhook dependencies with native Python technical analysis.
"""

__version__ = "1.0.0"

from backend.strategy.models import (
    Candle,
    Timeframe,
    Direction,
    BiasDirection,
    SetupType,
    SignalGrade,
    Signal,
    AnalysisResult,
)
from backend.strategy.config import strategy_settings, redis_manager
from backend.strategy.market_data import market_data_layer, MarketDataLayer
from backend.strategy.candle_aggregator import candle_aggregator, CandleAggregator
from backend.strategy.session_manager import session_manager, SessionManager
from backend.strategy.signal_generator import signal_generator, SignalGenerator
from backend.strategy.risk_integration import risk_integration, RiskIntegration
from backend.strategy.engine import strategy_engine, StrategyEngine
from backend.strategy.exceptions import (
    StrategyEngineError,
    MarketDataError,
    MT5ConnectionError,
    DataValidationError,
    RedisConnectionError,
)

__all__ = [
    # Models
    "Candle",
    "Timeframe",
    "Direction",
    "BiasDirection",
    "SetupType",
    "SignalGrade",
    "Signal",
    "AnalysisResult",
    # Config
    "strategy_settings",
    "redis_manager",
    # Market Data
    "market_data_layer",
    "MarketDataLayer",
    # Candle Aggregator
    "candle_aggregator",
    "CandleAggregator",
    # Session Manager
    "session_manager",
    "SessionManager",
    # Signal Generator
    "signal_generator",
    "SignalGenerator",
    # Risk Integration
    "risk_integration",
    "RiskIntegration",
    # Engine
    "strategy_engine",
    "StrategyEngine",
    # Exceptions
    "StrategyEngineError",
    "MarketDataError",
    "MT5ConnectionError",
    "DataValidationError",
    "RedisConnectionError",
]