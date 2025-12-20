import pytest
import numpy as np
import trimesh
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.buildings import BuildingExtruder
from app.terrain import TerrainGenerator

@pytest.fixture
def center_coords():
    return 43.4723, -80.5449

@pytest.fixture
def simple_building_data(center_coords):
    lat, lon = center_coords
    # Small square building around center
    return [{
        "id": 1,
        "type": "way",
        "coordinates": [
            [lon, lat],
            [lon + 0.0001, lat],
            [lon + 0.0001, lat + 0.0001],
            [lon, lat + 0.0001],
            [lon, lat]  # Close loop
        ],
        "building_type": "residential",
        "height": 10.0,
        "levels": 3,
        "tags": {}
    }]

def test_extrude_simple_building(center_coords, simple_building_data):
    """Test extruding a building without terrain"""
    lat, lon = center_coords
    extruder = BuildingExtruder(lat, lon, terrain_mesh=None)
    
    meshes = extruder.extrude_buildings(simple_building_data)
    
    assert len(meshes) == 1
    mesh = meshes[0]
    assert isinstance(mesh, trimesh.Trimesh)
    
    # Check vertex count. A box has 8 vertices, but triangulation might split faces.
    # At minimum > 0
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    
    # Check height (approx)
    # y-min should be 0 (no terrain)
    # y-max should be 10 (height)
    y_vals = mesh.vertices[:, 1]
    assert np.isclose(y_vals.min(), 0.0, atol=0.1)
    assert np.isclose(y_vals.max(), 10.0, atol=0.1)

def test_extrude_with_terrain(center_coords, simple_building_data):
    """Test extruding a building on top of terrain"""
    lat, lon = center_coords
    
    # Create simple flat terrain at elevation 50m
    elevation_data = np.full((10, 10), 50.0)
    # Bounds surrounding the building
    bounds = (lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01)
    
    terrain_gen = TerrainGenerator()
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=100)
    # Be careful: TerrainGenerator generates Y-up vertices.
    # We should NOT manually center it here because BuildingExtruder expects absolute coords relative to its own transformer?
    # Wait, BuildingExtruder uses its own transformer.
    # And TerrainGenerator creates vertices based on ITS own transformer.
    # If we pass different center lat/lon to both, they won't align.
    # But TerrainGenerator calculates its own center from bounds.
    # BuildingExtruder takes explicit center.
    # To make them match, we should align them.
    
    # Let's inspect how they align.
    # TerrainGenerator center: mid of bounds.
    # Bounds: (lon-0.01, lat-0.01, lon+0.01, lat+0.01) -> center is (lat, lon) which matches our fixture.
    # So they should align perfectly.
    
    extruder = BuildingExtruder(lat, lon, terrain_mesh=terrain_mesh)
    meshes = extruder.extrude_buildings(simple_building_data)
    
    assert len(meshes) == 1
    mesh = meshes[0]
    
    # Check base elevation
    # Should be sitting on top of 50m terrain
    y_vals = mesh.vertices[:, 1]
    # Min y should be ~50
    assert np.isclose(y_vals.min(), 50.0, atol=1.0)
    # Max y should be ~60 (50 + 10 building height)
    assert np.isclose(y_vals.max(), 60.0, atol=1.0)

def test_estimate_height():
    ext = BuildingExtruder(0, 0)
    assert ext.estimate_height("residential", levels=5) == 17.5 # 5 * 3.5
    assert ext.estimate_height("commercial") == 15.0 # default
