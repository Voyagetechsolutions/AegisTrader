# Mobile Trading Implementation Plan

## Vision: Plug-and-Play Mobile Trading System

**Goal:** Download app → Connect to MT5 → Start trading US30, NASDAQ, XAUUSD automatically

## Current State vs Target State

### Current State ✅
- Dual-engine architecture designed (Core + Scalp)
- Backend infrastructure complete (69 tests passing)
- Mobile app with monitoring UI
- API endpoints functional
- **BUT:** Not connected to live trading

### Target State 🎯
1. **Multi-Market Analysis**: Analyze US30, NASDAQ, XAUUSD simultaneously
2. **Separate Engine Controls**: Independent on/off switches for Core and Scalp
3. **Mobile-First Trading**: Execute trades directly from phone via MT5 mobile
4. **Plug-and-Play**: Download app → Login → Trade

---

## Phase 1: Multi-Market Support

### 1.1 Backend: Multi-Instrument Coordinator

**Current:** Single instrument processing
**Target:** Parallel processing of US30, NASDAQ, XAUUSD

```python
# backend/strategy/multi_market_coordinator.py
class MultiMarketCoordinator:
    def __init__(self):
        self.instruments = [
            Instrument.US30,
            Instrument.NASDAQ,
            Instrument.XAUUSD
        ]
        self.coordinators = {
            inst: TradingCoordinator(config_for(inst))
            for inst in self.instruments
        }
    
    async def process_all_markets(self):
        """Process all markets in parallel"""
        tasks = [
            self.process_market(inst)
            for inst in self.instruments
        ]
        results = await asyncio.gather(*tasks)
        return results
    
    async def process_market(self, instrument):
        """Process single market"""
        bars = await self.get_market_data(instrument)
        spread = await self.get_current_spread(instrument)
        
        coordinator = self.coordinators[instrument]
        signal = coordinator.process_market_data(
            instrument=instrument,
            bars=bars,
            current_spread=spread
        )
        
        if signal:
            await self.execute_signal(signal)
        
        return signal
```

**Files to Create:**
- `backend/strategy/multi_market_coordinator.py`
- `backend/tests/test_multi_market_coordinator.py`

**API Endpoint:**
```python
# backend/routers/dual_engine.py
@router.get("/markets/status")
async def get_all_markets_status():
    """Get status for all markets"""
    return {
        "US30": coordinator.get_status(Instrument.US30),
        "NASDAQ": coordinator.get_status(Instrument.NASDAQ),
        "XAUUSD": coordinator.get_status(Instrument.XAUUSD),
    }
```

### 1.2 Mobile: Multi-Market Display

**Update engines tab to show all markets:**

```typescript
// mobile/app/(tabs)/engines.tsx
<View style={styles.marketsSection}>
  <Text style={styles.sectionTitle}>Active Markets</Text>
  
  {['US30', 'NASDAQ', 'XAUUSD'].map(market => (
    <MarketCard
      key={market}
      instrument={market}
      coreStatus={status.core_strategy[market]}
      scalpStatus={status.quick_scalp[market]}
      regime={status.market_regimes[market]}
    />
  ))}
</View>
```

---

## Phase 2: Separate Engine Controls

### 2.1 Backend: Independent Engine Settings

**Add per-engine auto-trade flags:**

```python
# backend/models/models.py
class BotSetting(Base):
    # Existing fields...
    
    # New fields for dual-engine control
    core_strategy_enabled: bool = True
    quick_scalp_enabled: bool = True
    
    # Per-instrument settings
    us30_enabled: bool = True
    nasdaq_enabled: bool = True
    xauusd_enabled: bool = True
```

**API Endpoints:**

```python
# backend/routers/dual_engine.py
@router.post("/engines/core/toggle")
async def toggle_core_strategy(enabled: bool):
    """Enable/disable Core Strategy engine"""
    settings.core_strategy_enabled = enabled
    await db.commit()
    return {"ok": True, "core_strategy_enabled": enabled}

@router.post("/engines/scalp/toggle")
async def toggle_quick_scalp(enabled: bool):
    """Enable/disable Quick Scalp engine"""
    settings.quick_scalp_enabled = enabled
    await db.commit()
    return {"ok": True, "quick_scalp_enabled": enabled}

@router.post("/markets/{instrument}/toggle")
async def toggle_market(instrument: str, enabled: bool):
    """Enable/disable specific market"""
    # Update instrument-specific setting
    return {"ok": True, "instrument": instrument, "enabled": enabled}
```

