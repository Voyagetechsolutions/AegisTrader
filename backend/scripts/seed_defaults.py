"""
seed_defaults.py
Creates default user and bot settings for initial setup.

Run with: python -m backend.scripts.seed_defaults
"""

import asyncio
import uuid
from datetime import datetime

import pytz
from sqlalchemy import select

from backend.database import AsyncSessionLocal, create_tables
from backend.models.models import User, BotSetting, BotMode, LotMode


async def seed_default_user():
    """Create a default user and settings if none exist."""

    async with AsyncSessionLocal() as db:
        # Check if any user exists
        result = await db.execute(select(User).limit(1))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User already exists: {existing_user.id}")
            return

        # Create default user
        user = User(
            id=uuid.uuid4(),
            email="trader@aegis.local",
            telegram_chat_id=None,  # Will be set when user sends /start to bot
            whatsapp_enabled=False,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create default bot settings
        settings = BotSetting(
            id=uuid.uuid4(),
            user_id=user.id,
            analysis_symbol="TVC:DJI",
            execution_symbol="US30",
            mode=BotMode.ANALYZE,
            auto_trade_enabled=False,
            sessions={
                "london": {"start": "10:00", "end": "13:00"},
                "new_york": {"start": "15:30", "end": "17:30"},
                "power_hour": {"start": "20:00", "end": "22:00"},
            },
            spread_max_points=5.0,
            spread_multiplier=2.0,
            news_block_standard_mins=15,
            news_block_major_mins=30,
            max_trades_per_day=2,
            max_losses_per_day=2,
            max_daily_drawdown_pct=2.0,
            lot_mode=LotMode.MINIMUM_LOT,
            fixed_lot=None,
            risk_percent=None,
            max_slippage_points=10.0,
            swing_alert_only=True,
            use_one_minute_refinement=False,
        )
        db.add(settings)

        await db.commit()
        print(f"Created default user: {user.id}")
        print(f"Created default settings: {settings.id}")


async def main():
    """Main entry point."""
    print("Creating database tables...")
    await create_tables()
    print("Tables created.")

    print("\nSeeding default user...")
    await seed_default_user()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
