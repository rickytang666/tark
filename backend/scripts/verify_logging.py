import sys
import os
import threading
import time
import requests
import uvicorn
import logging
from unittest.mock import MagicMock

# fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main

# Mock return values
DUMMY_OBJ = "dummy_for_logging.obj"

# 1. Mock MeshGenerator
class MockGenerator:
    def __init__(self, *args, **kwargs):
        pass
        
    def generate(self, *args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback(10, "mock_gen_start")
            progress_callback(100, "mock_gen_done")
            
        # Create a real dummy file because the code checks os.path.exists
        with open(DUMMY_OBJ, "w") as f:
            f.write("v 0 0 0\n")
            
        return os.path.abspath(DUMMY_OBJ), None, []

# Replace in app.main
app.main.MeshGenerator = MockGenerator

# 2. Mock trimesh used in _run_generation_sync
# Since it's imported locally inside the function, we patch sys.modules
mock_trimesh = MagicMock()
mock_mesh = MagicMock()
mock_mesh.vertices = [0, 0, 0] # len 3
mock_trimesh.load.return_value = mock_mesh
# Ensure isinstance(mesh, trimesh.Scene) is False so it goes to else block
mock_trimesh.Scene = type("Scene", (), {}) 

sys.modules["trimesh"] = mock_trimesh

# 3. Server
def run_server():
    fastapi_app = app.main.app
    # Run loop
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8891, log_level="info")

def verify_logging():
    # colors
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"

    print(f"{green}--- starting logging verification ---{reset}")
    
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1)
    
    url = "http://127.0.0.1:8891/generate"
    headers = {"x-mock-ip": "8.8.8.8"}
    payload = {
        "bbox": {"north": 40.015, "south": 40, "east": -74, "west": -74.015},
        "quality": "low",
        "job_id": "test-logging-job"
    }
    
    try:
        print("triggering generation (look for json logs below)...")
        resp = requests.post(url, json=payload, headers=headers)
        print(f"status: {resp.status_code}")
        
        # Monitor for a bit to let background task finish
        time.sleep(2)
        
    finally:
        # cleanup
        if os.path.exists(DUMMY_OBJ):
            os.remove(DUMMY_OBJ)
            
if __name__ == "__main__":
    verify_logging()
