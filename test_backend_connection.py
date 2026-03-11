"""
Quick test to check if backend is accessible from network
"""
import requests
import socket

def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unable to detect"

def test_backend(ip, port=8000):
    """Test if backend is accessible"""
    print(f"\n{'='*60}")
    print(f"TESTING BACKEND CONNECTION")
    print(f"{'='*60}\n")
    
    print(f"Your computer's IP: {get_local_ip()}")
    print(f"Testing IP: {ip}")
    print(f"Port: {port}\n")
    
    # Test 1: Health endpoint
    print("Test 1: Health Check")
    try:
        response = requests.get(f"http://{ip}:{port}/dashboard/health", timeout=5)
        print(f"  ✓ SUCCESS - Status: {response.status_code}")
        print(f"  Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print(f"  ✗ FAILED - Cannot connect")
        print(f"  Solution: Start backend with: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        return False
    except requests.exceptions.Timeout:
        print(f"  ✗ FAILED - Timeout")
        print(f"  Solution: Check firewall settings")
        return False
    except Exception as e:
        print(f"  ✗ FAILED - {e}")
        return False
    
    # Test 2: Dashboard status
    print("\nTest 2: Dashboard Status")
    try:
        response = requests.get(f"http://{ip}:{port}/dashboard/status", timeout=5)
        print(f"  ✓ SUCCESS - Status: {response.status_code}")
        data = response.json()
        print(f"  Mode: {data.get('mode', 'unknown')}")
        print(f"  MT5 Connected: {data.get('mt5_connected', False)}")
    except Exception as e:
        print(f"  ✗ FAILED - {e}")
    
    # Test 3: MT5 status
    print("\nTest 3: MT5 Status")
    try:
        response = requests.get(f"http://{ip}:{port}/mt5/status", timeout=5)
        print(f"  ✓ SUCCESS - Status: {response.status_code}")
        data = response.json()
        print(f"  Connected: {data.get('connected', False)}")
    except Exception as e:
        print(f"  ✗ FAILED - {e}")
    
    # Test 4: Dual-engine status
    print("\nTest 4: Dual-Engine Status")
    try:
        response = requests.get(f"http://{ip}:{port}/dual-engine/status", timeout=5)
        print(f"  ✓ SUCCESS - Status: {response.status_code}")
    except Exception as e:
        print(f"  ✗ FAILED - {e}")
    
    print(f"\n{'='*60}")
    print(f"BACKEND IS ACCESSIBLE FROM NETWORK!")
    print(f"{'='*60}\n")
    print(f"Mobile app should use: http://{ip}:{port}")
    print(f"\nNext steps:")
    print(f"1. Make sure your phone is on the same WiFi network")
    print(f"2. Open Expo Go app and scan the QR code")
    print(f"3. App should connect successfully\n")
    
    return True

if __name__ == "__main__":
    # Test with the IP from mobile config
    test_ip = "192.168.8.152"
    
    print("\nNOTE: If this test fails, your backend might not be running")
    print("      or it's not accessible from the network.\n")
    
    input("Press Enter to start test...")
    
    test_backend(test_ip)
