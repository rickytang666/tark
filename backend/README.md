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
│   └── test_overpass.py      # Test Overpass building fetcher
├── requirements.txt
└── temp/                     # Temporary file storage
```

## Development Status

### ✅ Completed

- FastAPI project structure
- Basic API endpoints
- Module scaffolding
- **Mapbox Terrain-RGB fetcher**
  - Tile fetching, stitching, RGB→elevation decoding
  - Tested: 131k elevation points for 0.74 km² area
- **Overpass API building fetcher**
  - OSM building queries, polygon parsing
  - Height/level/type extraction
  - Tested: 1081 buildings with 87% height coverage

### 🚧 In Progress

- Terrain mesh generation
- Building extrusion

### 📋 TODO

- Mesh merging and optimization
- OBJ/MTL export
- Error handling and validation
- Testing with real coordinates
