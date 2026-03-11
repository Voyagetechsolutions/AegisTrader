"""
Compatibility Layer for Python Strategy Engine.

Provides adapter interfaces to maintain compatibility with existing
Aegis Trader systems while integrating the new strategy engine.
"""

from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from backend.strategy.config import redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Signal, Direction, SetupType, SignalGrade
from backend.schemas.schemas import TradingViewWebhookPayload
from backend.modules.confluence_scoring import (
    score_setup, ConfluenceResult, classify_setup_type
)
from backend.modules.alert_manager import send_signal_alert
from backend.routers.mt5_bridge import mt5_bridge


class ConfluenceAdapter:
    """
    Adapter to integrate strategy engine signals with existing confluence scoring.
    
    Converts strategy engine analysis results into TradingView webhook format
    for compatibility with existing confluence scoring system.
    """
    
    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("confluence_adapter")
        self.redis_mgr = redis_mgr or redis_manager
    
    def convert_signal_to_payload(self, signal: Signal) -> TradingViewWebhookPayload:
        """
        Convert strategy engine signal to TradingView webhook payload format.
        
        This maintains compatibility with existing confluence scoring while
        using data from the new strategy engine.
        
        Args:
            signal: Strategy engine signal.
            
        Returns:
            TradingViewWebhookPayload compatible with existing systems.
        """
        # Extract analysis breakdown
        breakdown = signal.analysis_breakdown or {}
        
        # Convert direction
        direction = "long" if signal.direction == Direction.LONG else "short"
        
        # Use webhook secret from settings for internal signals
        from backend.config import settings
        
        # Create payload with strategy engine data
        payload = TradingViewWebhookPayload(
            secret=settings.webhook_secret,  # Use configured secret
            symbol="US30",
            direction=direction,
            entry=float(signal.entry),
            stop_loss=float(signal.stop_loss),
            tp1=float(signal.take_profit),
            tp2=float(signal.take_profit * 1.2),  # Extended TP2
            
            # MTF bias from analysis (use neutral if not available)
            weekly_bias=breakdown.get("weekly_bias", "neutral"),
            daily_bias=breakdown.get("daily_bias", "neutral"),
            h4_bias=breakdown.get("h4_bias", "neutral"),
            h1_bias=breakdown.get("h1_bias", "neutral"),
            m15_bias=breakdown.get("m15_bias", "neutral"),
            m5_bias=breakdown.get("m5_bias", "neutral"),
            
            # Key levels from analysis
            level_250=breakdown.get("level_250"),
            level_125=breakdown.get("level_125"),
            
            # Confluence factors
            liquidity_sweep=breakdown.get("liquidity_score", 0) > 0,
            fvg_present=breakdown.get("fvg_score", 0) > 0,
            displacement_present=breakdown.get("displacement_score", 0) > 0,
            mss_present=breakdown.get("structure_score", 0) > 0,
        )
        
        return payload
    
    def score_strategy_signal(
        self,
        signal: Signal,
        spread_ok: bool = True,
        session_active: bool = True
    ) -> ConfluenceResult:
        """
        Score a strategy engine signal using existing confluence scoring.
        
        Args:
            signal: Strategy engine signal.
            spread_ok: Whether spread is acceptable.
            session_active: Whether in active session.
            
        Returns:
            ConfluenceResult from existing scoring system.
        """
        # Convert to webhook payload format
        payload = self.convert_signal_to_payload(signal)
        
        # Use existing confluence scoring
        result = score_setup(payload, spread_ok, session_active)
        
        self.logger.debug(
            f"Confluence score: {result.score} ({result.grade}) "
            f"for {signal.setup_type.value} signal"
        )
        
        return result
    
    def validate_signal_compatibility(self, signal: Signal) -> bool:
        """
        Validate that signal is compatible with existing systems.
        
        Args:
            signal: Strategy engine signal.
            
        Returns:
            True if compatible, False otherwise.
        """
        try:
            # Test conversion
            payload = self.convert_signal_to_payload(signal)
            
            # Test scoring
            result = self.score_strategy_signal(signal)
            
            # Validate required fields
            required_fields = [
                signal.entry, signal.stop_loss, signal.take_profit,
                signal.direction, signal.setup_type
            ]
            
            if any(field is None for field in required_fields):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Signal compatibility validation failed: {e}")
            return False


