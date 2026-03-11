# Complete System Setup Guide - Dual-Engine Trading System

## Overview
This guide walks you through setting up the complete dual-engine trading system from scratch, including backend, mobile app, and MT5 integration.

---

## Prerequisites

### Required Software
- Python 3.10+
- Node.js 18+
- MetaTrader 5 Terminal
- Expo CLI (for mobile development)
- PostgreSQL (optional, SQLite works for development)

### Required Accounts
- MT5 broker account (demo or live)
- Mobile device or emulator for testing

---

## Part 1: Backend Setup

### 1. Clone and Install Dependencies

```bash
# Navigate to project directory
cd aegis-trader

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` file in project root:

```env
# Database
DATABASE_URL=sqlite:///./aegis_trader.db

# MT5 Bridge Secret (must match EA)
MT5_NODE_SECRET=Y_qQkaWbdXEdeJs-XXitLw

# API Settings
APP_ENV=development
TIMEZONE=Africa/Johannesburg

# Telegram (optional)
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# News API (optional)
FOREXFACTORY_ENABLED=true
```

### 3. Initialize Database

```bash
# Run migrations
python -m backend.database

# Or start the server (auto-creates tables in dev mode)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Backend is Running

Open browser: `http://localhost:8000/docs`

You should see the FastAPI Swagger documentation.

---

## Part 2: MT5 Setup

### 1. Install MetaTrader 5

Download and install MT5 from your broker.

### 2. Enable WebRequest

1. Open MT5
2. Go to: Tools → Options → Expert Advisors
3. Check "Allow WebRequest for listed URL"
4. Add: `http://127.0.0.1:8000`
5. Click OK

### 3. Install Expert Advisor

**Option A: Use Updated EA (Recommended)**

1. Copy `mql5/AegisTradeBridge_v2.mq5` to:
   ```
   C:\Users\[YourName]\AppData\Roaming\MetaQuotes\Terminal\[BrokerID]\MQL5\Experts\
   ```

2. Open MetaEditor (F4 in MT5)
3. Open `AegisTradeBridge_v2.mq5`
4. Click Compile (F7)
5. Verify no errors

**Option B: Use Original EA**

1. Copy `mql5/AegisTradeBridge.mq5` (basic version without command polling)
2. Follow same steps as Option A

### 4. Attach EA to Chart

1. Open MT5
2. Open a chart (US30, NAS100, or XAUUSD)
3. Drag `AegisTradeBridge_v2` from Navigator → Expert Advisors
4. Configure settings:
   - API_URL: `http://127.0.0.1:8000`
   - API_SECRET: `Y_qQkaWbdXEdeJs-XXitLw` (must match .env)
   - HeartbeatSec: `5`
   - PollIntervalMs: `1000`
   - MagicNumber: `202600`
5. Click OK
6. Enable AutoTrading (button in toolbar)

### 5. Verify MT5 Connection

Check backend logs for:
```
MT5 Heartbeat: Balance=$10000.00, Positions=0
```

Or check API: `http://localhost:8000/mt5/status`

---

## Part 3: Mobile App Setup

### 1. Install Dependencies

```bash
cd mobile

# Install packages
npm install

# Or with yarn
yarn install
```

### 2. Configure API URL

Edit `mobile/services/api.ts`:

```typescript
const API_BASE_URL = __DEV__
  ? 'http://YOUR_COMPUTER_IP:8000'  // Change to your IP
  : 'https://your-render-app.onrender.com';
```

**Find Your IP:**
- Windows: `ipconfig` (look for IPv4 Address)
- Mac/Linux: `ifconfig` (look for inet)

Example: `http://192.168.1.100:8000`

### 3. Start Development Server

```bash
# Start Expo
npx expo start

# Or
npm start
```

### 4. Run on Device

**Option A: Physical Device**
1. Install Expo Go app from App Store/Play Store
2. Scan QR code from terminal
3. App will load

**Option B: Emulator**
1. Press `a` for Android emulator
2. Press `i` for iOS simulator (Mac only)

### 5. Verify Mobile Connection

1. Open app
2. Navigate to "Engines" tab (⚡ icon)
3. Check MT5 connection status (should show green if connected)
4. Check account balance displays

---

## Part 4: Start Trading Loop

### 1. Verify All Components Running

**Backend:**
- Server running on port 8000
- No errors in logs

**MT5:**
- EA attached to chart
- AutoTrading enabled
- Green "✓ Connected to backend" in chart comment

**Mobile:**
- App loaded successfully
- Engines screen shows data
- MT5 status shows "Connected"

### 2. Configure Engines

In mobile app (Engines screen):

1. **Enable/Disable Engines:**
   - Toggle "Core Strategy" (100-point confluence)
   - Toggle "Quick Scalp" (M1 momentum)

2. **Enable/Disable Markets:**
   - Toggle "US30" (Dow Jones)
   - Toggle "NAS100" (NASDAQ)
   - Toggle "XAUUSD" (Gold)

### 3. Start Trading Loop

1. Tap "START" button in Trading Loop section
2. Confirm you want to start
3. Status changes to "Running" with green indicator
4. "🔴 LIVE" badge appears
5. Statistics start updating

### 4. Monitor Activity

**Real-time Updates:**
- Signal notifications appear as alerts
- Trade execution notifications
- Loop statistics update every 60 seconds

**WebSocket Connection:**
- "🔴 LIVE" indicator shows WebSocket active
- Auto-reconnects if connection drops

---

## Part 5: Testing the System

### 1. Test Signal Generation

**Manual Test:**
```bash
# In Python console or script
import asyncio
from backend.services.trading_loop import trading_loop_service

# Start loop
asyncio.run(trading_loop_service.start())
```

Watch for:
- Market data fetching
- Regime detection
- Signal generation
- Trade execution (if approved)

