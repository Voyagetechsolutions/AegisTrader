"""
Keep-Alive Script for Render.com Free Tier

Prevents backend from spinning down after 15 minutes of inactivity.
Run this on your local machine to keep cloud backend awake.

Usage:
    python keep_alive.py
"""

import requests
import time
import sys
from datetime import datetime
from pathlib import Path

# Configuration
BACKEND_URL = "https://aegis-trader-backend.onrender.com"  # Change to your URL
PING_INTERVAL = 600  # 10 minutes
TIMEOUT = 10

def get_backend_url():
    """Get backend URL from user or config."""
    print("=" * 60)
    print("KEEP-ALIVE SCRIPT FOR RENDER.COM")
    print("=" * 60)
    print()
    
    url = input("Enter your backend URL (e.g., https://aegis-trader-backend.onrender.com): ").strip()
    
    if not url.startswith("http"):
        url = f"https://{url}"
    
    return url

def ping_backend(url):
    """Ping backend health endpoint."""
    try:
        response = requests.get(f"{url}/health", timeout=TIMEOUT)
        status = "✓" if response.status_code == 200 else "✗"
        return True, response.status_code, status
    except requests.exceptions.Timeout:
        return False, None, "✗ (timeout)"
    except requests.exceptions.ConnectionError:
        return False, None, "✗ (connection error)"
    except Exception as e:
        return False, None, f"✗ ({str(e)})"

def main():
    """Main keep-alive loop."""
    url = get_backend_url()
    
    print()
    print(f"Backend URL: {url}")
    print(f"Ping interval: {PING_INTERVAL} seconds ({PING_INTERVAL // 60} minutes)")
    print()
    print("Starting keep-alive pings...")
    print("Press Ctrl+C to stop")
    print()
    print("-" * 60)
    
    ping_count = 0
    
    try:
        while True:
            ping_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            success, status_code, status = ping_backend(url)
            
            if success:
                print(f"[{timestamp}] Ping #{ping_count}: {status} (HTTP {status_code})")
            else:
                print(f"[{timestamp}] Ping #{ping_count}: {status}")
            
            # Wait before next ping
            time.sleep(PING_INTERVAL)
            
    except KeyboardInterrupt:
        print()
        print("-" * 60)
        print(f"Keep-alive stopped. Sent {ping_count} pings.")
        print("Backend may spin down after 15 minutes of inactivity.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
