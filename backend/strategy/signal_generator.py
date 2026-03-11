"""
Signal Generator for the Python Strategy Engine.

Combines analysis results from all engines through the confluence scoring
system to generate actionable trading signals.
"""

from __future__ import annotations
import json
from datetime import datetime, time
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID
import pytz

from backend.strategy.config import strategy_settings, redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.session_manager import SessionManager
from backend.strategy.models import (
    Candle, Timeframe, Direction, SetupType, SignalGrade,
    Signal, AnalysisResult, BiasResult, LevelResult,
    LiquidityResult, FVGResult, DisplacementResult, StructureResult,
    BiasDirection,
)
from backend.strategy.risk_integration import risk_integration


def classify_signal_grade(score: float) -> SignalGrade:
    """
    Classify signal grade based on confluence score.

    A+: score >= 85
    A:  score >= 75
    B:  score < 75

    Args:
        score: Confluence score (0-100).

    Returns:
        SignalGrade classification.
    """
    if score >= 85:
        return SignalGrade.A_PLUS
    elif score >= 75:
        return SignalGrade.A
    else:
        return SignalGrade.B


def determine_setup_type(
    bias: BiasDirection,
    structure_break: Optional[str],
    has_displacement: bool
) -> SetupType:
    """
    Determine the setup type based on analysis.

    Args:
        bias: Current market bias.
        structure_break: Type of structure break if any.
        has_displacement: Whether displacement was detected.

    Returns:
        SetupType classification.
    """
    is_bullish = bias == BiasDirection.BULLISH

    # Swing setups: CHoCH or shift with displacement
    if structure_break and "choch" in structure_break:
        return SetupType.SWING_LONG if is_bullish else SetupType.SWING_SHORT

    # Continuation setups: BOS or aligned bias
    return SetupType.CONTINUATION_LONG if is_bullish else SetupType.CONTINUATION_SHORT


def calculate_trade_levels(
    entry: float,
    direction: Direction,
    atr: float = 50.0
) -> Dict[str, float]:
    """
    Calculate stop loss and take profit levels.

    Args:
        entry: Entry price.
        direction: Trade direction.
        atr: Average True Range for level calculation.

    Returns:
        Dictionary with entry, stop_loss, take_profit.
    """
    if direction == Direction.LONG:
        stop_loss = entry - (atr * 1.5)
        take_profit = entry + (atr * 3.0)
    else:
        stop_loss = entry + (atr * 1.5)
        take_profit = entry - (atr * 3.0)

    return {
        "entry": entry,
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
    }


