"""
Quick script to check backend and MT5 connection status
"""
import requests
import json

backend_url = "http://192.168.8.152:8000"

print("=" * 60)
print("BACKEND STATUS CHECK")
print("=" * 60)

# Test 1: Health check
print("\n1. Testing /health endpoint...")
try:
    response = requests.get(f"{backend_url}/health", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Dashboard status
print("\n2. Testing /dashboard/status endpoint...")
try:
    response = requests.get(f"{backend_url}/dashboard/status", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: MT5 connection status
print("\n3. Testing /mt5/connection/status endpoint...")
try:
    response = requests.get(f"{backend_url}/mt5/connection/status", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: MT5 price endpoint
print("\n4. Testing /mt5/price/US30 endpoint...")
try:
    response = requests.get(f"{backend_url}/mt5/price/US30", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 5: MT5 heartbeat
print("\n5. Testing /mt5/heartbeat endpoint...")
try:
    response = requests.get(f"{backend_url}/mt5/heartbeat", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 60)
print("DIAGNOSIS:")
print("=" * 60)
print("If /health works but /mt5/price returns 503:")
print("  -> MT5 terminal is not connected to backend")
print("  -> Solution: Start MT5 terminal and load AegisTradeBridge EA")
print("\nIf /mt5/heartbeat shows 'No heartbeat data':")
print("  -> EA is not running or not sending heartbeats")
print("  -> Solution: Check MT5 Expert Advisors tab")
print("=" * 60)
