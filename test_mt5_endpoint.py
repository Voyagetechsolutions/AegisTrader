"""
Test MT5 endpoint to diagnose 404 errors
"""
import requests
import time

BASE_URL = "http://192.168.8.152:8000"

def test_endpoint():
    """Test the MT5 price endpoint multiple times"""
    print("\n" + "="*60)
    print("TESTING MT5 PRICE ENDPOINT")
    print("="*60 + "\n")
    
    success_count = 0
    fail_count = 0
    errors = []
    
    # Test 20 times
    for i in range(20):
        try:
            response = requests.get(f"{BASE_URL}/mt5/price/US30", timeout=5)
            
            if response.status_code == 200:
                success_count += 1
                print(f"Test {i+1}: ✓ SUCCESS (200)")
            elif response.status_code == 404:
                fail_count += 1
                print(f"Test {i+1}: ✗ FAILED (404)")
                errors.append(f"Test {i+1}: 404 Not Found")
            else:
                fail_count += 1
                print(f"Test {i+1}: ✗ FAILED ({response.status_code})")
                errors.append(f"Test {i+1}: {response.status_code} - {response.text}")
        
        except requests.exceptions.ConnectionError:
            fail_count += 1
            print(f"Test {i+1}: ✗ CONNECTION ERROR")
            errors.append(f"Test {i+1}: Connection Error")
        
        except Exception as e:
            fail_count += 1
            print(f"Test {i+1}: ✗ ERROR - {e}")
            errors.append(f"Test {i+1}: {str(e)}")
        
        time.sleep(0.5)  # Wait 500ms between requests
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: 20")
    print(f"Successful: {success_count} ({success_count/20*100:.1f}%)")
    print(f"Failed: {fail_count} ({fail_count/20*100:.1f}%)")
    
    if errors:
        print(f"\nErrors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
    
    print("\n" + "="*60)
    
    if fail_count > 0:
        print("\nDIAGNOSIS:")
        print("The endpoint is returning 404 errors intermittently.")
        print("\nPossible causes:")
        print("1. Backend server needs restart")
        print("2. MT5 manager not initialized")
        print("3. Race condition in request handling")
        print("\nSOLUTION:")
        print("1. Stop the backend server (Ctrl+C)")
        print("2. Restart it: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
        print("3. Run this test again")
    else:
        print("\n✓ All tests passed! Endpoint is working correctly.")

if __name__ == "__main__":
    test_endpoint()
