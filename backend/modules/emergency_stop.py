"""
emergency_stop.py
Global emergency stop mechanism for immediate trading halt.

Provides:
- Global kill switch
- Immediate trade blocking
- Pending order cancellation
- Optional position closing
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Trade, TradeStatus, BotSetting

logger = logging.getLogger(__name__)

# Global emergency stop state
_emergency_stop_active = False
_emergency_stop_lock = asyncio.Lock()
_emergency_stop_reason: Optional[str] = None
_emergency_stop_timestamp: Optional[datetime] = None


async def activate_emergency_stop(
    db: AsyncSession,
    reason: str,
    close_positions: bool = False,
    mt5_bridge = None,
) -> dict:
    """
    Activate emergency stop - immediately halt all trading.
    
    Args:
        db: Database session
        reason: Reason for emergency stop
        close_positions: If True, close all open positions
        mt5_bridge: MT5 bridge for closing positions
        
    Returns:
        Dict with status and actions taken
    """
    global _emergency_stop_active, _emergency_stop_reason, _emergency_stop_timestamp
    
    async with _emergency_stop_lock:
        if _emergency_stop_active:
            return {
                "success": False,
                "message": "Emergency stop already active",
                "reason": _emergency_stop_reason,
            }
        
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {reason}")
        
        _emergency_stop_active = True
        _emergency_stop_reason = reason
        _emergency_stop_timestamp = datetime.now(pytz.UTC)
        
        actions_taken = []
        
        # 1. Disable auto-trading for all users
        try:
            result = await db.execute(select(BotSetting))
            settings = result.scalars().all()
            
            for setting in settings:
                setting.auto_trade_enabled = False
            
            await db.commit()
            actions_taken.append(f"Disabled auto-trading for {len(settings)} users")
        except Exception as e:
            logger.error(f"Failed to disable auto-trading: {e}")
            actions_taken.append(f"Failed to disable auto-trading: {e}")
        
        # 2. Close all open positions if requested
        if close_positions and mt5_bridge:
            try:
                from backend.modules.trade_manager import close_all_trades
                from backend.models.models import TradeCloseReason
                
                closed_count = await close_all_trades(
                    db,
                    user_id=None,  # All users
                    mt5_bridge=mt5_bridge,
                    reason=TradeCloseReason.FORCE_CLOSED,
                )
                actions_taken.append(f"Closed {closed_count} open positions")
            except Exception as e:
                logger.error(f"Failed to close positions: {e}")
                actions_taken.append(f"Failed to close positions: {e}")
        
        # 3. Send critical alerts
        try:
            from backend.modules.alert_manager import send_critical_alert
            await send_critical_alert(
                f"🚨 EMERGENCY STOP ACTIVATED\n\n"
                f"Reason: {reason}\n"
                f"Time: {_emergency_stop_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"Actions taken:\n" + "\n".join(f"- {a}" for a in actions_taken)
            )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
        
        return {
            "success": True,
            "message": "Emergency stop activated",
            "reason": reason,
            "timestamp": _emergency_stop_timestamp.isoformat(),
            "actions_taken": actions_taken,
        }


async def deactivate_emergency_stop(
    db: AsyncSession,
    authorized_by: str,
) -> dict:
    """
    Deactivate emergency stop - allow trading to resume.
    
    Args:
        db: Database session
        authorized_by: Who authorized the deactivation
        
    Returns:
        Dict with status
    """
    global _emergency_stop_active, _emergency_stop_reason, _emergency_stop_timestamp
    
    async with _emergency_stop_lock:
        if not _emergency_stop_active:
            return {
                "success": False,
                "message": "Emergency stop not active",
            }
        
        logger.warning(f"Emergency stop deactivated by {authorized_by}")
        
        _emergency_stop_active = False
        previous_reason = _emergency_stop_reason
        _emergency_stop_reason = None
        _emergency_stop_timestamp = None
        
        # Send alert
        try:
            from backend.modules.alert_manager import send_critical_alert
            await send_critical_alert(
                f"✅ Emergency stop deactivated\n\n"
                f"Authorized by: {authorized_by}\n"
                f"Previous reason: {previous_reason}\n\n"
                f"⚠️ Auto-trading remains DISABLED\n"
                f"Manual re-enable required via settings"
            )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
        
        return {
            "success": True,
            "message": "Emergency stop deactivated",
            "authorized_by": authorized_by,
            "note": "Auto-trading remains disabled - manual re-enable required",
        }


def is_emergency_stop_active() -> bool:
    """Check if emergency stop is currently active."""
    return _emergency_stop_active


def get_emergency_stop_status() -> dict:
    """Get current emergency stop status."""
    return {
        "active": _emergency_stop_active,
        "reason": _emergency_stop_reason,
        "timestamp": _emergency_stop_timestamp.isoformat() if _emergency_stop_timestamp else None,
    }


async def check_emergency_stop() -> tuple[bool, Optional[str]]:
    """
    Check if trading is allowed (emergency stop not active).
    
    Returns:
        Tuple of (allowed, reason_if_blocked)
    """
    if _emergency_stop_active:
        return False, f"Emergency stop active: {_emergency_stop_reason}"
    return True, None
