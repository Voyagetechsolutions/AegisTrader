"""
webhook.py
Execution callback endpoint for MT5 agent.

API Endpoints:
  POST /execution/callback - MT5 agent execution callback
"""

from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.schemas.schemas import ExecutionCallback
from backend.modules.trade_manager import handle_execution_callback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])

# Default user ID - in multi-user mode this would be looked up from the secret
DEFAULT_USER_ID = None  # None = system-level signal


# ---------------------------------------------------------------------------
# Execution Callback (per spec)
# ---------------------------------------------------------------------------

@router.post(
    "/execution/callback",
    summary="MT5 agent execution callback",
)
async def execution_callback(
    callback: ExecutionCallback,
    db: AsyncSession = Depends(get_db),
    x_mt5_secret: str = Header(None, alias="X-MT5-Secret"),
):
    """
    MT5 agent returns execution status.

    Request per spec:
    {
        "trade_id": "uuid",
        "status": "executed",
        "broker_order_id": "123456",
        "fill_price": 46140,
        "slippage_points": 2,
        "message": "Order placed successfully"
    }
    """
    # Authenticate MT5 node
    if x_mt5_secret != settings.mt5_node_secret:
        logger.warning("Execution callback received with invalid secret")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MT5 secret",
        )

    logger.info("Execution callback: trade=%s status=%s", callback.trade_id, callback.status)

    trade = await handle_execution_callback(
        db=db,
        trade_id=callback.trade_id,
        status=callback.status,
        broker_order_id=callback.broker_order_id,
        fill_price=callback.fill_price,
        slippage_points=callback.slippage_points,
        message=callback.message,
    )

    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade not found: {callback.trade_id}",
        )

    return {
        "ok": True,
        "trade_id": str(trade.id),
        "status": trade.status.value if trade.status else None,
        "state": trade.state.value if trade.state else None,
    }
