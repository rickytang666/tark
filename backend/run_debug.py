"""
debug runner for backend 2.0
runs the mesh generator on a small area (central park, ny)
enables debug mode to export separate layers
"""
import os
import sys

# Add the current directory to python path so we can import 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.generator import MeshGenerator

def run_debug():
    # Use environment variable or a placeholder if just testing logic
    token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    
    # 1. Setup
    output_dir = os.path.join(os.getcwd(), "debug_output")
    print(f"📂 Debug Output Directory: {output_dir}")
    
    generator = MeshGenerator(
        temp_dir=output_dir,
        mapbox_token=token
    )
    
    # 2. Define Area (Central Park South - Small Patch)
    # 40.7681° N, 73.9749° W
    center_lat = 40.7681
    center_lon = -73.9749
    
    # Create a small bbox (approx 500m x 500m)
    # 0.005 degrees is roughly 500m
    delta = 0.0025
    north = center_lat + delta
    south = center_lat - delta
    east = center_lon + delta
    west = center_lon - delta
    
    print(f"🗺️  Area: {north:.4f}N, {west:.4f}W to {south:.4f}S, {east:.4f}E")
    
    # 3. Modify this to True to actually hit APIs (requires valid token)
    # consistently fail if token is fake, but logic will run until fetch
    print("⚠️  Note: Ensure MAPBOX_ACCESS_TOKEN is set in environment for real data.")
    
    try:
        obj, mtl, textures = generator.generate(
            north=north,
            south=south,
            east=east,
            west=west,
            include_buildings=True,
            include_textures=True,
            zoom_level=14, # Higher zoom for better detail
            debug=True # <--- ENABLE DEBUG MODE
        )
        print(f"\n🎉 Success! Output at: {obj}")
        print(f"🔍 check {output_dir}/debug_terrain_only.obj")
        print(f"🔍 check {output_dir}/debug_buildings_only.obj")
        
    except Exception as e:
        print(f"\n❌ Error (Expected if no token): {e}")
    
    print("\n📂 Output Directory Contents:")
    for f in os.listdir(output_dir):
        print(f"   - {f}")

if __name__ == "__main__":
    run_debug()
