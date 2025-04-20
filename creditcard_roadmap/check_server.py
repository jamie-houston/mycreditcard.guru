#!/usr/bin/env python
import requests
import sys

def check_server(base_url="http://localhost:5001"):
    """Test if the server is running and responding properly."""
    routes_to_check = [
        {"url": "/health", "name": "Health Check"},
        {"url": "/", "name": "Landing Page"},
        {"url": "/login", "name": "Login Page"},
        {"url": "/register", "name": "Registration Page"},
        {"url": "/recommendations/", "name": "Recommendations List"}
    ]
    
    success = True
    
    try:
        for route in routes_to_check:
            print(f"Checking {route['name']}...")
            response = requests.get(f"{base_url}{route['url']}", timeout=5)
            
            # Consider both 200 (OK) and 302 (redirect) as success
            # The redirect may happen for protected routes if not logged in
            if response.status_code in [200, 302]:
                print(f"✅ {route['name']} check passed with status {response.status_code}")
            else:
                print(f"❌ {route['name']} check failed with status {response.status_code}")
                success = False
        
        if success:
            print("\n✅ All checks passed - server is healthy")
        else:
            print("\n⚠️ Some checks failed - server may have issues")
        
        return success
    
    except requests.RequestException as e:
        print(f"❌ Server connection failed: {e}")
        return False

if __name__ == "__main__":
    success = check_server()
    sys.exit(0 if success else 1) 