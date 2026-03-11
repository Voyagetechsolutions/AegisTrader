# Mobile App Connection Guide

## Quick Setup

### 1. Find Your Computer's IP Address

**On Windows:**
```bash
ipconfig
```
Look for "IPv4 Address" under your active network adapter (usually starts with 192.168.x.x or 10.0.x.x)

**Example output:**
```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

### 2. Update Mobile App Configuration

Edit `mobile/services/api.ts` and change line 6:

```typescript
const API_BASE_URL = __DEV__
  ? 'http://YOUR_IP_HERE:8000'  // ← Change this
  : 'https://your-render-app.onrender.com';
```

**Example:**
```typescript
const API_BASE_URL = __DEV__
  ? 'http://192.168.1.100:8000'
  : 'https://your-render-app.onrender.com';
```

### 3. Make Sure Backend is Accessible

Your backend must be running with `--host 0.0.0.0` to accept connections from other devices:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**NOT** just `--reload` (that only listens on localhost)

### 4. Check Firewall

Make sure Windows Firewall allows connections on port 8000:

1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP" and enter "8000" → Next
6. Select "Allow the connection" → Next
7. Check all profiles → Next
8. Name it "Aegis Trader Backend" → Finish

### 5. Start the Mobile App

```bash
cd mobile
npx expo start
```

Then scan the QR code with Expo Go app on your phone.

---

## Troubleshooting

### "Network request failed"

**Check 1:** Are you on the same WiFi network?
- Phone and computer must be on the same network

**Check 2:** Is backend running with `--host 0.0.0.0`?
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Check 3:** Can you access backend from phone browser?
- Open phone browser
- Go to `http://YOUR_IP:8000/health`
- Should see: `{"status":"ok","env":"development","version":"1.0.0"}`

**Check 4:** Is firewall blocking?
- Temporarily disable Windows Firewall to test
- If it works, add firewall rule (see step 4 above)

### "Connection timeout"

- Backend might not be running
- Wrong IP address in api.ts
- Firewall blocking connections

### "Backend Offline" in app

- Backend is not running
- Wrong IP address
- Network connectivity issue

---

## Current Status

Your mobile app is already configured to:
- ✓ Fetch dashboard status every 3 seconds
- ✓ Fetch current price every 2 seconds
- ✓ Display real account balance
- ✓ Show real-time bid price
- ✓ All API endpoints connected

You just need to:
1. Update the IP address in `mobile/services/api.ts`
2. Start backend with `--host 0.0.0.0`
3. Recompile MT5 bridge (for faster updates)
4. Start mobile app with `npx expo start`

---

## Testing Connection

### Test 1: Backend Health Check
```bash
curl http://YOUR_IP:8000/health
```
Should return: `{"status":"ok",...}`

### Test 2: Dashboard Status
```bash
curl http://YOUR_IP:8000/dashboard/status
```
Should return JSON with balance, trades, etc.

### Test 3: Current Price
```bash
curl http://YOUR_IP:8000/mt5/price/US30
```
Should return: `{"symbol":"US30","bid":42850.25,"ask":42852.25,...}`

If all three work, your mobile app will connect successfully!

---

## What You'll See in Mobile App

Once connected:
- **Account Balance**: Real balance from MT5 (updates every 3s)
- **Current Price**: Real bid price from MT5 (updates every 2s)
- **Trading Pair**: US30 (active), Gold/Nasdaq (disabled)
- **Status**: Mode, Session, Trades, Drawdown
- **Quick Controls**: Mode switching, Auto-trade toggle
- **Risk Status**: Daily limits and progress
- **System Health**: Database, MT5, Telegram status
- **Emergency Stop**: One-tap trading halt

All data is live from your MT5 account!
