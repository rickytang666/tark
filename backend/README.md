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
# Make sure .env is configured with your MAPBOX_ACCESS_TOKEN
python tests/test_mapbox.py
```

This will fetch elevation data for a small area near San Francisco and verify the fetcher works correctly.

Expected output:

```
🗺️  Testing Mapbox Terrain-RGB Fetcher

📍 Fetching elevation data for: ...
⏳ Fetching tiles from Mapbox...
✅ Successfully fetched elevation data!

📊 Results:
   Array shape: (256, 512)
   Tiles fetched: 2
   Min elevation: -1.50 meters
   Max elevation: 282.20 meters
   ...
✅ All tests passed!
```

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
│   └── test_overpass.py      # Test Overpass building fetcher (coming soon)
├── requirements.txt
└── temp/                     # Temporary file storage
```

## Development Status

### ✅ Completed

- FastAPI project structure
- Basic API endpoints
- Module scaffolding
- **Mapbox Terrain-RGB fetcher** (fully functional)
  - Lat/lon to tile coordinate conversion
  - Multi-tile fetching and stitching
  - RGB to elevation decoding
  - Metadata generation

### 🚧 In Progress

- Overpass API building fetcher
- Terrain mesh generation
- Building extrusion

### 📋 TODO

- Mesh merging and optimization
- OBJ/MTL export
- Error handling and validation
- Testing with real coordinates
