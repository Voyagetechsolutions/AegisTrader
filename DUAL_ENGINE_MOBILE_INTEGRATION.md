# Dual-Engine Mobile Integration Guide

## Overview

The dual-engine trading system is now wired to the mobile app, providing real-time visibility into:
- Core Strategy and Quick Scalp engine status
- Market regime detection (volatility + trend)
- Performance metrics per engine
- Active signals from both engines
- Engine decision logs

## Backend API Endpoints

### New Router: `/dual-engine`

All dual-engine endpoints are available under the `/dual-engine` prefix:

#### Status & Health
- `GET /dual-engine/status` - Complete system status
- `GET /dual-engine/health` - Component health check
- `GET /dual-engine/regime/{instrument}` - Market regime for specific instrument

#### Performance
- `GET /dual-engine/performance/{engine}` - Performance metrics per engine
- `GET /dual-engine/performance/compare` - Compare Core vs Scalp performance

#### Signals
- `GET /dual-engine/signals/active` - Currently active signals
- `GET /dual-engine/signals/history` - Historical signals with filters

#### Configuration
- `GET /dual-engine/config` - Current configuration
- `POST /dual-engine/config/update` - Update configuration

#### Decision Logs
- `GET /dual-engine/decisions/recent` - Recent engine selection decisions

## Mobile App Integration

### New API Client Methods

Added to `AegisTraderMobile/src/api.ts`:

```typescript
// Get complete dual-engine status
await apiClient.getDualEngineStatus();

// Get market regime for instrument
await apiClient.getMarketRegime('US30');

// Get engine performance
await apiClient.getEnginePerformance('CORE_STRATEGY');

// Compare engines
await apiClient.compareEnginePerformance();

// Get active signals
await apiClient.getActiveSignals();

// Get configuration
await apiClient.getDualEngineConfig();

// Health check
await apiClient.dualEngineHealthCheck();
```

### New Screen Component

Created `AegisTraderMobile/src/screens/DualEngineScreen.tsx`:

Features:
- Real-time engine status cards (Core Strategy + Quick Scalp)
- Market regime indicators with color-coded volatility and trend
- Active signals list with unified format
- Auto-refresh every 30 seconds
- Pull-to-refresh support
- Error handling and retry logic

## Data Flow

```
Market Data → Trading Coordinator
    ↓
Regime Detection → Decision Engine
    ↓
Core Strategy ←→ Quick Scalp
    ↓
Unified Signals → API Endpoints
    ↓
Mobile App Display
```

## Response Models

### DualEngineStatus
```typescript
{
  core_strategy: {
    engine: "CORE_STRATEGY",
    active: true,
    trades_today: 1,
    daily_limit: 2,
    can_trade: true,
    block_reason: null,
    performance: {...}
  },
  quick_scalp: {
    engine: "QUICK_SCALP",
    active: true,
    trades_today: 5,
    daily_limit: 15,
    can_trade: true,
    block_reason: null,
    performance: {...}
  },
  market_regimes: [
    {
      instrument: "US30",
      volatility: "NORMAL",
      trend: "WEAK_TREND",
      atr_current: 100.0,
      atr_average: 100.0,
      atr_ratio: 1.0,
      timestamp: "2026-03-11T04:00:00Z"
    }
  ],
  active_signals: 2,
  last_decision: "Core Strategy A+ signal - highest priority",
  timestamp: "2026-03-11T04:00:00Z"
}
```

### MarketRegime
```typescript
{
  instrument: "US30",
  volatility: "HIGH",  // LOW, NORMAL, HIGH, EXTREME
  trend: "STRONG_TREND",  // STRONG_TREND, WEAK_TREND, RANGING, CHOPPY
  atr_current: 150.0,
  atr_average: 100.0,
  atr_ratio: 1.5,
  timestamp: "2026-03-11T04:00:00Z"
}
```

### UnifiedSignal
```typescript
{
  signal_id: "uuid",
  engine: "CORE_STRATEGY",
  instrument: "US30",
  direction: "LONG",
  entry_price: 42000.0,
  stop_loss: 41900.0,
  tp1: 42100.0,
  tp2: 42200.0,
  risk_reward_ratio: 2.0,
  status: "EXECUTED",
  grade: "A_PLUS",
  score: 87,
  session: "LONDON",
  timestamp: "2026-03-11T04:00:00Z",
  reasons: ["HTF alignment", "Key level", "Liquidity sweep"]
}
```

## Integration Steps

### 1. Add Navigation (if using React Navigation)

