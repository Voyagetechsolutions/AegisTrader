"""Test timezone handling for MT5 data"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_timezone():
    from strategy.market_data import market_data_layer
    
    print("Testing MT5 timezone handling...")
    
    # Initialize MT5
    success = await market_data_layer.initialize_mt5()
    if not success:
        print("Failed to initialize MT5")
        return
    
    print("✓ MT5 initialized")
    
    # Fetch a candle
    candle = await market_data_layer.fetch_latest_candle(retries=1)
    
    if candle:
        print(f"\n✓ Candle fetched successfully!")
        print(f"  Timestamp: {candle.timestamp}")
        print(f"  Timezone: {candle.timestamp.tzinfo}")
        print(f"  Close: {candle.close}")
        print(f"  Volume: {candle.volume}")
        
        # Check if timestamp is reasonable
        now = datetime.now(timezone.utc)
        print(f"\n  Current UTC time: {now}")
        print(f"  Candle age: {(now - candle.timestamp).total_seconds():.0f} seconds")
        
        if candle.timestamp <= now:
            print("\n✓ Timestamp validation PASSED")
        else:
            print("\n✗ Timestamp validation FAILED (still in future)")
    else:
        print("✗ Failed to fetch candle")
    
    await market_data_layer.shutdown_mt5()

if __name__ == "__main__":
    asyncio.run(test_timezone())
