import pytest
import numpy as np
import trimesh
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.buildings import BuildingExtruder
from app.terrain import TerrainGenerator
from app.utils.coords import CoordinateTransformer

def test_coordinate_alignment_synthetic():
    """Test that terrain and buildings line up using synthetic data"""
    
    # Define a shared center
    center_lat = 43.0
    center_lon = -80.0
    
    # create bounds centered on this
    # +/- 0.01 degrees is roughly +/- 1km
    bounds = (center_lon - 0.01, center_lat - 0.01, center_lon + 0.01, center_lat + 0.01)
    
    # 1. Create flat terrain at y=0
    # 20x20 grid
    elevation_data = np.zeros((20, 20)) 
    
    # Pass explicit transformer to terrain generator?
    # TerrainGenerator doesn't accept a transformer in __init__, but it creates one inside generate_mesh.
    # It centers on the bounds center.
    # Our bounds center is exactly (center_lat, center_lon).
    
    terrain_gen = TerrainGenerator()
    terrain_mesh = terrain_gen.generate_mesh(
        elevation_data, 
        bounds, 
        resolution=100
    )
    
    # 2. Extract a "building" at the exact center
    # The center of the bounds is (center_lat, center_lon).
    # In local coords, this should be (0,0).
    
    building_data = [{
        "id": 1,
        "type": "way",
        "coordinates": [
            [center_lon - 0.0001, center_lat - 0.0001],
            [center_lon + 0.0001, center_lat - 0.0001],
            [center_lon + 0.0001, center_lat + 0.0001],
            [center_lon - 0.0001, center_lat + 0.0001],
            [center_lon - 0.0001, center_lat - 0.0001]
        ],
        "building_type": "box",
        "height": 10.0,
        "levels": 1,
        "tags": {}
    }]
    
    extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
    building_meshes = extruder.extrude_buildings(building_data)
    
    assert len(building_meshes) == 1
    b_mesh = building_meshes[0]
    
    # Check bounds of building mesh
    # It should be centered around (0,0) in X-Z plane
    min_x, min_y, min_z = b_mesh.bounds[0]
    max_x, max_y, max_z = b_mesh.bounds[1]
    
    # X and Z should be symmetric around 0
    # e.g. -5 to 5
    assert np.isclose((min_x + max_x) / 2, 0.0, atol=1.0)
    assert np.isclose((min_z + max_z) / 2, 0.0, atol=1.0)
    
    # Verify it sits on terrain (y=0)
    assert np.isclose(min_y, 0.0, atol=0.1)

def test_manual_coordinate_check():
    """Verify raw coordinate math"""
    center_lat = 43.0
    center_lon = -80.0
    transformer = CoordinateTransformer(center_lat, center_lon)
    
    # Center should transform to (0,0)
    x, z = transformer.latlon_to_local(center_lat, center_lon)
    assert np.isclose(x, 0.0)
    assert np.isclose(z, 0.0)
    
    # Point to the North (lat + 0.01)
    # roughly 1111 meters
    x_n, z_n = transformer.latlon_to_local(center_lat + 0.01, center_lon)
    # Longitude is same (x should be 0 or small error)
    # Latitude increased (z should be positive ~1111m)
    # The transformer returns (x=easting, y=northing) usually?
    # Let's check CoordinateTransformer implementation if accessible, or assume standard.
    # Usually: lat increase -> northing increase (y or z depending on system).
    
    assert np.isclose(x_n, 0.0, atol=1.0)
    assert z_n > 1000.0  # Should be around 1111m
    
    # Point to East (lon + 0.01)
    x_e, z_e = transformer.latlon_to_local(center_lat, center_lon + 0.01)
    assert x_e > 0.0
    assert np.isclose(z_e, 0.0, atol=1.0)
