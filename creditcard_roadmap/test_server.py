#!/usr/bin/env python
import requests
import sys
import os
import time
import subprocess
import signal
import atexit

def test_server(base_url="http://localhost:5001"):
    """Test if the server is running and responding properly."""
    try:
        # Check health endpoint
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code != 200:
            print(f"❌ Health check failed with status {health_response.status_code}")
            return False
        
        print(f"✅ Health check passed: {health_response.json()}")
        
        # Check landing page
        home_response = requests.get(base_url, timeout=5)
        if home_response.status_code != 200:
            print(f"❌ Landing page check failed with status {home_response.status_code}")
            return False
        
        print("✅ Landing page loaded successfully")
        return True
    
    except requests.RequestException as e:
        print(f"❌ Server connection failed: {e}")
        return False

def start_server():
    """Start the Flask server and test it."""
    print("Starting Flask server...")
    
    # Start the server as a subprocess
    server_process = subprocess.Popen(
        ["flask", "--app", "run.py", "run", "--port", "5001", "--host", "0.0.0.0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Register a function to kill the server when this script exits
    def cleanup():
        print("Stopping Flask server...")
        if server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=5)
    
    atexit.register(cleanup)
    
    # Wait for server to start
    print("Waiting for server to start...")
    for _ in range(10):
        time.sleep(1)
        if test_server():
            print("Server is running and healthy!")
            # Keep server running
            while True:
                line = server_process.stdout.readline()
                if not line and server_process.poll() is not None:
                    break
                if line:
                    print(f"SERVER: {line.strip()}")
            return 0
    
    print("Server failed to start properly within the timeout period.")
    return 1

if __name__ == "__main__":
    sys.exit(start_server()) 