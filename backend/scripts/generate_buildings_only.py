"""
generate buildings-only obj file for inspection

creates a mesh with only buildings (no terrain) so you can
verify building positions in unity without terrain clutter
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

def generate_buildings_only():
    """generate buildings-only obj file"""
    
    # load test config
    config_path = Path(__file__).parent.parent / "tests" / "fixtures" / "test_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    test_area = config["test_area"]
    bbox = test_area["bbox"]
    center_lat = test_area["center_lat"]
    center_lon = test_area["center_lon"]
    
    print(f"generating buildings for: {test_area['name']}")
    print(f"  bbox: N={bbox['north']}, S={bbox['south']}, E={bbox['east']}, W={bbox['west']}")
    print()
    
    # load elevation data for terrain (needed for building placement)
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    elevation_data = np.load(fixtures_dir / "test_elevation_data.npy")
    
    # generate terrain mesh (for elevation sampling only, won't be exported)
    print("generating terrain mesh for elevation sampling...")
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    print(f"  terrain: {len(terrain_mesh.vertices)} vertices")
    print()
    
    # fetch buildings
    print("fetching buildings from OSM...")
    overpass = OverpassFetcher(timeout=30)
    building_data = overpass.fetch_buildings(
        bbox["north"],
        bbox["south"],
        bbox["east"],
        bbox["west"]
    )
    print(f"  found {len(building_data)} buildings")
    print()
    
    if len(building_data) == 0:
        print("no buildings found in this area")
        return
    
    # extrude buildings
    print("extruding buildings...")
    extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
    building_meshes = extruder.extrude_buildings(building_data, min_height=3.0)
    
    # filter out None values (failed buildings)
    valid_building_meshes = [m for m in building_meshes if m is not None]
    print(f"  extruded {len(valid_building_meshes)} buildings")
    print()
    
    # combine all building meshes
    if len(valid_building_meshes) == 0:
        print("no valid building meshes generated")
        return
    
    print("combining building meshes...")
    combined_mesh = trimesh.util.concatenate(valid_building_meshes)
    print(f"  combined: {len(combined_mesh.vertices)} vertices, {len(combined_mesh.faces)} faces")
    print()
    
    # save to obj
    output_dir = Path(__file__).parent.parent / "temp"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "buildings_only.obj"
    
    combined_mesh.export(output_path)
    print(f"saved: {output_path}")
    print()
    
    # print building statistics
    print("BUILDING STATISTICS:")
    bounds = combined_mesh.bounds
    print(f"  x range: {bounds[0][0]:.2f} to {bounds[1][0]:.2f}")
    print(f"  y range: {bounds[0][1]:.2f} to {bounds[1][1]:.2f}")
    print(f"  z range: {bounds[0][2]:.2f} to {bounds[1][2]:.2f}")
    print()
    
    # save building metadata for testing
    metadata = {
        "num_buildings": len(building_data),
        "num_meshes": len(building_meshes),
        "bounds": {
            "x_min": float(bounds[0][0]),
            "x_max": float(bounds[1][0]),
            "y_min": float(bounds[0][1]),
            "y_max": float(bounds[1][1]),
            "z_min": float(bounds[0][2]),
            "z_max": float(bounds[1][2])
        },
        "buildings": []
    }
    
    # record first few buildings for reference
    for i, building in enumerate(building_data[:10]):
        coords = building["coordinates"]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroid_lat = np.mean(lats)
        centroid_lon = np.mean(lons)
        
        metadata["buildings"].append({
            "id": building["id"],
            "type": building["building_type"],
            "centroid_lat": float(centroid_lat),
            "centroid_lon": float(centroid_lon)
        })
    
    metadata_path = fixtures_dir / "test_buildings_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"saved metadata: {metadata_path}")
    print()
    print("import buildings_only.obj to unity to verify positions")

if __name__ == "__main__":
    generate_buildings_only()
