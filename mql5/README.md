# MT5 Bridge - AegisTradeBridge.mq5

## Overview

This is a simplified MT5 Expert Advisor that connects MetaTrader 5 to the Aegis Trader Python backend.

## Features

- ✅ No external libraries required (uses only built-in MQL5)
- ✅ Heartbeat system (sends status every 30 seconds)
- ✅ Account balance and equity monitoring
- ✅ Position tracking
- ✅ Order placement (buy/sell)
- ✅ Stop loss modification
- ✅ Partial position closing
- ✅ Close all positions
- ✅ On-chart status display

## Installation

1. **Copy to MT5:**
   - In MT5: File → Open Data Folder
   - Navigate to: `MQL5/Experts/`
   - Copy `AegisTradeBridge.mq5` here

2. **Compile:**
   - Open MetaEditor (F4)
   - Open `AegisTradeBridge.mq5`
   - Click Compile (F7)
   - Check for "0 errors"

3. **Configure:**
   Edit the input parameters at the top of the file:
   ```cpp
   input string   API_URL        = "http://localhost:8000";
   input string   API_SECRET     = "your-secret-here";
   input int      HeartbeatSec   = 30;
   input ulong    MagicNumber    = 202600;
   input int      Slippage       = 10;
   ```

4. **Enable WebRequest:**
   - Tools → Options → Expert Advisors
   - Check "Allow WebRequest for listed URL"
   - Add: `http://localhost:8000`
   - Click OK

5. **Attach to Chart:**
   - Open US30 chart
   - Drag `AegisTradeBridge` from Navigator to chart
   - Enable AutoTrading (Alt+A)

## Configuration

### API_URL
- Default: `http://localhost:8000`
- Change if backend runs on different port or machine
- Must match backend URL

### API_SECRET
- Must match `MT5_NODE_SECRET` in `.env` file
- Used for authentication
- Keep this secret!

### HeartbeatSec
- Default: 30 seconds
- How often to send status to backend
- Don't set too low (causes spam)

### MagicNumber
- Default: 202600
- Identifies orders from this EA
- Don't change unless you know what you're doing

### Slippage
- Default: 10 points
- Maximum allowed slippage for orders
- Adjust based on your broker

## Verification

### Check Experts Tab
After attaching to chart, check the Experts tab (View → Toolbox → Experts):

**Good:**
```
=== Aegis Trade Bridge Initialized ===
Backend URL: http://localhost:8000
Symbol: US30
Magic Number: 202600
Heartbeat: Every 30 seconds
✓ Connected to backend
```

**Bad:**
```
WebRequest error. Add http://localhost:8000 to allowed URLs
```
→ Solution: Enable WebRequest (see step 4 above)

### Check Chart
The EA displays status on the chart:
```
=== Aegis Trader Bridge ===
Status: ✓ Connected
Balance: $10000.00
Equity: $10000.00
Positions: 0
Last HB: 14:30:45
```

### Check Backend
```bash
curl http://localhost:8000/dashboard/health
```

Should show:
```json
{
  "ok": true,
  "components": {
    "mt5_node": true  // ← Should be true
  }
}
```

## Functions

### Heartbeat
- Sends every 30 seconds (configurable)
- Includes: balance, equity, margin, positions
- Backend uses this to verify connection

### PlaceOrder
- Opens buy or sell orders
- Parameters: symbol, direction, lots, SL, TP, comment
- Returns: success/failure

### ModifySL
- Modifies stop loss of existing position
- Parameters: ticket, new_sl
- Used for breakeven moves

### ClosePartial
- Closes part of a position
- Parameters: ticket, lots
- Used for TP1 (close 50%)

### ClosePosition
- Closes entire position
- Parameters: ticket

### CloseAllPositions
- Closes all positions with this MagicNumber
- Used for emergency stop

## Troubleshooting

### "WebRequest error"
- Add backend URL to WebRequest whitelist
- Tools → Options → Expert Advisors
- Check "Allow WebRequest for listed URL"
- Add: `http://localhost:8000`

### "Backend connection lost"
- Check backend is running
- Check API_URL is correct
- Check firewall allows connections
- Check API_SECRET matches .env

### "Position not found"
- Position may have been closed
- Check MagicNumber matches
- Check you're on the right account

### Orders not executing
- Check AutoTrading is enabled (green button)
- Check account has sufficient margin
- Check symbol is correct
- Check broker allows EAs

## Logs

All activity is logged to the Experts tab:
- ✓ = Success
- ✗ = Error
- Connection status
- Order placements
- Modifications
- Errors

## Security

- Keep API_SECRET private
- Don't share your .mq5 file with secrets
- Use different secrets for demo/live
- Monitor the Experts tab regularly

## Support

See main documentation:
- `MT5_SETUP_GUIDE.md` - Complete setup guide
- `MT5_QUICK_SETUP.md` - Quick reference
- `COMPLETE_SETUP_GUIDE.md` - Full system guide

## Version

- Version: 1.00
- Last Updated: 2026
- Compatible with: MT5 Build 3000+
- No external libraries required
