"""
Startup diagnostic script for cloud deployment.
Run this to check if the backend can start properly.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_imports():
    """Check if all required modules can be imported."""
    logger.info("Checking imports...")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pydantic
        import httpx
        import aiohttp
        logger.info("✓ All core imports successful")
        return True
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False

def check_config():
    """Check if configuration loads properly."""
    logger.info("Checking configuration...")
    try:
        from backend.config import settings
        logger.info(f"✓ Config loaded: env={settings.app_env}, db={settings.database_url[:50]}...")
        return True
    except Exception as e:
        logger.error(f"✗ Config error: {e}")
        return False

def check_database():
    """Check if database connection works."""
    logger.info("Checking database...")
    try:
        from backend.database import engine
        from backend.config import settings
        logger.info(f"✓ Database engine created: {settings.database_url[:50]}...")
        return True
    except Exception as e:
        logger.error(f"✗ Database error: {e}")
        return False

def check_app():
    """Check if FastAPI app can be created."""
    logger.info("Checking FastAPI app...")
    try:
        from backend.main import app
        logger.info(f"✓ FastAPI app created: {app.title}")
        return True
    except Exception as e:
        logger.error(f"✗ App creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks."""
    logger.info("=" * 60)
    logger.info("AEGIS TRADER STARTUP DIAGNOSTIC")
    logger.info("=" * 60)
    
    checks = [
        ("Imports", check_imports),
        ("Configuration", check_config),
        ("Database", check_database),
        ("FastAPI App", check_app),
    ]
    
    results = []
    for name, check_func in checks:
        logger.info(f"\n[{name}]")
        result = check_func()
        results.append((name, result))
    
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("\n✓ All checks passed! Backend should start successfully.")
        return 0
    else:
        logger.error("\n✗ Some checks failed. Fix errors above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
