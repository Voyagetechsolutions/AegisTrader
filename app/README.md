# 📱 Aegis Trader Mobile App

React Native mobile app that connects to your Python backend.

## 🚀 Quick Start

### 1. Install Dependencies:
```bash
cd app
npm install
```

### 2. Update Backend URL:
Edit `App.js` line 6:
```javascript
const API_URL = 'http://YOUR_BACKEND_URL:8000';
```

### 3. Run the App:
```bash
# Web (instant preview)
npm run web

# Android (requires Android Studio)
npm run android

# iOS (requires Mac + Xcode)
npm run ios
```

## 📱 Install on Phone

### Option 1: Expo Go App (Easiest)
1. Install "Expo Go" from App Store/Play Store
2. Run `npm start` in terminal
3. Scan QR code with Expo Go app
4. App runs on your phone instantly!

### Option 2: Build Native App
```bash
# Install EAS CLI
npm install -g eas-cli

# Build for Android
eas build --platform android

# Build for iOS
eas build --platform ios
```

## ✨ Features

- **Real-time data** from Python backend
- **Mode switching** (Analyze, Trade, Swing)
- **Auto-trading toggle**
- **Risk monitoring**
- **Account balance**
- **Pull to refresh**

## 🔧 Backend Connection

The app connects to these endpoints:
- `GET /dashboard/status` - Get bot status
- `POST /dashboard/auto-trade` - Toggle auto trading
- `POST /dashboard/mode` - Change bot mode

Make sure your Python backend is running!