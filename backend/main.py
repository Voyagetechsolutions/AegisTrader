"""
main.py
FastAPI application entry point for Aegis Trader backend.
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import create_tables
from backend.routers.webhook import router as webhook_router
from backend.routers.telegram import router as telegram_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.ea_router import router as ea_router
from backend.routers.strategy import router as strategy_router
from backend.routers.strategy_engine import router as strategy_engine_router
from backend.routers.mobile import router as mobile_router
from backend.routers.mt5_heartbeat import router as mt5_heartbeat_router
from backend.routers.dual_engine import router as dual_engine_router
from backend.routers.mt5_connection import router as mt5_connection_router
from backend.routers.trading_loop_router import router as trading_loop_router

logging.basicConfig(
    level=logging.INFO if settings.app_env == "production" else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Scheduler ─────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler(timezone=settings.timezone)


def _register_scheduled_jobs():
    """Register all background jobs."""
    from backend.services.weekly_report import run_weekly_report_job
    from backend.modules.news_filter import sync_forexfactory_news
    from backend.database import AsyncSessionLocal

    async def _weekly_job():
        await run_weekly_report_job()

    async def _news_sync_job():
        async with AsyncSessionLocal() as db:
            await sync_forexfactory_news(db)

    async def _position_monitor_job():
        """Monitor open positions for TP/SL hits."""
        try:
            from backend.modules.trade_manager import monitor_positions
            await monitor_positions()
        except ImportError:
            logger.debug("Position monitoring not yet implemented")
        except Exception as e:
            logger.error(f"Position monitor error: {e}")

    # Every Sunday at 07:00 SAST → send weekly overview
    scheduler.add_job(
        _weekly_job,
        trigger="cron",
        day_of_week="sun",
        hour=7,
        minute=0,
        id="weekly_report",
        replace_existing=True,
    )

    # Every day at 00:01 SAST → sync ForexFactory news
    scheduler.add_job(
        _news_sync_job,
        trigger="cron",
        hour=0,
        minute=1,
        id="news_sync",
        replace_existing=True,
    )

    # Every 60 seconds → monitor open positions
    scheduler.add_job(
        _position_monitor_job,
        trigger="interval",
        seconds=60,
        id="position_monitor",
        replace_existing=True,
    )

    logger.info("Scheduled jobs registered: weekly_report, news_sync, position_monitor")


# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(f"Starting Aegis Trader backend [{settings.app_env}]")
    
    try:
        # Create tables (both dev and production need this for SQLite)
        # For PostgreSQL in production, use migrations instead
        if "sqlite" in settings.database_url.lower():
            await create_tables()
            logger.info("Database tables created/verified")
        else:
            logger.info("Using PostgreSQL - ensure migrations are run")

        # Start scheduler
        _register_scheduled_jobs()
        scheduler.start()
        logger.info("APScheduler started")
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        # Don't crash - allow app to start even if scheduler fails
        logger.warning("Continuing startup despite errors")

    yield

    # Shutdown
    try:
        scheduler.shutdown(wait=False)
        logger.info("Aegis Trader backend shutting down")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# ── App ───────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Aegis Trader API",
    description="Automated trading assistant and execution engine for US30",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────

app.include_router(webhook_router)
app.include_router(telegram_router)
app.include_router(dashboard_router)
app.include_router(ea_router)
app.include_router(strategy_router)
app.include_router(strategy_engine_router)
app.include_router(mobile_router)
app.include_router(mt5_heartbeat_router)
app.include_router(mt5_connection_router)
app.include_router(dual_engine_router)
app.include_router(trading_loop_router)


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "ok",
        "env": settings.app_env,
        "version": "1.0.0",
        "database": "connected" if settings.database_url else "not configured"
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Aegis Trader API is running",
        "version": "1.0.0",
        "docs": "/docs" if settings.app_env != "production" else "disabled in production",
        "health": "/health"
    }
