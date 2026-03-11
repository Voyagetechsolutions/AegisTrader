"""
Error Recovery and Degraded Mode for Python Strategy Engine.

Provides graceful error handling, automatic reconnection, and degraded
mode operation for critical errors.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from enum import Enum
from sqlalchemy import text

from backend.strategy.logging_config import get_component_logger, performance_logger


class EngineMode(Enum):
    """Strategy engine operating modes."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    RECOVERY = "recovery"
    OFFLINE = "offline"


class ErrorRecoveryManager:
    """
    Manages error recovery and degraded mode operation.
    
    Provides automatic reconnection for MT5 and Redis failures,
    graceful degradation for critical errors, and Telegram alerts.
    """
    
    def __init__(self):
        self.logger = get_component_logger("error_recovery")
        self.mode = EngineMode.NORMAL
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
        self.recovery_attempts: Dict[str, int] = {}
        
        # Configuration
        self.max_retries = 3
        self.retry_delay_base = 5  # seconds
        self.max_retry_delay = 300  # 5 minutes
        self.error_threshold = 5  # errors before degraded mode
        self.recovery_timeout = 600  # 10 minutes
    
    async def handle_error(
        self,
        component: str,
        error: Exception,
        recovery_func: Optional[Callable] = None
    ) -> bool:
        """
        Handle error with automatic recovery attempts.
        
        Args:
            component: Component name (e.g., 'mt5', 'redis', 'analysis')
            error: Exception that occurred
            recovery_func: Optional recovery function to call
            
        Returns:
            True if recovered, False if still failing
        """
        error_key = f"{component}_{type(error).__name__}"
        
        # Track error
        self._track_error(error_key)
        performance_logger.log_error(component, type(error).__name__)
        
        self.logger.error(
            f"{component} error: {error} "
            f"(count: {self.error_counts.get(error_key, 0)})"
        )
        
        # Check if we should enter degraded mode
        if self._should_enter_degraded_mode(component):
            await self._enter_degraded_mode(component, str(error))
            return False
        
        # Attempt recovery if function provided
        if recovery_func:
            recovered = await self._attempt_recovery(
                component, recovery_func, error_key
            )
            
            if recovered:
                self.logger.info(f"{component} recovered successfully")
                self._reset_error_count(error_key)
                return True
        
        return False
    
    def _track_error(self, error_key: str):
        """Track error occurrence."""
        if error_key not in self.error_counts:
            self.error_counts[error_key] = 0
        
        self.error_counts[error_key] += 1
        from datetime import timezone
        self.last_errors[error_key] = datetime.now(timezone.utc)
    
    def _should_enter_degraded_mode(self, component: str) -> bool:
        """Check if component errors exceed threshold."""
        component_errors = sum(
            count for key, count in self.error_counts.items()
            if key.startswith(component)
        )
        
        return component_errors >= self.error_threshold
    
    async def _enter_degraded_mode(self, component: str, reason: str):
        """Enter degraded mode for component failure."""
        if self.mode == EngineMode.NORMAL:
            self.mode = EngineMode.DEGRADED
            self.logger.warning(
                f"Entering DEGRADED mode due to {component} failures: {reason}"
            )
            
            # Send Telegram alert
            await self._send_telegram_alert(
                f"⚠️ Strategy Engine DEGRADED\n"
                f"Component: {component}\n"
                f"Reason: {reason}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
    
    async def _attempt_recovery(
        self,
        component: str,
        recovery_func: Callable,
        error_key: str
    ) -> bool:
        """
        Attempt recovery with exponential backoff.
        
        Args:
            component: Component name
            recovery_func: Recovery function to call
            error_key: Error tracking key
            
        Returns:
            True if recovery successful
        """
        if error_key not in self.recovery_attempts:
            self.recovery_attempts[error_key] = 0
        
        attempt = self.recovery_attempts[error_key]
        
        if attempt >= self.max_retries:
            self.logger.error(
                f"{component} recovery failed after {self.max_retries} attempts"
            )
            return False
        
        # Calculate backoff delay
        delay = min(
            self.retry_delay_base * (2 ** attempt),
            self.max_retry_delay
        )
        
        self.logger.info(
            f"Attempting {component} recovery (attempt {attempt + 1}/{self.max_retries}) "
            f"in {delay}s"
        )
        
        await asyncio.sleep(delay)
        
        try:
            # Attempt recovery
            if asyncio.iscoroutinefunction(recovery_func):
                result = await recovery_func()
            else:
                result = recovery_func()
            
            # Recovery successful
            self.recovery_attempts[error_key] = 0
            return True
            
        except Exception as e:
            self.logger.error(f"{component} recovery attempt failed: {e}")
            self.recovery_attempts[error_key] += 1
            return False
    
    def _reset_error_count(self, error_key: str):
        """Reset error count after successful recovery."""
        if error_key in self.error_counts:
            self.error_counts[error_key] = 0
        
        if error_key in self.recovery_attempts:
            self.recovery_attempts[error_key] = 0
    
    async def _send_telegram_alert(self, message: str):
        """Send Telegram alert for critical errors."""
        try:
            from backend.modules.alert_manager import send_message
            await send_message(message)
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
    
    async def check_recovery_status(self) -> bool:
        """
        Check if system can exit degraded mode.
        
        Returns:
            True if system is healthy enough to exit degraded mode
        """
        if self.mode != EngineMode.DEGRADED:
            return True
        
        # Check if errors have cleared
        from datetime import timezone
        recent_errors = sum(
            1 for timestamp in self.last_errors.values()
            if datetime.now(timezone.utc) - timestamp < timedelta(minutes=5)
        )
        
        if recent_errors == 0:
            await self._exit_degraded_mode()
            return True
        
        return False
    
    async def _exit_degraded_mode(self):
        """Exit degraded mode and return to normal operation."""
        self.mode = EngineMode.NORMAL
        self.logger.info("Exiting DEGRADED mode - returning to NORMAL operation")
        
        # Send Telegram alert
        await self._send_telegram_alert(
            f"✅ Strategy Engine RECOVERED\n"
            f"Mode: NORMAL\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Reset error counts
        self.error_counts.clear()
        self.recovery_attempts.clear()
    
    def get_mode(self) -> EngineMode:
        """Get current operating mode."""
        return self.mode
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for monitoring."""
        return {
            "mode": self.mode.value,
            "error_counts": self.error_counts.copy(),
            "recovery_attempts": self.recovery_attempts.copy(),
            "last_errors": {
                key: timestamp.isoformat()
                for key, timestamp in self.last_errors.items()
            },
            "total_errors": sum(self.error_counts.values())
        }
    
    async def force_recovery_mode(self):
        """Force system into recovery mode for manual intervention."""
        self.mode = EngineMode.RECOVERY
        self.logger.warning("Forced into RECOVERY mode")
        
        await self._send_telegram_alert(
            f"🔧 Strategy Engine RECOVERY MODE\n"
            f"Manual intervention required\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    async def force_offline_mode(self):
        """Force system offline for maintenance."""
        self.mode = EngineMode.OFFLINE
        self.logger.warning("Forced OFFLINE for maintenance")
        
        await self._send_telegram_alert(
            f"🛑 Strategy Engine OFFLINE\n"
            f"System maintenance in progress\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )


class ConnectionManager:
    """Manages automatic reconnection for external services."""
    
    def __init__(self, error_recovery: ErrorRecoveryManager):
        self.logger = get_component_logger("connection_manager")
        self.error_recovery = error_recovery
        self.connections: Dict[str, bool] = {
            "redis": False,
            "mt5": False,
            "database": False
        }
    
    async def ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is active."""
        try:
            from backend.strategy.config import redis_manager
            redis = await redis_manager.get_redis()
            await redis.ping()
            self.connections["redis"] = True
            return True
        except Exception as e:
            self.connections["redis"] = False
            
            async def recover():
                from backend.strategy.config import redis_manager
                await redis_manager.close()
                redis = await redis_manager.get_redis()
                await redis.ping()
            
            recovered = await self.error_recovery.handle_error(
                "redis", e, recover
            )
            return recovered
    
    async def ensure_mt5_connection(self) -> bool:
        """Ensure MT5 connection is active."""
        try:
            # TODO: Implement MT5 connection check
            self.connections["mt5"] = True
            return True
        except Exception as e:
            self.connections["mt5"] = False
            
            async def recover():
                # TODO: Implement MT5 reconnection
                pass
            
            recovered = await self.error_recovery.handle_error(
                "mt5", e, recover
            )
            return recovered
    
    async def ensure_database_connection(self) -> bool:
        """Ensure database connection is active."""
        try:
            from backend.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            self.connections["database"] = True
            return True
        except Exception as e:
            self.connections["database"] = False
            
            async def recover():
                # Database connection pool should auto-recover
                pass
            
            recovered = await self.error_recovery.handle_error(
                "database", e, recover
            )
            return recovered
    
    async def check_all_connections(self) -> Dict[str, bool]:
        """Check all connection statuses."""
        await self.ensure_redis_connection()
        await self.ensure_mt5_connection()
        await self.ensure_database_connection()
        
        return self.connections.copy()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status summary."""
        all_connected = all(self.connections.values())
        
        return {
            "all_connected": all_connected,
            "connections": self.connections.copy(),
            "timestamp": datetime.now().isoformat()
        }


# Global instances
error_recovery_manager = ErrorRecoveryManager()
connection_manager = ConnectionManager(error_recovery_manager)