### 2.2 Mobile: Engine Control Switches

**Add toggle switches in engines tab:**

```typescript
// mobile/app/(tabs)/engines.tsx
<View style={styles.engineControls}>
  <View style={styles.controlRow}>
    <Text style={styles.controlLabel}>🎯 Core Strategy</Text>
    <Switch
      value={coreEnabled}
      onValueChange={toggleCoreStrategy}
      trackColor={{ false: '#444', true: Colors.info }}
    />
  </View>
  
  <View style={styles.controlRow}>
    <Text style={styles.controlLabel}>⚡ Quick Scalp</Text>
    <Switch
      value={scalpEnabled}
      onValueChange={toggleQuickScalp}
      trackColor={{ false: '#444', true: Colors.success }}
    />
  </View>
</View>

<View style={styles.marketControls}>
  <Text style={styles.sectionTitle}>Active Markets</Text>
  {['US30', 'NASDAQ', 'XAUUSD'].map(market => (
    <View key={market} style={styles.controlRow}>
      <Text style={styles.controlLabel}>{market}</Text>
      <Switch
        value={marketEnabled[market]}
        onValueChange={(val) => toggleMarket(market, val)}
      />
    </View>
  ))}
</View>
```

---

## Phase 3: Mobile MT5 Integration

### 3.1 Architecture: Mobile-First Trading

**Current Architecture (Desktop-Centric):**
```
Phone → Backend Server → MT5 Desktop → Broker
```

**Target Architecture (Mobile-First):**
```
Phone → Backend Server → MT5 Mobile API → Broker
         ↓
    Direct MT5 Mobile (optional)
```

### 3.2 MT5 Mobile Connection Options

**Option A: MetaTrader Mobile API (Recommended)**
```python
# backend/modules/mt5_mobile_bridge.py
class MT5MobileBridge:
    """Bridge to MT5 Mobile via MetaQuotes API"""
    
    def __init__(self, account_number, password, server):
        self.account = account_number
        self.password = password
        self.server = server
        self.api = MetaTraderAPI()
    
    async def connect(self):
        """Connect to MT5 account"""
        return await self.api.connect(
            account=self.account,
            password=self.password,
            server=self.server
        )
    
    async def place_order(self, signal):
        """Place order via MT5 Mobile"""
        return await self.api.trade(
            symbol=signal.instrument,
            action=signal.direction,
            volume=signal.lot_size,
            price=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.tp1
        )
```

**Option B: Direct MT5 Mobile Integration**
- Use MT5 Mobile's built-in Expert Advisor support
- Deploy EA to MT5 Mobile that listens to backend signals
- More complex but gives full control

**Option C: Hybrid Approach (Best)**
- Backend generates signals
- Push notifications to phone
- User can execute via MT5 Mobile app
- Or auto-execute if enabled

### 3.3 Mobile App: MT5 Connection Setup

**Add MT5 connection screen:**

