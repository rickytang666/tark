# Tark

turn any location into a game-ready 3d mesh. select an area, get terrain + buildings as .obj file for unity/unreal/blender.

**stack:** next.js 16 + fastapi + mapbox terrain-rgb + openstreetmap

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

## progress

**days 1-4: backend** ✅

- mapbox terrain fetcher (multi-tile stitching)
- overpass api building fetcher
- terrain mesh generation (130k+ vertices)
- building extrusion with triangulation
- full pipeline: bbox → terrain + buildings → obj

**days 5-6: frontend setup** ✅

- next.js 16 + typescript + tailwind
- api client
- landing page

**days 5-6: frontend core** 🚧

- [ ] leaflet map integration
- [ ] rectangle selection tool
- [ ] area preview ui
- [ ] validation feedback

**days 7-8: integration**

- connect frontend to backend
- file downloads
- loading states

**days 9-10: polish**

- test real locations
- verify in unity/unreal
- bug fixes

## structure

```
tark/
├── frontend/       # next.js interface
├── backend/        # fastapi mesh generator
└── plan/           # design docs
```

## specs

- bbox: 1-5km (min 1km to prevent distortion)
- scale: 1 obj unit = 1 meter
- coords: wgs84 → utm → local tangent plane
- output: obj + mtl

see [backend/STANDARDS.md](backend/STANDARDS.md)
