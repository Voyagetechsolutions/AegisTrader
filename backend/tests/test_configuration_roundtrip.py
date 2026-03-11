"""
Property-based tests for Configuration serialization and parsing.

Tests Property 30 from the design document:
- Property 30: Configuration Round-Trip

Requirements: 27.1, 27.3, 27.4
"""

import pytest
from hypothesis import given, strategies as st, settings

from backend.strategy.dual_engine_models import (
    Configuration,
    Instrument,
    SessionType,
)
from backend.strategy.config_serializer import (
    serialize_configuration,
    parse_configuration,
)


# Strategy for generating valid time strings in HH:MM format
@st.composite
def time_string(draw):
    """Generate valid time strings in HH:MM format."""
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    return f"{hour:02d}:{minute:02d}"


# Strategy for generating valid instrument lists
@st.composite
def instrument_list(draw):
    """Generate non-empty list of unique instruments."""
    instruments = draw(
        st.lists(
            st.sampled_from(list(Instrument)),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    return instruments


# Strategy for generating session limits dictionary
@st.composite
def session_limits_dict(draw):
    """Generate dictionary mapping SessionType to trade limits."""
    return {
        SessionType.LONDON: draw(st.integers(min_value=1, max_value=10)),
        SessionType.NY_OPEN: draw(st.integers(min_value=1, max_value=10)),
        SessionType.POWER_HOUR: draw(st.integers(min_value=1, max_value=10)),
    }


# Strategy for generating spread limits dictionary
@st.composite
def spread_limits_dict(draw, instruments):
    """Generate dictionary mapping Instrument to spread limits."""
    return {
        inst: draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False))
        for inst in instruments
    }


# Strategy for generating valid Configuration objects
@st.composite
def configuration_strategy(draw):
    """Generate random valid Configuration objects."""
    instruments = draw(instrument_list())
    
    # Generate time window (ensure start < end)
    start_hour = draw(st.integers(min_value=0, max_value=22))
    start_minute = draw(st.integers(min_value=0, max_value=59))
    end_hour = draw(st.integers(min_value=start_hour, max_value=23))
    
    if end_hour == start_hour:
        end_minute = draw(st.integers(min_value=start_minute + 1, max_value=59))
    else:
        end_minute = draw(st.integers(min_value=0, max_value=59))
    
    signal_window_start = f"{start_hour:02d}:{start_minute:02d}"
    signal_window_end = f"{end_hour:02d}:{end_minute:02d}"
    
    # Generate risk parameters
    core_risk = draw(st.floats(min_value=0.001, max_value=0.05, allow_nan=False, allow_infinity=False))
    scalp_risk_min = draw(st.floats(min_value=0.001, max_value=0.01, allow_nan=False, allow_infinity=False))
    scalp_risk_max = draw(st.floats(min_value=scalp_risk_min, max_value=0.02, allow_nan=False, allow_infinity=False))
    
    config = Configuration(
        instruments=instruments,
        signal_window_start=signal_window_start,
        signal_window_end=signal_window_end,
        core_risk_per_trade=core_risk,
        core_max_daily_trades=draw(st.integers(min_value=1, max_value=10)),
        core_max_daily_drawdown=draw(st.floats(min_value=0.01, max_value=0.1, allow_nan=False, allow_infinity=False)),
        scalp_risk_per_trade_min=scalp_risk_min,
        scalp_risk_per_trade_max=scalp_risk_max,
        scalp_session_limits=draw(session_limits_dict()),
        spread_limits_global=draw(spread_limits_dict(instruments)),
        spread_limits_scalp=draw(spread_limits_dict(instruments)),
        slippage_limit=draw(st.floats(min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False)),
        news_buffer_before=draw(st.integers(min_value=10, max_value=120)),
        news_buffer_after=draw(st.integers(min_value=10, max_value=180)),
    )
    
    return config


# Feature: dual-engine-strategy-system, Property 30: Configuration Round-Trip
@given(config=configuration_strategy())
@settings(max_examples=100)
def test_configuration_roundtrip(config):
    """
    Property 30: Configuration Round-Trip
    
    For any valid Configuration object, serializing then parsing should produce
    an equivalent Configuration object with all fields preserved.
    
    Validates: Requirements 27.1, 27.3, 27.4
    """
    # Serialize the configuration
    serialized = serialize_configuration(config)
    
    # Parse it back
    parsed = parse_configuration(serialized)
    
    # Verify all fields are preserved
    assert parsed.instruments == config.instruments
    assert parsed.signal_window_start == config.signal_window_start
    assert parsed.signal_window_end == config.signal_window_end
    assert parsed.core_risk_per_trade == config.core_risk_per_trade
    assert parsed.core_max_daily_trades == config.core_max_daily_trades
    assert parsed.core_max_daily_drawdown == config.core_max_daily_drawdown
    assert parsed.scalp_risk_per_trade_min == config.scalp_risk_per_trade_min
    assert parsed.scalp_risk_per_trade_max == config.scalp_risk_per_trade_max
    assert parsed.scalp_session_limits == config.scalp_session_limits
    assert parsed.spread_limits_global == config.spread_limits_global
    assert parsed.spread_limits_scalp == config.spread_limits_scalp
    assert parsed.slippage_limit == config.slippage_limit
    assert parsed.news_buffer_before == config.news_buffer_before
    assert parsed.news_buffer_after == config.news_buffer_after
    
    # Verify double round-trip (serialize → parse → serialize produces same result)
    serialized_again = serialize_configuration(parsed)
    parsed_again = parse_configuration(serialized_again)
    
    assert parsed_again.instruments == config.instruments
    assert parsed_again.signal_window_start == config.signal_window_start
    assert parsed_again.signal_window_end == config.signal_window_end
    assert parsed_again.core_risk_per_trade == config.core_risk_per_trade
    assert parsed_again.core_max_daily_trades == config.core_max_daily_trades
    assert parsed_again.core_max_daily_drawdown == config.core_max_daily_drawdown
    assert parsed_again.scalp_risk_per_trade_min == config.scalp_risk_per_trade_min
    assert parsed_again.scalp_risk_per_trade_max == config.scalp_risk_per_trade_max
    assert parsed_again.scalp_session_limits == config.scalp_session_limits
    assert parsed_again.spread_limits_global == config.spread_limits_global
    assert parsed_again.spread_limits_scalp == config.spread_limits_scalp
    assert parsed_again.slippage_limit == config.slippage_limit
    assert parsed_again.news_buffer_before == config.news_buffer_before
    assert parsed_again.news_buffer_after == config.news_buffer_after
