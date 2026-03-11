"""
Test execution simulator directly.
"""
import sys
sys.path.insert(0, '..')

from execution_simulator import ExecutionSimulator
from datetime import datetime

# Create simulator
sim = ExecutionSimulator(spread_points=3.0, slippage_points=2.0)

# Open long position
pos = sim.open_position(
    timestamp=datetime.now(),
    direction="long",
    entry=42000.0,
    sl=41950.0,
    tp1=42075.0,
    tp2=42150.0,
    size=1.0
)

print(f"Position opened:")
print(f"  Entry: {pos.entry_price} (requested: 42000)")
print(f"  SL: {pos.sl}")
print(f"  TP1: {pos.tp1}")
print(f"  TP2: {pos.tp2}")
print(f"  Status: {pos.status.value}\n")

# Simulate price hitting TP1
event = sim.update_position(pos, 42075.0, datetime.now())
if event:
    print(f"TP1 Hit:")
    print(f"  Event: {event['event']}")
    print(f"  Exit price: {event['price']}")
    print(f"  PnL: ${event['pnl']:.2f}")
    print(f"  Remaining size: {pos.remaining_size}")
    print(f"  SL moved to: {pos.sl}\n")

# Simulate price hitting TP2
event = sim.update_position(pos, 42150.0, datetime.now())
if event:
    print(f"TP2 Hit:")
    print(f"  Event: {event['event']}")
    print(f"  Exit price: {event['price']}")
    print(f"  PnL: ${event['pnl']:.2f}")
    print(f"  Remaining size: {pos.remaining_size}\n")

# Close remaining
event = sim.close_position(pos, 42200.0, datetime.now())
print(f"Runner Closed:")
print(f"  Exit price: {event['price']}")
print(f"  PnL: ${event['pnl']:.2f}\n")

# Calculate total
total_pnl = sim._calculate_pnl(pos)
print(f"Total PnL: ${total_pnl:.2f}")
print(f"Entry: {pos.entry_price}, Final: 42200")
print(f"Spread cost: {pos.entry_spread + pos.exit_spread} points")
print(f"Slippage cost: {pos.slippage} points")
