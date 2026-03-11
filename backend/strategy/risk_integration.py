"""
Risk Integration for the Python Strategy Engine.

Integrates the strategy engine with the existing risk management system
to enforce daily limits and kill switch functionality.
"""

from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from backend.strategy.config import redis_manager, RedisManager
from backend.strategy.logging_config import get_component_logger
from backend.strategy.models import Signal, Direction
from backend.modules.risk_engine import check_risk, disable_auto_trading, RiskStatus
from backend.database import AsyncSessionLocal


class RiskIntegration:
    """
    Integrates strategy engine with existing risk management.
    
    Provides risk validation for signals before execution and
    maintains compatibility with existing risk limits.
    """
    
    def __init__(self, redis_mgr: Optional[RedisManager] = None):
        self.logger = get_component_logger("risk_integration")
        self.redis_mgr = redis_mgr or redis_manager
        
        # Cache for risk status to avoid frequent DB queries
        self._risk_cache: Dict[str, tuple[RiskStatus, datetime]] = {}
        self._cache_ttl_seconds = 60  # Cache for 1 minute
    
    async def validate_signal_risk(
        self,
        signal: Signal,
        user_id: Optional[UUID] = None,
        account_balance: float = 1000.0
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a signal can be executed based on risk limits.
        
        Args:
            signal: Trading signal to validate.
            user_id: User ID for risk limits (None = default).
            account_balance: Current account balance from MT5.
            
        Returns:
            Tuple of (allowed, reason_if_blocked).
        """
        try:
            # Check cached risk status first
            cache_key = f"risk:{user_id or 'default'}"
            cached_risk = self._get_cached_risk(cache_key)
            
            if cached_risk:
                risk_status = cached_risk
            else:
                # Query fresh risk status
                async with AsyncSessionLocal() as db:
                    risk_status = await check_risk(db, user_id, account_balance)
                
                # Cache the result
                self._cache_risk_status(cache_key, risk_status)
            
            if not risk_status.allowed:
                self.logger.warning(
                    f"Signal blocked by risk limits: {risk_status.reason}"
                )
                return False, risk_status.reason
            
            # Additional strategy-specific risk checks
            additional_check = await self._additional_risk_checks(
                signal, risk_status, user_id
            )
            
            if not additional_check[0]:
                return additional_check
            
            self.logger.debug(
                f"Signal passed risk validation: "
                f"trades_today={risk_status.trades_today}, "
                f"losses_today={risk_status.losses_today}, "
                f"drawdown={risk_status.drawdown_pct:.2f}%"
            )
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Risk validation error: {e}")
            # Fail safe - block signal on error
            return False, f"Risk validation error: {e}"
    
    async def _additional_risk_checks(
        self,
        signal: Signal,
        risk_status: RiskStatus,
        user_id: Optional[UUID]
    ) -> tuple[bool, Optional[str]]:
        """
        Additional strategy-specific risk checks.
        
        Args:
            signal: Trading signal.
            risk_status: Current risk status.
            user_id: User ID.
            
        Returns:
            Tuple of (allowed, reason_if_blocked).
        """
        # Check if we're approaching limits (warn at 80%)
        if risk_status.trades_today >= 1:  # 1 out of 2 max trades
            self.logger.warning(
                f"Approaching daily trade limit: {risk_status.trades_today}/2"
            )
        
        if risk_status.drawdown_pct >= 1.6:  # 80% of 2% limit
            self.logger.warning(
                f"Approaching drawdown limit: {risk_status.drawdown_pct:.2f}%/2.0%"
            )
        
        # Check signal quality vs risk
        if signal.confluence_score < 80 and risk_status.trades_today >= 1:
            return False, "Lower quality signal rejected - already traded today"
        
        # Check if signal direction aligns with recent performance
        # (This could be enhanced with more sophisticated logic)
        
        return True, None
    
    def _get_cached_risk(self, cache_key: str) -> Optional[RiskStatus]:
        """Get cached risk status if still valid."""
        if cache_key in self._risk_cache:
            risk_status, timestamp = self._risk_cache[cache_key]
            from datetime import timezone
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            
            if age < self._cache_ttl_seconds:
                return risk_status
            else:
                # Remove expired cache
                del self._risk_cache[cache_key]
        
        return None
    
    def _cache_risk_status(self, cache_key: str, risk_status: RiskStatus):
        """Cache risk status with timestamp."""
        from datetime import timezone
        self._risk_cache[cache_key] = (risk_status, datetime.now(timezone.utc))
        
        # Cleanup old cache entries (keep max 10)
        if len(self._risk_cache) > 10:
            oldest_key = min(
                self._risk_cache.keys(),
                key=lambda k: self._risk_cache[k][1]
            )
            del self._risk_cache[oldest_key]
    
    async def handle_risk_violation(
        self,
        user_id: Optional[UUID],
        reason: str,
        account_balance: float
    ):
        """
        Handle risk limit violations by disabling auto trading.
        
        Args:
            user_id: User ID.
            reason: Reason for violation.
            account_balance: Current account balance.
        """
        try:
            async with AsyncSessionLocal() as db:
                await disable_auto_trading(db, user_id, reason)
            
            self.logger.error(f"Auto trading disabled: {reason}")
            
            # Clear risk cache to force fresh check
            cache_key = f"risk:{user_id or 'default'}"
            if cache_key in self._risk_cache:
                del self._risk_cache[cache_key]
                
        except Exception as e:
            self.logger.error(f"Error handling risk violation: {e}")
    
    async def get_risk_status(
        self,
        user_id: Optional[UUID] = None,
        account_balance: float = 1000.0
    ) -> RiskStatus:
        """
        Get current risk status for monitoring.
        
        Args:
            user_id: User ID (None = default).
            account_balance: Current account balance.
            
        Returns:
            Current RiskStatus.
        """
        try:
            async with AsyncSessionLocal() as db:
                return await check_risk(db, user_id, account_balance)
        except Exception as e:
            self.logger.error(f"Error getting risk status: {e}")
            # Return safe default
            return RiskStatus(
                allowed=False,
                trades_today=999,
                losses_today=999,
                drawdown_pct=100.0,
                reason=f"Risk status error: {e}"
            )
    
    async def clear_risk_cache(self):
        """Clear all cached risk data."""
        self._risk_cache.clear()
        self.logger.debug("Risk cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "cached_entries": len(self._risk_cache),
            "cache_ttl_seconds": self._cache_ttl_seconds,
            "cache_keys": list(self._risk_cache.keys())
        }


# Global risk integration instance
risk_integration = RiskIntegration()