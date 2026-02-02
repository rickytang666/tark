# tark backend

fastapi + redis backend for generating game-ready 3d meshes from real-world locations.

## setup

```bash
# install uv if not installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# setup project
./setup.sh
```

**requirements:**

- redis must be running (`redis-server`)
- `.env` must contain `MAPBOX_ACCESS_TOKEN`

## run

```bash
uv run uvicorn app.main:app --reload
```

- api: `http://localhost:8000`
- docs: `http://localhost:8000/docs`
- metrics: `http://localhost:8000/metrics`

## testing

```bash
# run verification scripts
uv run python scripts/verify_async.py
uv run python scripts/verify_rate_limit.py

# run unit tests
uv run python tests/test_mapbox.py
uv run python tests/test_overpass.py
```

## features

### core

- **async generation:** heavy mesh processing runs in background threads
- **job persistence:** progress stored in redis (1h expiry)
- **metrics:** prometheus endpoint at `/metrics`
- **logging:** structured json logs

### rate limiting

- **limit:** 5 requests/minute per ip
- **bypass:** localhost requests are exempt
- **headers:** `x-mock-ip` allowed from localhost for testing

## api

### POST /generate

generate mesh for bounding box. Returns `job_id`.

**body:**

```json
{
  "bbox": { "north": 43.48, "south": 43.46, "east": -80.52, "west": -80.56 },
  "quality": "medium"
}
```

### GET /progress/{job_id}

get status (`queued`, `processing`, `complete`, `error`).

### GET /download/{job_id}

download result zip (only when status is `complete`).

## structure

```
backend/
├── app/
│   ├── main.py          # fastapi app + routes
│   └── generator.py     # mesh generation pipeline
├── scripts/             # verification scripts
├── tests/               # unit tests
├── docs/                # technical documentation
└── temp/                # temporary file storage
```
