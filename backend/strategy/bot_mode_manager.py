"""
Bot Mode Manager for Python Strategy Engine.

Manages bot operating modes (Analyze, Trade, Swing) and ensures
identical behavior to the existing webhook-based system while
integrating with the new strategy engine.
"""

from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.strategy.config import redis_manager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Signal, Direction, SetupType, SignalGrade
from backend.models.models import BotSetting, BotMode
from backend.database import get_db


class BotModeManager:
    """
    Manages bot operating modes for the strategy engine.
    
    Provides mode-specific signal processing that maintains identical
    behavior to the existing webhook-based system.
    """
    
    def __init__(self):
        self.logger = get_component_logger("bot_mode_manager")
        self._cached_settings = {}
        self._cache_expiry = {}
        self.cache_duration = 300  # 5 minutes
    
    async def get_bot_settings(self, user_id: Optional[UUID] = None) -> Optional[BotSetting]:
        """
        Get bot settings for user or default settings.
        
        Args:
            user_id: User ID, None for default settings.
            
        Returns:
            BotSetting instance or None if not found.
        """
        # Check cache first
        cache_key = str(user_id) if user_id else "default"
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        if (cache_key in self._cached_settings and 
            cache_key in self._cache_expiry and
            now < self._cache_expiry[cache_key]):
            return self._cached_settings[cache_key]
        
        # Fetch from database
        async for db in get_db():
            try:
                if user_id:
                    result = await db.execute(
                        select(BotSetting).where(BotSetting.user_id == user_id)
                    )
                    settings = result.scalar_one_or_none()
                else:
                    # Get default settings (first one)
                    result = await db.execute(select(BotSetting).limit(1))
                    settings = result.scalar_one_or_none()
                
                # Cache the result
                self._cached_settings[cache_key] = settings
                self._cache_expiry[cache_key] = now.replace(
                    second=now.second + self.cache_duration
                )
                
                return settings
                
            except Exception as e:
                self.logger.error(f"Error fetching bot settings: {e}")
                return None
            finally:
                await db.close()
    
    async def get_current_mode(self, user_id: Optional[UUID] = None) -> BotMode:
        """
        Get current bot mode for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            Current BotMode, defaults to ANALYZE.
        """
        settings = await self.get_bot_settings(user_id)
        return settings.mode if settings else BotMode.ANALYZE
    
    async def is_auto_trade_enabled(self, user_id: Optional[UUID] = None) -> bool:
        """
        Check if auto trading is enabled for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            True if auto trading is enabled.
        """
        settings = await self.get_bot_settings(user_id)
        return settings.auto_trade_enabled if settings else False
    
    async def should_execute_signal(
        self,
        signal: Signal,
        user_id: Optional[UUID] = None,
        session_active: bool = True,
        risk_allowed: bool = True
    ) -> Dict[str, Any]:
        """
        Determine if signal should be executed based on bot mode and conditions.
        
        Args:
            signal: Strategy engine signal.
            user_id: User ID for settings lookup.
            session_active: Whether in active trading session.
            risk_allowed: Whether risk limits allow execution.
            
        Returns:
            Dictionary with execution decision and reason.
        """
        settings = await self.get_bot_settings(user_id)
        
        if not settings:
            return {
                "execute": False,
                "action": "alerted",
                "reason": "No bot settings found - alert only",
                "mode": "analyze"
            }
        
        mode = settings.mode
        auto_trade = settings.auto_trade_enabled
        is_swing_setup = signal.setup_type in [SetupType.SWING_LONG, SetupType.SWING_SHORT]
        
        # Analyze mode: Always alert only
        if mode == BotMode.ANALYZE:
            return {
                "execute": False,
                "action": "alerted", 
                "reason": "Analyze mode - alert only",
                "mode": mode.value
            }
        
        # Swing mode or swing setup: Always alert only (user approval required)
        if mode == BotMode.SWING or is_swing_setup:
            return {
                "execute": False,
                "action": "alerted",
                "reason": "Swing setup - user approval required" if is_swing_setup else "Swing mode - alert only",
                "mode": mode.value
            }
        
        # Trade mode: Execute if conditions met
        if mode == BotMode.TRADE:
            # Check if signal is eligible for auto trade (A+ grade)
            if signal.grade != SignalGrade.A_PLUS:
                return {
                    "execute": False,
                    "action": "alerted",
                    "reason": f"Grade {signal.grade.value} - alert only",
                    "mode": mode.value
                }
            
            # Check if auto trading is enabled
            if not auto_trade:
                return {
                    "execute": False,
                    "action": "alerted",
                    "reason": "Auto trading disabled - alert only",
                    "mode": mode.value
                }
            
            # Check session timing
            if not session_active:
                return {
                    "execute": False,
                    "action": "alerted",
                    "reason": "Outside trading session - alert only",
                    "mode": mode.value
                }
            
            # Check risk limits
            if not risk_allowed:
                return {
                    "execute": False,
                    "action": "alerted",
                    "reason": "Risk limits exceeded - alert only",
                    "mode": mode.value
                }
            
            # All conditions met - execute
            return {
                "execute": True,
                "action": "executed",
                "reason": "A+ grade in Trade mode - executing",
                "mode": mode.value
            }
        
        # Default fallback
        return {
            "execute": False,
            "action": "alerted",
            "reason": f"Unknown mode {mode.value} - alert only",
            "mode": mode.value
        }
    
    async def get_execution_symbol(self, user_id: Optional[UUID] = None) -> str:
        """
        Get execution symbol for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            Execution symbol (e.g., "US30").
        """
        settings = await self.get_bot_settings(user_id)
        return settings.execution_symbol if settings else "US30"
    
    async def get_analysis_symbol(self, user_id: Optional[UUID] = None) -> str:
        """
        Get analysis symbol for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            Analysis symbol (e.g., "TVC:DJI").
        """
        settings = await self.get_bot_settings(user_id)
        return settings.analysis_symbol if settings else "TVC:DJI"
    
    async def get_session_config(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get session configuration for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            Session configuration dictionary.
        """
        settings = await self.get_bot_settings(user_id)
        
        if settings and settings.sessions:
            return settings.sessions
        
        # Default session configuration
        return {
            "london": {"start": "10:00", "end": "13:00"},
            "new_york": {"start": "15:30", "end": "17:30"},
            "power_hour": {"start": "20:00", "end": "22:00"}
        }
    
    async def get_risk_config(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get risk configuration for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            Risk configuration dictionary.
        """
        settings = await self.get_bot_settings(user_id)
        
        if not settings:
            return {
                "max_trades_per_day": 2,
                "max_losses_per_day": 2,
                "max_daily_drawdown_pct": 2.0,
                "max_slippage_points": 10.0
            }
        
        return {
            "max_trades_per_day": settings.max_trades_per_day,
            "max_losses_per_day": settings.max_losses_per_day,
            "max_daily_drawdown_pct": float(settings.max_daily_drawdown_pct),
            "max_slippage_points": float(settings.max_slippage_points)
        }
    
    async def invalidate_cache(self, user_id: Optional[UUID] = None):
        """
        Invalidate cached settings for user.
        
        Args:
            user_id: User ID, None for default.
        """
        cache_key = str(user_id) if user_id else "default"
        
        if cache_key in self._cached_settings:
            del self._cached_settings[cache_key]
        
        if cache_key in self._cache_expiry:
            del self._cache_expiry[cache_key]
        
        self.logger.debug(f"Invalidated cache for user {user_id}")
    
    async def update_mode(
        self,
        mode: BotMode,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Update bot mode for user.
        
        Args:
            mode: New bot mode.
            user_id: User ID, None for default.
            
        Returns:
            True if updated successfully.
        """
        async for db in get_db():
            try:
                if user_id:
                    result = await db.execute(
                        select(BotSetting).where(BotSetting.user_id == user_id)
                    )
                    settings = result.scalar_one_or_none()
                else:
                    result = await db.execute(select(BotSetting).limit(1))
                    settings = result.scalar_one_or_none()
                
                if not settings:
                    self.logger.error(f"No bot settings found for user {user_id}")
                    return False
                
                settings.mode = mode
                await db.commit()
                
                # Invalidate cache
                await self.invalidate_cache(user_id)
                
                self.logger.info(f"Updated bot mode to {mode.value} for user {user_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating bot mode: {e}")
                await db.rollback()
                return False
            finally:
                await db.close()
    
    async def toggle_auto_trade(
        self,
        enabled: bool,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Toggle auto trading for user.
        
        Args:
            enabled: Whether to enable auto trading.
            user_id: User ID, None for default.
            
        Returns:
            True if updated successfully.
        """
        async for db in get_db():
            try:
                if user_id:
                    result = await db.execute(
                        select(BotSetting).where(BotSetting.user_id == user_id)
                    )
                    settings = result.scalar_one_or_none()
                else:
                    result = await db.execute(select(BotSetting).limit(1))
                    settings = result.scalar_one_or_none()
                
                if not settings:
                    self.logger.error(f"No bot settings found for user {user_id}")
                    return False
                
                settings.auto_trade_enabled = enabled
                await db.commit()
                
                # Invalidate cache
                await self.invalidate_cache(user_id)
                
                action = "enabled" if enabled else "disabled"
                self.logger.info(f"Auto trading {action} for user {user_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error toggling auto trade: {e}")
                await db.rollback()
                return False
            finally:
                await db.close()
    
    async def get_mode_status(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get comprehensive mode status for user.
        
        Args:
            user_id: User ID, None for default.
            
        Returns:
            Mode status dictionary.
        """
        settings = await self.get_bot_settings(user_id)
        
        if not settings:
            return {
                "mode": "analyze",
                "auto_trade_enabled": False,
                "execution_symbol": "US30",
                "analysis_symbol": "TVC:DJI",
                "error": "No bot settings found"
            }
        
        return {
            "mode": settings.mode.value,
            "auto_trade_enabled": settings.auto_trade_enabled,
            "execution_symbol": settings.execution_symbol,
            "analysis_symbol": settings.analysis_symbol,
            "sessions": settings.sessions,
            "risk_config": {
                "max_trades_per_day": settings.max_trades_per_day,
                "max_losses_per_day": settings.max_losses_per_day,
                "max_daily_drawdown_pct": float(settings.max_daily_drawdown_pct)
            }
        }


# Global bot mode manager instance
bot_mode_manager = BotModeManager()