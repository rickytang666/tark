"""
Test script for terrain texture generation
Tests satellite image fetching and UV mapping
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.textures import MapboxSatelliteFetcher
from app.terrain import TerrainGenerator
from app.fetchers.mapbox import MapboxTerrainFetcher
import numpy as np

load_dotenv()


def test_satellite_fetch():
    """Test satellite image fetching"""
    
    print("🛰️  Testing Satellite Image Fetching\n")
    
    # Get Mapbox token
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return False
    
    # Test area: University of Waterloo (small area)
    north = 43.475
    south = 43.470
    east = -80.535
    west = -80.545
    
    print(f"📍 Test area:")
    print(f"   North: {north}, South: {south}")
    print(f"   East: {east}, West: {west}\n")
    
    try:
        # Initialize satellite fetcher
        fetcher = MapboxSatelliteFetcher(access_token)
        
        # Fetch satellite image
        temp_dir = Path(__file__).parent.parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        output_path = str(temp_dir / "test_terrain_texture.png")
        
        image, saved_path = fetcher.fetch_satellite_image(
            north=north, south=south, east=east, west=west,
            width=512, height=512,
            output_path=output_path
        )
        
        print(f"\n📊 Results:")
        print(f"   Image size: {image.size}")
        print(f"   Image mode: {image.mode}")
        print(f"   Saved to: {saved_path}")
        
        # Verify file exists
        if os.path.exists(saved_path):
            file_size = os.path.getsize(saved_path) / 1024  # KB
            print(f"   File size: {file_size:.2f} KB")
            print(f"\n✅ Satellite image fetch successful!")
            return True
        else:
            print(f"\n❌ Image file not found")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_terrain_uvs():
    """Test terrain UV coordinate generation"""
    
    print("\n\n🗺️  Testing Terrain UV Generation\n")
    
    # Get Mapbox token
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return False
    
    # Test area
    north = 43.475
    south = 43.470
    east = -80.535
    west = -80.545
    
    try:
        # 1. Fetch elevation data
        print("⏳ Fetching elevation data...")
        mapbox_fetcher = MapboxTerrainFetcher(access_token)
        elevation_data, metadata = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        print(f"✅ Elevation data: {elevation_data.shape}\n")
        
        # 2. Generate terrain mesh with UVs
        print("⏳ Generating terrain mesh with UVs...")
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=True
        )
        
        print(f"\n📊 Results:")
        print(f"   Vertices: {len(terrain_mesh.vertices):,}")
        print(f"   Faces: {len(terrain_mesh.faces):,}")
        
        # Check UV coordinates
        if hasattr(terrain_mesh.visual, 'uv'):
            uvs = terrain_mesh.visual.uv
            print(f"   UV coordinates: {len(uvs):,}")
            print(f"   UV shape: {uvs.shape}")
            print(f"   UV range: U=[{uvs[:, 0].min():.3f}, {uvs[:, 0].max():.3f}], V=[{uvs[:, 1].min():.3f}, {uvs[:, 1].max():.3f}]")
            
            # Verify UVs are in valid range
            if (uvs[:, 0].min() >= 0 and uvs[:, 0].max() <= 1 and
                uvs[:, 1].min() >= 0 and uvs[:, 1].max() <= 1):
                print(f"\n✅ UV coordinates are valid (0-1 range)!")
                return True
            else:
                print(f"\n❌ UV coordinates out of range")
                return False
        else:
            print(f"\n❌ Mesh has no UV coordinates")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_textured_terrain_export():
    """Test exporting terrain mesh with texture"""
    
    print("\n\n📦 Testing Textured Terrain Export\n")
    
    # Get Mapbox token
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return False
    
    # Test area
    north = 43.475
    south = 43.470
    east = -80.535
    west = -80.545
    
    try:
        temp_dir = Path(__file__).parent.parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 1. Fetch satellite texture
        print("⏳ Fetching satellite texture...")
        satellite_fetcher = MapboxSatelliteFetcher(access_token)
        texture_path = str(temp_dir / "test_terrain_texture.png")
        _, saved_texture = satellite_fetcher.fetch_satellite_image(
            north=north, south=south, east=east, west=west,
            width=512, height=512,
            output_path=texture_path
        )
        
        # 2. Fetch elevation
        print("⏳ Fetching elevation data...")
        mapbox_fetcher = MapboxTerrainFetcher(access_token)
        elevation_data, _ = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        
        # 3. Generate terrain with UVs
        print("⏳ Generating terrain mesh with UVs...")
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=True
        )
        
        # 4. Export to OBJ
        print("⏳ Exporting to OBJ...")
        output_path = str(temp_dir / "test_terrain_textured.obj")
        terrain_mesh.export(output_path, file_type='obj', include_normals=True)
        
        print(f"\n📊 Results:")
        print(f"   OBJ file: {output_path}")
        print(f"   Texture file: {saved_texture}")
        
        # Verify files exist
        if os.path.exists(output_path):
            obj_size = os.path.getsize(output_path) / 1024  # KB
            print(f"   OBJ size: {obj_size:.2f} KB")
            
            # Check if OBJ has texture coordinates (vt lines)
            with open(output_path, 'r') as f:
                lines = f.readlines()
                vt_count = sum(1 for line in lines if line.startswith('vt '))
                print(f"   Texture coords in OBJ: {vt_count:,}")
                
                if vt_count > 0:
                    print(f"\n✅ Textured terrain export successful!")
                    print(f"   Import {output_path} into Blender with texture!")
                    return True
                else:
                    print(f"\n❌ OBJ has no texture coordinates")
                    return False
        else:
            print(f"\n❌ OBJ file not created")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TERRAIN TEXTURE TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Satellite image fetching
    results.append(("Satellite Fetch", test_satellite_fetch()))
    
    # Test 2: UV coordinate generation
    results.append(("UV Generation", test_terrain_uvs()))
    
    # Test 3: Textured terrain export
    results.append(("Textured Export", test_textured_terrain_export()))
    
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