```typescript
// mobile/app/setup/mt5-connection.tsx
export default function MT5ConnectionScreen() {
  const [accountNumber, setAccountNumber] = useState('');
  const [password, setPassword] = useState('');
  const [server, setServer] = useState('');
  const [broker, setBroker] = useState('');
  
  const connectMT5 = async () => {
    try {
      const result = await api.connectMT5({
        account: accountNumber,
        password: password,
        server: server,
        broker: broker,
      });
      
      if (result.success) {
        // Save credentials securely
        await SecureStore.setItemAsync('mt5_account', accountNumber);
        await SecureStore.setItemAsync('mt5_password', password);
        await SecureStore.setItemAsync('mt5_server', server);
        
        navigation.navigate('Dashboard');
      }
    } catch (error) {
      Alert.alert('Connection Failed', error.message);
    }
  };
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Connect MT5 Account</Text>
      
      <TextInput
        placeholder="Account Number"
        value={accountNumber}
        onChangeText={setAccountNumber}
        keyboardType="numeric"
        style={styles.input}
      />
      
      <TextInput
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        style={styles.input}
      />
      
      <TextInput
        placeholder="Server (e.g., ICMarkets-Demo)"
        value={server}
        onChangeText={setServer}
        style={styles.input}
      />
      
      <Picker
        selectedValue={broker}
        onValueChange={setBroker}
        style={styles.picker}
      >
        <Picker.Item label="Select Broker" value="" />
        <Picker.Item label="IC Markets" value="icmarkets" />
        <Picker.Item label="Exness" value="exness" />
        <Picker.Item label="XM" value="xm" />
        <Picker.Item label="FTMO" value="ftmo" />
      </Picker>
      
      <TouchableOpacity
        style={styles.connectButton}
        onPress={connectMT5}
      >
        <Text style={styles.connectButtonText}>Connect MT5</Text>
      </TouchableOpacity>
      
      <Text style={styles.helpText}>
        Your credentials are encrypted and stored securely on your device
      </Text>
    </View>
  );
}
```

---

## Phase 4: Plug-and-Play Setup

### 4.1 First-Time Setup Flow

**Onboarding Screens:**

1. **Welcome Screen**
   - "Welcome to Aegis Trader"
   - "Automated trading for US30, NASDAQ, XAUUSD"
   - "Get Started" button

2. **MT5 Connection Screen**
   - Enter MT5 credentials
   - Select broker
   - Test connection
   - Save securely

3. **Strategy Selection Screen**
   - Enable/disable Core Strategy
   - Enable/disable Quick Scalp
   - Select markets to trade

4. **Risk Settings Screen**
   - Set risk per trade (0.5% - 2%)
   - Set daily loss limit
   - Set max trades per day

5. **Confirmation Screen**
   - Review all settings
   - "Start Trading" button

### 4.2 Backend: Setup API

```python
# backend/routers/setup.py
@router.post("/setup/complete")
async def complete_setup(setup_data: SetupData):
    """Complete first-time setup"""
    
    # 1. Validate MT5 connection
    mt5_valid = await validate_mt5_credentials(
        setup_data.mt5_account,
        setup_data.mt5_password,
        setup_data.mt5_server
    )
    
    if not mt5_valid:
        raise HTTPException(400, "Invalid MT5 credentials")
    
    # 2. Create bot settings
    settings = BotSetting(
        user_id=setup_data.user_id,
        mode=BotMode.TRADE,
        auto_trade_enabled=True,
        core_strategy_enabled=setup_data.core_enabled,
        quick_scalp_enabled=setup_data.scalp_enabled,
        us30_enabled=setup_data.markets.us30,
        nasdaq_enabled=setup_data.markets.nasdaq,
        xauusd_enabled=setup_data.markets.xauusd,
        risk_percent=setup_data.risk_percent,
        max_trades_per_day=setup_data.max_trades,
        max_daily_drawdown_pct=setup_data.max_drawdown,
    )
    
    db.add(settings)
    await db.commit()
    
    # 3. Start trading coordinator
    await start_trading_coordinator(settings)
    
    return {
        "ok": True,
        "message": "Setup complete! Trading will begin shortly.",
        "settings": settings
    }
```

### 4.3 Mobile: Persistent State

**Store setup completion:**

```typescript
// mobile/services/setup.ts
export const setupService = {
  async isSetupComplete(): Promise<boolean> {
    const completed = await AsyncStorage.getItem('setup_complete');
    return completed === 'true';
  },
  
  async markSetupComplete(): Promise<void> {
    await AsyncStorage.setItem('setup_complete', 'true');
  },
  
  async getMT5Credentials() {
    return {
      account: await SecureStore.getItemAsync('mt5_account'),
      password: await SecureStore.getItemAsync('mt5_password'),
      server: await SecureStore.getItemAsync('mt5_server'),
    };
  },
};
```

**App entry point with setup check:**

```typescript
// mobile/app/_layout.tsx
export default function RootLayout() {
  const [setupComplete, setSetupComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    checkSetup();
  }, []);
  
  const checkSetup = async () => {
    const complete = await setupService.isSetupComplete();
    setSetupComplete(complete);
    setLoading(false);
  };
  
  if (loading) {
    return <LoadingScreen />;
  }
  
  if (!setupComplete) {
    return <SetupFlow onComplete={() => setSetupComplete(true)} />;
  }
  
  return <MainApp />;
}
```

