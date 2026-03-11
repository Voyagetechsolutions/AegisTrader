# 🎯 Aegis Trader - Complete Setup Guide

Everything you need to get Aegis Trader running with your broker.

---

## 📋 What You Need

- **Windows Computer** (for MetaTrader 5)
- **MT5 Account** (demo or live from your broker)
- **Python 3.9+** (for backend)
- **Node.js** (optional, for advanced features)
- **Smartphone** (for mobile app)

---

## 🚀 Quick Start (30 Minutes)

### 1. Backend Setup (10 min)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start backend
python -m uvicorn backend.main:app --reload --port 8000
```

### 2. MT5 Setup (10 min)

See `MT5_QUICK_SETUP.md` for step-by-step:
1. Install MT5 from your broker
2. Copy bridge to MT5
3. Attach to US30 chart
4. Enable AutoTrading

### 3. Mobile App Setup (10 min)

```bash
cd mobile
rm -rf node_modules package-lock.json
npm install
npm start
```

Update IP in `mobile/services/api.ts` and scan QR code.

---

## 📚 Detailed Guides

### Backend & System
- `README.md` - Main project documentation
- `CRITICAL_FIXES_APPLIED.md` - All safety fixes implemented
- `FINAL_SAFETY_VALIDATION.md` - Production readiness checklist

### MT5 Connection
- `MT5_SETUP_GUIDE.md` - **Complete MT5 setup guide** ⭐
- `MT5_QUICK_SETUP.md` - Quick 5-minute setup
- `mql5/AegisTradeBridge.mq5` - The bridge code

### Mobile App
- `MOBILE_APP_UPDATED.md` - Complete mobile documentation
- `MOBILE_QUICK_START.md` - Quick start guide
- `mobile/README_UPDATED.md` - In-folder documentation
- `mobile/EXPO_55_UPGRADE.md` - Expo 55 upgrade notes

### Audits & Safety
- `AEGIS_TRADER_AUDIT_REPORT.md` - Full system audit
- `AEGIS_TRADER_FAILURE_MODE_AUDIT.md` - Failure mode analysis

---

## 🔧 Configuration

### 1. Environment Variables (.env)

```bash
# Application
APP_ENV=development
DASHBOARD_JWT_SECRET=your-jwt-secret

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# MT5 Connection
MT5_NODE_URL=http://localhost:8001
MT5_NODE_SECRET=your-mt5-secret

# Risk Limits
MAX_DAILY_TRADES=2
MAX_DAILY_LOSSES=2
MAX_DAILY_DRAWDOWN_PCT=2.0
MAX_SPREAD_POINTS=5
MAX_SLIPPAGE_POINTS=10

# Timezone
TIMEZONE=Africa/Johannesburg
```

### 2. MT5 Bridge (AegisTradeBridge.mq5)

```cpp
string API_BASE_URL = "http://localhost:8000";
string API_SECRET = "your-mt5-secret";  // Match .env
```

### 3. Mobile App (mobile/services/api.ts)

```typescript
const API_BASE_URL = __DEV__ 
  ? 'http://YOUR_IP:8000'  // Your computer's IP
  : 'https://your-production-url.com';
```

---

## ✅ Verification Checklist

### Backend
- [ ] Backend starts without errors
- [ ] Health check returns OK: `curl http://localhost:8000/dashboard/health`
- [ ] Dashboard accessible at `http://localhost:8000`
- [ ] Telegram bot responds to `/start`

### MT5
- [ ] MT5 installed and logged in
- [ ] Bridge compiled without errors
- [ ] Bridge attached to US30 chart
- [ ] AutoTrading enabled (green button)
- [ ] "Connected to backend" in Experts tab
- [ ] Balance displays in dashboard

### Mobile
- [ ] App connects (green dot in header)
- [ ] Status bar shows data
- [ ] Signals tab loads
- [ ] Trades tab loads
- [ ] Mode switching works

---

## 🎮 How to Use

### Modes

**Analyze Mode** (Safe)
- System analyzes market
- Generates signals
- NO trades executed
- Use for testing and learning

**Trade Mode** (Live)
- System analyzes market
- Generates signals
- Executes trades automatically
- Requires auto_trade enabled

**Swing Mode** (Manual)
- System analyzes market
- Sends swing trade alerts
- You approve/reject manually
- Good for learning

### Controls

**Via Dashboard:**
- Switch modes with Quick Controls
- Toggle auto-trading
- Close all positions
- Emergency stop

**Via Mobile:**
- Same controls as dashboard
- Monitor on the go
- Get push notifications

**Via Telegram:**
```
/start - Show menu
/status - Current status
/mode analyze - Switch to analyze
/mode trade - Switch to trade
/settings - View settings
/closeall - Close all positions
/stop - Emergency stop
```

---

## 🛡️ Safety Features

