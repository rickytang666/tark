<div align="center">
    <h1>Tark</h1>
    <p><strong>Google Earth for game developers.</strong></p>
    <p>Click anywhere on the map. Get a game-ready 3D mesh in 20 seconds. Real terrain, real buildings, real textures.</p>
</div>

---

## What you get

Draw a box on the map, download a .zip with:

- Terrain mesh (30m resolution elevation from Mapbox)
- Buildings (from OpenStreetMap, extruded to real heights)
- Satellite texture mapped on the terrain
- 1:1 scale (1 unit = 1 meter)

## How to use it

1. Go to localhost:3000
2. Shift+drag to select an area (1-5km works best)
3. Pick quality level (**Low** to **Ultra**)
4. Hit generate
5. Drag the .obj into Unity/Unreal/Blender

Takes 30-120 seconds depending on area size.

## Features

- **Async Generation**: Heavy mesh processing runs in background threads.
- **Job Persistence**: Progress stored in Redis (1h expiry).
- **Rate Limiting**: 5 requests/minute per IP (exempt on localhost).
- **Monitoring**: Prometheus metrics at `backend:8000/metrics`.
- **Structured Logging**: JSON logs for easy tracking.

## Stack

- **Frontend**: Next.js + Tailwind CSS + Leaflet
- **Backend**: FastAPI + Redis + Trimesh + Prometheus
- **Data**: Mapbox Terrain-RGB (elevation), OSM Overpass (buildings), Mapbox Static (satellite)

## Setup

You need:

- Python 3.13+
- Node.js 18+
- Redis (for job persistence)
- Mapbox API token (free tier at https://account.mapbox.com/access-tokens/)

**Backend:**

```bash
cd backend
./setup.sh
# ensure redis-server is running
# add MAPBOX_ACCESS_TOKEN to .env
uv run uvicorn app.main:app --reload  # runs on :8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev  # runs on :3000
```

Open localhost:3000, shift+drag on the map, hit generate.

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for detailed sub-system documentation.

## Unity import

⚠️ Optimized for Unity. Blender/Unreal work but are experimental.

1. Extract the .zip
2. Drag .obj into Unity Assets
3. Done (textures load automatically, scale is 1:1)

See `docs/unity.md` for details.

## Limits

- Min: 1km × 1km (smaller = weird terrain stretching)
- Sweet spot: 2km × 2km
- Max: 5km × 5km (bigger = timeout/OOM)
