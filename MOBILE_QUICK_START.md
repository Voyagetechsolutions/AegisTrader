# 📱 Mobile App - Quick Start

The mobile app in the `mobile/` folder is now fully connected to the backend and matches the dashboard design.

## 🚀 Quick Start (3 Steps)

### 1. Update IP Address

Edit `mobile/services/api.ts` line 6:

```typescript
const API_BASE_URL = __DEV__ 
  ? 'http://YOUR_IP_HERE:8000'  // ← Change this
  : 'https://your-production-url.com';
```

**Find your IP:**
```bash
# Windows
ipconfig

# Mac/Linux
ifconfig
```

### 2. Start Backend

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 3. Start Mobile App

```bash
cd mobile
rm -rf node_modules package-lock.json  # Clean install for Expo 55
npm install
npm start
```

Then press `w` for web or scan QR code with Expo Go app (version 55).

## ✅ What's Working

- Dashboard with live status
- Mode switching (Analyze, Trade, Swing)
- Auto-trading toggle
- Risk monitoring
- Signals with grades
- Trade history with P&L
- Weekly overview
- Emergency stop
- Close all positions

## 🎨 Design

Matches dashboard HTML:
- Background: #0a0e1a
- Accent: #00d4aa
- Same layout and colors

## 📚 Full Documentation

See `MOBILE_APP_UPDATED.md` for complete details.

## 🐛 Troubleshooting

**Backend Offline?**
- Check backend is running
- Verify IP address in `services/api.ts`
- Check firewall allows port 8000

**Data not loading?**
- Check backend logs
- Test: `curl http://localhost:8000/dashboard/status`
- Try pull-to-refresh in app

That's it! The mobile app is ready to use. 🎉
