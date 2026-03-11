"""
Custom exceptions for the Python Strategy Engine.

Defines specific exception types for different error conditions
to enable proper error handling and recovery.
"""


class StrategyEngineError(Exception):
    """Base exception for all strategy engine errors."""
    pass


class MarketDataError(StrategyEngineError):
    """Raised when market data operations fail."""
    pass


class MT5ConnectionError(MarketDataError):
    """Raised when MT5 connection fails."""
    pass


class DataValidationError(MarketDataError):
    """Raised when market data validation fails."""
    pass


class RedisConnectionError(StrategyEngineError):
    """Raised when Redis connection fails."""
    pass


class AnalysisEngineError(StrategyEngineError):
    """Raised when analysis engine operations fail."""
    pass


class SignalGenerationError(StrategyEngineError):
    """Raised when signal generation fails."""
    pass


class ConfigurationError(StrategyEngineError):
    """Raised when configuration is invalid."""
    pass


class PerformanceError(StrategyEngineError):
    """Raised when performance targets are not met."""
    pass