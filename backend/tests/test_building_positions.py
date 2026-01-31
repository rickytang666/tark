"""
test building cardinal positions

verifies that buildings maintain correct cardinal directions:
- buildings to the north have higher z coordinates
- buildings to the east have lower x coordinates (due to negation)
- buildings to the south have lower z coordinates
- buildings to the west have higher x coordinates
"""
import pytest
import numpy as np
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.overpass import OverpassFetcher
from app.buildings import BuildingExtruder
from app.terrain import TerrainGenerator
from app.utils.coords import CoordinateTransformer


def load_test_data():
    """load test config and elevation data"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    
    with open(fixtures_dir / "test_config.json") as f:
        config = json.load(f)
    
    elevation_data = np.load(fixtures_dir / "test_elevation_data.npy")
    
    return config["test_area"], elevation_data


def test_building_cardinal_directions():
    """
    test that buildings maintain correct cardinal positions
    
    if building A is north of building B in real world,
    then building A should have higher z coordinate in mesh
    """
    test_area, elevation_data = load_test_data()
    bbox = test_area["bbox"]
    center_lat = test_area["center_lat"]
    center_lon = test_area["center_lon"]
    
    # generate terrain for elevation sampling
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    # fetch buildings
    overpass = OverpassFetcher(timeout=30)
    building_data = overpass.fetch_buildings(
        bbox["north"],
        bbox["south"],
        bbox["east"],
        bbox["west"]
    )
    
    if len(building_data) < 4:
        pytest.skip(f"not enough buildings for cardinal test (need 4, got {len(building_data)})")
    
    print(f"\nfound {len(building_data)} buildings")
    
    # calculate centroids for all buildings
    building_positions = []
    for building in building_data:
        coords = building["coordinates"]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroid_lat = np.mean(lats)
        centroid_lon = np.mean(lons)
        
        building_positions.append({
            "id": building["id"],
            "lat": centroid_lat,
            "lon": centroid_lon,
            "type": building["building_type"]
        })
    
    # sort buildings by latitude and longitude to find extremes
    sorted_by_lat = sorted(building_positions, key=lambda b: b["lat"])
    sorted_by_lon = sorted(building_positions, key=lambda b: b["lon"])
    
    # pick buildings from different corners
    southmost = sorted_by_lat[0]
    northmost = sorted_by_lat[-1]
    westmost = sorted_by_lon[0]
    eastmost = sorted_by_lon[-1]
    
    print("\nTEST BUILDINGS:")
    print(f"  southmost: id={southmost['id']}, lat={southmost['lat']:.6f}")
    print(f"  northmost: id={northmost['id']}, lat={northmost['lat']:.6f}")
    print(f"  westmost:  id={westmost['id']}, lon={westmost['lon']:.6f}")
    print(f"  eastmost:  id={eastmost['id']}, lon={eastmost['lon']:.6f}")
    print()
    
    # transform to mesh coordinates
    transformer = CoordinateTransformer(center_lat, center_lon)
    
    south_x, south_z = transformer.latlon_to_local(southmost["lat"], southmost["lon"])
    north_x, north_z = transformer.latlon_to_local(northmost["lat"], northmost["lon"])
    west_x, west_z = transformer.latlon_to_local(westmost["lat"], westmost["lon"])
    east_x, east_z = transformer.latlon_to_local(eastmost["lat"], eastmost["lon"])
    
    print("MESH COORDINATES:")
    print(f"  southmost: x={south_x:.2f}, z={south_z:.2f}")
    print(f"  northmost: x={north_x:.2f}, z={north_z:.2f}")
    print(f"  westmost:  x={west_x:.2f}, z={west_z:.2f}")
    print(f"  eastmost:  x={east_x:.2f}, z={east_z:.2f}")
    print()
    
    # TEST 1: north-south axis (z coordinate)
    print("TEST 1: NORTH-SOUTH AXIS")
    print(f"  northmost building z ({north_z:.2f}) > southmost building z ({south_z:.2f})?")
    assert north_z > south_z, (
        f"north-south axis inverted: "
        f"northmost building (lat={northmost['lat']:.6f}) has z={north_z:.2f}, "
        f"southmost building (lat={southmost['lat']:.6f}) has z={south_z:.2f}. "
        f"expected north_z > south_z"
    )
    print(f"  ✓ PASS: north is higher z ({north_z:.2f} > {south_z:.2f})")
    print()
    
    # TEST 2: east-west axis (x coordinate)
    # note: x is negated in coords.py, so east (higher lon) should have LOWER x
    print("TEST 2: EAST-WEST AXIS")
    print(f"  eastmost lon: {eastmost['lon']:.6f}, x={east_x:.2f}")
    print(f"  westmost lon: {westmost['lon']:.6f}, x={west_x:.2f}")
    print(f"  eastmost building x ({east_x:.2f}) < westmost building x ({west_x:.2f})?")
    print(f"  (x is negated, so higher longitude = lower x)")
    
    assert east_x < west_x, (
        f"east-west axis inverted: "
        f"eastmost building (lon={eastmost['lon']:.6f}) has x={east_x:.2f}, "
        f"westmost building (lon={westmost['lon']:.6f}) has x={west_x:.2f}. "
        f"expected east_x < west_x (due to negation)"
    )
    print(f"  ✓ PASS: east is lower x ({east_x:.2f} < {west_x:.2f})")
    print()


def test_buildings_sit_on_terrain():
    """
    test that buildings are placed at correct terrain elevation
    not floating or sinking
    """
    test_area, elevation_data = load_test_data()
    bbox = test_area["bbox"]
    center_lat = test_area["center_lat"]
    center_lon = test_area["center_lon"]
    
    # generate terrain
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    # fetch buildings
    overpass = OverpassFetcher(timeout=30)
    building_data = overpass.fetch_buildings(
        bbox["north"],
        bbox["south"],
        bbox["east"],
        bbox["west"]
    )
    
    if len(building_data) == 0:
        pytest.skip("no buildings found in test area")
    
    # extrude buildings
    extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
    building_meshes = extruder.extrude_buildings(building_data, min_height=3.0)
    
    print(f"\ngenerated {len(building_meshes)} building meshes")
    
    # check each building
    transformer = CoordinateTransformer(center_lat, center_lon)
    misplaced = []
    
    for i, (building, mesh) in enumerate(zip(building_data, building_meshes)):
        if mesh is None:
            continue
        
        # get building centroid in lat/lon
        coords = building["coordinates"]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroid_lat = np.mean(lats)
        centroid_lon = np.mean(lons)
        
        # transform to mesh coordinates
        x, z = transformer.latlon_to_local(centroid_lat, centroid_lon)
        
        # sample terrain elevation at this position
        terrain_elevation = extruder._sample_terrain_elevation(x, z)
        
        if terrain_elevation is None:
            continue  # building outside terrain bounds
        
        # get building base elevation (minimum y)
        building_base = np.min(mesh.vertices[:, 1])
        
        # check if building sits on terrain
        diff = abs(building_base - terrain_elevation)
        
        if diff > 1.0:  # tolerance: 1 meter
            # debug: also check what elevation the building THINKS it used
            # by looking at the mesh metadata or recalculating
            misplaced.append({
                "id": building["id"],
                "centroid": (centroid_lat, centroid_lon),
                "mesh_pos": (x, z),
                "terrain_elevation": terrain_elevation,
                "building_base": building_base,
                "building_height": np.max(mesh.vertices[:, 1]) - building_base,
                "diff": diff
            })
    
    if misplaced:
        print(f"\nFOUND {len(misplaced)} MISPLACED BUILDINGS:")
        for b in misplaced[:5]:
            print(f"  id={b['id']}: terrain={b['terrain_elevation']:.2f}m, "
                  f"base={b['building_base']:.2f}m, height={b['building_height']:.2f}m, diff={b['diff']:.2f}m")
            print(f"    position: x={b['mesh_pos'][0]:.2f}, z={b['mesh_pos'][1]:.2f}")
        if len(misplaced) > 5:
            print(f"  ... and {len(misplaced) - 5} more")
    
    total_buildings = len(building_meshes)
    correct_buildings = total_buildings - len(misplaced)
    accuracy = correct_buildings / total_buildings * 100 if total_buildings > 0 else 0
    
    print(f"\nBUILDING PLACEMENT ACCURACY:")
    print(f"  total buildings: {total_buildings}")
    print(f"  correctly placed: {correct_buildings}")
    print(f"  misplaced: {len(misplaced)}")
    print(f"  accuracy: {accuracy:.1f}%")
    
    assert len(misplaced) == 0, (
        f"{len(misplaced)} buildings are not sitting on terrain correctly. "
        f"they are floating or sinking."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