### Risk Limits
- Max 2 trades per day
- Max 2 losses per day
- Max 2% daily drawdown
- Automatic stop when limits hit

### Trade Management
- TP1 at 1:1 (close 50%)
- Move SL to breakeven after TP1
- TP2 at 2:1 (close remaining)
- Runner continues if momentum strong

### Filters
- News blackout (30min before/after major news)
- Session windows (London, NY, Power Hour)
- Spread filter (max 5 points)
- Slippage validation (max 10 points)

### Emergency Controls
- Emergency stop button
- Close all positions
- Safe mode
- Manual override always available

---

## 📊 Monitoring

### Dashboard
- Live status and metrics
- Recent signals
- Trade history
- Risk monitoring

### Mobile App
- Same as dashboard
- Monitor anywhere
- Quick controls
- Real-time updates

### Telegram
- Trade notifications
- Signal alerts
- Risk warnings
- Daily summaries

### MT5
- Watch Experts tab for logs
- Monitor open positions
- Check account balance
- Review trade history

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install -r requirements.txt

# Check .env file exists
ls -la .env
```

### MT5 Not Connecting
1. Check MT5 is running
2. Check EA is attached to chart
3. Check AutoTrading enabled
4. Verify API_BASE_URL in bridge
5. Check MT5_NODE_SECRET matches
6. Add backend URL to WebRequest whitelist

### Mobile App Won't Connect
1. Check backend is running
2. Verify IP address in api.ts
3. Check firewall allows port 8000
4. Ensure same WiFi network
5. Try `curl http://YOUR_IP:8000/dashboard/health`

### No Trades Executing
1. Check mode is "trade" (not "analyze")
2. Check auto_trade is enabled
3. Check risk limits not hit
4. Check news blackout not active
5. Check spread not too high
6. Review backend logs for errors

---

## 🎓 Learning Path

### Week 1: Demo Testing
- Run in "analyze" mode
- Study signals generated
- Understand confluence scoring
- Learn session windows
- Review paper trade results

### Week 2: Live Monitoring
- Switch to "trade" mode on demo
- Monitor all trades closely
- Verify TP1/TP2/BE logic
- Check risk limits work
- Test emergency controls

### Week 3: Optimization
- Adjust settings if needed
- Fine-tune risk parameters
- Test different sessions
- Review performance stats
- Prepare for live

### Week 4: Go Live
- Start with small lot sizes
- Monitor first trades closely
- Scale up gradually
- Keep emergency stop ready
- Review daily

---

## 📞 Support Resources

### Documentation
- All guides in project root
- Code comments in source files
- API documentation in backend
- Type definitions in mobile app

### Logs
```bash
# Backend logs
python -m uvicorn backend.main:app --reload --port 8000

# MT5 logs
# In MT5: View → Toolbox → Experts tab

# Mobile logs
# In Expo: Check console output
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/dashboard/health

# Get status
curl http://localhost:8000/dashboard/status

# Test MT5 connection
curl http://localhost:8000/dashboard/positions
```

---

## ⚠️ Important Warnings

1. **Always test on demo first** - Minimum 1 week
2. **Never risk more than you can afford to lose**
3. **Monitor the system regularly** - Don't set and forget
4. **Keep emergency stop accessible** - Know how to stop it
5. **Review trades daily** - Learn from each trade
6. **Start small** - Scale up gradually
7. **Understand the strategy** - Don't trade blind
8. **Check your broker's rules** - Some brokers restrict EAs
9. **Backup your settings** - Save your configuration
10. **Stay updated** - Check for system updates

---

## 🚀 Next Steps

1. ✅ Complete backend setup
2. ✅ Connect MT5 with your broker
3. ✅ Install mobile app
4. ✅ Run in analyze mode for 1 week
5. ✅ Switch to trade mode on demo
6. ✅ Monitor for 1 week
7. ✅ Review all trades
8. ✅ Go live when confident
9. ✅ Start small
10. ✅ Scale gradually

---

## 📈 Success Tips

- **Be patient** - Don't rush to live trading
- **Keep learning** - Study each signal and trade
- **Stay disciplined** - Follow the risk rules
- **Monitor closely** - Especially first few weeks
- **Adjust carefully** - Don't over-optimize
- **Trust the process** - Let the system work
- **Stay calm** - Losses are part of trading
- **Review regularly** - Weekly performance reviews
- **Keep records** - Document everything
- **Ask questions** - Use the documentation

---

## 🎯 Goals

- **Week 1**: Understand the system
- **Week 2**: Verify it works on demo
- **Week 3**: Optimize settings
- **Week 4**: Go live carefully
- **Month 2**: Build confidence
- **Month 3**: Scale up gradually
- **Month 6**: Consistent results

---

Good luck with your trading! Remember: The system is a tool, but YOU are in control. Always monitor it and make sure it's working correctly with your broker. 🚀

For detailed MT5 setup, see: **MT5_SETUP_GUIDE.md**
