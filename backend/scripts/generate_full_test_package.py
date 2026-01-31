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
    print("generating full test package")
    print("=" * 80)
    print(f"\narea: {test_area['name']}")
    print(f"  bbox: N={bbox['north']:.6f}, S={bbox['south']:.6f}")
    print(f"        E={bbox['east']:.6f}, W={bbox['west']:.6f}")
    
    # check for mapbox token
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("\n\033[31merror:\033[0m MAPBOX_ACCESS_TOKEN not found in .env")
        return
    
    # create generator
    temp_dir = Path(__file__).parent.parent / "temp"
    generator = MeshGenerator(str(temp_dir), mapbox_token)
    
    # generate (using the actual generate method signature)
    obj_path, mtl_path, texture_files = generator.generate(
        north=bbox["north"],
        south=bbox["south"],
        east=bbox["east"],
        west=bbox["west"],
        include_buildings=True,
        include_textures=True,
        zoom_level=12,
        texture_max_dimension=1024
    )
    
    print("\n" + "=" * 80)
    print(f"\033[32mpackage saved:\033[0m {obj_path}")
    print("=" * 80)
    print("\nto test in unity:")
    print("  1. drag the .obj file into unity assets")
    print("  2. verify terrain texture and building placement")

if __name__ == "__main__":
    generate_full_package()
