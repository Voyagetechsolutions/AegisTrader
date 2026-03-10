import requests
import json
import uuid

# Backend webhook URL
url = "http://localhost:8002/webhook/tradingview"

# Test payload representing a perfect A+ setup
payload = {
    "secret": "changeme",
    "symbol": "TVC:DJI",
    "direction": "long",
    "setup_type": "continuation_long",
    "timeframe": "5",
    "entry": 39000.0,
    "stop_loss": 38950.0,
    "tp1": 39050.0,
    "tp2": 39100.0,
    
    # 20 pts HTF
    "weekly_bias": "bull",
    "daily_bias": "buy",
    "h4_bias": "bull",
    "h1_bias": "bull",
    "m15_bias": "bull",
    "m5_bias": "bull_shift",
    "m1_bias": "bull",
    
    # Levels (15 + 10 = 25 pts)
    "level_250": 39000.0,
    "level_125": 39000.0,
    
    # Confluence booleans (15 + 15 + 10 + 10 = 50 pts)
    "fvg_present": True,
    "liquidity_sweep": True,
    "displacement_present": True,
    "mss_present": True,
    
    # Context (5 + 5 = 10 pts)
    "session_name": "New York",
    "spread": 2.5,
    
    "tv_timestamp": "2026-03-10T09:00:00Z"
}

print(f"Sending payload to {url}...")
response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print("Response JSON:")
print(json.dumps(response.json(), indent=2))

# Now test the polling endpoint to verify the queue
poll_url = "http://localhost:8002/mt5/poll"
headers = {"X-MT5-Secret": "changeme_mt5"}
print(f"\nPolling MT5 EA endpoint {poll_url}...")
poll_response = requests.get(poll_url, headers=headers)
print(f"Status Code: {poll_response.status_code}")
print("Queued Commands:")
print(json.dumps(poll_response.json(), indent=2))
