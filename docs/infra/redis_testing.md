# redis testing guide

how to verify redis persistence works.

## 1. manual verification

1.  **start server**

    ```bash
    uv run uvicorn app.main:app
    ```

2.  **create job**

    ```bash
    curl -X POST http://localhost:8000/generate -H "Content-Type: application/json" -d '{
      "bbox": {
        "north": 40.7, "south": 40.68,
        "east": -74.0, "west": -74.02
      }
    }'
    ```

    _copy the `job_id` from response._

3.  **stop server**
    _press `Ctrl+C` in terminal._

4.  **restart server**

    ```bash
    uv run uvicorn app.main:app
    ```

5.  **check status**
    ```bash
    curl http://localhost:8000/progress/{job_id}
    ```
    _response should be `{"status": "complete", ...}` (or whatever state it was in)._

## 2. automated check (todo)

future: add pytest fixture that spins up redis docker container.
