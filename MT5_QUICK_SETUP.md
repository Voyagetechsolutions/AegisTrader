# 🚀 MT5 Quick Setup - 5 Minutes

## Step 1: Install MT5
- Download from your broker's website
- Login with your broker credentials

## Step 2: Install Bridge
1. Copy `mql5/AegisTradeBridge.mq5`
2. In MT5: File → Open Data Folder → MQL5/Experts/
3. Paste the file
4. Open MetaEditor (F4) and compile (F7)

## Step 3: Configure
Edit `AegisTradeBridge.mq5` (lines 13-17):
```cpp
input string   API_URL        = "http://localhost:8000";
input string   API_SECRET     = "your-secret-here";
```

Edit `.env`:
```bash
MT5_NODE_SECRET=your-secret-here
EXECUTION_SYMBOL=US30  # Check your broker's symbol name
```

**Important:** Add backend URL to MT5 WebRequest whitelist:
- Tools → Options → Expert Advisors
- Check "Allow WebRequest for listed URL"
- Add: `http://localhost:8000`

## Step 4: Attach to Chart
1. Open US30 chart in MT5
2. Drag AegisTradeBridge from Navigator to chart
3. Enable AutoTrading (Alt+A)
4. Check Experts tab for "Connected to backend"

## Step 5: Start Backend
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

## Verify
```bash
curl http://localhost:8000/dashboard/health
```

Should show `"mt5_node": true`

## ✅ Done!
- Dashboard should show green MT5 indicator
- Balance should display
- System ready to analyze and trade

## 📚 Full Guide
See `MT5_SETUP_GUIDE.md` for detailed instructions and troubleshooting.