### 2. Test WebSocket Updates

1. Keep mobile app open on Engines screen
2. Start trading loop
3. Watch for real-time updates
4. Verify alerts appear for signals/trades

### 3. Test MT5 Integration

**Check Historical Data:**
```bash
# Test endpoint
curl http://localhost:8000/mt5/price/US30
```

**Check Positions:**
```bash
curl http://localhost:8000/mt5/positions
```

### 4. Test Emergency Stop

1. In mobile app, go to Dashboard
2. Tap "Emergency Stop"
3. Verify trading loop stops
4. Verify no new trades placed

---

## Part 6: Troubleshooting

### Backend Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt --upgrade
```

**Database errors:**
```bash
# Delete and recreate
rm aegis_trader.db
python -m backend.database
```

**Port already in use:**
```bash
# Change port
uvicorn backend.main:app --reload --port 8001
```

### MT5 Issues

**EA not connecting:**
1. Check WebRequest is enabled
2. Verify API_URL matches backend
3. Check API_SECRET matches .env
4. Restart MT5 terminal

**"WebRequest not allowed" error:**
1. Add `http://127.0.0.1:8000` to allowed URLs
2. Restart MT5
3. Reattach EA

**No historical data:**
1. Ensure EA v2 is being used
2. Check EA logs for errors
3. Verify symbol is available in MT5

### Mobile Issues

**Cannot connect to backend:**
1. Verify backend is running
2. Check IP address is correct
3. Ensure phone and computer on same network
4. Try `http://localhost:8000` if using emulator

**WebSocket not connecting:**
1. Check trading loop is running
2. Verify WebSocket URL in api.ts
3. Check for firewall blocking WebSocket

**App crashes on start:**
```bash
# Clear cache
npx expo start -c

# Reinstall dependencies
rm -rf node_modules
npm install
```

---

## Part 7: Production Deployment

### Backend Deployment (Render.com)

1. Create account on Render.com
2. Connect GitHub repository
3. Create new Web Service
4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from .env
6. Deploy

### Mobile Deployment

**iOS (TestFlight):**
```bash
eas build --platform ios
eas submit --platform ios
```

**Android (Google Play):**
```bash
eas build --platform android
eas submit --platform android
```

### MT5 VPS Setup

1. Rent VPS from broker or third-party
2. Install MT5 on VPS
3. Configure EA with production backend URL
4. Keep VPS running 24/7

---

## System Architecture

```
┌─────────────────┐
│   Mobile App    │
│   (React Native)│
└────────┬────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────┐
│  Backend API    │
│  (FastAPI)      │
└────────┬────────┘
         │ Command Queue
         ▼
┌─────────────────┐
│   MT5 Bridge    │
│   (MQL5 EA)     │
└────────┬────────┘
         │ MT5 API
         ▼
┌─────────────────┐
│  MT5 Terminal   │
│  (Broker)       │
└─────────────────┘
```

---

## Key Features Checklist

### ✅ Dual-Engine System
- [x] Core Strategy (100-point confluence)
- [x] Quick Scalp (M1 momentum)
- [x] Auto-Trade Decision Engine
- [x] Conflict resolution

### ✅ Market Analysis
- [x] Regime detection (volatility + trend)
- [x] Multi-market support (US30, NAS100, XAUUSD)
- [x] Performance tracking
- [x] News blackout detection

### ✅ Trading Loop
- [x] Continuous market analysis (60s intervals)
- [x] Live market data fetching
- [x] Signal generation
- [x] Trade execution
- [x] WebSocket real-time updates

### ✅ Mobile App
- [x] Engine controls (enable/disable)
- [x] Market controls (enable/disable)
- [x] Trading loop control (start/stop)
- [x] Real-time signal notifications
- [x] MT5 connection status
- [x] Performance dashboard

### ✅ Safety Features
- [x] Emergency stop
- [x] Risk validation
- [x] Position limits
- [x] News blackout
- [x] Connection health monitoring

---

## Next Steps

1. **Test with Demo Account**
   - Run system for 1-2 weeks
   - Monitor signal quality
   - Verify trade execution
   - Track performance

2. **Optimize Parameters**
   - Adjust confluence thresholds
   - Fine-tune regime detection
   - Optimize position sizing
   - Refine entry/exit rules

3. **Add Enhancements**
   - Push notifications
   - Advanced analytics
   - Backtesting module
   - Multi-timeframe analysis

4. **Go Live**
   - Switch to live account
   - Start with small position sizes
   - Monitor closely for first week
   - Scale up gradually

---

## Support & Resources

- **Documentation:** See all `*.md` files in project root
- **API Docs:** `http://localhost:8000/docs`
- **Logs:** Check backend console and MT5 Experts log
- **Issues:** Check GitHub issues or create new one

---

## Important Notes

⚠️ **Risk Warning:**
- Trading involves substantial risk of loss
- Only trade with capital you can afford to lose
- Past performance does not guarantee future results
- Always test thoroughly on demo before going live

⚠️ **System Requirements:**
- Stable internet connection required
- MT5 terminal must run 24/7 for live trading
- Mobile app needs network access to backend
- Backend should be deployed on reliable hosting

⚠️ **Maintenance:**
- Monitor system logs daily
- Check for errors and warnings
- Update dependencies regularly
- Backup database periodically

---

## Quick Start Commands

```bash
# Start backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Start mobile
cd mobile && npx expo start

# Run tests
pytest backend/tests/

# Check system status
curl http://localhost:8000/health
curl http://localhost:8000/mt5/status
curl http://localhost:8000/trading-loop/status
```

---

**System Status:** ✅ Ready for Testing

All components are implemented and integrated. The system is ready for end-to-end testing with live MT5 connection.
