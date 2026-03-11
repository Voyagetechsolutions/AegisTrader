"""
Configuration serialization and parsing for the Dual-Engine Strategy System.

This module provides functions to serialize Configuration objects to JSON format
and parse JSON back into Configuration objects with validation.

Requirements: 27.1, 27.3, 27.4
"""

import json
from typing import Dict, Any, Union
from backend.strategy.dual_engine_models import (
    Configuration,
    Instrument,
    SessionType,
)


def serialize_configuration(config: Configuration) -> str:
    """
    Serialize a Configuration object to JSON string.
    
    Args:
        config: Configuration object to serialize
        
    Returns:
        JSON string representation of the configuration
        
    Requirements: 27.3
    """
    config_dict = {
        "instruments": [inst.value for inst in config.instruments],
        "signal_window_start": config.signal_window_start,
        "signal_window_end": config.signal_window_end,
        "core_risk_per_trade": config.core_risk_per_trade,
        "core_max_daily_trades": config.core_max_daily_trades,
        "core_max_daily_drawdown": config.core_max_daily_drawdown,
        "scalp_risk_per_trade_min": config.scalp_risk_per_trade_min,
        "scalp_risk_per_trade_max": config.scalp_risk_per_trade_max,
        "scalp_session_limits": {
            session.value: limit 
            for session, limit in config.scalp_session_limits.items()
        },
        "spread_limits_global": {
            inst.value: limit 
            for inst, limit in config.spread_limits_global.items()
        },
        "spread_limits_scalp": {
            inst.value: limit 
            for inst, limit in config.spread_limits_scalp.items()
        },
        "slippage_limit": config.slippage_limit,
        "news_buffer_before": config.news_buffer_before,
        "news_buffer_after": config.news_buffer_after,
    }
    
    return json.dumps(config_dict, indent=2)


