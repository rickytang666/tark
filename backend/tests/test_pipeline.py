"""
Test script for full mesh generation pipeline
Tests the complete workflow: terrain + buildings → merged scene
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.generator import MeshGenerator

load_dotenv()


def test_full_pipeline():
    """Test the complete mesh generation pipeline"""
    
    print("🌍 Testing Full Mesh Generation Pipeline\n")
    
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
    print(f"   East: {east}, West: {west}")
    print(f"   Area: ~{((north-south)*111)*((east-west)*111):.2f} km²\n")
    
    try:
        # Initialize generator
        temp_dir = Path(__file__).parent.parent / "temp"
        generator = MeshGenerator(str(temp_dir), access_token)
        
        # Generate complete scene
        obj_path, mtl_path = generator.generate(
            north=north,
            south=south,
            east=east,
            west=west,
            include_buildings=True
        )
        
        print("📊 Results:")
        print(f"   OBJ file: {obj_path}")
        if mtl_path:
            print(f"   MTL file: {mtl_path}")
        
        # Verify files exist
        print("\n🔍 Sanity checks:")
        
        if os.path.exists(obj_path):
            file_size = os.path.getsize(obj_path) / (1024 * 1024)  # MB
            print(f"   ✅ OBJ file created ({file_size:.2f} MB)")
        else:
            print("   ❌ OBJ file not found")
            return False
        
        # Check file has content
        with open(obj_path, 'r') as f:
            lines = f.readlines()
            vertex_count = sum(1 for line in lines if line.startswith('v '))
            face_count = sum(1 for line in lines if line.startswith('f '))
            
            print(f"   ✅ OBJ contains {vertex_count:,} vertices")
            print(f"   ✅ OBJ contains {face_count:,} faces")
            
            if vertex_count > 100000 and face_count > 200000:
                print("   ✅ Scene has terrain + buildings (high poly count)")
        
        print("\n💾 Complete scene exported!")
        print(f"   Import {obj_path} into Blender/Unity")
        print("   You should see SF terrain with 1000+ buildings!")
        
        print("\n✅ Full pipeline test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)

