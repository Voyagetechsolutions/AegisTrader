# Mobile Dual-Engine Setup Guide

## Quick Start

The dual-engine system is now fully integrated into the mobile app (in the `mobile` folder) with a dedicated "⚡" tab.

## What's New

### New Tab: Engines (⚡)
- Real-time status for Core Strategy and Quick Scalp engines
- Market regime indicators with color-coded volatility and trend
- Active signals from both engines in unified format
- Last decision made by the Auto-Trade Decision Engine

### Features
- **Engine Status Cards**: See which engines are active/blocked and why
- **Market Regimes**: Real-time volatility and trend classification per instrument
- **Active Signals**: Unified view of signals from both engines
- **Auto-Refresh**: Updates every 30 seconds automatically
- **Pull-to-Refresh**: Manual refresh support

## Setup Instructions

### 1. Configure Backend URL

Edit `mobile/services/api.ts`:

```typescript
const API_BASE_URL = __DEV__
  ? 'http://YOUR_IP_ADDRESS:8000'  // Change this to your computer's IP
  : 'https://your-render-app.onrender.com';
```

### 2. Install Dependencies (if needed)

```bash
cd mobile
npm install
```

### 3. Start Backend

```bash
# From project root
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start Mobile App

```bash
cd mobile
npm start
```

Then:
- Press `a` for Android emulator
- Press `i` for iOS simulator
- Scan QR code with Expo Go app on physical device

## Testing the Integration

### 1. Check Connection

Open the app and look for:
- Green connection dot in top-right corner
- Data loading in Overview tab

### 2. Navigate to Engines Tab

Tap the "⚡" tab (second tab from left)

You should see:
- Core Strategy status card (blue border)
- Quick Scalp status card (green border)
- Market regime cards for each instrument
- Active signals section

### 3. Test API Endpoints

From your terminal:

```bash
# Test dual-engine status
curl http://localhost:8000/dual-engine/status

# Test market regime
curl http://localhost:8000/dual-engine/regime/US30

# Test active signals
curl http://localhost:8000/dual-engine/signals/active

# Test health check
curl http://localhost:8000/dual-engine/health
```

### 4. Verify Real-Time Updates

- Pull down to refresh
- Wait 5 seconds for auto-refresh
- Check that data updates

## UI Components

### Engine Status Cards

**Core Strategy (Blue Border)**
- Shows: ACTIVE/BLOCKED status
- Displays: Trades today / Daily limit (0/2)
- Shows block reason if blocked

**Quick Scalp (Green Border)**
- Shows: ACTIVE/BLOCKED status
- Displays: Trades today / Daily limit (0/15)
- Shows block reason if blocked

### Market Regime Cards

For each instrument (US30, XAUUSD, NASDAQ):

**Volatility Badge Colors:**
- Gray: LOW
- Green: NORMAL
- Orange: HIGH
- Red: EXTREME

**Trend Badge Colors:**
- Green: STRONG_TREND
- Blue: WEAK_TREND
- Orange: RANGING
- Red: CHOPPY

**Metrics:**
- ATR current vs average
- ATR ratio (multiplier)

### Active Signals

Each signal shows:
- Engine icon (🎯 Core or ⚡ Scalp)
- Instrument name
- Direction badge (green for LONG, red for SHORT)
- Entry, SL, TP1, TP2 prices
- Risk:Reward ratio

## Troubleshooting

### Connection Issues

**Problem**: Red connection dot, no data loading

**Solutions:**
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify API URL in `.env` or `app.json`
3. Check firewall allows connections on port 8000
4. Try using IP address instead of `localhost`

### Empty Engines Tab

**Problem**: "Loading dual-engine system..." never completes

**Solutions:**
1. Check backend logs for errors
2. Verify dual-engine router is registered: `curl http://localhost:8000/dual-engine/health`
3. Check browser console for API errors
4. Restart backend and mobile app

