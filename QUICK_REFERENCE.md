# Quick Reference Guide - Dual-Engine Trading System

## Daily Operations

### Starting the System

```bash
# 1. Start Backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 2. Open MT5 and verify EA is running
# Look for: "✓ Connected to backend" in chart comment

# 3. Start Mobile App
cd mobile && npx expo start

# 4. Start Trading Loop (from mobile)
# Engines tab → Tap START button
```

### Stopping the System

```bash
# 1. Stop Trading Loop (from mobile)
# Engines tab → Tap STOP button

# 2. Stop Backend
# Ctrl+C in terminal

# 3. Close MT5 (optional)
```

---

## System Health Checks

### Backend Health
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "env": "development", "version": "1.0.0"}

curl http://localhost:8000/trading-loop/status
# Check: running: true/false, signals_generated, trades_executed
```

### MT5 Connection
```bash
curl http://localhost:8000/mt5/status
# Check: connected: true, status: "connected"

curl http://localhost:8000/mt5/heartbeat/status
# Check: connected: true, seconds_since < 60
```

### Trading Loop
```bash
curl http://localhost:8000/trading-loop/health
# Check: status: "healthy" or "stopped"
```

---

## Mobile App Quick Actions

### Engines Screen

**Start Trading:**
1. Verify MT5 shows "Connected" (green)
2. Enable desired engines (Core/Scalp)
3. Enable desired markets (US30/NAS100/XAUUSD)
4. Tap START button
5. Confirm start
6. Watch for "🔴 LIVE" indicator

**Stop Trading:**
1. Tap STOP button
2. Confirm stop
3. Verify status changes to "Stopped"

**Emergency Stop:**
1. Go to Dashboard tab
2. Tap "Emergency Stop"
3. Confirm action
4. All trading halts immediately

---

## Common Commands

### Backend

```bash
# Run tests
pytest backend/tests/

# Run specific test file
pytest backend/tests/test_auto_trade_decision_engine.py

# Check logs
tail -f backend.log

# Database reset (development only)
rm aegis_trader.db
python -m backend.database
```

### Mobile

```bash
# Clear cache and restart
npx expo start -c

# Run on Android
npx expo start --android

# Run on iOS
npx expo start --ios

# Build for production
eas build --platform all
```

### MT5

```
# Recompile EA
1. Open MetaEditor (F4)
2. Open AegisTradeBridge_v2.mq5
3. Press F7 to compile
4. Check for errors

# Reattach EA
1. Remove EA from chart
2. Drag EA back onto chart
3. Verify settings
4. Click OK
5. Enable AutoTrading
```

---

## API Endpoints Reference

### Trading Loop
- `GET /trading-loop/status` - Get loop status
- `POST /trading-loop/start` - Start loop
- `POST /trading-loop/stop` - Stop loop
- `POST /trading-loop/settings` - Update settings
- `WS /trading-loop/ws` - WebSocket connection

### Dual-Engine
- `GET /dual-engine/status` - Engine status
- `GET /dual-engine/signals/active` - Active signals
- `POST /dual-engine/engines/core/toggle` - Toggle Core Strategy
- `POST /dual-engine/engines/scalp/toggle` - Toggle Quick Scalp
- `POST /dual-engine/markets/{instrument}/toggle` - Toggle market

### MT5
- `GET /mt5/status` - Connection status
- `GET /mt5/account` - Account info
- `GET /mt5/positions` - Open positions
- `GET /mt5/price/{symbol}` - Current price
- `POST /mt5/connect` - Connect to MT5
- `POST /mt5/disconnect` - Disconnect from MT5

### Dashboard
- `GET /dashboard/status` - System overview
- `GET /dashboard/signals` - Recent signals
- `GET /dashboard/trades` - Trade history
- `POST /dashboard/emergency-stop` - Activate emergency stop
- `POST /dashboard/closeall` - Close all positions

---

## Troubleshooting Quick Fixes

### Backend Won't Start
```bash
# Check if port is in use
netstat -ano | findstr :8000

# Kill process using port (Windows)
taskkill /PID <PID> /F

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### MT5 Not Connecting
```
1. Check WebRequest is enabled
   Tools → Options → Expert Advisors → Allow WebRequest
   Add: http://127.0.0.1:8000

2. Verify API_SECRET matches .env file
   EA Settings → API_SECRET = Y_qQkaWbdXEdeJs-XXitLw

3. Check backend is running
   curl http://localhost:8000/health

4. Restart MT5 terminal

5. Reattach EA to chart
```

### Mobile Can't Connect
```
1. Verify backend is running
   curl http://localhost:8000/health

2. Check IP address in api.ts
   Should be your computer's IP, not localhost

3. Ensure phone and computer on same network

4. Try clearing app cache
   npx expo start -c

5. Check firewall isn't blocking port 8000
```

