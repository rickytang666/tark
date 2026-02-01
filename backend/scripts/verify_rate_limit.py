
import sys
import os
import requests
import time
import threading
import uvicorn
import app.main

# 1. mock remote address
# slowapi uses request.client.host
# we need to subclass/wrap app or mock the request scope?
# simpler: just use requests headers locally? 
# no, slowapi uses `get_remote_address` which checks `request.client` or headers if configured.
# but our backend isn't configured for proxy headers yet (trusted_hosts).

# actually, we can just monkeypatch the key function in the script!
original_key_func = app.main.rate_limit_key

def mock_key_func(request):
    # simulate external ip
    return "8.8.8.8"

# monkeypatch key func on the limiter instance
# (limiter is instance of Limiter)
app.main.limiter.key_func = mock_key_func

# 2. server thread
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
        "bbox": {"north": 40, "south": 39, "east": -74, "west": -75},
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
            resp = requests.post(url, json=payload, timeout=5)
            
            print(f"req {i}: status {resp.status_code}")
            
            if i <= 5:
                if resp.status_code != 200:
                    print(f"{red}failure: expected 200, got {resp.status_code}{reset}")
            else:
                if resp.status_code == 429:
                    print(f"{green}success: req {i} blocked (429)!{reset}")
                    return # pass
                else:
                    print(f"{red}failure: req {i} allowed (code {resp.status_code}) - limit broken?{reset}")
        
        except Exception as e:
            print(f"{red}error: {e}{reset}")

if __name__ == "__main__":
    # add backend to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    test_rate_limit()
