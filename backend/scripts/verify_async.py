
import sys
import os
import threading
import time
import requests
import uvicorn

# add backend directory to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main

# 1. mock the slow function
original_sync = app.main._run_generation_sync

def mock_heavy_task(*args, **kwargs):
    print("\n[mock] starting heavy task (sleep 5s)...")
    time.sleep(5)
    print("\n[mock] heavy task finished.")

# monkeypatch
app.main._run_generation_sync = mock_heavy_task

# 2. server thread
def run_server():
    # access app from the module explicitly to avoid namespace confusion
    fastapi_app = app.main.app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8888, log_level="error")

def test_concurrency():
    # start server in background
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1) # wait for startup

    # colors
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"



    print("[test] triggering generation...")
    # trigger generation (will sleep 5s)
    try:
        requests.post("http://127.0.0.1:8888/generate", json={
            "bbox": {"north": 40, "south": 39, "east": -74, "west": -75},
            "quality": "low",
            "job_id": "test-async"
        }, timeout=1)
    except requests.exceptions.ReadTimeout:
        print(f"{red}warning: /generate timed out (server blocked?){reset}")
    except Exception as e:
        print(f"{red}error posting to /generate: {e}{reset}")

    print("[test] checking health immediately...")
    start = time.time()
    try:
        resp = requests.get("http://127.0.0.1:8888/health", timeout=1)
        elapsed = time.time() - start
        print(f"[test] health response time: {elapsed:.4f}s")
        print(f"[test] health status: {resp.status_code}")
        
        if elapsed < 1.0 and resp.status_code == 200:
            print(f"\n{green}success: server responded instantly!{reset}")
        else:
            print(f"\n{red}failure: server blocked or error! code={resp.status_code}{reset}")
    except Exception as e:
        print(f"\n{red}failure: health check failed: {e}{reset}")

if __name__ == "__main__":
    test_concurrency()