### WebSocket Not Connecting
```
1. Verify trading loop is running
   curl http://localhost:8000/trading-loop/status

2. Check WebSocket URL in api.ts
   Should use ws:// not http://

3. Restart mobile app

4. Check backend logs for WebSocket errors
```

### No Signals Generated
```
1. Check trading loop is running
   Mobile: Engines tab → Status should be "Running"

2. Verify markets are enabled
   Mobile: Engines tab → Toggle switches should be ON

3. Check MT5 is sending data
   curl http://localhost:8000/mt5/heartbeat/status

4. Review backend logs for errors
   Look for: "Market data fetch", "Signal generated"

5. Verify market conditions
   May not generate signals in choppy/ranging markets
```

---

## Configuration Files

### Backend (.env)
```env
DATABASE_URL=sqlite:///./aegis_trader.db
MT5_NODE_SECRET=Y_qQkaWbdXEdeJs-XXitLw
APP_ENV=development
TIMEZONE=Africa/Johannesburg
```

### Mobile (services/api.ts)
```typescript
const API_BASE_URL = __DEV__
  ? 'http://192.168.1.100:8000'  // Your computer's IP
  : 'https://your-app.onrender.com';
```

### MT5 EA Settings
```
API_URL: http://127.0.0.1:8000
API_SECRET: Y_qQkaWbdXEdeJs-XXitLw
HeartbeatSec: 5
PollIntervalMs: 1000
MagicNumber: 202600
Slippage: 10
```

---

## Performance Monitoring

### Key Metrics to Watch

**Trading Loop:**
- Iterations: Should increment every 60s
- Signals Generated: Track daily count
- Trades Executed: Compare to signals
- Errors: Should be minimal

**Engines:**
- Core Strategy: 1-2 trades/day target
- Quick Scalp: 5-15 trades/day target
- Win Rate: Monitor per engine
- Average R: Track profitability

**System:**
- MT5 Connection: Should stay green
- WebSocket: Should show "🔴 LIVE"
- Response Times: API calls < 1s
- Memory Usage: Monitor backend process

### Daily Checklist

**Morning (Before Market Open):**
- [ ] Start backend server
- [ ] Verify MT5 connected
- [ ] Check for system updates
- [ ] Review overnight performance
- [ ] Check news calendar

**During Trading:**
- [ ] Monitor signal quality
- [ ] Watch for errors in logs
- [ ] Check position management
- [ ] Verify stop losses in place
- [ ] Monitor account balance

**Evening (After Market Close):**
- [ ] Review day's trades
- [ ] Check performance metrics
- [ ] Backup database
- [ ] Review logs for errors
- [ ] Plan for next day

---

## Emergency Procedures

### System Crash
```
1. Stop trading loop immediately
2. Close all open positions manually in MT5
3. Check logs for error cause
4. Restart backend
5. Verify MT5 connection
6. Test with small position before resuming
```

### Unexpected Losses
```
1. Activate Emergency Stop
2. Review recent trades
3. Check for system errors
4. Verify strategy logic
5. Analyze market conditions
6. Adjust parameters if needed
```

### Connection Loss
```
1. Check internet connection
2. Verify MT5 terminal running
3. Check backend server status
4. Review firewall settings
5. Restart affected components
6. Monitor for reconnection
```

---

## Support Resources

### Documentation
- `IMPLEMENTATION_COMPLETE.md` - Full system overview
- `COMPLETE_SYSTEM_SETUP.md` - Detailed setup guide
- `PHASE_3_TRADING_LOOP_COMPLETE.md` - Trading loop details
- `CURRENT_STRATEGY_RUNTHROUGH.md` - Strategy explanation

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Logs
- Backend: Console output or `backend.log`
- MT5: Experts tab in MT5 terminal
- Mobile: Expo console output

### Testing
```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test
pytest backend/tests/test_trading_coordinator_integration.py -v
```

---

## Quick Tips

💡 **Always test on demo account first**
💡 **Monitor the first few signals closely**
💡 **Start with one market, then scale up**
💡 **Keep position sizes small initially**
💡 **Review performance daily**
💡 **Backup database regularly**
💡 **Update dependencies monthly**
💡 **Check logs for warnings**
💡 **Use emergency stop if unsure**
💡 **Document any issues encountered**

---

## Contact & Support

For issues or questions:
1. Check documentation files
2. Review API docs at `/docs`
3. Check logs for error messages
4. Test individual components
5. Create GitHub issue if needed

---

**Last Updated:** March 11, 2026
**System Version:** 2.0.0
**Status:** Production Ready (Pending Live Testing)
