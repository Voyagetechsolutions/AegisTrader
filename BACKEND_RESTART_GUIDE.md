# Backend Restart Guide

## Problem
The backend server is running but not responding to requests (timing out). This happens when:
- The backend process is hung or stuck
- Port 8000 is occupied by a frozen process
- MT5 connection is blocking the event loop

## Solution

### Quick Restart (Recommended)

1. **Run the restart script:**
   ```bash
   restart_backend.bat
   ```

   This will:
   - Kill all Python processes
   - Wait 2 seconds
   - Start the backend fresh

2. **Verify it's working:**
   ```bash
   python check_backend_status.py
   ```

   You should see:
   - `/health` returns 200 OK
   - `/dashboard/status` returns 200 OK
   - `/mt5/price/US30` may return 503 (this is OK if MT5 isn't connected)

### Manual Restart

If the script doesn't work:

1. **Stop all Python processes:**
   ```powershell
   taskkill /F /IM python.exe /T
   ```

2. **Wait a few seconds**, then start backend:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Keep the terminal open** - this is your backend server

## Understanding the Errors

### Port Already in Use (WinError 10013)
```
ERROR: [WinError 10013] An attempt was made to access a socket...
```
**Cause:** Another process is using port 8000  
**Fix:** Run `restart_backend.bat` to kill existing processes

### Module Not Found
```
ModuleNotFoundError: No module named 'backend'
```
**Cause:** Running from wrong directory (`backend/` folder)  
**Fix:** Always run from parent directory (where this file is located)

### Request Timeouts
```
HTTPConnectionPool: Read timed out
```
**Cause:** Backend is frozen/hung  
**Fix:** Restart the backend using `restart_backend.bat`

## Mobile App Connection

After restarting the backend:

1. **Backend must be accessible from network:**
   - IP: `192.168.8.152`
   - Port: `8000`
   - Started with: `--host 0.0.0.0`

2. **Mobile app will connect automatically** if backend is running

3. **Expected behavior:**
   - Dashboard tab: Shows account info (may show $0 if MT5 not connected)
   - Engines tab: Shows dual engine controls
   - Some endpoints return 503 if MT5 isn't connected (this is normal)

## MT5 Connection (Optional)

The backend works WITHOUT MT5 connected, but some features require it:

- `/mt5/price/*` endpoints need MT5
- Live trading needs MT5
- Account balance needs MT5

To connect MT5:
1. Open MT5 terminal
2. Load `AegisTradeBridge.mq5` EA on any chart
3. EA will send heartbeats to backend
4. Backend will show "MT5 Connected" status

## Troubleshooting

### Backend starts but mobile app shows errors
- Check firewall isn't blocking port 8000
- Verify IP address: `ipconfig` should show `192.168.8.152`
- Test from mobile device browser: `http://192.168.8.152:8000/health`

### Backend crashes immediately
- Check for syntax errors in Python files
- Look at the error message in terminal
- Try running without `--reload` flag

### Can't kill Python processes
```powershell
# Force kill all Python
Get-Process python | Stop-Process -Force
```

## Quick Reference

**Start backend:**
```bash
restart_backend.bat
```

**Check status:**
```bash
python check_backend_status.py
```

**Stop backend:**
- Press `Ctrl+C` in the backend terminal
- Or run: `taskkill /F /IM python.exe /T`

**Correct directory:**
```
C:\Users\bathini bona\Documents\Aegis Trader\
```

**Wrong directory:**
```
C:\Users\bathini bona\Documents\Aegis Trader\backend\  ❌
```
