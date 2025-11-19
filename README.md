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
3. Pick quality level
4. Hit generate
5. Drag the .obj into Unity/Unreal/Blender

Takes 30-120 seconds depending on area size.

## Stack

- Next.js + Leaflet (frontend map picker)
- FastAPI + Trimesh (backend mesh generation)
- Mapbox Terrain-RGB (elevation)
- OpenStreetMap Overpass (buildings)
- Mapbox Static (satellite texture)

## Setup

You need:

- Python 3.11+
- Node.js 18+
- Mapbox API token (free tier at https://account.mapbox.com/access-tokens/)

**Backend:**

```bash
cd backend
./setup.sh
# add MAPBOX_ACCESS_TOKEN to .env
source venv/bin/activate
python -m app.main  # runs on :8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev  # runs on :3000
```

Open localhost:3000, shift+drag on the map, hit generate.

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
