
import sys
import os

# add backend directory to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
import time
import threading
import uvicorn
import app.main

# 1. server thread
def run_server():
    fastapi_app = app.main.app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8889, log_level="error")

def test_rate_limit():
    # start server
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1)

    url = "http://127.0.0.1:8889/generate"
    payload = {
        "bbox": {"north": 40.015, "south": 40.00, "east": -74.00, "west": -74.015},
        "quality": "low",
        "job_id": "test-limit"
    }

    # colors
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"

    print(f"[test] firing 6 requests from '8.8.8.8' (limit is 5/min)...")

    for i in range(1, 8):
        try:
            # unique job id to allow parallel processing if async works
            payload["job_id"] = f"test-limit-{i}"
            # use x-mock-ip to simulate external user (enabled for localhost in main.py)
            headers = {"x-mock-ip": "8.8.8.8"}
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
            
            print(f"req {i}: status {resp.status_code}")
            
            if i <= 5:
                if resp.status_code != 200:
                    print(f"{red}failure: expected 200, got {resp.status_code}{reset}")
                    print(f"response: {resp.text}")
            else:
                if resp.status_code == 429:
                    print(f"{green}success: req {i} blocked (429)!{reset}")
                    return # pass
                else:
                    print(f"{red}failure: req {i} allowed (code {resp.status_code}) - limit broken?{reset}")
                    print(f"response: {resp.text}")
        
        except Exception as e:
            print(f"{red}error: {e}{reset}")

if __name__ == "__main__":
    test_rate_limit()
