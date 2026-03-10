"""
webhook.py
Receives TradingView Pine Script alert webhook payloads.
Authenticated by a shared webhook secret.

API Endpoints:
  POST /webhooks/tradingview - Receive TradingView alert
  POST /execution/callback - MT5 agent execution callback
"""

from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.schemas.schemas import (
    TradingViewWebhookPayload,
    WebhookResponse,
    ExecutionCallback,
)
from backend.modules.signal_engine import process_signal
from backend.modules.alert_manager import send_signal_alert
from backend.modules.trade_manager import open_trade, handle_execution_callback
from backend.routers.mt5_bridge import mt5_bridge

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])

# Default user ID - in multi-user mode this would be looked up from the secret
DEFAULT_USER_ID = None  # None = system-level signal


# ---------------------------------------------------------------------------
# TradingView Webhook (per spec)
# ---------------------------------------------------------------------------

@router.post(
    "/webhooks/tradingview",
    response_model=WebhookResponse,
    summary="Receive TradingView alert payload",
)
async def receive_tradingview_alert(
    payload: TradingViewWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Entry point for all TradingView webhook alerts.

    The Pine Script indicator sends a JSON payload containing:
    - Signal direction, prices, MTF bias
    - Confluence factors (FVG, liquidity sweep, displacement, MSS)
    - A shared secret for authentication

    Flow:
      authenticate -> idempotency check -> session filter -> spread filter
      -> score -> persist -> dispatch (alert/execute/ignore)

    Response per spec:
    {
        "ok": true,
        "signal_id": "uuid",
        "score": 89,
        "grade": "A+",
        "auto_trade_eligible": true,
        "reason": "Passed all filters"
    }
    """
    # Authenticate
    if payload.secret != settings.webhook_secret:
        logger.warning("Webhook received with invalid secret")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret",
        )

    logger.info(f"Webhook received: {payload.symbol} {payload.direction} entry={payload.entry}")

    # Fetch account balance for risk engine
    account_balance = await mt5_bridge.get_account_balance()

    # Run full signal pipeline
    result = await process_signal(
        db=db,
        payload=payload,
        user_id=DEFAULT_USER_ID,
        account_balance=account_balance,
    )

    # Handle duplicate signal
    if result.action == "duplicate":
        return WebhookResponse(
            ok=True,
            signal_id=str(result.signal.id) if result.signal else None,
            score=result.signal.score if result.signal else None,
            grade=result.signal.grade.value if result.signal and result.signal.grade else None,
            auto_trade_eligible=False,
            reason=result.reason,
        )

    # Post-pipeline alerts for A and A+ grades
    if result.signal and result.action in ("alerted", "executed"):
        await send_signal_alert(result.signal)

    # Execute trade for A+ eligible signals
    if result.action == "executed" and result.signal:
        await open_trade(
            db=db,
            signal=result.signal,
            user_id=DEFAULT_USER_ID,
            mt5_bridge=mt5_bridge,
            account_balance=account_balance,
        )

    # Build response per spec
    auto_eligible = False
    if result.score_result:
        auto_eligible = result.score_result.auto_trade_eligible

    return WebhookResponse(
        ok=True,
        signal_id=str(result.signal.id) if result.signal else None,
        score=result.signal.score if result.signal else None,
        grade=result.signal.grade.value if result.signal and result.signal.grade else None,
        auto_trade_eligible=auto_eligible,
        reason=result.reason,
    )


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

    logger.info(f"Execution callback: trade={callback.trade_id} status={callback.status}")

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


# ---------------------------------------------------------------------------
# Test Endpoint (dev only)
# ---------------------------------------------------------------------------

@router.post("/webhooks/test", summary="Test webhook endpoint (dev only)")
async def test_webhook(payload: dict):
    """Echo endpoint for testing webhook delivery from TradingView."""
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Only available in development mode")
    return {"received": payload}
