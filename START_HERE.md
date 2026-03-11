# START TRADING NOW - Simple Guide

## What This Does

This is a **WORKING TRADER** that:
- Connects directly to your MT5 terminal (no EA needed)
- Analyzes US30 every 30 seconds
- Takes REAL trades when signals appear
- Shows you everything in real-time

## Quick Start (3 Steps)

### 1. Make Sure MT5 is Running
- Open MetaTrader 5
- Login to your account (demo or live)
- That's it - no EA needed!

### 2. Run the Trader
Double-click: `START_TRADING.bat`

OR run in terminal:
```bash
python simple_trader.py
```

### 3. Watch It Trade
You'll see:
- Current price and indicators
- When signals are detected
- Trades being placed
- Profit/loss updates

## What You'll See

```
========================================
Iteration #1 - 2026-03-11 14:30:00
========================================

📈 Market Analysis:
   Price: 38450.00
   EMA Fast (9): 38445.50
   EMA Slow (21): 38440.20
   RSI (14): 55.30

📊 Open Positions: 0

🟢 BUY SIGNAL DETECTED!
✅ BUY order placed: Ticket #12345
   Price: 38450.00
   SL: 38400.00
   TP: 38550.00

⏰ Next check in 30 seconds...
```

## Strategy

**Simple Momentum Strategy:**
- BUY when: Fast EMA crosses above Slow EMA + RSI < 70
- SELL when: Fast EMA crosses below Slow EMA + RSI > 30
- Stop Loss: 50 points
- Take Profit: 100 points

## Configuration

Edit `simple_trader.py` to change:

```python
SYMBOL = "US30"        # Your broker's symbol name
LOT_SIZE = 0.01        # Position size (start small!)
TIMEFRAME = mt5.TIMEFRAME_M5  # M1, M5, M15, H1, etc.
```

## Common Symbol Names by Broker

- **US30:** US30, US30Cash, USTEC, DJ30, Dow30
- **NAS100:** NAS100, US100, USTEC, NDX
- **XAUUSD:** XAUUSD, GOLD, Gold

Check your MT5 Market Watch to see exact names.

## Troubleshooting

### "MT5 initialization failed"
- Make sure MT5 is running
- Try restarting MT5
- Check you're logged in

### "Symbol US30 not found"
- The script will show available symbols
- Change SYMBOL in the script to match your broker
- Example: `SYMBOL = "US30Cash"`

### "Order failed"
- Check you have enough margin
- Verify symbol is tradable
- Try smaller lot size (0.01)

## Stop Trading

Press `Ctrl+C` in the terminal

The script will:
- Stop taking new trades
- Show final statistics
- Disconnect cleanly

## Safety Features

- Only 1 position at a time
- Always uses stop loss
- Small default lot size (0.01)
- Easy to stop (Ctrl+C)

## Next Steps

Once this is working:
1. Watch it trade for a few hours
2. Adjust lot size if needed
3. Try different symbols
4. Modify the strategy

## Need Help?

1. Check MT5 is running
2. Verify symbol name matches your broker
3. Start with demo account
4. Use small lot sizes

---

**Ready to trade? Double-click START_TRADING.bat**
