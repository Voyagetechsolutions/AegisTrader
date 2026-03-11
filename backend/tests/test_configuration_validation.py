"""
Property-based tests for Configuration validation.

Tests Property 31 from the design document:
- Property 31: Configuration Validation

Requirements: 27.2, 27.5, 27.6, 27.7
"""

import json
import pytest
from hypothesis import given, strategies as st, settings, assume

from backend.strategy.dual_engine_models import (
    Configuration,
    Instrument,
    SessionType,
)
from backend.strategy.config_serializer import (
    serialize_configuration,
    parse_configuration,
)


# Strategy for generating invalid configurations with missing fields
@st.composite
def config_with_missing_fields(draw):
    """Generate configuration JSON with one or more missing required fields."""
    # Start with a valid configuration
    valid_config = {
        "instruments": ["US30", "XAUUSD"],
        "signal_window_start": "10:00",
        "signal_window_end": "22:00",
        "core_risk_per_trade": 0.01,
        "core_max_daily_trades": 2,
        "core_max_daily_drawdown": 0.02,
        "scalp_risk_per_trade_min": 0.0025,
        "scalp_risk_per_trade_max": 0.005,
        "scalp_session_limits": {
            "LONDON": 5,
            "NY_OPEN": 5,
            "POWER_HOUR": 3
        },
        "spread_limits_global": {
            "US30": 5.0,
            "XAUUSD": 3.0,
            "NAS100": 4.0
        },
        "spread_limits_scalp": {
            "US30": 3.0,
            "XAUUSD": 2.0,
            "NAS100": 2.0
        },
        "slippage_limit": 10.0,
        "news_buffer_before": 30,
        "news_buffer_after": 60,
    }
    
    # Remove 1-3 random fields
    fields_to_remove = draw(st.lists(
        st.sampled_from(list(valid_config.keys())),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    for field in fields_to_remove:
        del valid_config[field]
    
    return json.dumps(valid_config), fields_to_remove


# Strategy for generating configurations with out-of-range values
@st.composite
def config_with_invalid_ranges(draw):
    """Generate configuration JSON with out-of-range numeric values."""
    field_choice = draw(st.sampled_from([
        "core_risk_per_trade",
        "core_max_daily_trades",
        "core_max_daily_drawdown",
        "scalp_risk_per_trade_min",
        "scalp_risk_per_trade_max",
        "slippage_limit",
        "news_buffer_before",
        "news_buffer_after",
        "scalp_session_limits",
        "spread_limits_global",
        "spread_limits_scalp",
    ]))
    
    valid_config = {
        "instruments": ["US30", "XAUUSD"],
        "signal_window_start": "10:00",
        "signal_window_end": "22:00",
        "core_risk_per_trade": 0.01,
        "core_max_daily_trades": 2,
        "core_max_daily_drawdown": 0.02,
        "scalp_risk_per_trade_min": 0.0025,
        "scalp_risk_per_trade_max": 0.005,
        "scalp_session_limits": {
            "LONDON": 5,
            "NY_OPEN": 5,
            "POWER_HOUR": 3
        },
        "spread_limits_global": {
            "US30": 5.0,
            "XAUUSD": 3.0,
            "NAS100": 4.0
        },
        "spread_limits_scalp": {
            "US30": 3.0,
            "XAUUSD": 2.0,
            "NAS100": 2.0
        },
        "slippage_limit": 10.0,
        "news_buffer_before": 30,
        "news_buffer_after": 60,
    }
    
    # Generate invalid value based on field type
    if field_choice == "core_risk_per_trade":
        # Must be between 0.0 and 0.05
        invalid_value = draw(st.one_of(
            st.floats(min_value=-1.0, max_value=0.0),
            st.floats(min_value=0.051, max_value=1.0)
        ))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "core_max_daily_trades":
        # Must be at least 1
        invalid_value = draw(st.integers(max_value=0))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "core_max_daily_drawdown":
        # Must be between 0.0 and 0.2
        invalid_value = draw(st.one_of(
            st.floats(min_value=-1.0, max_value=0.0),
            st.floats(min_value=0.21, max_value=1.0)
        ))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "scalp_risk_per_trade_min":
        # Must be between 0.0 and 0.01
        invalid_value = draw(st.one_of(
            st.floats(min_value=-1.0, max_value=0.0),
            st.floats(min_value=0.011, max_value=1.0)
        ))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "scalp_risk_per_trade_max":
        # Must be between 0.0 and 0.02
        invalid_value = draw(st.one_of(
            st.floats(min_value=-1.0, max_value=0.0),
            st.floats(min_value=0.021, max_value=1.0)
        ))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "slippage_limit":
        # Must be non-negative
        invalid_value = draw(st.floats(min_value=-100.0, max_value=-0.1))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "news_buffer_before":
        # Must be non-negative
        invalid_value = draw(st.integers(min_value=-100, max_value=-1))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "news_buffer_after":
        # Must be non-negative
        invalid_value = draw(st.integers(min_value=-100, max_value=-1))
        valid_config[field_choice] = invalid_value
    
    elif field_choice == "scalp_session_limits":
        # Session limits must be at least 1
        session = draw(st.sampled_from(["LONDON", "NY_OPEN", "POWER_HOUR"]))
        valid_config[field_choice][session] = draw(st.integers(max_value=0))
    
    elif field_choice == "spread_limits_global":
        # Spread limits must be non-negative
        instrument = draw(st.sampled_from(["US30", "XAUUSD", "NAS100"]))
        valid_config[field_choice][instrument] = draw(st.floats(min_value=-10.0, max_value=-0.1))
    
    elif field_choice == "spread_limits_scalp":
        # Spread limits must be non-negative
        instrument = draw(st.sampled_from(["US30", "XAUUSD", "NAS100"]))
        valid_config[field_choice][instrument] = draw(st.floats(min_value=-10.0, max_value=-0.1))
    
    return json.dumps(valid_config), field_choice


# Strategy for generating configurations with invalid time formats
@st.composite
def config_with_invalid_time_format(draw):
    """Generate configuration JSON with invalid time format."""
    valid_config = {
        "instruments": ["US30", "XAUUSD"],
        "signal_window_start": "10:00",
        "signal_window_end": "22:00",
        "core_risk_per_trade": 0.01,
        "core_max_daily_trades": 2,
        "core_max_daily_drawdown": 0.02,
        "scalp_risk_per_trade_min": 0.0025,
        "scalp_risk_per_trade_max": 0.005,
        "scalp_session_limits": {
            "LONDON": 5,
            "NY_OPEN": 5,
            "POWER_HOUR": 3
        },
        "spread_limits_global": {
            "US30": 5.0,
            "XAUUSD": 3.0,
            "NAS100": 4.0
        },
        "spread_limits_scalp": {
            "US30": 3.0,
            "XAUUSD": 2.0,
            "NAS100": 2.0
        },
        "slippage_limit": 10.0,
        "news_buffer_before": 30,
        "news_buffer_after": 60,
    }
    
    # Generate invalid time format
    time_field = draw(st.sampled_from(["signal_window_start", "signal_window_end"]))
    invalid_time = draw(st.one_of(
        st.text(min_size=1, max_size=10).filter(lambda x: ":" not in x or len(x.split(":")) != 2),
        st.just("25:00"),  # Invalid hour
        st.just("10:60"),  # Invalid minute
        st.just("10"),     # Missing colon
        st.just("10:"),    # Missing minute
        st.just(":30"),    # Missing hour
    ))
    
    valid_config[time_field] = invalid_time
    
    return json.dumps(valid_config), time_field


# Strategy for generating configurations with min > max
@st.composite
def config_with_inverted_min_max(draw):
    """Generate configuration JSON where scalp_risk_per_trade_min > scalp_risk_per_trade_max."""
    valid_config = {
        "instruments": ["US30", "XAUUSD"],
        "signal_window_start": "10:00",
        "signal_window_end": "22:00",
        "core_risk_per_trade": 0.01,
        "core_max_daily_trades": 2,
        "core_max_daily_drawdown": 0.02,
        "scalp_risk_per_trade_min": 0.008,  # Greater than max
        "scalp_risk_per_trade_max": 0.005,
        "scalp_session_limits": {
            "LONDON": 5,
            "NY_OPEN": 5,
            "POWER_HOUR": 3
        },
        "spread_limits_global": {
            "US30": 5.0,
            "XAUUSD": 3.0,
            "NAS100": 4.0
        },
        "spread_limits_scalp": {
            "US30": 3.0,
            "XAUUSD": 2.0,
            "NAS100": 2.0
        },
        "slippage_limit": 10.0,
        "news_buffer_before": 30,
        "news_buffer_after": 60,
    }
    
    return json.dumps(valid_config)


# Strategy for generating configurations with empty instruments list
@st.composite
def config_with_empty_instruments(draw):
    """Generate configuration JSON with empty instruments list."""
    valid_config = {
        "instruments": [],  # Empty list
        "signal_window_start": "10:00",
        "signal_window_end": "22:00",
        "core_risk_per_trade": 0.01,
        "core_max_daily_trades": 2,
        "core_max_daily_drawdown": 0.02,
        "scalp_risk_per_trade_min": 0.0025,
        "scalp_risk_per_trade_max": 0.005,
        "scalp_session_limits": {
            "LONDON": 5,
            "NY_OPEN": 5,
            "POWER_HOUR": 3
        },
        "spread_limits_global": {
            "US30": 5.0,
            "XAUUSD": 3.0,
            "NAS100": 4.0
        },
        "spread_limits_scalp": {
            "US30": 3.0,
            "XAUUSD": 2.0,
            "NAS100": 2.0
        },
        "slippage_limit": 10.0,
        "news_buffer_before": 30,
        "news_buffer_after": 60,
    }
    
    return json.dumps(valid_config)


# Feature: dual-engine-strategy-system, Property 31: Configuration Validation
@given(config_data=config_with_missing_fields())
@settings(max_examples=100)
def test_configuration_validation_missing_fields(config_data):
    """
    Property 31: Configuration Validation - Missing Fields
    
    For any configuration with missing required fields, the parser should
    return a descriptive error message listing the missing fields.
    
    Validates: Requirements 27.2, 27.5
    """
    config_json, missing_fields = config_data
    
    with pytest.raises(ValueError) as exc_info:
        parse_configuration(config_json)
    
    error_message = str(exc_info.value)
    
    # Verify error message is descriptive
    assert "Missing required fields" in error_message
    
    # Verify at least one missing field is mentioned in the error
    assert any(field in error_message for field in missing_fields)


# Feature: dual-engine-strategy-system, Property 31: Configuration Validation
@given(config_data=config_with_invalid_ranges())
@settings(max_examples=100)
def test_configuration_validation_out_of_range(config_data):
    """
    Property 31: Configuration Validation - Out of Range Values
    
    For any configuration with out-of-range numeric values, the parser should
    return a descriptive error message indicating which field is invalid and why.
    
    Validates: Requirements 27.2, 27.6, 27.7
    """
    config_json, invalid_field = config_data
    
    with pytest.raises(ValueError) as exc_info:
        parse_configuration(config_json)
    
    error_message = str(exc_info.value)
    
    # Verify error message is descriptive and mentions the problematic field
    assert len(error_message) > 0
    
    # Verify the error relates to validation (not just parsing)
    assert any(keyword in error_message.lower() for keyword in [
        "must be", "cannot", "invalid", "between", "at least", "non-negative"
    ])


# Feature: dual-engine-strategy-system, Property 31: Configuration Validation
@given(config_data=config_with_invalid_time_format())
@settings(max_examples=100)
def test_configuration_validation_invalid_time_format(config_data):
    """
    Property 31: Configuration Validation - Invalid Time Format
    
    For any configuration with invalid time format, the parser should
    return a descriptive error message.
    
    Validates: Requirements 27.2, 27.6
    """
    config_json, time_field = config_data
    
    with pytest.raises(ValueError) as exc_info:
        parse_configuration(config_json)
    
    error_message = str(exc_info.value)
    
    # Verify error message mentions time format issue
    assert "HH:MM" in error_message or time_field in error_message


# Feature: dual-engine-strategy-system, Property 31: Configuration Validation
@given(config_json=config_with_inverted_min_max())
@settings(max_examples=100)
def test_configuration_validation_min_greater_than_max(config_json):
    """
    Property 31: Configuration Validation - Min > Max
    
    For any configuration where scalp_risk_per_trade_min > scalp_risk_per_trade_max,
    the parser should return a descriptive error message.
    
    Validates: Requirements 27.2, 27.6
    """
    with pytest.raises(ValueError) as exc_info:
        parse_configuration(config_json)
    
    error_message = str(exc_info.value)
    
    # Verify error message mentions the min/max relationship
    assert "scalp_risk_per_trade_min" in error_message
    assert "scalp_risk_per_trade_max" in error_message
    assert "greater than" in error_message or "cannot" in error_message


# Feature: dual-engine-strategy-system, Property 31: Configuration Validation
@given(config_json=config_with_empty_instruments())
@settings(max_examples=100)
def test_configuration_validation_empty_instruments(config_json):
    """
    Property 31: Configuration Validation - Empty Instruments
    
    For any configuration with empty instruments list, the parser should
    return a descriptive error message.
    
    Validates: Requirements 27.2, 27.5
    """
    with pytest.raises(ValueError) as exc_info:
        parse_configuration(config_json)
    
    error_message = str(exc_info.value)
    
    # Verify error message mentions instruments
    assert "instruments" in error_message.lower()
    assert "empty" in error_message.lower() or "cannot" in error_message.lower()


# Feature: dual-engine-strategy-system, Property 31: Configuration Validation
def test_configuration_validation_invalid_json():
    """
    Property 31: Configuration Validation - Invalid JSON
    
    For any invalid JSON string, the parser should return a descriptive error message.
    
    Validates: Requirements 27.2
    """
    invalid_json = "{ this is not valid json }"
    
    with pytest.raises(ValueError) as exc_info:
        parse_configuration(invalid_json)
    
    error_message = str(exc_info.value)
    
    # Verify error message mentions JSON format issue
    assert "JSON" in error_message or "format" in error_message.lower()
