"""
Signal serialization and parsing for the Dual-Engine Strategy System.

This module provides functions to serialize Signal objects (CoreSignal and ScalpSignal)
to JSON format and parse JSON back into Signal objects with validation.

Requirements: 28.1, 28.2, 28.5
"""

import json
from datetime import datetime
from typing import Dict, Any, Union
from backend.strategy.dual_engine_models import (
    CoreSignal,
    ScalpSignal,
    ConfluenceScore,
    Instrument,
    Direction,
    SignalGrade,
    SessionType,
)


def serialize_core_signal(signal: CoreSignal) -> str:
    """
    Serialize a CoreSignal object to JSON string with ISO 8601 timestamp.
    
    Args:
        signal: CoreSignal object to serialize
        
    Returns:
        JSON string representation of the signal
        
    Requirements: 28.3, 28.6
    """
    signal_dict = {
        "type": "CORE",
        "instrument": signal.instrument.value,
        "direction": signal.direction.value,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "tp1": signal.tp1,
        "tp2": signal.tp2,
        "confluence_score": {
            "total": signal.confluence_score.total,
            "htf_alignment": signal.confluence_score.htf_alignment,
            "key_level": signal.confluence_score.key_level,
            "liquidity_sweep": signal.confluence_score.liquidity_sweep,
            "fvg": signal.confluence_score.fvg,
            "displacement": signal.confluence_score.displacement,
            "mss": signal.confluence_score.mss,
            "vwap": signal.confluence_score.vwap,
            "volume_spike": signal.confluence_score.volume_spike,
            "atr": signal.confluence_score.atr,
            "htf_target": signal.confluence_score.htf_target,
            "session": signal.confluence_score.session,
            "spread": signal.confluence_score.spread,
        },
        "grade": signal.grade.value,
        "timestamp": signal.timestamp.isoformat(),
    }
    
    return json.dumps(signal_dict, indent=2)


def serialize_scalp_signal(signal: ScalpSignal) -> str:
    """
    Serialize a ScalpSignal object to JSON string with ISO 8601 timestamp.
    
    Args:
        signal: ScalpSignal object to serialize
        
    Returns:
        JSON string representation of the signal
        
    Requirements: 28.3, 28.6
    """
    signal_dict = {
        "type": "SCALP",
        "instrument": signal.instrument.value,
        "direction": signal.direction.value,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "session": signal.session.value,
        "timestamp": signal.timestamp.isoformat(),
    }
    
    return json.dumps(signal_dict, indent=2)


def parse_core_signal(json_str: str) -> CoreSignal:
    """
    Parse a JSON string into a CoreSignal object with validation.
    
    Args:
        json_str: JSON string representation of core signal
        
    Returns:
        CoreSignal object
        
    Raises:
        ValueError: If JSON is invalid or required fields are missing
        
    Requirements: 28.1, 28.2, 28.5
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Validate signal type
    if data.get("type") != "CORE":
        raise ValueError(f"Expected signal type 'CORE', got: {data.get('type')}")
    
    # Validate required fields
    required_fields = [
        "instrument",
        "direction",
        "entry_price",
        "stop_loss",
        "tp1",
        "tp2",
        "confluence_score",
        "grade",
        "timestamp",
    ]
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Parse and validate instrument
    try:
        instrument = Instrument(data["instrument"])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid instrument value: {e}")
    
    # Parse and validate direction
    try:
        direction = Direction(data["direction"])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid direction value: {e}")
    
    # Parse and validate numeric fields
    try:
        entry_price = float(data["entry_price"])
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got: {entry_price}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid entry_price: {e}")
    
    try:
        stop_loss = float(data["stop_loss"])
        if stop_loss <= 0:
            raise ValueError(f"stop_loss must be positive, got: {stop_loss}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid stop_loss: {e}")
    
    try:
        tp1 = float(data["tp1"])
        if tp1 <= 0:
            raise ValueError(f"tp1 must be positive, got: {tp1}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid tp1: {e}")
    
    try:
        tp2 = float(data["tp2"])
        if tp2 <= 0:
            raise ValueError(f"tp2 must be positive, got: {tp2}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid tp2: {e}")
    
    # Parse confluence score
    try:
        confluence_data = data["confluence_score"]
        confluence_score = ConfluenceScore(
            total=int(confluence_data["total"]),
            htf_alignment=int(confluence_data["htf_alignment"]),
            key_level=int(confluence_data["key_level"]),
            liquidity_sweep=int(confluence_data["liquidity_sweep"]),
            fvg=int(confluence_data["fvg"]),
            displacement=int(confluence_data["displacement"]),
            mss=int(confluence_data["mss"]),
            vwap=int(confluence_data["vwap"]),
            volume_spike=int(confluence_data["volume_spike"]),
            atr=int(confluence_data["atr"]),
            htf_target=int(confluence_data["htf_target"]),
            session=int(confluence_data["session"]),
            spread=int(confluence_data["spread"]),
        )
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid confluence_score: {e}")
    
    # Parse and validate grade
    try:
        grade = SignalGrade(data["grade"])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid grade value: {e}")
    
    # Parse and validate timestamp
    try:
        timestamp = datetime.fromisoformat(data["timestamp"])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid timestamp (must be ISO 8601 format): {e}")
    
    return CoreSignal(
        instrument=instrument,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        confluence_score=confluence_score,
        grade=grade,
        timestamp=timestamp,
    )


def parse_scalp_signal(json_str: str) -> ScalpSignal:
    """
    Parse a JSON string into a ScalpSignal object with validation.
    
    Args:
        json_str: JSON string representation of scalp signal
        
    Returns:
        ScalpSignal object
        
    Raises:
        ValueError: If JSON is invalid or required fields are missing
        
    Requirements: 28.1, 28.2, 28.5
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Validate signal type
    if data.get("type") != "SCALP":
        raise ValueError(f"Expected signal type 'SCALP', got: {data.get('type')}")
    
    # Validate required fields
    required_fields = [
        "instrument",
        "direction",
        "entry_price",
        "stop_loss",
        "take_profit",
        "session",
        "timestamp",
    ]
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Parse and validate instrument
    try:
        instrument = Instrument(data["instrument"])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid instrument value: {e}")
    
    # Parse and validate direction
    try:
        direction = Direction(data["direction"])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid direction value: {e}")
    
    # Parse and validate numeric fields
    try:
        entry_price = float(data["entry_price"])
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got: {entry_price}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid entry_price: {e}")
    
    try:
        stop_loss = float(data["stop_loss"])
        if stop_loss <= 0:
            raise ValueError(f"stop_loss must be positive, got: {stop_loss}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid stop_loss: {e}")
    
    try:
        take_profit = float(data["take_profit"])
        if take_profit <= 0:
            raise ValueError(f"take_profit must be positive, got: {take_profit}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid take_profit: {e}")
    
    # Parse and validate session
    try:
        session = SessionType(data["session"])
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid session value: {e}")
    
    # Parse and validate timestamp
    try:
        timestamp = datetime.fromisoformat(data["timestamp"])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid timestamp (must be ISO 8601 format): {e}")
    
    return ScalpSignal(
        instrument=instrument,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        session=session,
        timestamp=timestamp,
    )
