#!/usr/bin/env python3
"""
Test file serving through the uploads API.
"""

import requests
from pathlib import Path

# Test parameters
BASE_URL = "http://localhost:5000"
USER_ID = "6a292a1c188b6a3153d8ad81"
FILES_TO_TEST = [
    "generated_design_f648d012_render.jpg",
    "comparison_room_577d97ed.jpg",
    "room_577d97ed.jpg"
]

print("\n" + "="*70)
print("🧪 Testing File Serving Through API")
print("="*70 + "\n")

# Check if files exist locally
from config.settings import settings
print(f"Upload directory: {settings.storage.UPLOAD_DIR}\n")

for filename in FILES_TO_TEST:
    file_path = Path(settings.storage.UPLOAD_DIR) / USER_ID / filename
    
    print(f"Testing: {filename}")
    print(f"  Local path: {file_path}")
    print(f"  Exists: {'✅' if file_path.exists() else '❌'}")
    
    if file_path.exists():
        print(f"  Size: {file_path.stat().st_size:,} bytes")
        
        # Test URL
        url = f"{BASE_URL}/api/uploads/{USER_ID}/{filename}"
        print(f"  URL: {url}")
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  HTTP Status: ✅ {response.status_code}")
                print(f"  Content-Type: {response.headers.get('Content-Type')}")
                print(f"  Content-Length: {len(response.content):,} bytes")
            else:
                print(f"  HTTP Status: ❌ {response.status_code}")
                print(f"  Error: {response.text[:200]}")
        except requests.exceptions.ConnectionError:
            print(f"  ⚠️ Server not running at {BASE_URL}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print()

print("="*70)
print("💡 If you see connection errors, make sure the Flask app is running:")
print("   python app_minimal.py")
print("="*70 + "\n")
