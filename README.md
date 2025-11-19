# Tark

turn any location into a game-ready 3d mesh. select an area, get terrain + buildings as .obj file for unity/unreal/blender.

**stack:** next.js 15 + fastapi + mapbox terrain-rgb + openstreetmap

## quick start

### backend

```bash
cd backend
./setup.sh
# add MAPBOX_ACCESS_TOKEN to .env
source venv/bin/activate
python -m app.main
```

runs at `http://localhost:8000`

### frontend

```bash
cd frontend
npm install
npm run dev
```

runs at `http://localhost:3000`

## specs

- **area:** 1-5km per side (min 1km to prevent distortion)
- **scale:** 1 obj unit = 1 meter
- **coords:** wgs84 → utm → local tangent plane
- **output:** obj + mtl + satellite texture png
- **terrain resolution:** ~30m at zoom 12
- **buildings:** osm data with height estimation

## using the mesh

download returns a zip file. extract and drag the `.obj` file into blender/unity - textures load automatically.

see `docs/unity.md` for unity import guide.

## project structure

```
tark/
├── frontend/       # next.js interface
├── backend/        # fastapi mesh generator
└── docs/           # documentation
```

## technical details

- coordinate system: y-up, right-handed
- terrain: gaussian smoothing (σ=1.5) to reduce mapbox tile noise
- buildings: elevation-aware placement on terrain
- textures: satellite imagery with planar uv projection

see `backend/docs/` for implementation details.
