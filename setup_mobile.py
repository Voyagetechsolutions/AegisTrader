"""
Quick setup script to configure mobile app with your computer's IP address.
"""

import socket
import re
from pathlib import Path

def get_local_ip():
    """Get the local IP address of this computer."""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def update_mobile_config(ip_address):
    """Update the mobile app API configuration with the correct IP."""
    api_file = Path("mobile/services/api.ts")
    
    if not api_file.exists():
        print(f"❌ Error: {api_file} not found")
        return False
    
    # Read the file
    content = api_file.read_text()
    
    # Replace the IP address
    pattern = r"'http://[\d\.]+:8000'"
    replacement = f"'http://{ip_address}:8000'"
    
    new_content = re.sub(pattern, replacement, content)
    
    # Write back
    api_file.write_text(new_content)
    
    return True

def main():
    print("=" * 60)
    print("Aegis Trader Mobile App Setup")
    print("=" * 60)
    print()
    
    # Get IP address
    ip = get_local_ip()
    
    if not ip:
        print("❌ Could not detect IP address automatically")
        print()
        print("Please find your IP manually:")
        print("  Windows: Run 'ipconfig' and look for IPv4 Address")
        print("  Mac/Linux: Run 'ifconfig' and look for inet address")
        return
    
    print(f"✓ Detected IP address: {ip}")
    print()
    
    # Update config
    print("Updating mobile/services/api.ts...")
    if update_mobile_config(ip):
        print(f"✓ Updated API_BASE_URL to: http://{ip}:8000")
    else:
        print("❌ Failed to update configuration")
        return
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print()
    print("1. Start backend with network access:")
    print(f"   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    print()
    print("2. Test backend is accessible:")
    print(f"   curl http://{ip}:8000/health")
    print()
    print("3. Start mobile app:")
    print("   cd mobile")
    print("   npx expo start")
    print()
    print("4. Scan QR code with Expo Go app on your phone")
    print()
    print("Note: Make sure your phone and computer are on the same WiFi network!")
    print()

if __name__ == "__main__":
    main()