---

## Phase 5: Real-Time Trading Loop

### 5.1 Backend: Continuous Market Analysis

```python
# backend/services/trading_loop.py
class TradingLoop:
    """Main trading loop for continuous market analysis"""
    
    def __init__(self):
        self.coordinator = MultiMarketCoordinator()
        self.running = False
    
    async def start(self):
        """Start the trading loop"""
        self.running = True
        
        while self.running:
            try:
                # Process all markets
                await self.coordinator.process_all_markets()
                
                # Wait before next iteration (e.g., 1 second)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def stop(self):
        """Stop the trading loop"""
        self.running = False
```

**Start on app launch:**

```python
# backend/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    trading_loop = TradingLoop()
    asyncio.create_task(trading_loop.start())
    
    yield
    
    # Shutdown
    await trading_loop.stop()

app = FastAPI(lifespan=lifespan)
```

### 5.2 Mobile: Real-Time Updates

**WebSocket connection for live updates:**

```typescript
// mobile/services/websocket.ts
export class TradingWebSocket {
  private ws: WebSocket | null = null;
  
  connect(onMessage: (data: any) => void) {
    this.ws = new WebSocket('ws://YOUR_SERVER:8000/ws');
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

**Use in engines tab:**

```typescript
// mobile/app/(tabs)/engines.tsx
useEffect(() => {
  const ws = new TradingWebSocket();
  
  ws.connect((data) => {
    if (data.type === 'signal') {
      // New signal generated
      setActiveSignals(prev => [...prev, data.signal]);
    } else if (data.type === 'regime_update') {
      // Market regime changed
      updateRegime(data.instrument, data.regime);
    } else if (data.type === 'trade_executed') {
      // Trade executed
      showNotification('Trade Executed', data.message);
    }
  });
  
  return () => ws.disconnect();
}, []);
```

---

## Phase 6: Push Notifications

### 6.1 Setup Expo Notifications

```bash
cd mobile
npx expo install expo-notifications
```

```typescript
// mobile/services/notifications.ts
import * as Notifications from 'expo-notifications';

export const notificationService = {
  async requestPermissions() {
    const { status } = await Notifications.requestPermissionsAsync();
    return status === 'granted';
  },
  
  async sendSignalNotification(signal: UnifiedSignal) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: `${signal.engine} Signal`,
        body: `${signal.instrument} ${signal.direction} @ ${signal.entry_price}`,
        data: { signal },
      },
      trigger: null, // Send immediately
    });
  },
  
  async sendTradeNotification(trade: Trade) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Trade Executed',
        body: `${trade.symbol} ${trade.direction} - Entry: ${trade.entry_price}`,
        data: { trade },
      },
      trigger: null,
    });
  },
};
```

### 6.2 Backend: Send Notifications

```python
# backend/services/notification_service.py
async def send_push_notification(user_id: str, title: str, body: str, data: dict):
    """Send push notification to user's device"""
    
    # Get user's push token
    push_token = await get_user_push_token(user_id)
    
    if not push_token:
        return
    
    # Send via Expo Push API
    async with aiohttp.ClientSession() as session:
        await session.post(
            'https://exp.host/--/api/v2/push/send',
            json={
                'to': push_token,
                'title': title,
                'body': body,
                'data': data,
            }
        )
