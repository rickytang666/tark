# GeoMesh Backend

FastAPI backend for generating game-ready 3D meshes from real-world locations.

## Setup

1. **Create virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

**Note:** We removed `rasterio` from requirements for now since it requires GDAL system dependencies. For the MVP, we'll decode Mapbox Terrain-RGB tiles directly using Pillow, which is simpler and sufficient for our needs.

3. **Configure environment:**

```bash
cp .env.example .env
# Edit .env and add your Mapbox access token
```

4. **Run development server:**

```bash
python -m app.main
# Or use uvicorn directly:
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

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
├── requirements.txt
└── temp/                     # Temporary file storage
```

## Development Status

### ✅ Completed

- FastAPI project structure
- Basic API endpoints
- Module scaffolding

### 🚧 In Progress

- Mapbox Terrain-RGB fetcher
- Overpass API building fetcher
- Terrain mesh generation
- Building extrusion

### 📋 TODO

- Mesh merging and optimization
- OBJ/MTL export
- Error handling and validation
- Testing with real coordinates
