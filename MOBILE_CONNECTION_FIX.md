# Mobile App Network Error Fix

## Problem
Your mobile app is getting "Network Error" when trying to connect to the backend API at `http://192.168.8.152:8000`.

## Quick Diagnosis

### Step 1: Check if Backend is Running
Open a new terminal and run:
```bash
curl http://192.168.8.152:8000/dashboard/health
```

If this fails, your backend isn't running or the IP is wrong.

### Step 2: Start the Backend Server
If the backend isn't running, start it:

```bash
cd "C:\Users\bathini bona\Documents\Aegis Trader"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--host 0.0.0.0` is CRITICAL - it allows connections from other devices on your network.

### Step 3: Verify Your IP Address
Check your actual IP address:

```bash
ipconfig
```

Look for "IPv4 Address" under your active network adapter (WiFi or Ethernet).
It should look like `192.168.x.x` or `10.0.x.x`.

### Step 4: Update Mobile App Configuration
If your IP is different from `192.168.8.152`, update it:

```bash
python setup_mobile.py
```

This will automatically detect your IP and update the mobile app configuration.

### Step 5: Restart Expo
After updating the IP, restart your Expo development server:

1. Stop the current Expo server (Ctrl+C)
2. Clear the cache and restart:
```bash
cd mobile
npx expo start -c
```

## Common Issues

### Issue 1: Backend Not Accessible from Network
**Symptom:** Backend works on `localhost:8000` but not on `192.168.x.x:8000`

**Solution:** Make sure you start the backend with `--host 0.0.0.0`:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Issue 2: Firewall Blocking Connections
**Symptom:** Backend is running but mobile app can't connect

**Solution:** Allow Python through Windows Firewall:
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Find Python and check both "Private" and "Public"

### Issue 3: Phone on Different Network
**Symptom:** Everything looks correct but still can't connect

**Solution:** Make sure your phone and computer are on the SAME WiFi network.
- Computer: Check WiFi settings
- Phone: Check WiFi settings
- They must be connected to the same router

### Issue 4: Using Android Emulator
**Symptom:** Using Android Studio emulator

**Solution:** Android emulator uses special IP:
- Change API URL to `http://10.0.2.2:8000` (this maps to your computer's localhost)

## Testing the Connection

### Test 1: From Your Computer
```bash
curl http://192.168.8.152:8000/dashboard/health
```

Should return: `{"status":"healthy"}`

### Test 2: From Your Phone's Browser
Open your phone's web browser and go to:
```
http://192.168.8.152:8000/docs
```

You should see the FastAPI documentation page.

### Test 3: Check Backend Logs
When the mobile app tries to connect, you should see requests in the backend terminal:
```
INFO:     192.168.x.x:xxxxx - "GET /dashboard/status HTTP/1.1" 200 OK
```

If you don't see these logs, the requests aren't reaching the backend.

## Complete Restart Procedure

If nothing works, do a complete restart:

1. **Stop everything:**
   - Stop Expo (Ctrl+C)
   - Stop Backend (Ctrl+C)
   - Close Expo Go app on phone

2. **Get your IP:**
   ```bash
   ipconfig
   ```
   Note your IPv4 address (e.g., `192.168.8.152`)

3. **Update mobile config:**
   ```bash
   python setup_mobile.py
   ```

4. **Start backend with network access:**
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

5. **Start Expo with clean cache:**
   ```bash
   cd mobile
   npx expo start -c
   ```

6. **Scan QR code** with Expo Go app

7. **Wait for app to load** - first load takes longer

## Verification

Once connected, you should see in the mobile app:
- Dashboard showing account balance
- MT5 connection status
- Dual-engine status
- No more "Network Error" messages

## Still Not Working?

Check these:

1. **Backend is running:** You should see uvicorn logs in terminal
2. **Correct IP:** Run `ipconfig` and verify
3. **Same network:** Phone and computer on same WiFi
4. **Firewall:** Python allowed through firewall
5. **Port 8000:** Not blocked or used by another app

## Quick Test Script

Create a file `test_connection.py`:

```python
import requests

ip = "192.168.8.152"  # Change to your IP
port = 8000

try:
    response = requests.get(f"http://{ip}:{port}/dashboard/health", timeout=5)
    print(f"✓ Backend is accessible!")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
except requests.exceptions.ConnectionError:
    print(f"✗ Cannot connect to {ip}:{port}")
    print(f"  Make sure backend is running with: --host 0.0.0.0")
except requests.exceptions.Timeout:
    print(f"✗ Connection timeout")
    print(f"  Backend might be slow or firewall is blocking")
except Exception as e:
    print(f"✗ Error: {e}")
```

Run it:
```bash
python test_connection.py
```
