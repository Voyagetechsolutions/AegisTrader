"""
Production Deployment Checklist and Runner
"""
import asyncio
import sys
sys.path.insert(0, '..')

from strategy.engine import strategy_engine
from news_filter import news_filter
from trade_journal import trade_journal
from datetime import datetime


async def run_production_checks():
    """Run all production readiness checks."""
    
    print("=" * 60)
    print("AEGIS TRADER - PRODUCTION READINESS CHECK")
    print("=" * 60)
    print()
    
    checks_passed = 0
    checks_total = 10
    
    # 1. Strategy Engine
    print("[1/10] Strategy Engine...")
    try:
        await strategy_engine.initialize()
        print("  [OK] Engine initialized")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 2. Redis Connection
    print("[2/10] Redis Connection...")
    try:
        from strategy.config import redis_manager
        redis = await redis_manager.get_redis()
        # Test connection
        result = await redis.ping()
        if result:
            print("  [OK] Redis connected")
            checks_passed += 1
        else:
            print("  [FAIL] Redis ping failed")
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 3. MT5 Connection
    print("[3/10] MT5 Connection...")
    try:
        import MetaTrader5 as mt5  # type: ignore
        if mt5.initialize():
            print("  [OK] MT5 connected")
            mt5.shutdown()
            checks_passed += 1
        else:
            error = mt5.last_error()
            print(f"  [FAIL] MT5 not available: {error}")
    except ImportError:
        print("  [FAIL] MT5 library not installed - run: pip install MetaTrader5")
    except Exception as e:
        print(f"  [FAIL] MT5 error: {e}")
    
    # 4. News Filter
    print("[4/10] News Filter...")
    try:
        allowed, reason = news_filter.is_trading_allowed(datetime.now())
        print(f"  [OK] News filter active (allowed: {allowed})")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 5. Trade Journal
    print("[5/10] Trade Journal...")
    try:
        stats = trade_journal.get_stats()
        print(f"  [OK] Journal ready (trades: {len(trade_journal.trades)})")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 6. Execution Simulator
    print("[6/10] Execution Simulator...")
    try:
        from execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator()
        print("  [OK] Execution simulator ready")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 7. All Analysis Engines
    print("[7/10] Analysis Engines...")
    try:
        engines = [
            strategy_engine.bias_engine,
            strategy_engine.level_engine,
            strategy_engine.fvg_engine,
            strategy_engine.liquidity_engine,
            strategy_engine.displacement_engine,
            strategy_engine.structure_engine
        ]
        print(f"  [OK] All {len(engines)} engines loaded")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 8. Signal Generator
    print("[8/10] Signal Generator...")
    try:
        from strategy.signal_generator import signal_generator
        print("  [OK] Signal generator ready")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 9. Risk Integration
    print("[9/10] Risk Management...")
    try:
        from strategy.risk_integration import risk_integration
        print("  [OK] Risk management active")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    # 10. Compatibility Layer
    print("[10/10] System Compatibility...")
    try:
        from strategy.compatibility import system_compatibility
        status = await system_compatibility.get_system_status()
        print(f"  [OK] Compatibility layer active")
        checks_passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
    
    print()
    print("=" * 60)
    print(f"CHECKS PASSED: {checks_passed}/{checks_total}")
    print("=" * 60)
    print()
    
    if checks_passed == checks_total:
        print("[OK] SYSTEM READY FOR PRODUCTION")
        print()
        print("Next steps:")
        print("1. Run 3-4 weeks in ANALYZE mode")
        print("2. Review trade journal and performance")
        print("3. Enable AUTO-TRADING if satisfied")
        print()
        return True
    else:
        print("[FAIL] SYSTEM NOT READY")
        print(f"Fix {checks_total - checks_passed} failing checks before deployment")
        print()
        return False


async def start_production():
    """Start production trading system."""
    
    ready = await run_production_checks()
    
    if not ready:
        print("Aborting - system not ready")
        return
    
    print("Starting production system...")
    print("Mode: ANALYZE (safe mode - no auto-trading)")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        await strategy_engine.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await strategy_engine.stop()
        print("System stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        asyncio.run(start_production())
    else:
        asyncio.run(run_production_checks())
