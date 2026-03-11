# Complete Working System - Get Trading NOW

## What You Have

You now have **TWO WAYS** to trade:

### Option 1: Standalone Trader (Fastest - No Backend Needed)
- **File:** `run_complete_system.py`
- **Start:** Double-click `START_COMPLETE_SYSTEM.bat`
- **What it does:** 
  - Connects directly to MT5
  - Uses your dual-engine strategies (Core + Quick Scalp)
  - Takes real trades
  - Shows everything in console
- **Best for:** Quick testing, seeing trades immediately

### Option 2: Full System (Backend + Mobile + Trading)
- **Components:** Backend API + Mobile App + Trading Engine
- **What it does:**
  - Backend serves API and runs strategies
  - Mobile app shows real-time data
  - Trading engine executes trades
  - Everything connected
- **Best for:** Production use, mobile monitoring

---

## QUICK START - Option 1 (Recommended First)

### Step 1: Open MT5
- Launch MetaTrader 5
- Login to your account (demo recommended for testing)
- That's it!

### Step 2: Start Trading
Double-click: **`START_COMPLETE_SYSTEM.bat`**

### Step 3: Watch It Work
You'll see:
```
======================================================================
ITERATION #1 - 2026-03-11 14:30:00
======================================================================

📋 Verifying symbols...
✓ US30 - Dow Jones Industrial Average
✓ NAS100 - NASDAQ 100 Index
✓ XAUUSD - Gold vs US Dollar

📊 Analyzing 3 markets...

✨ SIGNAL GENERATED:
   Engine: QUICK_SCALP
   Instrument: US30
   Direction: LONG
   Entry: 38450.00
   SL: 38400.00
   TP1: 38500.00
   R:R: 1.00
   Status: APPROVED

🎯 Executing trade: QUICK_SCALP - US30 LONG
✅ Trade executed: Ticket #12345
   Entry: 38450.00
   SL: 38400.00
   TP: 38500.00

📈 Statistics:
   Iterations: 1
   Signals Generated: 1
   Trades Executed: 1

💰 Account:
   Balance: $10000.00
   Equity: $10000.00
   Profit: $0.00

⏰ Next iteration in 60 seconds...
```

### Configuration

If your broker uses different symbol names, edit `run_complete_system.py` line 30:

```python
# Change these to match your broker
def get_mt5_symbol_name(self, instrument: Instrument) -> str:
    base_name = instrument.value
    variations = [
        base_name,           # US30
        f"{base_name}Cash",  # US30Cash
        f"{base_name}.cash", # US30.cash
        # Add your broker's format here
    ]
```

Common broker formats:
- **IC Markets:** US30, NAS100, XAUUSD
- **Pepperstone:** US30Cash, NAS100Cash, XAUUSDCash
- **FTMO:** US30.cash, NAS100.cash, XAUUSD.cash

---

## FULL SYSTEM SETUP - Option 2

### Part 1: Start Backend

```bash
# Terminal 1
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Test it: Open browser to `http://localhost:8000/docs`

### Part 2: Start Mobile App

```bash
# Terminal 2
cd mobile
npx expo start
```

Then:
- Scan QR code with Expo Go app (on phone)
- OR press 'a' for Android emulator
- OR press 'i' for iOS simulator

### Part 3: Connect Everything

1. **In mobile app:**
   - Go to Engines tab (⚡ icon)
   - You should see MT5 status
   - Toggle engines ON (Core Strategy, Quick Scalp)
   - Toggle markets ON (US30, NAS100, XAUUSD)
   - Tap START button

2. **Backend will:**
   - Connect to MT5
   - Start analyzing markets
   - Generate signals
   - Execute trades

3. **Mobile will show:**
   - Real-time signals
   - Trade notifications
   - Account balance
   - Performance stats

---

## What Each Component Does

### Dual-Engine Strategies

**Core Strategy:**
- 100-point confluence system
- Analyzes 7 indicators
- 1-2 trades per day
- 2:1 risk:reward
- High-quality setups only

**Quick Scalp:**
- M1 momentum entries
- 5-15 trades per day
- 1:1 risk:reward
- Fast in, fast out

**Auto-Trade Decision Engine:**
- Coordinates both engines
- Resolves conflicts (Core A+ wins)
- Prevents duplicate positions
- Uses market regime for tiebreakers

### Market Regime Detection

**Volatility (ATR-based):**
- LOW: Tight ranges
- NORMAL: Average movement
- HIGH: Increased volatility
- EXTREME: Major moves