```

---

## Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. ✅ Multi-market coordinator backend
2. ✅ Separate engine control API
3. ✅ Mobile UI for engine controls
4. ✅ Multi-market display

### Phase 2: MT5 Integration (Week 3-4)
1. ⚠️ Research MT5 Mobile API options
2. ⚠️ Implement MT5 connection backend
3. ⚠️ Build MT5 setup flow in mobile
4. ⚠️ Test with demo account

### Phase 3: Trading Loop (Week 5-6)
1. ⚠️ Implement continuous market analysis
2. ⚠️ Add WebSocket for real-time updates
3. ⚠️ Test signal generation
4. ⚠️ Test trade execution

### Phase 4: Polish (Week 7-8)
1. ⚠️ Add push notifications
2. ⚠️ Build onboarding flow
3. ⚠️ Add error handling
4. ⚠️ Security hardening
5. ⚠️ Performance optimization

---

## Technical Challenges & Solutions

### Challenge 1: MT5 Mobile API Access
**Problem:** MT5 doesn't have official mobile API
**Solutions:**
- Use MetaTrader Web API (requires broker support)
- Deploy EA on VPS that mobile app communicates with
- Use MT5 Manager API (requires special license)
- Hybrid: Generate signals, user executes manually

**Recommended:** Start with signal generation + manual execution, add auto-execution later

### Challenge 2: Background Processing on Mobile
**Problem:** iOS/Android limit background tasks
**Solutions:**
- Run backend on cloud server (Render, Railway, AWS)
- Mobile app is just UI + control panel
- Backend does all heavy lifting
- Push notifications alert user

**Recommended:** Cloud-hosted backend (already planned)

### Challenge 3: Real-Time Data Feed
**Problem:** Need live market data for all 3 instruments
**Solutions:**
- MT5 data feed (requires connection)
- Broker API (varies by broker)
- Third-party data provider (costs money)
- Hybrid: Use MT5 when available, fallback to broker API

**Recommended:** MT5 data feed via desktop/VPS bridge

### Challenge 4: Secure Credential Storage
**Problem:** Storing MT5 credentials securely
**Solutions:**
- Use expo-secure-store (encrypted storage)
- Never send credentials to backend
- Use tokens/session IDs instead
- Implement biometric authentication

**Recommended:** expo-secure-store + biometric auth

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User's Phone                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Aegis Trader Mobile App                          │  │
│  │  - Dashboard                                      │  │
│  │  - Engine Controls                                │  │
│  │  - Market Monitoring                              │  │
│  │  - MT5 Connection                                 │  │
│  └───────────────────────────────────────────────────┘  │
│                    ↓ HTTPS/WSS                          │
└─────────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Cloud Server (Render/Railway)              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Aegis Trader Backend                             │  │
│  │  - FastAPI Server                                 │  │
│  │  - Trading Coordinator                            │  │
│  │  - Multi-Market Analysis                          │  │
│  │  - Signal Generation                              │  │
│  │  - WebSocket Server                               │  │
│  └───────────────────────────────────────────────────┘  │
│                    ↓ MT5 API                            │
└─────────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│              MT5 Bridge (VPS/Desktop)                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  MT5 Terminal + Expert Advisor                    │  │
│  │  - Receives signals from backend                  │  │
│  │  - Executes trades                                │  │
│  │  - Sends position updates                         │  │
│  └───────────────────────────────────────────────────┘  │
│                    ↓ FIX/API                            │
└─────────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│                    Broker                               │
│  - IC Markets / Exness / XM / FTMO                     │
│  - Executes orders                                      │
│  - Provides market data                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Next Steps

### Immediate (This Week)
1. Add separate engine control switches to mobile UI
2. Update backend to support per-engine enable/disable
3. Add multi-market status endpoint
4. Test engine controls

### Short Term (Next 2 Weeks)
1. Research MT5 Mobile API options
2. Design MT5 connection flow
3. Build onboarding screens
4. Implement secure credential storage

### Medium Term (Next Month)
1. Implement MT5 bridge
2. Build trading loop
3. Add WebSocket real-time updates
4. Test with demo account

### Long Term (Next 2 Months)
1. Add push notifications
2. Performance optimization
3. Security audit
4. Beta testing
5. App store submission

---

## Summary

**What We're Building:**
- Mobile app that trades US30, NASDAQ, XAUUSD automatically
- Separate controls for Core Strategy and Quick Scalp
- Plug-and-play setup (download → connect MT5 → trade)
- Real-time monitoring and notifications

**Key Features:**
- ✅ Multi-market analysis
- ✅ Independent engine controls
- ⚠️ MT5 mobile integration
- ⚠️ One-time setup flow
- ⚠️ Real-time updates
- ⚠️ Push notifications

**Timeline:** 6-8 weeks for full implementation

**Next Action:** Start with Phase 1 (multi-market support + engine controls)
