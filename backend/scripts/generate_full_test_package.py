"""
generate full test package with terrain, buildings, textures, and materials

creates complete zip package like the production pipeline
"""
import sys
import os
import json
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.generator import MeshGenerator
from dotenv import load_dotenv

load_dotenv()

def generate_full_package():
    """generate full test package"""
    
    # load test config
    config_path = Path(__file__).parent.parent / "tests" / "fixtures" / "test_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    test_area = config["test_area"]
    bbox = test_area["bbox"]
    
    print("=" * 80)
    print("GENERATING FULL TEST PACKAGE")
    print("=" * 80)
    print()
    print(f"area: {test_area['name']}")
    print(f"  bbox: N={bbox['north']:.6f}, S={bbox['south']:.6f}")
    print(f"        E={bbox['east']:.6f}, W={bbox['west']:.6f}")
    print()
    print("this will generate:")
    print("  - terrain mesh with satellite texture")
    print("  - buildings with materials")
    print("  - complete .zip package")
    print()
    
    # check for mapbox token
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("ERROR: MAPBOX_ACCESS_TOKEN not found in .env")
        return
    
    # create generator
    temp_dir = Path(__file__).parent.parent / "temp"
    generator = MeshGenerator(str(temp_dir), mapbox_token)
    
    print("generating...")
    print()
    
    # generate (using the actual generate method signature)
    zip_path = generator.generate(
        north=bbox["north"],
        south=bbox["south"],
        east=bbox["east"],
        west=bbox["west"],
        include_buildings=True,
        include_textures=True,
        zoom_level=12,
        texture_max_dimension=1024
    )
    
    print()
    print("=" * 80)
    print("✅ GENERATION COMPLETE")
    print("=" * 80)
    print()
    print(f"package saved: {zip_path}")
    print()
    print("to test in unity:")
    print("  1. extract the zip file")
    print("  2. drag the .obj file into unity assets")
    print("  3. textures should load automatically")
    print()
    print("verify:")
    print("  - terrain has satellite imagery texture")
    print("  - buildings are grey/concrete color")
    print("  - buildings sit on terrain (minor clipping ok)")
    print("  - north is north, coordinates correct")

if __name__ == "__main__":
    generate_full_package()
