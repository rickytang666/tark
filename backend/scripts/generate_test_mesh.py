"""
generate minimal test mesh for unity verification

creates terrain + buildings obj without textures for fast testing
"""
import sys
import os
import json
from pathlib import Path
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.overpass import OverpassFetcher
from app.buildings import BuildingExtruder
from app.terrain import TerrainGenerator
from dotenv import load_dotenv

load_dotenv()

def generate_test_mesh():
    """generate minimal test mesh"""
    
    # load test config
    config_path = Path(__file__).parent.parent / "tests" / "fixtures" / "test_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    test_area = config["test_area"]
    bbox = test_area["bbox"]
    center_lat = test_area["center_lat"]
    center_lon = test_area["center_lon"]
    
    print(f"generating test mesh: {test_area['name']}")
    print(f"  bbox: N={bbox['north']:.6f}, S={bbox['south']:.6f}")
    print(f"        E={bbox['east']:.6f}, W={bbox['west']:.6f}")
    print()
    
    # load elevation data
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    elevation_data = np.load(fixtures_dir / "test_elevation_data.npy")
    
    # 1. generate terrain
    print("[1/3] generating terrain...")
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(
        elevation_data, 
        bounds, 
        resolution=30.0,
        generate_uvs=False  # skip uvs for faster generation
    )
    print(f"  terrain: {len(terrain_mesh.vertices)} vertices, {len(terrain_mesh.faces)} faces")
    print()
    
    # 2. fetch buildings
    print("[2/3] fetching buildings...")
    overpass = OverpassFetcher(timeout=30)
    building_data = overpass.fetch_buildings(
        bbox["north"],
        bbox["south"],
        bbox["east"],
        bbox["west"]
    )
    print(f"  found {len(building_data)} buildings")
    print()
    
    # 3. flatten terrain under buildings (optional - set to True to enable)
    flatten_terrain = False
    
    if flatten_terrain:
        print("[3/5] flattening terrain under buildings...")
        extruder_temp = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
        footprints = extruder_temp.get_building_footprints_for_flattening(building_data)
        print(f"  flattening {len(footprints)} building footprints...")
        terrain_mesh = terrain_gen.flatten_building_footprints(terrain_mesh, footprints)
        print(f"  terrain flattened")
        print()
    
    # 4. extrude buildings
    print(f"[{4 if flatten_terrain else 3}/{5 if flatten_terrain else 3}] extruding buildings...")
    extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
    building_meshes = extruder.extrude_buildings(building_data, min_height=3.0)
    
    # filter out None values
    valid_building_meshes = [m for m in building_meshes if m is not None]
    print(f"  extruded {len(valid_building_meshes)} buildings")
    print()
    
    # 5. combine
    print(f"[{5 if flatten_terrain else 4}/{5 if flatten_terrain else 3}] combining meshes...")
    all_meshes = [terrain_mesh] + valid_building_meshes
    combined_mesh = trimesh.util.concatenate(all_meshes)
    print(f"  combined: {len(combined_mesh.vertices)} vertices, {len(combined_mesh.faces)} faces")
    print()
    
    # 6. export
    output_dir = Path(__file__).parent.parent / "temp"
    output_dir.mkdir(exist_ok=True)
    output_name = "test_mesh_flattened.obj" if flatten_terrain else "test_mesh.obj"
    output_path = output_dir / output_name
    
    combined_mesh.export(output_path)
    
    print(f"✅ saved: {output_path}")
    print()
    if flatten_terrain:
        print("TERRAIN FLATTENING ENABLED")
        print("  terrain has been flattened under each building footprint")
        print("  buildings should sit on flat pads (no clipping)")
        print()
    print("import to unity:")
    print(f"  1. drag {output_path.name} into unity assets")
    print("  2. verify:")
    print("     - terrain is not upside down")
    print("     - buildings are on terrain (not floating/sinking)")
    print("     - north is north (buildings in correct positions)")
    if flatten_terrain:
        print("     - buildings sit on flat foundations (no weird bumps underneath)")
    print()
    
    # print bounds for reference
    bounds = combined_mesh.bounds
    print("mesh bounds:")
    print(f"  x: {bounds[0][0]:.2f} to {bounds[1][0]:.2f} ({bounds[1][0] - bounds[0][0]:.2f}m)")
    print(f"  y: {bounds[0][1]:.2f} to {bounds[1][1]:.2f} ({bounds[1][1] - bounds[0][1]:.2f}m)")
    print(f"  z: {bounds[0][2]:.2f} to {bounds[1][2]:.2f} ({bounds[1][2] - bounds[0][2]:.2f}m)")

if __name__ == "__main__":
    generate_test_mesh()
