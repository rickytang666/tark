import sys
import os
import threading
import time
import requests
import uvicorn

# fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main

def run_server():
    fastapi_app = app.main.app
    # Run loop
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8892, log_level="error")

def verify_metrics():
    print("--- Starting Metrics Verification ---")
    
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2) # Give uvicorn a bit more time
    
    # 1. Hit the API to generate some metrics
    print("Generating some traffic...")
    try:
        requests.get("http://127.0.0.1:8892/health")
        requests.get("http://127.0.0.1:8892/health")
    except Exception as e:
        print(f"Error generating traffic: {e}")
        return

    # 2. Check metrics endpoint
    url = "http://127.0.0.1:8892/metrics"
    print(f"Checking {url}...")
    
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            content = resp.text
            # Check for key prometheus metrics
            checks = [
                "http_requests_total",
                "http_request_duration_seconds_bucket",
                "python_info"
            ]
            
            # colors
            green = "\033[92m"
            red = "\033[91m"
            reset = "\033[0m"
            
            all_passed = True
            for check in checks:
                if check in content:
                    print(f"{green}found '{check}'{reset}")
                else:
                    print(f"{red}missing '{check}'{reset}")
                    all_passed = False
            
            if all_passed:
                print(f"\n{green}success: metrics endpoint is functional.{reset}")
            else:
                print(f"\n{red}failure: missing expected metrics.{reset}")
        else:
            print(f"{red}failure: expected 200 ok, got {resp.status_code}{reset}")
            
    except Exception as e:
        print(f"Error fetching metrics: {e}")
    
if __name__ == "__main__":
    verify_metrics()
