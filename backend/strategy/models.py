"""
Core data models for the Python Strategy Engine.

Defines the fundamental data structures used throughout the system
for market data, analysis results, and signal generation.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class Timeframe(Enum):
    """Market data timeframes supported by the strategy engine."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    DAILY = "Daily"
    WEEKLY = "Weekly"


class Direction(Enum):
    """Trade direction for signals and analysis."""
    LONG = "long"
    SHORT = "short"


class BiasDirection(Enum):
    """Market bias classification."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULL_SHIFT = "bull_shift"
    BEAR_SHIFT = "bear_shift"


class SetupType(Enum):
    """Trading setup classification."""
    CONTINUATION_LONG = "continuation_long"
    CONTINUATION_SHORT = "continuation_short"
    SWING_LONG = "swing_long"
    SWING_SHORT = "swing_short"


class SignalGrade(Enum):
    """Signal quality grading."""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"


@dataclass
class Candle:
    """OHLCV market data for a specific timeframe."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: Timeframe
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert candle to dictionary for Redis storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timeframe": self.timeframe.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Candle:
        """Create candle from dictionary (Redis retrieval)."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=int(data["volume"]),
            timeframe=Timeframe(data["timeframe"])
        )


@dataclass
class BiasResult:
    """Market bias analysis result."""
    direction: BiasDirection
    ema_distance: float
    structure_shift: Optional[str] = None


@dataclass
class LevelResult:
    """Key level analysis result."""
    nearest_250: float
    nearest_125: float
    distance_to_250: float
    distance_to_125: float


@dataclass
class LiquidityResult:
    """Liquidity sweep analysis result."""
    recent_sweeps: List[Dict[str, Any]]
    sweep_type: Optional[str] = None
    time_since_sweep: Optional[float] = None


@dataclass
class FVGResult:
    """Fair Value Gap analysis result."""
    active_fvgs: List[Dict[str, Any]]
    retest_opportunity: Optional[Dict[str, Any]] = None


@dataclass
class DisplacementResult:
    """Displacement candle analysis result."""
    recent_displacement: Optional[Dict[str, Any]]
    direction: Optional[Direction] = None
    strength: float = 0.0


@dataclass
class StructureResult:
    """Market structure analysis result."""
    recent_breaks: List[Dict[str, Any]]
    current_trend: Optional[Direction] = None
    break_type: Optional[str] = None


@dataclass
class AnalysisResult:
    """Complete analysis result for a timeframe."""
    timestamp: datetime
    timeframe: Timeframe
    bias: BiasResult
    levels: LevelResult
    liquidity: LiquidityResult
    fvg: FVGResult
    displacement: DisplacementResult
    structure: StructureResult
    confluence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe.value,
            "bias": {
                "direction": self.bias.direction.value,
                "ema_distance": self.bias.ema_distance,
                "structure_shift": self.bias.structure_shift
            },
            "levels": {
                "nearest_250": self.levels.nearest_250,
                "nearest_125": self.levels.nearest_125,
                "distance_to_250": self.levels.distance_to_250,
                "distance_to_125": self.levels.distance_to_125
            },
            "liquidity": {
                "recent_sweeps": self.liquidity.recent_sweeps,
                "sweep_type": self.liquidity.sweep_type,
                "time_since_sweep": self.liquidity.time_since_sweep
            },
            "fvg": {
                "active_fvgs": self.fvg.active_fvgs,
                "retest_opportunity": self.fvg.retest_opportunity
            },
            "displacement": {
                "recent_displacement": self.displacement.recent_displacement,
                "direction": self.displacement.direction.value if self.displacement.direction else None,
                "strength": self.displacement.strength
            },
            "structure": {
                "recent_breaks": self.structure.recent_breaks,
                "current_trend": self.structure.current_trend.value if self.structure.current_trend else None,
                "break_type": self.structure.break_type
            },
            "confluence_score": self.confluence_score
        }


@dataclass
class Signal:
    """Trading signal generated by the strategy engine."""
    timestamp: datetime
    setup_type: SetupType
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    confluence_score: float
    grade: SignalGrade
    analysis_breakdown: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for API/storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "setup_type": self.setup_type.value,
            "direction": self.direction.value,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confluence_score": self.confluence_score,
            "grade": self.grade.value,
            "analysis_breakdown": self.analysis_breakdown
        }