class MT5BridgeAdapter:
    """
    Adapter to maintain compatibility with existing MT5 bridge.
    
    Ensures strategy engine signals can be executed through the
    existing MT5 bridge without modifications.
    """
    
    def __init__(self):
        self.logger = get_component_logger("mt5_adapter")
        self.bridge = mt5_bridge
    
    async def execute_signal(
        self,
        signal: Signal,
        lot_size: float = 0.01,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute strategy engine signal through existing MT5 bridge.
        
        Args:
            signal: Strategy engine signal.
            lot_size: Position size.
            user_id: User ID for tracking.
            
        Returns:
            Execution result dictionary.
        """
        try:
            from backend.schemas.schemas import MT5OrderRequest
            
            # Convert signal to MT5 order format
            order_request = MT5OrderRequest(
                symbol="US30",
                direction=signal.direction.value.lower(),
                lot_size=lot_size,
                sl_price=float(signal.stop_loss),
                tp1_price=float(signal.take_profit),
                tp2_price=float(signal.take_profit * 1.2),
                open_price=float(signal.entry),
                current_sl=float(signal.stop_loss),
                comment=f"Strategy Engine {signal.setup_type.value}",
            )
            
            # Execute through existing bridge
            response = await self.bridge.place_order(order_request)
            
            if response.success:
                self.logger.info(
                    f"Signal executed: ticket={response.ticket}, "
                    f"price={response.actual_price}"
                )
                
                return {
                    "success": True,
                    "ticket": response.ticket,
                    "fill_price": response.actual_price,
                    "slippage": response.slippage,
                }
            else:
                self.logger.error(f"Signal execution failed: {response.error}")
                return {
                    "success": False,
                    "error": response.error,
                }
                
        except Exception as e:
            self.logger.error(f"MT5 execution error: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions through existing bridge."""
        try:
            positions = await self.bridge.get_positions()
            return [
                {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "direction": pos.direction.value,
                    "lot_size": pos.lot_size,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "pnl": pos.pnl,
                }
                for pos in positions
            ]
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    async def modify_position(
        self,
        ticket: int,
        new_sl: Optional[float] = None,
        new_tp: Optional[float] = None
    ) -> bool:
        """Modify position through existing bridge."""
        try:
            if new_sl:
                success = await self.bridge.modify_sl(ticket, new_sl)
                if success:
                    self.logger.info(f"Modified SL for ticket {ticket}: {new_sl}")
                return success
            return True
        except Exception as e:
            self.logger.error(f"Error modifying position: {e}")
            return False


class TelegramAdapter:
    """
    Adapter to maintain compatibility with existing Telegram alert system.
    
    Ensures strategy engine signals are formatted and sent through
    existing Telegram infrastructure.
    """
    
    def __init__(self):
        self.logger = get_component_logger("telegram_adapter")
    
    async def send_strategy_signal_alert(
        self,
        signal: Signal,
        confluence_result: Optional[ConfluenceResult] = None
    ) -> bool:
        """
        Send strategy engine signal through existing Telegram system.
        
        Args:
            signal: Strategy engine signal.
            confluence_result: Optional confluence scoring result.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            # Convert to database Signal model for existing alert system
            from backend.models.models import Signal as DBSignal
            
            # Create compatible signal object
            db_signal = self._convert_to_db_signal(signal, confluence_result)
            
            # Send through existing alert system (it's not async)
            success = send_signal_alert(db_signal)
            
            if success:
                self.logger.info(f"Telegram alert sent for {signal.setup_type.value}")
            else:
                self.logger.warning("Failed to send Telegram alert")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Telegram alert error: {e}")
            return False
    
    def _convert_to_db_signal(
        self,
        signal: Signal,
        confluence_result: Optional[ConfluenceResult] = None
    ) -> Any:
        """
        Convert strategy engine signal to database Signal model.
        
        Args:
            signal: Strategy engine signal.
            confluence_result: Optional confluence result.
            
        Returns:
            Database Signal model instance.
        """
        from backend.models.models import (
            Signal as DBSignal, Direction as DBDirection,
            SetupType as DBSetupType, SignalGrade as DBGrade
        )
        
        # Map enums
        direction_map = {
            Direction.LONG: DBDirection.LONG,
            Direction.SHORT: DBDirection.SHORT,
        }
        
        setup_map = {
            SetupType.CONTINUATION_LONG: DBSetupType.CONTINUATION_LONG,
            SetupType.CONTINUATION_SHORT: DBSetupType.CONTINUATION_SHORT,
            SetupType.SWING_LONG: DBSetupType.SWING_LONG,
            SetupType.SWING_SHORT: DBSetupType.SWING_SHORT,
        }
        
        grade_map = {
            SignalGrade.A_PLUS: DBGrade.A_PLUS,
            SignalGrade.A: DBGrade.A,
            SignalGrade.B: DBGrade.B,
        }
        
        # Extract analysis data
        breakdown = signal.analysis_breakdown or {}
        
        from datetime import timezone
        
        # Create database signal
        db_signal = DBSignal(
            timestamp=signal.timestamp.replace(tzinfo=timezone.utc) if signal.timestamp.tzinfo is None else signal.timestamp,
            execution_symbol="US30",
            direction=direction_map[signal.direction],
            setup_type=setup_map.get(signal.setup_type),
            entry_price=signal.entry,
            stop_loss=signal.stop_loss,
            tp1=signal.take_profit,
            tp2=signal.take_profit * 1.2,  # Extended TP2
            score=int(signal.confluence_score),
            grade=grade_map[signal.grade],
            
            # MTF bias
            weekly_bias=breakdown.get("weekly_bias"),
            daily_bias=breakdown.get("daily_bias"),
            h4_bias=breakdown.get("h4_bias"),
            h1_bias=breakdown.get("h1_bias"),
            
            # Key levels
            level_250=breakdown.get("level_250"),
            level_125=breakdown.get("level_125"),
            
            # Confluence factors
            liquidity_sweep=breakdown.get("liquidity_score", 0) > 0,
            fvg_present=breakdown.get("fvg_score", 0) > 0,
            displacement_present=breakdown.get("displacement_score", 0) > 0,
            mss_present=breakdown.get("structure_score", 0) > 0,
            
            # Additional fields
            eligible_for_auto_trade=confluence_result.auto_trade_eligible if confluence_result else False,
            session_name="strategy_engine",
            spread_points=2.0,  # Default acceptable spread
            news_blocked=False,
        )
        
        return db_signal


class SystemCompatibility:
    """
    Main compatibility coordinator for the strategy engine.
    
    Orchestrates all compatibility adapters to ensure seamless
    integration with existing Aegis Trader systems.
    """
    
    def __init__(self):
        self.logger = get_component_logger("system_compatibility")
        self.confluence_adapter = ConfluenceAdapter()
        self.mt5_adapter = MT5BridgeAdapter()
        self.telegram_adapter = TelegramAdapter()
    
    async def process_strategy_signal(
        self,
        signal: Signal,
        user_id: Optional[UUID] = None,
        lot_size: float = 0.01,
        send_alerts: bool = True,
        execute_trade: bool = False
    ) -> Dict[str, Any]:
        """
        Process strategy engine signal through all compatibility systems.
        
        Args:
            signal: Strategy engine signal.
            user_id: User ID for tracking.
            lot_size: Position size for execution.
            send_alerts: Whether to send Telegram alerts.
            execute_trade: Whether to execute the trade.
            
        Returns:
            Processing result dictionary.
        """
        result = {
            "signal_id": str(signal.timestamp),
            "compatibility_check": False,
            "confluence_score": None,
            "alert_sent": False,
            "trade_executed": False,
            "bot_mode_info": {},
            "errors": [],
        }
        
        try:
            # 1. Get bot mode information
            try:
                from backend.strategy.bot_mode_manager import bot_mode_manager
                mode_status = await bot_mode_manager.get_mode_status(user_id)
                result["bot_mode_info"] = mode_status
            except ImportError:
                self.logger.warning("Bot mode manager not available")
                result["bot_mode_info"] = {"mode": "analyze", "auto_trade_enabled": False}
            
            # 2. Validate compatibility
            if not self.confluence_adapter.validate_signal_compatibility(signal):
                result["errors"].append("Signal compatibility validation failed")
                return result
            
            result["compatibility_check"] = True
            
            # 3. Score through existing confluence system
            confluence_result = self.confluence_adapter.score_strategy_signal(signal)
            result["confluence_score"] = confluence_result.score
            result["confluence_grade"] = confluence_result.grade
            
            # 4. Send Telegram alert if requested
            if send_alerts:
                alert_success = await self.telegram_adapter.send_strategy_signal_alert(
                    signal, confluence_result
                )
                result["alert_sent"] = alert_success
                if not alert_success:
                    result["errors"].append("Failed to send Telegram alert")
            
            # 5. Execute trade if requested and eligible
            # Note: execute_trade parameter now comes from bot mode manager decision
            if execute_trade and confluence_result.auto_trade_eligible:
                execution_result = await self.mt5_adapter.execute_signal(
                    signal, lot_size, user_id
                )
                result["trade_executed"] = execution_result["success"]
                result["execution_details"] = execution_result
                
                if not execution_result["success"]:
                    result["errors"].append(f"Trade execution failed: {execution_result.get('error')}")
            elif execute_trade and not confluence_result.auto_trade_eligible:
                result["errors"].append(f"Trade not executed: signal not eligible (grade {confluence_result.grade})")
            
            self.logger.info(
                f"Strategy signal processed: score={confluence_result.score}, "
                f"mode={result['bot_mode_info'].get('mode', 'unknown')}, "
                f"alert_sent={result['alert_sent']}, "
                f"trade_executed={result['trade_executed']}"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing strategy signal: {e}")
            result["errors"].append(str(e))
        
        return result
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get compatibility system status for monitoring.
        
        Returns:
            System status dictionary.
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "mt5_bridge": "unknown",
            "telegram": "unknown",
            "confluence_scoring": "available",
            "positions_count": 0,
        }
        
        try:
            # Check MT5 bridge
            positions = await self.mt5_adapter.get_positions()
            status["positions_count"] = len(positions)
            status["mt5_bridge"] = "connected"
        except Exception as e:
            status["mt5_bridge"] = f"error: {e}"
        
        try:
            # Test Telegram (just check if we can import)
            from backend.modules.alert_manager import get_bot
            bot = get_bot()
            status["telegram"] = "available" if bot else "unavailable"
        except Exception as e:
            status["telegram"] = f"error: {e}"
        
        return status


# Global compatibility coordinator
system_compatibility = SystemCompatibility()