**Trend (EMA + swings):**
- STRONG_TREND: Clear direction
- WEAK_TREND: Mild direction
- RANGING: Sideways
- CHOPPY: Erratic

### Performance Tracking

Tracks per engine + instrument:
- Win rate
- Average R
- Profit factor
- Max drawdown
- Consecutive wins/losses

---

## Troubleshooting

### "MT5 initialization failed"
```bash
# Check MT5 is running
# Try restarting MT5
# Verify you're logged in
```

### "Symbol US30 not found"
The script will show available symbols. Common fixes:
```python
# Edit run_complete_system.py
# Change symbol mapping to match your broker
SYMBOL = "US30Cash"  # or US30.cash, or USTEC, etc.
```

### "No signals generated"
This is normal! The strategies are selective:
- Core Strategy: Only trades A+ setups
- Quick Scalp: Needs momentum
- May take 30-60 minutes to see first signal
- Check market is open and moving

### Backend won't start
```bash
# Install dependencies
pip install -r requirements.txt

# Check port 8000 is free
netstat -ano | findstr :8000

# Try different port
uvicorn backend.main:app --port 8001
```

### Mobile won't connect
```typescript
// Edit mobile/services/api.ts
const API_BASE_URL = 'http://YOUR_COMPUTER_IP:8000'

// Find your IP:
// Windows: ipconfig
// Mac: ifconfig
// Example: http://192.168.1.100:8000
```

---

## Safety Features

### Built-in Protection
- ✅ Stop loss on every trade
- ✅ Position limits (1 per instrument)
- ✅ Daily trade limits per engine
- ✅ News blackout detection
- ✅ Emergency stop button
- ✅ Risk validation before execution

### Recommended Settings
- Start with demo account
- Use small lot sizes (0.01)
- Monitor first 10 trades closely
- Adjust parameters based on results

---

## What to Expect

### First Hour
- System connects to MT5
- Starts analyzing markets
- May not generate signals immediately
- This is normal - strategies are selective

### First Day
- Core Strategy: 0-2 signals expected
- Quick Scalp: 2-8 signals expected
- Some signals may not execute (regime filters)
- Monitor win rate and R multiples

### First Week
- Enough data to evaluate performance
- Adjust lot sizes if needed
- Fine-tune strategy parameters
- Consider going live if results good

---

## Performance Targets

### Core Strategy
- Win Rate: 60%+ target
- Average R: 1.5+ target
- Trades/Day: 1-2
- Best in: Trending markets

### Quick Scalp
- Win Rate: 55%+ target
- Average R: 0.8+ target
- Trades/Day: 5-15
- Best in: Volatile markets

### Combined
- Monthly Return: 5-10% target
- Max Drawdown: <20%
- Sharpe Ratio: 1.5+ target

---

## Next Steps

1. **Start with Option 1** (standalone trader)
   - See trades happening immediately
   - Verify strategies work
   - Check symbol names are correct

2. **Then try Option 2** (full system)
   - Start backend
   - Connect mobile app
   - Monitor from phone

3. **Optimize**
   - Adjust lot sizes
   - Fine-tune parameters
   - Add more markets
   - Scale up gradually

---

## Files You Need

### To Trade Now:
- `run_complete_system.py` - Complete trading system
- `START_COMPLETE_SYSTEM.bat` - Easy starter

### For Full System:
- `backend/` - API and strategies
- `mobile/` - Mobile app
- `.env` - Configuration

### For Reference:
- `CURRENT_STRATEGY_RUNTHROUGH.md` - Strategy details
- `IMPLEMENTATION_COMPLETE.md` - System overview
- `QUICK_REFERENCE.md` - Daily operations

---

## Support

### Check Logs
```bash
# Standalone trader
cat trading_system.log

# Backend
# Check console output

# MT5
# Check Experts tab in MT5
```

### Common Issues
1. Symbol not found → Check broker's symbol names
2. No signals → Wait longer, strategies are selective
3. Connection failed → Restart MT5
4. Backend error → Check dependencies installed

---

## Ready to Trade?

### Fastest Way (5 minutes):
1. Open MT5
2. Double-click `START_COMPLETE_SYSTEM.bat`
3. Watch trades happen!

### Full System (15 minutes):
1. Start backend: `uvicorn backend.main:app --reload`
2. Start mobile: `cd mobile && npx expo start`
3. Open mobile app
4. Tap START on Engines screen
5. Monitor from phone!

---

**The system is ready. Your dual-engine strategies are implemented. MT5 connection works. Time to trade!**