### No Market Regimes

**Problem**: Market regime section is empty

**Solutions:**
1. Backend needs market data to calculate regimes
2. Check if Trading Coordinator is initialized
3. Verify instruments are configured
4. May need to process market data first

### Styling Issues

**Problem**: UI looks broken or misaligned

**Solutions:**
1. Clear Expo cache: `expo start -c`
2. Restart app completely
3. Check React Native version compatibility

## Development Tips

### Hot Reload

Changes to `App.tsx` will hot reload automatically. If not:
- Shake device and select "Reload"
- Press `r` in terminal running `npm start`

### Debugging

Enable debug mode:
```typescript
// In App.tsx
console.log('Dual-engine status:', dualEngineStatus);
console.log('Active signals:', activeSignals);
```

View logs:
- Expo: Check terminal running `npm start`
- Android: `adb logcat`
- iOS: Xcode console

### Testing Without Backend

Mock data for testing:
```typescript
// In App.tsx, replace API call with:
setDualEngineStatus({
  core_strategy: {
    engine: 'CORE_STRATEGY',
    active: true,
    trades_today: 1,
    daily_limit: 2,
    can_trade: true,
    block_reason: null,
    performance: null,
  },
  quick_scalp: {
    engine: 'QUICK_SCALP',
    active: true,
    trades_today: 5,
    daily_limit: 15,
    can_trade: true,
    block_reason: null,
    performance: null,
  },
  market_regimes: [
    {
      instrument: 'US30',
      volatility: 'NORMAL',
      trend: 'WEAK_TREND',
      atr_current: 100.0,
      atr_average: 100.0,
      atr_ratio: 1.0,
      timestamp: new Date().toISOString(),
    },
  ],
  active_signals: 0,
  last_decision: 'Core Strategy A+ signal - highest priority',
  timestamp: new Date().toISOString(),
});
```

## Next Steps

### Enhancements to Consider

1. **Performance Charts**: Add visual charts for engine performance over time
2. **Push Notifications**: Alert when engines make decisions
3. **Engine Controls**: Enable/disable engines from mobile
4. **Decision History**: View past engine decisions with filters
5. **Regime History**: Chart volatility and trend over time
6. **Comparison View**: Side-by-side engine performance comparison

### Integration with Existing Features

The engines tab complements existing tabs:
- **Overview**: General bot status and controls
- **Engines**: Dual-engine system status (NEW)
- **Signals**: Historical signals from all sources
- **Trades**: Trade history and P&L
- **Settings**: Configuration and session windows

## API Reference

### Dual-Engine Endpoints

All available at `/dual-engine/*`:

```typescript
// Get complete status
await api.getDualEngineStatus();

// Get market regime for instrument
await api.getMarketRegime('US30');

// Get engine performance
await api.getEnginePerformance('CORE_STRATEGY');

// Compare engines
await api.compareEnginePerformance();

// Get active signals
await api.getActiveSignals();

// Get configuration
await api.getDualEngineConfig();

// Health check
await api.dualEngineHealthCheck();
```

## Files Modified

### Mobile App
- `mobile/app/(tabs)/engines.tsx` - New engines tab component
- `mobile/app/(tabs)/_layout.tsx` - Added engines tab to navigation
- `mobile/services/api.ts` - Added dual-engine API methods
- `mobile/types/index.ts` - Added dual-engine TypeScript types

### Backend
- `backend/routers/dual_engine.py` - Dual-engine API endpoints
- `backend/main.py` - Registered dual_engine_router

## Summary

The mobile app now has a dedicated "⚡" tab that provides:
- ✅ Real-time engine status monitoring
- ✅ Market regime visualization
- ✅ Active signals from both engines
- ✅ Auto-refresh every 5 seconds
- ✅ Pull-to-refresh support
- ✅ Color-coded indicators
- ✅ Clean, intuitive UI

The integration is complete and ready for testing!
