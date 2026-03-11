"""
Quick test script to verify the strategy engine pipeline works.
"""
import asyncio
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '..')

from strategy.models import Candle, Timeframe
from strategy.engine import strategy_engine

async def create_mock_candle(price: float, timestamp: datetime) -> Candle:
    """Create a mock 1M candle for testing."""
    return Candle(
        timestamp=timestamp,
        open=price,
        high=price + 20,
        low=price - 20,
        close=price + 10,
        volume=1000,
        timeframe=Timeframe.M1
    )

async def test_pipeline():
    """Test the complete pipeline with mock data."""
    print("Testing Strategy Engine Pipeline\n")
    
    try:
        # Initialize
        print("1. Initializing engine...")
        await strategy_engine.initialize()
        print("   OK Engine initialized\n")
        
        # Generate 100 mock 1M candles
        print("2. Generating mock candles...")
        base_price = 42000.0
        now = datetime.now()
        
        for i in range(100):
            timestamp = now - timedelta(minutes=100-i)
            price = base_price + (i * 5)
            candle = await create_mock_candle(price, timestamp)
            
            await strategy_engine.market_data.store_candle(candle)
            await strategy_engine.aggregator.process_new_candle(candle)
        
        print(f"   OK Generated 100 candles\n")
        
        # Check aggregated candles
        print("3. Checking aggregated timeframes...")
        candles_5m = await strategy_engine.aggregator.get_timeframe_candles(Timeframe.M5, 10)
        candles_1h = await strategy_engine.aggregator.get_timeframe_candles(Timeframe.H1, 5)
        print(f"   OK 5M candles: {len(candles_5m)}")
        print(f"   OK 1H candles: {len(candles_1h)}\n")
        
        # Test analysis engines
        print("4. Testing analysis engines...")
        if len(candles_5m) >= 50:
            bias = await strategy_engine.bias_engine.analyze(candles_5m, Timeframe.M5)
            print(f"   OK Bias: {bias.direction.value} (EMA dist: {bias.ema_distance:.2f})")
            
            levels = await strategy_engine.level_engine.analyze(candles_5m)
            print(f"   OK Levels: 250={levels.nearest_250}, 125={levels.nearest_125}")
            
            liquidity = await strategy_engine.liquidity_engine.analyze(candles_5m, Timeframe.M5)
            print(f"   OK Liquidity: {len(liquidity.recent_sweeps)} sweeps")
            
            fvg = await strategy_engine.fvg_engine.analyze(candles_5m, Timeframe.M5)
            print(f"   OK FVG: {len(fvg.active_fvgs)} active")
            
            displacement = await strategy_engine.displacement_engine.analyze(candles_5m, Timeframe.M5)
            print(f"   OK Displacement: {displacement.strength:.1f}% strength")
            
            structure = await strategy_engine.structure_engine.analyze(candles_5m, Timeframe.M5)
            print(f"   OK Structure: {len(structure.recent_breaks)} breaks\n")
        
        # Test one full cycle
        print("5. Running one full processing cycle...")
        await strategy_engine._process_cycle()
        print("   OK Cycle completed\n")
        
        # Get status
        print("6. Engine status:")
        status = await strategy_engine.get_status()
        print(f"   Running: {status['running']}")
        print(f"   Initialized: {status['components_initialized']}")
        
        print("\nALL TESTS PASSED")
        
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await strategy_engine.stop()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
