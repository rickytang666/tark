# Tark Backend

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

Fetches elevation data for uwaterloo area. Expected: ~131k elevation points, 2 tiles.

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

Extrudes building footprints to 3D boxes with proper triangulation. Expected: 1211 buildings, 20k vertices. Exports to `temp/test_buildings.obj`.

### Test Full Pipeline

```bash
python tests/test_pipeline.py
```

Complete pipeline: terrain + buildings merged with proper elevation. Expected: 86k vertices, 166k faces. Exports to `temp/scene.obj`.

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

## status

### completed

- fastapi with cors, validation, health checks
- mapbox terrain-rgb fetcher (multi-tile stitching, rgb→elevation)
- overpass api building fetcher (osm ways/relations parsing)
- terrain mesh generation (131k vertices, 260k triangles)
- building extrusion with proper triangulation
  - parses ALL outer ways from relations (complex shapes preserved)
  - supports inner ways (courtyards/holes)
  - bounding box fallback for failed extrusions
  - 100% success rate with statistics tracking
- full pipeline: bbox → terrain + buildings → merged obj

### building shape accuracy fixes

**fixed issue**: buildings were losing complex shapes (L/U/H-shaped)

**root cause**: `overpass.py` only used first outer way from osm relations

**solution**:

- parse ALL outer ways → complex shapes preserved
- support inner ways → courtyards work
- bounding box fallback → no disappearing buildings
- statistics tracking → transparency

### known limitations

- bbox requirements: 1km × 1km minimum, 5km × 5km maximum
- unit: 1 obj unit = 1 meter
- osm data completeness varies by location
- overpass api can timeout (increase timeout if needed)

see `STANDARDS.md` and `ACCURACY_ANALYSIS.md` for details
