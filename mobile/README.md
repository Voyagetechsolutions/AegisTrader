# Aegis Trader Mobile App

Mobile command center for the Aegis Trader bot. Control your trading robot from anywhere.

## Features

- **Dashboard**: Real-time bot status, PnL, and system health
- **Signals**: View all trading opportunities with grades and scores
- **Trades**: Manage open positions, close trades
- **Overview**: Weekly bias ladder and market scenarios
- **Emergency Stop**: Instant safe mode activation

## Tech Stack

- React Native + Expo
- TypeScript
- Expo Router (file-based routing)
- React Query (data fetching)
- Axios (API client)

## Setup

### 1. Install dependencies

```bash
npm install
```

### 2. Configure API endpoint

Edit `services/api.ts` and set your backend URL:

```typescript
const API_BASE_URL = __DEV__ 
  ? 'http://YOUR_LOCAL_IP:8000'  // Use your computer's IP, not localhost
  : 'https://your-render-app.onrender.com';
```

**Important**: When testing on a physical device, use your computer's local IP address (e.g., `http://192.168.1.100:8000`), not `localhost`.

### 3. Run the app

```bash
# Start Expo dev server
npx expo start

# Then:
# - Press 'a' for Android
# - Press 'i' for iOS (macOS only)
# - Scan QR code with Expo Go app
```

## Backend API Requirements

The mobile app expects these endpoints:

### Status
- `GET /mobile/status` - Bot status and health

### Signals
- `GET /mobile/signals` - List all signals
- `GET /mobile/signals/{id}` - Signal details

### Trades
- `GET /mobile/trades/open` - Open positions
- `GET /mobile/trades/history` - Trade history
- `POST /mobile/trades/{id}/close` - Close a trade
- `POST /mobile/trades/close-all` - Close all trades

### Bot Control
- `POST /mobile/mode` - Switch bot mode
- `POST /mobile/safe-mode` - Enable safe mode

### Reports
- `GET /mobile/weekly-overview` - Weekly market analysis

## Building for Production

### Android APK

```bash
# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Build Android APK
eas build --platform android --profile preview
```

### iOS (requires macOS)

```bash
eas build --platform ios --profile preview
```

## App Structure

```
mobile/
├── app/
│   ├── (tabs)/
│   │   ├── index.tsx      # Dashboard
│   │   ├── signals.tsx    # Signals list
│   │   ├── trades.tsx     # Trades management
│   │   └── overview.tsx   # Weekly overview
│   └── _layout.tsx        # Root layout
├── services/
│   └── api.ts             # API client
├── types/
│   └── index.ts           # TypeScript types
├── constants/
│   └── theme.ts           # Colors and styling
└── components/            # Reusable components
```

## Development Tips

1. **Hot Reload**: Changes auto-reload in Expo Go
2. **Debugging**: Shake device → "Debug Remote JS"
3. **Network**: Ensure phone and computer are on same WiFi
4. **API Testing**: Use your computer's local IP, not localhost

## Next Steps

1. Add push notifications (Firebase Cloud Messaging)
2. Add swing trade approval screen
3. Add biometric authentication
4. Add risk settings management
5. Build production APK/IPA

## Troubleshooting

**Can't connect to backend?**
- Use your computer's IP address, not localhost
- Check firewall allows port 8000
- Ensure backend is running

**App crashes on startup?**
- Clear Expo cache: `npx expo start -c`
- Reinstall dependencies: `rm -rf node_modules && npm install`

**Slow performance?**
- Disable remote debugging
- Use production build instead of Expo Go
