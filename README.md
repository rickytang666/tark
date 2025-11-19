<div align="center">
    <h1>Tark</h1>
    <p>Turn any real-world location into a game-ready 3D mesh.</p>
    <p>Select any area on a map, get terrain + buildings as a textured .obj file. Drop it into Unity, Unreal, or Blender.</p>
</div>

---

## What It Does

Tark generates 3D meshes from real-world geographic data:

- **Terrain**: Elevation data from Mapbox Terrain-RGB (30m resolution)
- **Buildings**: Footprints from OpenStreetMap, extruded to realistic heights
- **Textures**: Satellite imagery automatically mapped to terrain
- **Scale**: 1:1 metric scale (1 unit = 1 meter)

Perfect for game prototyping, urban planning visualization, or creating realistic environments based on actual locations.

## How It Works

1. **Select Area**: Draw a rectangle on the map (1-5km per side)
2. **Generate**: Backend fetches elevation data and building footprints
3. **Process**: Generates terrain mesh, extrudes buildings, applies textures
4. **Download**: Get a .zip with .obj, .mtl, and texture files
5. **Import**: Drag the .obj into your game engine

The entire process takes 30-120 seconds depending on area size.

## Tech Stack

**Frontend:**

- Next.js +Tailwind CSS
- Leaflet for map selection

**Backend:**

- FastAPI
- Trimesh for mesh generation
- NumPy + SciPy for terrain processing
- PyProj for coordinate transformations

**Data Sources:**

- Mapbox Terrain-RGB API (elevation data)
- OpenStreetMap via Overpass API (buildings)
- Mapbox Static API (satellite imagery)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Mapbox API token (get free tier: https://account.mapbox.com/access-tokens/)

### Backend Setup

```bash
cd backend
./setup.sh
# edit .env and add your MAPBOX_ACCESS_TOKEN
source venv/bin/activate
python -m app.main
```

backend runs at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

frontend runs at `http://localhost:3000`

### Using the App

1. Open `http://localhost:3000`
2. Hold Shift + drag to select an area (1-5km recommended)
3. Choose quality level (medium is default)
4. Click "Generate Mesh"
5. Download the .zip file

## Importing to Unity

⚠️ **Currently optimized for Unity. Blender/Unreal support is experimental.**

1. Extract the downloaded .zip file
2. Drag the `.obj` file into Unity's Assets folder
3. Textures load automatically
4. Scale is already correct (1 unit = 1 meter)

See `docs/unity.md` for detailed import guide.

## Area Guidelines

- **Minimum**: 1km × 1km (prevents terrain distortion)
- **Recommended**: 2km × 2km (best balance of detail and performance)
- **Maximum**: 5km × 5km (prevents timeout/memory issues)

Smaller areas may have unrealistic vertical exaggeration due to Mapbox tile behavior.
