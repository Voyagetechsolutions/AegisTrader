# 🔌 MetaTrader 5 Setup Guide - Connect Your Broker

This guide shows you how to connect Aegis Trader to MetaTrader 5 so it can analyze the market and execute trades through your broker.

## 📋 Overview

Aegis Trader uses a **bridge architecture**:

```
Python Backend (Analysis) ←→ MT5 Bridge (Node.js) ←→ MetaTrader 5 (Your Broker)
```

The system analyzes the market in Python and sends trade commands to MT5 through a bridge.

---

## 🎯 Step-by-Step Setup

### Step 1: Install MetaTrader 5

1. **Download MT5** from your broker's website
   - Examples: FTMO, TopStep, Forex.com, IC Markets, etc.
   - Or download from [MetaQuotes official site](https://www.metatrader5.com/en/download)

2. **Install MT5** on your Windows computer
   - The system requires Windows (MT5 doesn't run natively on Mac/Linux)
   - For Mac users: Use Parallels, VMware, or Boot Camp

3. **Login to your broker account**
   - Open MT5
   - File → Login to Trade Account
   - Enter your broker credentials
   - Select your broker's server

### Step 2: Install the MT5 Bridge Expert Advisor

The bridge is an MQL5 script that connects MT5 to the Python backend.

1. **Copy the bridge file:**
   ```bash
   # The bridge file is in your project
   mql5/AegisTradeBridge.mq5
   ```

2. **Open MT5 Data Folder:**
   - In MT5: File → Open Data Folder
   - Navigate to: `MQL5/Experts/`

3. **Copy the bridge:**
   - Copy `AegisTradeBridge.mq5` to the `Experts` folder
   - Or create it directly in MetaEditor

4. **Compile the Expert Advisor:**
   - In MT5: Tools → MetaQuotes Language Editor (or press F4)
   - Open `AegisTradeBridge.mq5`
   - Click "Compile" button (or press F7)
   - Check for "0 errors" in the output

### Step 3: Configure the Bridge

1. **Open the bridge file** in MetaEditor

2. **Set your configuration at the top:**
   ```cpp
   // Lines 13-17 in AegisTradeBridge.mq5
   input string   API_URL        = "http://localhost:8000";  // Your backend URL
   input string   API_SECRET     = "your-secret-here";       // Match .env file
   input int      HeartbeatSec   = 30;                       // Heartbeat every 30s
   input ulong    MagicNumber    = 202600;                   // Magic number
   input int      Slippage       = 10;                       // Max slippage
   ```

3. **Match the secret in your .env file:**
   ```bash
   # In your project root .env file
   MT5_NODE_SECRET=your-secret-here
   ```

4. **Save and recompile** the bridge (F7 in MetaEditor)

### Step 4: Attach the Bridge to a Chart

1. **Open a US30 chart** in MT5
   - File → New Chart → US30 (or US30.cash, US30m, depending on your broker)
   - Set timeframe to M5 (5-minute chart)

2. **Attach the Expert Advisor:**
   - In Navigator panel (Ctrl+N): Expert Advisors → AegisTradeBridge
   - Drag and drop onto the US30 chart
   - Or right-click chart → Expert Advisors → AegisTradeBridge

3. **Enable AutoTrading:**
   - Click "AutoTrading" button in MT5 toolbar (should turn green)
   - Or press Alt+A

4. **Configure EA settings:**
   - In the EA dialog:
     - ✅ Allow live trading
     - ✅ Allow DLL imports (if needed)
     - ✅ Allow WebRequest to your backend URL
   - Click OK

5. **Verify connection:**
   - Check the "Experts" tab at bottom of MT5
   - Should see: "AegisTradeBridge initialized"
   - Should see: "Connected to backend"

### Step 5: Configure Backend

1. **Update your .env file:**
   ```bash
   # MT5 Connection
   MT5_NODE_URL=http://localhost:8001
   MT5_NODE_SECRET=your-secret-key-here
   
   # Symbol mapping
   ANALYSIS_SYMBOL=US30
   EXECUTION_SYMBOL=US30  # Or US30.cash, US30m - check your broker
   ```

2. **Check your broker's symbol name:**
   - In MT5: View → Market Watch (Ctrl+M)
   - Find US30 (might be US30, US30.cash, US30m, etc.)
   - Use the exact name in EXECUTION_SYMBOL

### Step 6: Start the System

1. **Start the backend:**
   ```bash
   python -m uvicorn backend.main:app --reload --port 8000
   ```

2. **Verify MT5 connection:**
   ```bash
   curl http://localhost:8000/dashboard/health
   ```
   
   Should show:
   ```json
   {
     "ok": true,
     "components": {
       "database": true,
       "mt5_node": true,  // ← Should be true
       "telegram": true
     }
   }
   ```

3. **Check MT5 bridge logs:**
   - In MT5 Experts tab, you should see:
     - "Heartbeat sent"
     - "Balance: $XXXX"
     - "Positions: X"

---

## 🔧 Configuration Options

### Broker-Specific Settings

Different brokers have different symbol names and requirements:

**FTMO / TopStep:**
```bash
EXECUTION_SYMBOL=US30
```

**IC Markets / Pepperstone:**
```bash
EXECUTION_SYMBOL=US30.cash
```

**Forex.com:**
```bash
EXECUTION_SYMBOL=US30m
```

**Check your broker:**
- Open Market Watch in MT5
- Find the Dow Jones index
- Use the exact symbol name

### Lot Size Configuration

In your backend settings (via dashboard or Telegram):

**Fixed Lot Mode:**
```
/settings lot_mode fixed
/settings fixed_lot 0.1
```

**Risk Percentage Mode:**
```
/settings lot_mode risk_percent
/settings risk_percent 1.0
```

### Spread and Slippage

```bash
# In .env or via /settings
MAX_SPREAD_POINTS=5
MAX_SLIPPAGE_POINTS=10
```

---

## ✅ Verification Checklist

### MT5 Side
- [ ] MT5 installed and logged into broker
- [ ] US30 chart open
- [ ] AegisTradeBridge.mq5 compiled without errors
- [ ] EA attached to chart
- [ ] AutoTrading enabled (green button)
- [ ] "Connected to backend" in Experts tab
- [ ] No errors in Experts tab

### Backend Side
- [ ] Backend running on port 8000
- [ ] `.env` file configured with MT5_NODE_SECRET
- [ ] Health check shows mt5_node: true
- [ ] Dashboard shows "MT5 Node" green dot
- [ ] Balance displays correctly

### Test Trade
- [ ] Switch to "analyze" mode first
- [ ] Wait for a signal
- [ ] Check signal appears in dashboard/mobile
- [ ] Switch to "trade" mode
- [ ] Enable auto_trade
- [ ] Wait for next signal
- [ ] Verify trade opens in MT5

---

## 🐛 Troubleshooting

### "MT5 Node Offline" in Dashboard

**Problem:** Backend can't connect to MT5

**Solutions:**
1. Check MT5 is running
2. Check EA is attached to chart
3. Check AutoTrading is enabled
4. Verify API_BASE_URL in bridge matches backend
5. Check MT5_NODE_SECRET matches in both places
6. Check Windows Firewall allows connections

### "WebRequest not allowed"

**Problem:** MT5 blocks HTTP requests

**Solution:**
1. In MT5: Tools → Options → Expert Advisors
2. Check "Allow WebRequest for listed URL"
3. Add your backend URL: `http://localhost:8000`
4. Click OK
5. Restart MT5 and reattach the EA

**Note:** This is the most common issue! MT5 blocks all web requests by default for security.

### "Trade context busy"

**Problem:** MT5 is processing another operation

**Solution:**
- This is normal, the bridge will retry
- If persistent, restart MT5

### "Invalid stops"

**Problem:** SL/TP too close to entry

**Solution:**
1. Check your broker's minimum stop level
2. In MT5: Right-click symbol → Specification
3. Look for "Stops level"
4. Adjust your strategy if needed

### Trades not executing

**Problem:** Signals generated but no trades

**Checklist:**
1. Is auto_trade enabled? Check dashboard
2. Is mode set to "trade"? (not "analyze" or "swing")
3. Are risk limits hit? Check trades_today, losses_today
4. Is news blackout active? Check dashboard
5. Is spread too high? Check MAX_SPREAD_POINTS
6. Check backend logs for errors

---

## 🔐 Security Notes

### API Secret
- Use a strong random secret
- Never commit .env to git
- Keep MT5_NODE_SECRET private

### Demo vs Live
- **Always test on DEMO first**
- Verify all signals and trades work correctly
- Run for at least 1 week on demo
- Only switch to live when confident

### Risk Management
- Start with small lot sizes
- Use risk_percent mode (1-2% max)
- Monitor daily drawdown limits
- Keep emergency stop accessible

---

## 📊 Monitoring

### MT5 Experts Tab
Watch for:
- "Heartbeat sent" every 30s
- "Balance: $XXXX" updates
- "Order opened: #XXXXX" when trading
- Any error messages

### Backend Logs
```bash
# Watch backend logs
python -m uvicorn backend.main:app --reload --port 8000
```

Watch for:
- "MT5 health check: OK"
- "Signal generated: ..."
- "Trade opened: ..."
- Any errors or warnings

### Dashboard
- Check "MT5 Node" indicator (should be green)
- Monitor balance updates
- Watch open positions
- Check risk metrics

---

## 🚀 Going Live

### Pre-Live Checklist

1. **Demo Testing Complete**
   - [ ] Ran for at least 1 week
   - [ ] All signals executed correctly
   - [ ] TP1/TP2/BE logic working
   - [ ] Risk limits enforced
   - [ ] Emergency stop tested

2. **Live Account Setup**
   - [ ] Funded live account
   - [ ] MT5 logged into live account
   - [ ] Bridge attached to live chart
   - [ ] Reduced lot sizes for live
   - [ ] Risk limits set conservatively

3. **Monitoring Setup**
   - [ ] Telegram bot configured
   - [ ] Mobile app connected
   - [ ] Dashboard accessible
   - [ ] Alerts working

4. **Safety Measures**
   - [ ] Emergency stop tested
   - [ ] Close All tested
   - [ ] Daily drawdown limit set
   - [ ] Max trades per day set
   - [ ] News filter active

### First Live Trade

1. Start in "analyze" mode
2. Monitor signals for a few hours
3. Switch to "trade" mode
4. Enable auto_trade
5. Watch the first trade closely
6. Verify TP1/BE moves work
7. Monitor until trade closes

---

## 📞 Support

### Check Logs
```bash
# Backend logs
python -m uvicorn backend.main:app --reload --port 8000

# MT5 logs
# In MT5: View → Toolbox → Experts tab
```

### Test Connection
```bash
# Health check
curl http://localhost:8000/dashboard/health

# Get balance
curl http://localhost:8000/dashboard/status
```

### Common Issues
- See TROUBLESHOOTING section above
- Check CRITICAL_FIXES_APPLIED.md for known issues
- Review FINAL_SAFETY_VALIDATION.md for safety checks

---

## 🎓 Next Steps

1. **Complete this setup guide**
2. **Test on demo account** for 1 week minimum
3. **Review all signals and trades**
4. **Adjust settings** as needed
5. **Go live** when confident
6. **Monitor closely** for first week
7. **Scale up** gradually

---

## ⚠️ Important Reminders

- **Always test on demo first**
- **Never risk more than you can afford to lose**
- **Monitor the system regularly**
- **Keep emergency stop accessible**
- **Review trades daily**
- **Adjust risk limits as needed**

The system is designed to be safe, but YOU are responsible for monitoring it and making sure it operates correctly with your broker.

Good luck! 🚀