class SignalGenerator:
    """
    Generates trading signals from confluence analysis.

    Combines outputs from all analysis engines using the 100-point
    scoring system to produce graded signals.
    """

    # Minimum score to generate a signal
    MIN_SIGNAL_SCORE = 40  # Lowered for testing

    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("signal_generator")
        self.redis_mgr = redis_mgr or redis_manager
        self.settings = strategy_settings
        self.session_manager = SessionManager(strategy_settings.timezone)
        
        # Enable 24/7 trading by default (sessions still tracked for analytics)
        self.session_manager.enable_override()
        self.logger.info("24/7 trading enabled - sessions tracked but won't block trades")

        # Recent signals cache
        self._recent_signals: List[Signal] = []
        self._max_signals = 50

    async def evaluate_setup(
        self,
        analysis: AnalysisResult,
        current_price: float,
        user_id: Optional[UUID] = None,
        account_balance: float = 1000.0,
    ) -> Optional[Signal]:
        """
        Evaluate a trading setup and generate signal if criteria met.

        Args:
            analysis: Complete analysis result from all engines.
            current_price: Current market price.
            user_id: User ID for risk validation.
            account_balance: Current account balance from MT5.

        Returns:
            Signal if setup qualifies, None otherwise.
        """
        # Check session timing
        if not self.session_manager.is_within_session():
            self.logger.debug("Outside trading session - no signal generated")
            return None

        # Calculate confluence score
        score, breakdown = self._calculate_confluence_score(analysis)

        # Check minimum score
        if score < self.MIN_SIGNAL_SCORE:
            self.logger.debug(f"Score {score} below minimum {self.MIN_SIGNAL_SCORE}")
            return None

        # Determine direction and setup type
        direction = self._determine_direction(analysis.bias)
        if direction is None:
            return None

        setup_type = determine_setup_type(
            analysis.bias.direction,
            analysis.structure.break_type,
            analysis.displacement.recent_displacement is not None,
        )

        # Calculate trade levels
        levels = calculate_trade_levels(current_price, direction)

        # Create signal
        from datetime import timezone
        signal = Signal(
            timestamp=datetime.now(timezone.utc),
            setup_type=setup_type,
            direction=direction,
            entry=levels["entry"],
            stop_loss=levels["stop_loss"],
            take_profit=levels["take_profit"],
            confluence_score=score,
            grade=classify_signal_grade(score),
            analysis_breakdown=breakdown,
        )

        # Validate against risk limits
        risk_allowed, risk_reason = await risk_integration.validate_signal_risk(
            signal, user_id, account_balance
        )
        
        if not risk_allowed:
            self.logger.warning(f"Signal blocked by risk management: {risk_reason}")
            # Still store the signal for analysis but mark it as blocked
            signal.analysis_breakdown["risk_blocked"] = True
            signal.analysis_breakdown["risk_reason"] = risk_reason
            await self._store_signal(signal)
            return None

        # Store signal
        await self._store_signal(signal)

        # Process through bot mode manager and compatibility layer
        try:
            from backend.strategy.bot_mode_manager import bot_mode_manager
            from backend.strategy.compatibility import system_compatibility
            
            # Determine execution decision based on bot mode
            session_active = self.session_manager.is_within_session()
            execution_decision = await bot_mode_manager.should_execute_signal(
                signal=signal,
                user_id=user_id,
                session_active=session_active,
                risk_allowed=risk_allowed
            )
            
            # Add mode information to signal breakdown
            signal.analysis_breakdown["bot_mode"] = execution_decision["mode"]
            signal.analysis_breakdown["execution_decision"] = execution_decision["action"]
            signal.analysis_breakdown["execution_reason"] = execution_decision["reason"]
            
            # Process through compatibility layer
            compatibility_result = await system_compatibility.process_strategy_signal(
                signal=signal,
                user_id=user_id,
                send_alerts=True,  # Always send alerts for valid signals
                execute_trade=execution_decision["execute"],  # Execute based on bot mode
            )

            # Update signal with confluence score from existing system
            if compatibility_result.get("confluence_score"):
                signal.confluence_score = compatibility_result["confluence_score"]
                signal.grade = classify_signal_grade(signal.confluence_score)

            self.logger.info(
                f"Signal generated: {signal.grade.value} {signal.setup_type.value} "
                f"@ {signal.entry} (score: {score}) - mode: {execution_decision['mode']} "
                f"action: {execution_decision['action']} - compatibility: {compatibility_result.get('compatibility_check', False)}"
            )
        except ImportError:
            self.logger.warning("Bot mode manager or compatibility layer not available - signal generated without integration")
            self.logger.info(
                f"Signal generated: {signal.grade.value} {signal.setup_type.value} "
                f"@ {signal.entry} (score: {score})"
            )

        return signal

    def _calculate_confluence_score(
        self,
        analysis: AnalysisResult
    ) -> tuple[float, Dict[str, Any]]:
        """
        Calculate confluence score from analysis results.

        100-point scoring system based on:
        - Bias alignment: up to 15 points
        - Level proximity: up to 15 points
        - Liquidity sweep: up to 12 points
        - FVG presence: up to 10 points
        - Displacement: up to 15 points
        - Structure break: up to 15 points
        - HTF alignment: up to 10 points
        - Session timing: up to 8 points

        Returns:
            Tuple of (score, breakdown dict).
        """
        breakdown = {}
        total_score = 0.0

        # Bias contribution (15 pts max)
        bias_score = self._score_bias(analysis.bias)
        breakdown["bias"] = bias_score
        total_score += bias_score

        # Level proximity (15 pts max)
        level_score = self._score_levels(analysis.levels)
        breakdown["levels"] = level_score
        total_score += level_score

        # Liquidity sweep (12 pts max)
        liquidity_score = self._score_liquidity(analysis.liquidity)
        breakdown["liquidity"] = liquidity_score
        total_score += liquidity_score

        # FVG (10 pts max)
        fvg_score = self._score_fvg(analysis.fvg)
        breakdown["fvg"] = fvg_score
        total_score += fvg_score

        # Displacement (15 pts max)
        displacement_score = self._score_displacement(analysis.displacement)
        breakdown["displacement"] = displacement_score
        total_score += displacement_score

        # Structure (15 pts max)
        structure_score = self._score_structure(analysis.structure)
        breakdown["structure"] = structure_score
        total_score += structure_score

        # Session bonus (8 pts max)
        session = self.session_manager.get_active_session()
        if session == "power_hour":
            breakdown["session_bonus"] = 8.0
            total_score += 8.0
        elif session in ("london", "new_york"):
            breakdown["session_bonus"] = 5.0
            total_score += 5.0

        # Cap at 100
        total_score = min(total_score, 100.0)
        breakdown["total"] = total_score

        return total_score, breakdown

    def _score_bias(self, bias: BiasResult) -> float:
        """Score bias alignment."""
        if bias.direction in (BiasDirection.BULLISH, BiasDirection.BEARISH):
            base = 10.0
            # Bonus for strong EMA distance
            if abs(bias.ema_distance) > 30:
                base += 3.0
            # Bonus for structure shift
            if bias.structure_shift:
                base += 2.0
            return min(base, 15.0)
        return 0.0

    def _score_levels(self, levels: LevelResult) -> float:
        """Score level proximity."""
        score = 0.0

        # Near 250 level
        if levels.distance_to_250 <= 30:
            score += 10.0
        elif levels.distance_to_250 <= 60:
            score += 5.0

        # Near 125 level (if not already near 250)
        if levels.distance_to_125 <= 20 and levels.distance_to_250 > 30:
            score += 5.0

        return min(score, 15.0)

    def _score_liquidity(self, liquidity: LiquidityResult) -> float:
        """Score liquidity sweep presence."""
        if not liquidity.recent_sweeps:
            return 0.0

        if liquidity.time_since_sweep and liquidity.time_since_sweep < 30:
            return 12.0
        elif liquidity.time_since_sweep and liquidity.time_since_sweep < 60:
            return 8.0

        return 5.0

    def _score_fvg(self, fvg: FVGResult) -> float:
        """Score FVG presence."""
        if fvg.retest_opportunity:
            return 10.0
        elif fvg.active_fvgs:
            return 5.0
        return 0.0

    def _score_displacement(self, displacement: DisplacementResult) -> float:
        """Score displacement candle presence."""
        if not displacement.recent_displacement:
            return 0.0

        strength = displacement.strength
        if strength >= 70:
            return 15.0
        elif strength >= 50:
            return 10.0
        elif strength >= 30:
            return 5.0

        return 3.0

    def _score_structure(self, structure: StructureResult) -> float:
        """Score market structure."""
        if not structure.recent_breaks:
            return 0.0

        latest = structure.recent_breaks[-1]
        break_type = latest.get("type", "")

        if break_type == "choch":
            return 15.0
        elif break_type == "bos":
            return 10.0

        return 5.0

    def _determine_direction(self, bias: BiasResult) -> Optional[Direction]:
        """Determine trade direction from bias."""
        if bias.direction == BiasDirection.BULLISH:
            return Direction.LONG
        elif bias.direction == BiasDirection.BEARISH:
            return Direction.SHORT
        return None

    async def _store_signal(self, signal: Signal):
        """Store signal in cache and Redis."""
        self._recent_signals.append(signal)

        # Enforce max signals
        if len(self._recent_signals) > self._max_signals:
            self._recent_signals = self._recent_signals[-self._max_signals:]

        # Persist to Redis
        try:
            redis_client = await self.redis_mgr.get_redis()
            signals_data = [s.to_dict() for s in self._recent_signals]
            await redis_client.set("signals:recent", json.dumps(signals_data))
        except Exception as e:
            self.logger.error(f"Failed to persist signal: {e}")

    async def get_recent_signals(self, count: int = 10) -> List[Signal]:
        """Get recent signals."""
        return self._recent_signals[-count:]

    def validate_session_timing(self) -> bool:
        """Check if current time is within active trading session."""
        return self.session_manager.is_within_session()


# Global instance
signal_generator = SignalGenerator()