```typescript
// In your navigation stack
import DualEngineScreen from './src/screens/DualEngineScreen';

<Stack.Screen 
  name="DualEngine" 
  component={DualEngineScreen}
  options={{ title: 'Dual-Engine System' }}
/>
```

### 2. Add Menu Item

```typescript
// In your main menu/dashboard
<TouchableOpacity onPress={() => navigation.navigate('DualEngine')}>
  <Text>Dual-Engine System</Text>
</TouchableOpacity>
```

### 3. Test API Connection

```typescript
// Test in your app
const testDualEngine = async () => {
  try {
    const status = await apiClient.getDualEngineStatus();
    console.log('Dual-engine status:', status);
  } catch (error) {
    console.error('Failed to fetch dual-engine status:', error);
  }
};
```

## Visual Indicators

### Volatility Colors
- **LOW**: Gray (#6B7280)
- **NORMAL**: Green (#10B981)
- **HIGH**: Orange (#F59E0B)
- **EXTREME**: Red (#EF4444)

### Trend Colors
- **STRONG_TREND**: Green (#10B981)
- **WEAK_TREND**: Blue (#3B82F6)
- **RANGING**: Orange (#F59E0B)
- **CHOPPY**: Red (#EF4444)

### Engine Colors
- **Core Strategy**: Blue (#3B82F6)
- **Quick Scalp**: Green (#10B981)

## State Management Notes

The current implementation uses in-memory state (`_coordinator_state`) for demonstration. In production, you should:

1. Wire the actual `TradingCoordinator` instance
2. Store state in Redis or database
3. Use WebSocket for real-time updates
4. Implement proper state persistence

## Next Steps

1. **Wire Real Coordinator**: Replace `_coordinator_state` with actual `TradingCoordinator` instance
2. **Add WebSocket**: Real-time updates instead of polling
3. **Add Charts**: Visualize performance metrics over time
4. **Add Notifications**: Push notifications for engine decisions
5. **Add Controls**: Enable/disable engines from mobile
6. **Add Logs**: View detailed decision logs

## Testing

### Test Backend Endpoints

```bash
# Get dual-engine status
curl http://localhost:8000/dual-engine/status

# Get market regime
curl http://localhost:8000/dual-engine/regime/US30

# Get engine performance
curl http://localhost:8000/dual-engine/performance/CORE_STRATEGY

# Get active signals
curl http://localhost:8000/dual-engine/signals/active

# Health check
curl http://localhost:8000/dual-engine/health
```

### Test Mobile App

1. Start backend: `python -m uvicorn backend.main:app --reload`
2. Update `.env` in mobile app with backend URL
3. Run mobile app: `cd AegisTraderMobile && npm start`
4. Navigate to Dual-Engine screen
5. Verify data loads and refreshes

## Files Modified

### Backend
- `backend/routers/dual_engine.py` - New router with all endpoints
- `backend/main.py` - Registered dual_engine_router

### Mobile
- `AegisTraderMobile/src/api.ts` - Added dual-engine API methods and types
- `AegisTraderMobile/src/screens/DualEngineScreen.tsx` - New screen component

## Architecture

```
┌─────────────────────────────────────────┐
│         Mobile App (React Native)       │
│  ┌───────────────────────────────────┐  │
│  │   DualEngineScreen.tsx            │  │
│  │   - Engine Status Cards           │  │
│  │   - Market Regime Indicators      │  │
│  │   - Active Signals List           │  │
│  │   - Performance Metrics           │  │
│  └───────────────────────────────────┘  │
│              ↓ API Calls                │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend (Python)           │
│  ┌───────────────────────────────────┐  │
│  │   /dual-engine/* endpoints        │  │
│  │   - Status                        │  │
│  │   - Performance                   │  │
│  │   - Signals                       │  │
│  │   - Configuration                 │  │
│  └───────────────────────────────────┘  │
│              ↓                          │
│  ┌───────────────────────────────────┐  │
│  │   Trading Coordinator             │  │
│  │   - Regime Detector               │  │
│  │   - Decision Engine               │  │
│  │   - Performance Tracker           │  │
│  │   - Core Strategy Engine          │  │
│  │   - Quick Scalp Engine            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Summary

The dual-engine system is now fully accessible from the mobile app with:
- ✅ Complete API endpoints for all dual-engine features
- ✅ TypeScript types for type-safe API calls
- ✅ Beautiful mobile UI with real-time updates
- ✅ Color-coded indicators for quick status assessment
- ✅ Error handling and retry logic
- ✅ Pull-to-refresh and auto-refresh

The mobile app can now monitor both trading engines in real-time, view market regimes, track performance, and see active signals from a unified interface.
