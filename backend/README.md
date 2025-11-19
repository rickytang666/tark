# tark backend

fastapi backend for generating game-ready 3d meshes from real-world locations.

## setup

```bash
./setup.sh
```

edit `.env` and add your mapbox token from https://account.mapbox.com/access-tokens/

## run

```bash
source venv/bin/activate
python -m app.main
```

server runs at `http://localhost:8000`

api docs at `http://localhost:8000/docs`

## testing

```bash
# test terrain fetcher
python tests/test_mapbox.py

# test building fetcher
python tests/test_overpass.py

# test full pipeline
python tests/test_pipeline.py
```

## structure

```
backend/
├── app/
│   ├── main.py          # fastapi app + routes
│   ├── generator.py     # mesh generation pipeline
│   ├── terrain.py       # terrain mesh from elevation
│   ├── buildings.py     # building extrusion
│   ├── textures.py      # satellite imagery fetching
│   ├── fetchers/
│   │   ├── mapbox.py    # terrain-rgb api
│   │   └── overpass.py  # osm building data
│   └── utils/
│       ├── coords.py    # coordinate transformations
│       └── mesh.py      # mesh utilities
├── tests/               # test scripts
├── docs/                # technical documentation
└── temp/                # temporary file storage
```

## api

### POST /generate

generate mesh for bounding box.

**body:**

```json
{
  "bbox": {
    "north": 43.48,
    "south": 43.46,
    "east": -80.52,
    "west": -80.56
  },
  "quality": "medium"
}
```

**response:** zip file with obj + mtl + texture png

**quality options:**

- `low`: zoom 11, ~60m resolution, 512px texture
- `medium`: zoom 12, ~30m resolution, 1024px texture (default)
- `high`: zoom 13, ~15m resolution, 1280px texture
- `ultra`: zoom 14, ~7.5m resolution, 1280px texture

### GET /quality-options

returns available quality levels with descriptions.

### GET /health

health check endpoint.

## technical notes

- **bbox constraints:** 1-5km per side
- **coordinate system:** y-up, 1 unit = 1 meter
- **terrain smoothing:** gaussian filter (σ=1.5) applied to elevation data
- **building placement:** elevation-aware using terrain mesh sampling
- **output format:** wavefront obj + mtl with normals and uv coordinates

see `docs/` for detailed implementation documentation.

## known limitations

- buildings are simple box extrusions (no architectural details)
- building height estimation may be inaccurate if osm data is incomplete
- buildings have flat bases (don't follow terrain slopes)
- osm data completeness varies by location
- processing time: 30-120 seconds for large areas
