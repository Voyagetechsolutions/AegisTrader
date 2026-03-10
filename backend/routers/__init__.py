from backend.routers.webhook import router as webhook_router
from backend.routers.telegram import router as telegram_router
from backend.routers.dashboard import router as dashboard_router

__all__ = ["webhook_router", "telegram_router", "dashboard_router"]
