"""
Unified Signal Contract for Dual-Engine Strategy System.

Both Core Strategy and Quick Scalp engines must output signals using this
normalized contract. This prevents integration rot and enables clean routing.

Without this, you get messy different payloads and stupid bug farms.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
from backend.strategy.dual_engine_models import (
    Instrument,
    Direction,
    EngineType,
    SignalGrade
)


class SignalType(Enum):
    """Type of trading signal."""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    MODIFY = "MODIFY"


class SignalStatus(Enum):
    """Status of signal processing."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


@dataclass
class SignalReason:
    """Detailed reasoning for signal generation."""
    # Core factors
    htf_alignment: Optional[str] = None
    key_level: Optional[str] = None
    liquidity_sweep: Optional[str] = None
    fvg: Optional[str] = None
    displacement: Optional[str] = None
    mss: Optional[str] = None
    
    # Additional factors
    vwap: Optional[str] = None
    volume: Optional[str] = None
    atr: Optional[str] = None
    session: Optional[str] = None
    
    # Scalp-specific
    momentum_candle: Optional[str] = None
    micro_structure: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary, excluding None values."""
        return {
            k: v for k, v in self.__dict__.items()
            if v is not None
        }
    
    def to_string(self) -> str:
        """Convert to human-readable string."""
        reasons = []
        for key, value in self.to_dict().items():
            reasons.append(f"{key}: {value}")
        return " | ".join(reasons)


@dataclass
class UnifiedSignal:
    """
    Normalized signal contract for both engines.
    
    This is what both Core Strategy and Quick Scalp engines must output.
    Enables clean routing and prevents integration rot.
    """
    # Identity
    signal_id: str
    engine: EngineType
    signal_type: SignalType
    
    # Market
    instrument: Instrument
    direction: Direction
    
    # Quality
    grade: SignalGrade
    score: float  # 0-100 for Core, 0-100 for Scalp
    
    # Execution
    entry_price: float
    stop_loss: float
    
    # Take profits (Core has multiple, Scalp has one)
    tp1: float
    tp1_size: float  # Percentage of position (0.0-1.0)
    tp2: Optional[float] = None
    tp2_size: Optional[float] = None
    tp3: Optional[float] = None  # Runner for Core
    tp3_size: Optional[float] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    status: SignalStatus = SignalStatus.PENDING
    
    # Reasoning
    reasons: SignalReason = field(default_factory=SignalReason)
    
    # Risk
    risk_amount: Optional[float] = None  # In account currency
    position_size: Optional[float] = None  # In lots
    
    # Validation
    spread_check: bool = False
    session_check: bool = False
    news_check: bool = False
    
    def __post_init__(self):
        """Validate signal after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate signal parameters."""
        # Entry must be between stop loss and take profits
        if self.direction == Direction.LONG:
            if self.entry_price <= self.stop_loss:
                raise ValueError(
                    f"Long entry ({self.entry_price}) must be above "
                    f"stop loss ({self.stop_loss})"
                )
            if self.entry_price >= self.tp1:
                raise ValueError(
                    f"Long entry ({self.entry_price}) must be below "
                    f"TP1 ({self.tp1})"
                )
        else:  # SHORT
            if self.entry_price >= self.stop_loss:
                raise ValueError(
                    f"Short entry ({self.entry_price}) must be below "
                    f"stop loss ({self.stop_loss})"
                )
            if self.entry_price <= self.tp1:
                raise ValueError(
                    f"Short entry ({self.entry_price}) must be above "
                    f"TP1 ({self.tp1})"
                )
        
        # TP sizes must sum to 1.0 or less
        total_tp_size = self.tp1_size
        if self.tp2_size:
            total_tp_size += self.tp2_size
        if self.tp3_size:
            total_tp_size += self.tp3_size
        
        if total_tp_size > 1.0:
            raise ValueError(
                f"TP sizes sum to {total_tp_size}, must be <= 1.0"
            )
        
        # Score must be 0-100
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score must be 0-100, got {self.score}")
    
    def get_risk_reward_ratio(self) -> float:
        """Calculate risk-reward ratio to TP1."""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.tp1 - self.entry_price)
        return reward / risk if risk > 0 else 0.0
    
    def get_total_risk_reward(self) -> float:
        """Calculate weighted average R:R across all TPs."""
        risk = abs(self.entry_price - self.stop_loss)
        if risk == 0:
            return 0.0
        
        total_rr = 0.0
        
        # TP1
        reward1 = abs(self.tp1 - self.entry_price)
        total_rr += (reward1 / risk) * self.tp1_size
        
        # TP2
        if self.tp2 and self.tp2_size:
            reward2 = abs(self.tp2 - self.entry_price)
            total_rr += (reward2 / risk) * self.tp2_size
        
        # TP3
        if self.tp3 and self.tp3_size:
            reward3 = abs(self.tp3 - self.entry_price)
            total_rr += (reward3 / risk) * self.tp3_size
        
        return total_rr
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "signal_id": self.signal_id,
            "engine": self.engine.value,
            "signal_type": self.signal_type.value,
            "instrument": self.instrument.value,
            "direction": self.direction.value,
            "grade": self.grade.value,
            "score": self.score,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "tp1": self.tp1,
            "tp1_size": self.tp1_size,
            "tp2": self.tp2,
            "tp2_size": self.tp2_size,
            "tp3": self.tp3,
            "tp3_size": self.tp3_size,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "reasons": self.reasons.to_dict(),
            "risk_amount": self.risk_amount,
            "position_size": self.position_size,
            "spread_check": self.spread_check,
            "session_check": self.session_check,
            "news_check": self.news_check,
            "risk_reward_ratio": self.get_risk_reward_ratio(),
            "total_risk_reward": self.get_total_risk_reward()
        }
    
    def to_string(self) -> str:
        """Convert to human-readable string."""
        lines = [
            f"Signal: {self.signal_id}",
            f"Engine: {self.engine.value}",
            f"Instrument: {self.instrument.value}",
            f"Direction: {self.direction.value}",
            f"Grade: {self.grade.value} ({self.score:.0f} points)",
            f"Entry: {self.entry_price:.2f}",
            f"Stop Loss: {self.stop_loss:.2f}",
            f"TP1: {self.tp1:.2f} ({self.tp1_size:.0%})",
        ]
        
        if self.tp2:
            lines.append(f"TP2: {self.tp2:.2f} ({self.tp2_size:.0%})")
        if self.tp3:
            lines.append(f"TP3: {self.tp3:.2f} ({self.tp3_size:.0%})")
        
        lines.append(f"R:R: {self.get_risk_reward_ratio():.2f}")
        lines.append(f"Status: {self.status.value}")
        
        if self.reasons.to_dict():
            lines.append(f"Reasons: {self.reasons.to_string()}")
        
        return "\n".join(lines)


class SignalConverter:
    """
    Converts legacy signal formats to UnifiedSignal.
    
    Handles conversion from:
    - CoreSignal (from dual_engine_models)
    - ScalpSignal (from dual_engine_models)
    """
    
    @staticmethod
    def from_core_signal(
        core_signal,
        signal_id: str,
        reasons: Optional[SignalReason] = None
    ) -> UnifiedSignal:
        """
        Convert CoreSignal to UnifiedSignal.
        
        Args:
            core_signal: CoreSignal from dual_engine_models
            signal_id: Unique signal identifier
            reasons: Optional detailed reasoning
        
        Returns:
            UnifiedSignal
        """
        return UnifiedSignal(
            signal_id=signal_id,
            engine=EngineType.CORE_STRATEGY,
            signal_type=SignalType.ENTRY,
            instrument=core_signal.instrument,
            direction=core_signal.direction,
            grade=core_signal.grade,
            score=float(core_signal.confluence_score.total),
            entry_price=core_signal.entry_price,
            stop_loss=core_signal.stop_loss,
            tp1=core_signal.tp1,
            tp1_size=0.4,  # 40% at TP1
            tp2=core_signal.tp2,
            tp2_size=0.4,  # 40% at TP2
            tp3=None,  # Runner managed separately
            tp3_size=0.2,  # 20% runner
            timestamp=core_signal.timestamp,
            reasons=reasons or SignalReason()
        )
    
    @staticmethod
    def from_scalp_signal(
        scalp_signal,
        signal_id: str,
        grade: SignalGrade,
        score: float,
        reasons: Optional[SignalReason] = None
    ) -> UnifiedSignal:
        """
        Convert ScalpSignal to UnifiedSignal.
        
        Args:
            scalp_signal: ScalpSignal from dual_engine_models
            signal_id: Unique signal identifier
            grade: Signal grade (scalp doesn't have grades)
            score: Signal score (scalp doesn't have scores)
            reasons: Optional detailed reasoning
        
        Returns:
            UnifiedSignal
        """
        return UnifiedSignal(
            signal_id=signal_id,
            engine=EngineType.QUICK_SCALP,
            signal_type=SignalType.ENTRY,
            instrument=scalp_signal.instrument,
            direction=scalp_signal.direction,
            grade=grade,
            score=score,
            entry_price=scalp_signal.entry_price,
            stop_loss=scalp_signal.stop_loss,
            tp1=scalp_signal.take_profit,
            tp1_size=1.0,  # 100% at single TP
            tp2=None,
            tp2_size=None,
            tp3=None,
            tp3_size=None,
            timestamp=scalp_signal.timestamp,
            reasons=reasons or SignalReason()
        )


class SignalValidator:
    """
    Validates signals against filters before execution.
    
    Checks:
    - Spread limits
    - Session windows
    - News events
    - Risk limits
    """
    
    def __init__(
        self,
        spread_limits: Dict[Instrument, float],
        session_manager,
        news_filter
    ):
        """
        Initialize validator.
        
        Args:
            spread_limits: Max spread per instrument
            session_manager: Session manager instance
            news_filter: News filter instance
        """
        self.spread_limits = spread_limits
        self.session_manager = session_manager
        self.news_filter = news_filter
    
    def validate(
        self,
        signal: UnifiedSignal,
        current_spread: float
    ) -> tuple[bool, str]:
        """
        Validate signal against all filters.
        
        Args:
            signal: Signal to validate
            current_spread: Current market spread
        
        Returns:
            (is_valid, rejection_reason)
        """
        # Check spread
        max_spread = self.spread_limits.get(signal.instrument, float('inf'))
        if current_spread > max_spread:
            return False, f"Spread {current_spread} exceeds limit {max_spread}"
        signal.spread_check = True
        
        # Check session
        if not self.session_manager.is_signal_permitted(
            signal.timestamp,
            signal.engine
        ):
            return False, "Outside signal window"
        signal.session_check = True
        
        # Check news
        if self.news_filter.is_blocked(signal.timestamp):
            return False, "News event blocking"
        signal.news_check = True
        
        return True, "All checks passed"


class SignalRouter:
    """
    Routes validated signals to appropriate execution handlers.
    
    Handles:
    - MT5 execution
    - Telegram notifications
    - Database logging
    - Performance tracking
    """
    
    def __init__(self):
        """Initialize router."""
        self.handlers: List = []
    
    def register_handler(self, handler):
        """Register a signal handler."""
        self.handlers.append(handler)
    
    def route(self, signal: UnifiedSignal) -> bool:
        """
        Route signal to all registered handlers.
        
        Args:
            signal: Validated signal to route
        
        Returns:
            True if at least one handler succeeded
        """
        if signal.status != SignalStatus.APPROVED:
            raise ValueError(
                f"Cannot route signal with status {signal.status.value}"
            )
        
        success = False
        for handler in self.handlers:
            try:
                if handler.handle(signal):
                    success = True
            except Exception as e:
                # Log error but continue to other handlers
                print(f"Handler {handler.__class__.__name__} failed: {e}")
        
        if success:
            signal.status = SignalStatus.EXECUTED
        
        return success
