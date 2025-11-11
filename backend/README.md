# GeoMesh Backend

FastAPI backend for generating game-ready 3D meshes from real-world locations.

## Setup

### Quick Setup

```bash
./setup.sh
```

Then edit `.env` and add your Mapbox token from https://account.mapbox.com/access-tokens/

### Manual Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your MAPBOX_ACCESS_TOKEN
```

### Run Server

```bash
source venv/bin/activate
python -m app.main
```

Server runs at `http://localhost:8000`

## Testing

### Test Mapbox Terrain Fetcher

```bash
python tests/test_mapbox.py
```

Fetches elevation data for SF area. Expected: ~131k elevation points, 2 tiles, -1.5m to 282m range.

### Test Overpass Building Fetcher

```bash
python tests/test_overpass.py
```

Fetches building footprints from OSM. Expected: ~1000 buildings with height/type metadata.

### Test Terrain Mesh Generation

```bash
python tests/test_terrain.py
```

Generates 3D terrain mesh from elevation data. Expected: 131k vertices, 260k triangles. Exports to `temp/test_terrain.obj`.

### Test Building Extrusion

```bash
python tests/test_buildings.py
```

Extrudes building footprints to 3D boxes. Expected: 1081 buildings, 31k vertices, 62k faces. Exports to `temp/test_buildings.obj`.

### Test Full Pipeline

```bash
python tests/test_pipeline.py
```

Complete pipeline: terrain + buildings merged. Expected: 162k vertices, 322k faces. Exports to `temp/scene.obj`.

## API Documentation

Once running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI app + routes
│   ├── generator.py          # Main mesh generation pipeline
│   ├── terrain.py            # Terrain mesh generation
│   ├── buildings.py          # Building extrusion
│   ├── fetchers/
│   │   ├── mapbox.py         # Mapbox Terrain-RGB API
│   │   └── overpass.py       # OSM data via Overpass API
│   └── utils/
│       ├── coords.py         # Coordinate transformations
│       └── mesh.py           # Mesh utilities
├── tests/
│   ├── test_mapbox.py        # Test Mapbox terrain fetcher
│   ├── test_overpass.py      # Test Overpass building fetcher
│   ├── test_terrain.py       # Test terrain mesh generation
│   ├── test_buildings.py     # Test building extrusion
│   └── test_pipeline.py      # Test full pipeline (terrain + buildings)
├── requirements.txt
└── temp/                     # Temporary file storage
```

## Development Status

### ✅ Completed (Days 1-2)

- FastAPI project structure with CORS, validation, health checks
- **Mapbox Terrain-RGB fetcher**
  - Multi-tile fetching and stitching
  - RGB→elevation decoding
  - Tested: 131k elevation points for 0.74 km² SF area
- **Overpass API building fetcher**
  - OSM building queries with way/relation parsing
  - Height/level/type metadata extraction
  - Tested: 1081 buildings with 87% height coverage
- **Terrain mesh generation**
  - Elevation grid → 3D mesh with coordinate transformation
  - Triangle face generation, origin centering
  - Tested: 131k vertices, 260k triangles, exports to .obj
- **Building extrusion**
  - 2D footprints → 3D boxes with height estimation
  - Bottom/top/wall face generation, coordinate transformation
  - Tested: 1081 buildings, 100% success rate, 31k vertices
- **Full pipeline integration** (Days 3-4 complete)
  - End-to-end: bbox → terrain + buildings → merged OBJ
  - Coordinate system alignment, mesh centering
  - Tested: 162k vertices, 322k faces, 25MB OBJ export

### ⚠️ Known Issues & Standards

**IMPORTANT:** See `STANDARDS.md` for detailed specifications.

- **Bbox size requirements**: Minimum 1km × 1km, recommended 1.5-2km × 2km, maximum 5km × 5km
- **Unit standard**: 1 OBJ unit = 1 real-world meter (no scaling)
- **Terrain bbox cropping**: Mapbox tiles not cropped to exact bbox. Small areas (<1km) show vertical exaggeration.
- **Overpass API timeouts**: OSM Overpass API can timeout under load. Retry with increased timeout or test without buildings.

### 🚧 Next Steps

- Frontend (Next.js + Leaflet map interface)
- API integration with FastAPI backend
- Material/texture support

### 📋 TODO

- Mesh merging and optimization
- OBJ/MTL export
- Error handling and validation
- Testing with real coordinates
