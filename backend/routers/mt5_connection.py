"""
MT5 Connection API - Mobile-friendly endpoints for MT5 management.

Provides endpoints for:
- Connection status
- Account information
- Market data
- Connection testing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.modules.mt5_manager import mt5_manager
from backend.strategy.dual_engine_models import Instrument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mt5", tags=["MT5 Connection"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class ConnectionStatusResponse(BaseModel):
    """MT5 connection status."""
    connected: bool
    status: str
    last_check: Optional[str]
    bridge_healthy: bool
    reconnect_attempts: int


class AccountInfoResponse(BaseModel):
    """MT5 account information."""
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    open_positions: int


class MarketPriceResponse(BaseModel):
    """Current market price."""
    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: str


class ConnectionTestRequest(BaseModel):
    """Connection test request."""
    test_account_info: bool = True
    test_market_data: bool = True
    test_positions: bool = True


class ConnectionTestResponse(BaseModel):
    """Connection test results."""
    overall_success: bool
    connection_status: str
    account_info_test: bool
    market_data_test: bool
    positions_test: bool
    errors: List[str]


# ---------------------------------------------------------------------------
# Connection Status Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=ConnectionStatusResponse, summary="Get MT5 connection status")
async def get_connection_status():
    """
    Get current MT5 connection status.
    
    Returns:
    - Connection state (connected/disconnected/error)
    - Last health check time
    - Bridge health status
    - Reconnection attempts
    """
    try:
        status = await mt5_manager.get_connection_status()
        return ConnectionStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect", summary="Connect to MT5")
async def connect_mt5():
    """
    Establish connection to MT5.
    
    Returns:
        Connection result
    """
    try:
        success = await mt5_manager.connect()
        
        if success:
            return {
                "ok": True,
                "message": "Connected to MT5 successfully",
                "status": "connected"
            }
        else:
            return {
                "ok": False,
                "message": "Failed to connect to MT5 - check if EA is running",
                "status": "error"
            }
    except Exception as e:
        logger.error(f"Error connecting to MT5: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect", summary="Disconnect from MT5")
async def disconnect_mt5():
    """
    Disconnect from MT5.
    
    Returns:
        Disconnection result
    """
    try:
        await mt5_manager.disconnect()
        return {
            "ok": True,
            "message": "Disconnected from MT5",
            "status": "disconnected"
        }
    except Exception as e:
        logger.error(f"Error disconnecting from MT5: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=ConnectionTestResponse, summary="Test MT5 connection")
async def test_connection(request: ConnectionTestRequest):
    """
    Test MT5 connection with various checks.
    
    Args:
        request: Test configuration
    
    Returns:
        Test results for each component
    """
    errors = []
    results = {
        "account_info_test": False,
        "market_data_test": False,
        "positions_test": False,
    }
    
    # Check connection status
    try:
        is_connected = await mt5_manager.is_connected()
        connection_status = "connected" if is_connected else "disconnected"
    except Exception as e:
        connection_status = "error"
        errors.append(f"Connection check failed: {str(e)}")
    
    # Test account info
    if request.test_account_info:
        try:
            account_info = await mt5_manager.get_account_info()
            results["account_info_test"] = account_info["balance"] >= 0
            if not results["account_info_test"]:
                errors.append("Account info returned invalid balance")
        except Exception as e:
            errors.append(f"Account info test failed: {str(e)}")
    
    # Test market data
    if request.test_market_data:
        try:
            price = await mt5_manager.get_current_price(Instrument.US30)
            results["market_data_test"] = price["spread"] < 999.0
            if not results["market_data_test"]:
                errors.append("Market data unavailable")
        except Exception as e:
            errors.append(f"Market data test failed: {str(e)}")
    
    # Test positions
    if request.test_positions:
        try:
            positions = await mt5_manager.get_positions()
            results["positions_test"] = True  # Success if no exception
        except Exception as e:
            errors.append(f"Positions test failed: {str(e)}")
    
    overall_success = all(results.values()) and len(errors) == 0
    
    return ConnectionTestResponse(
        overall_success=overall_success,
        connection_status=connection_status,
        **results,
        errors=errors
    )


# ---------------------------------------------------------------------------
# Account Information Endpoints
# ---------------------------------------------------------------------------

@router.get("/account", response_model=AccountInfoResponse, summary="Get account information")
async def get_account_info():
    """
    Get MT5 account information.
    
    Returns:
    - Balance
    - Equity
    - Margin
    - Free margin
    - Margin level
    - Open positions count
    """
    try:
        account_info = await mt5_manager.get_account_info()
        return AccountInfoResponse(**account_info)
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Market Data Endpoints
# ---------------------------------------------------------------------------

@router.get("/price/{instrument}", response_model=MarketPriceResponse, summary="Get current price")
async def get_current_price(instrument: str):
    """
    Get current bid/ask price for instrument.
    
    Args:
        instrument: US30, NAS100, or XAUUSD
    
    Returns:
        Current bid, ask, spread
    """
    try:
        # Validate instrument
        instrument_upper = instrument.upper()
        if instrument_upper not in ["US30", "NAS100", "XAUUSD"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid instrument: {instrument}. Must be US30, NAS100, or XAUUSD"
            )
        
        # Check if MT5 is connected
        is_connected = await mt5_manager.is_connected()
        if not is_connected:
            logger.warning(f"MT5 not connected when requesting price for {instrument_upper}")
            raise HTTPException(
                status_code=503,
                detail="MT5 not connected. Please ensure MT5 is running and connected."
            )
        
        # Map to Instrument enum
        instrument_map = {
            "US30": Instrument.US30,
            "NAS100": Instrument.NAS100,
            "XAUUSD": Instrument.XAUUSD,
        }
        
        inst = instrument_map[instrument_upper]
        price = await mt5_manager.get_current_price(inst)
        
        return MarketPriceResponse(**price)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current price for {instrument}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spread/{instrument}", summary="Get current spread")
async def get_current_spread(instrument: str):
    """
    Get current spread for instrument.
    
    Args:
        instrument: US30, NAS100, or XAUUSD
    
    Returns:
        Current spread in points
    """
    try:
        # Validate instrument
        if instrument.upper() not in ["US30", "NAS100", "XAUUSD"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid instrument: {instrument}. Must be US30, NAS100, or XAUUSD"
            )
        
        # Map to Instrument enum
        instrument_map = {
            "US30": Instrument.US30,
            "NAS100": Instrument.NAS100,
            "XAUUSD": Instrument.XAUUSD,
        }
        
        inst = instrument_map[instrument.upper()]
        spread = await mt5_manager.get_current_spread(inst)
        
        return {
            "instrument": instrument.upper(),
            "spread": spread,
            "acceptable": spread < 10.0  # Flag if spread is acceptable
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Positions Endpoints
# ---------------------------------------------------------------------------

@router.get("/positions", summary="Get open positions")
async def get_positions():
    """
    Get all open positions from MT5.
    
    Returns:
        List of open positions
    """
    try:
        positions = await mt5_manager.get_positions()
        
        return {
            "positions": [
                {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": pos.type,
                    "volume": pos.volume,
                    "open_price": pos.open_price,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                }
                for pos in positions
            ],
            "total": len(positions)
        }
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/health", summary="MT5 health check")
async def mt5_health_check():
    """
    Quick health check for MT5 connection.
    
    Returns:
        Health status
    """
    try:
        is_connected = await mt5_manager.is_connected()
        
        return {
            "ok": is_connected,
            "service": "MT5",
            "status": "healthy" if is_connected else "unhealthy",
            "message": "MT5 connection active" if is_connected else "MT5 not connected"
        }
    except Exception as e:
        logger.error(f"MT5 health check failed: {e}")
        return {
            "ok": False,
            "service": "MT5",
            "status": "error",
            "message": str(e)
        }
