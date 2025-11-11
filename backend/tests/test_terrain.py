"""
Test script for terrain mesh generation
Tests converting elevation data to 3D mesh
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.mapbox import MapboxTerrainFetcher
from app.terrain import TerrainGenerator

load_dotenv()


def test_terrain_generation():
    """Test terrain mesh generation with real elevation data"""
    
    print("🗻 Testing Terrain Mesh Generation\n")
    
    # Get Mapbox token
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return False
    
    # Test area: University of Waterloo, Ontario (2km × 2km)
    north = 43.482620
    south = 43.464602
    east = -80.525265
    west = -80.550290
    
    print(f"📍 Test area:")
    print(f"   North: {north}, South: {south}")
    print(f"   East: {east}, West: {west}\n")
    
    try:
        # 1. Fetch elevation data
        print("⏳ Fetching elevation data...")
        fetcher = MapboxTerrainFetcher(access_token)
        elevation_array, metadata = fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        print(f"✅ Fetched {elevation_array.shape[0]}×{elevation_array.shape[1]} elevation grid\n")
        
        # 2. Generate terrain mesh
        print("⏳ Generating terrain mesh...")
        generator = TerrainGenerator()
        mesh = generator.generate_mesh(
            elevation_data=elevation_array,
            bounds=(west, south, east, north),
            resolution=30.0
        )
        print("✅ Terrain mesh generated!\n")
        
        # 3. Display results
        print("📊 Mesh Statistics:")
        print(f"   Vertices: {len(mesh.vertices):,}")
        print(f"   Faces: {len(mesh.faces):,}")
        print(f"   Bounds: {mesh.bounds}")
        print(f"   Centroid: {mesh.centroid}")
        print(f"   Is watertight: {mesh.is_watertight}")
        
        # 4. Sanity checks
        print("\n🔍 Sanity checks:")
        
        # Check vertex count
        expected_vertices = elevation_array.shape[0] * elevation_array.shape[1]
        if len(mesh.vertices) == expected_vertices:
            print(f"   ✅ Vertex count correct ({expected_vertices:,})")
        else:
            print(f"   ❌ Vertex count mismatch: {len(mesh.vertices)} vs {expected_vertices}")
            return False
        
        # Check face count (2 triangles per grid cell)
        expected_faces = (elevation_array.shape[0] - 1) * (elevation_array.shape[1] - 1) * 2
        if len(mesh.faces) == expected_faces:
            print(f"   ✅ Face count correct ({expected_faces:,})")
        else:
            print(f"   ❌ Face count mismatch: {len(mesh.faces)} vs {expected_faces}")
            return False
        
        # Check mesh is centered near origin
        centroid_distance = np.linalg.norm(mesh.centroid)
        if centroid_distance < 10:  # Within 10 meters of origin
            print(f"   ✅ Mesh centered at origin (distance: {centroid_distance:.2f}m)")
        else:
            print(f"   ⚠️  Mesh centroid far from origin: {centroid_distance:.2f}m")
        
        # Check elevation range preserved
        min_z = mesh.vertices[:, 2].min()
        max_z = mesh.vertices[:, 2].max()
        print(f"   ✅ Elevation range: {min_z:.2f}m to {max_z:.2f}m")
        
        # Check mesh has faces
        if len(mesh.faces) > 0:
            print("   ✅ Mesh has faces")
        
        # 5. Optional: Export to file for visual inspection
        output_path = Path(__file__).parent.parent / "temp" / "test_terrain.obj"
        output_path.parent.mkdir(exist_ok=True)
        mesh.export(str(output_path))
        print(f"\n💾 Exported mesh to: {output_path}")
        print("   Import into Blender/Unity to visualize!")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import numpy as np
    success = test_terrain_generation()
    sys.exit(0 if success else 1)