def parse_configuration(json_str: str) -> Configuration:
    """
    Parse a JSON string into a Configuration object with validation.
    
    Args:
        json_str: JSON string representation of configuration
        
    Returns:
        Configuration object
        
    Raises:
        ValueError: If JSON is invalid, required fields are missing, or values are out of range
        
    Requirements: 27.1, 27.2, 27.5, 27.6, 27.7
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Validate required fields
    required_fields = [
        "instruments",
        "signal_window_start",
        "signal_window_end",
        "core_risk_per_trade",
        "core_max_daily_trades",
        "core_max_daily_drawdown",
        "scalp_risk_per_trade_min",
        "scalp_risk_per_trade_max",
        "scalp_session_limits",
        "spread_limits_global",
        "spread_limits_scalp",
        "slippage_limit",
        "news_buffer_before",
        "news_buffer_after",
    ]
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Parse instruments
    try:
        instruments = [Instrument(inst) for inst in data["instruments"]]
        if not instruments:
            raise ValueError("instruments list cannot be empty")
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid instrument value: {e}")
    
    # Parse and validate time strings
    signal_window_start = data["signal_window_start"]
    signal_window_end = data["signal_window_end"]
    
    if not _is_valid_time_format(signal_window_start):
        raise ValueError(f"signal_window_start must be in HH:MM format, got: {signal_window_start}")
    if not _is_valid_time_format(signal_window_end):
        raise ValueError(f"signal_window_end must be in HH:MM format, got: {signal_window_end}")
    
    # Parse and validate numeric fields
    try:
        core_risk_per_trade = float(data["core_risk_per_trade"])
        if not (0.0 < core_risk_per_trade <= 0.05):
            raise ValueError(f"core_risk_per_trade must be between 0.0 and 0.05 (0-5%), got: {core_risk_per_trade}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid core_risk_per_trade: {e}")
    
    try:
        core_max_daily_trades = int(data["core_max_daily_trades"])
        if core_max_daily_trades < 1:
            raise ValueError(f"core_max_daily_trades must be at least 1, got: {core_max_daily_trades}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid core_max_daily_trades: {e}")
    
    try:
        core_max_daily_drawdown = float(data["core_max_daily_drawdown"])
        if not (0.0 < core_max_daily_drawdown <= 0.2):
            raise ValueError(f"core_max_daily_drawdown must be between 0.0 and 0.2 (0-20%), got: {core_max_daily_drawdown}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid core_max_daily_drawdown: {e}")
    
    try:
        scalp_risk_per_trade_min = float(data["scalp_risk_per_trade_min"])
        if not (0.0 < scalp_risk_per_trade_min <= 0.01):
            raise ValueError(f"scalp_risk_per_trade_min must be between 0.0 and 0.01 (0-1%), got: {scalp_risk_per_trade_min}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid scalp_risk_per_trade_min: {e}")
    
    try:
        scalp_risk_per_trade_max = float(data["scalp_risk_per_trade_max"])
        if not (0.0 < scalp_risk_per_trade_max <= 0.02):
            raise ValueError(f"scalp_risk_per_trade_max must be between 0.0 and 0.02 (0-2%), got: {scalp_risk_per_trade_max}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid scalp_risk_per_trade_max: {e}")
    
    if scalp_risk_per_trade_min > scalp_risk_per_trade_max:
        raise ValueError(f"scalp_risk_per_trade_min ({scalp_risk_per_trade_min}) cannot be greater than scalp_risk_per_trade_max ({scalp_risk_per_trade_max})")
    
    try:
        slippage_limit = float(data["slippage_limit"])
        if slippage_limit < 0:
            raise ValueError(f"slippage_limit must be non-negative, got: {slippage_limit}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid slippage_limit: {e}")
    
    try:
        news_buffer_before = int(data["news_buffer_before"])
        if news_buffer_before < 0:
            raise ValueError(f"news_buffer_before must be non-negative, got: {news_buffer_before}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid news_buffer_before: {e}")
    
    try:
        news_buffer_after = int(data["news_buffer_after"])
        if news_buffer_after < 0:
            raise ValueError(f"news_buffer_after must be non-negative, got: {news_buffer_after}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid news_buffer_after: {e}")
    
    # Parse scalp session limits
    try:
        scalp_session_limits = {}
        for session, limit in data["scalp_session_limits"].items():
            session_type = SessionType(session)
            limit_int = int(limit)
            if limit_int < 1:
                raise ValueError(f"Session limit for {session} must be at least 1, got: {limit_int}")
            scalp_session_limits[session_type] = limit_int
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid session type or limit in scalp_session_limits: {e}")
    
    # Parse spread limits
    try:
        spread_limits_global = {}
        for inst, limit in data["spread_limits_global"].items():
            instrument = Instrument(inst)
            limit_float = float(limit)
            if limit_float < 0:
                raise ValueError(f"Spread limit for {inst} must be non-negative, got: {limit_float}")
            spread_limits_global[instrument] = limit_float
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid instrument or limit in spread_limits_global: {e}")
    
    try:
        spread_limits_scalp = {}
        for inst, limit in data["spread_limits_scalp"].items():
            instrument = Instrument(inst)
            limit_float = float(limit)
            if limit_float < 0:
                raise ValueError(f"Spread limit for {inst} must be non-negative, got: {limit_float}")
            spread_limits_scalp[instrument] = limit_float
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid instrument or limit in spread_limits_scalp: {e}")
    
    return Configuration(
        instruments=instruments,
        signal_window_start=signal_window_start,
        signal_window_end=signal_window_end,
        core_risk_per_trade=core_risk_per_trade,
        core_max_daily_trades=core_max_daily_trades,
        core_max_daily_drawdown=core_max_daily_drawdown,
        scalp_risk_per_trade_min=scalp_risk_per_trade_min,
        scalp_risk_per_trade_max=scalp_risk_per_trade_max,
        scalp_session_limits=scalp_session_limits,
        spread_limits_global=spread_limits_global,
        spread_limits_scalp=spread_limits_scalp,
        slippage_limit=slippage_limit,
        news_buffer_before=news_buffer_before,
        news_buffer_after=news_buffer_after,
    )


def _is_valid_time_format(time_str: str) -> bool:
    """
    Validate time string is in HH:MM format.
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if valid HH:MM format, False otherwise
    """
    if not isinstance(time_str, str):
        return False
    
    parts = time_str.split(":")
    if len(parts) != 2:
        return False
    
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except ValueError:
        return False
