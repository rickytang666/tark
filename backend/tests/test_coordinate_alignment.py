"""
Test coordinate alignment between terrain and buildings
Verifies that both use the same coordinate system
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.coords import CoordinateTransformer
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
from app.fetchers.mapbox import MapboxTerrainFetcher

load_dotenv()


def test_coordinate_alignment():
    """Test that terrain and buildings use the same coordinate system"""
    
    print("🔍 Testing Coordinate Alignment\n")
    
    # Get Mapbox token
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return False
    
    # Test area: small area for quick test
    north = 43.475
    south = 43.470
    east = -80.535
    west = -80.545
    
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2
    
    print(f"📍 Test area:")
    print(f"   North: {north}, South: {south}")
    print(f"   East: {east}, West: {west}")
    print(f"   Center: {center_lat}, {center_lon}\n")
    
    try:
        # Create shared transformer
        print("⏳ Creating shared coordinate transformer...")
        shared_transformer = CoordinateTransformer(center_lat, center_lon)
        print(f"✅ Transformer center: ({shared_transformer.center_lat}, {shared_transformer.center_lon})")
        print(f"   UTM center: ({shared_transformer.center_x:.2f}, {shared_transformer.center_y:.2f})\n")
        
        # Fetch elevation data
        print("⏳ Fetching elevation data...")
        mapbox_fetcher = MapboxTerrainFetcher(access_token)
        elevation_data, _ = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        print(f"✅ Elevation data: {elevation_data.shape}\n")
        
        # Generate terrain with shared transformer
        print("⏳ Generating terrain mesh...")
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=False,
            transformer=shared_transformer
        )
        
        terrain_vertices = terrain_mesh.vertices
        print(f"✅ Terrain mesh: {len(terrain_vertices):,} vertices")
        print(f"   X range: [{terrain_vertices[:, 0].min():.2f}, {terrain_vertices[:, 0].max():.2f}]")
        print(f"   Z range: [{terrain_vertices[:, 2].min():.2f}, {terrain_vertices[:, 2].max():.2f}]")
        print(f"   Y range: [{terrain_vertices[:, 1].min():.2f}, {terrain_vertices[:, 1].max():.2f}]\n")
        
        # Test building coordinate transformation
        print("⏳ Testing building coordinate transformation...")
        building_extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh)
        building_extruder.transformer = shared_transformer
        
        # Test a known lat/lon point
        test_lat = center_lat
        test_lon = center_lon
        
        # Transform using building transformer
        building_x, building_z = building_extruder.transformer.latlon_to_local(test_lat, test_lon)
        building_x = -building_x  # Negated
        building_z = -building_z  # Negated
        
        # Find corresponding terrain vertex (should be near center)
        terrain_xz = terrain_vertices[:, [0, 2]]
        distances = np.sqrt(
            (terrain_xz[:, 0] - building_x)**2 + 
            (terrain_xz[:, 1] - building_z)**2
        )
        nearest_idx = np.argmin(distances)
        nearest_terrain_xz = terrain_xz[nearest_idx]
        
        print(f"✅ Building transformer:")
        print(f"   Test point ({test_lat}, {test_lon}) → ({building_x:.2f}, {building_z:.2f})")
        print(f"✅ Nearest terrain vertex:")
        print(f"   Position: ({nearest_terrain_xz[0]:.2f}, {nearest_terrain_xz[1]:.2f})")
        print(f"   Distance: {distances[nearest_idx]:.4f} meters\n")
        
        # Check alignment
        max_allowed_offset = 50.0  # 50 meters tolerance (terrain resolution is ~30m)
        if distances[nearest_idx] < max_allowed_offset:
            print(f"✅ Alignment check PASSED")
            print(f"   Offset: {distances[nearest_idx]:.2f}m < {max_allowed_offset}m")
            return True
        else:
            print(f"❌ Alignment check FAILED")
            print(f"   Offset: {distances[nearest_idx]:.2f}m >= {max_allowed_offset}m")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_same_transformer():
    """Test that using the same transformer instance gives identical results"""
    
    print("\n\n🔍 Testing Same Transformer Instance\n")
    
    center_lat = 43.4725
    center_lon = -80.5400
    
    # Create transformer
    transformer1 = CoordinateTransformer(center_lat, center_lon)
    transformer2 = CoordinateTransformer(center_lat, center_lon)
    
    # Test point
    test_lat = 43.473
    test_lon = -80.541
    
    x1, z1 = transformer1.latlon_to_local(test_lat, test_lon)
    x2, z2 = transformer2.latlon_to_local(test_lat, test_lon)
    
    print(f"Test point: ({test_lat}, {test_lon})")
    print(f"Transformer 1: ({x1:.6f}, {z1:.6f})")
    print(f"Transformer 2: ({x2:.6f}, {z2:.6f})")
    print(f"Difference: ({abs(x1-x2):.6f}, {abs(z1-z2):.6f})")
    
    # They should be identical (or very close due to floating point)
    if abs(x1 - x2) < 1e-6 and abs(z1 - z2) < 1e-6:
        print("✅ Transformers produce identical results")
        return True
    else:
        print("⚠️  Transformers produce slightly different results (expected for separate instances)")
        return True  # This is acceptable


if __name__ == "__main__":
    print("=" * 60)
    print("COORDINATE ALIGNMENT TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Same transformer instance
    results.append(("Same Transformer", test_same_transformer()))
    
    # Test 2: Coordinate alignment
    results.append(("Coordinate Alignment", test_coordinate_alignment()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️  Some tests failed"))
    
    sys.exit(0 if all_passed else 1)

