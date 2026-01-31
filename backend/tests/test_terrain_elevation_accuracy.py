"""
test terrain elevation accuracy

verifies that terrain mesh vertices have correct elevations
matching the source mapbox data
"""
import pytest
import numpy as np
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.terrain import TerrainGenerator
from app.utils.coords import CoordinateTransformer


def load_test_data():
    """load test elevation data and config"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    
    # load config
    with open(fixtures_dir / "test_config.json") as f:
        config = json.load(f)
    
    # load elevation data
    elevation_data = np.load(fixtures_dir / "test_elevation_data.npy")
    
    return config["test_area"], elevation_data


def test_terrain_corner_elevations():
    """
    test that terrain mesh corners have correct elevations
    from mapbox source data
    """
    test_area, elevation_data = load_test_data()
    bbox = test_area["bbox"]
    
    rows, cols = elevation_data.shape
    
    # generate terrain mesh
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    vertices = terrain_mesh.vertices
    
    # the key test: which corner of elevation_data corresponds to which vertex?
    # 
    # mapbox tiles are ordered: north->south (rows), west->east (cols)
    # so elevation_data[0, 0] should be NORTHWEST corner
    # 
    # terrain.py creates vertices row-by-row from meshgrid
    # vertex 0 should correspond to the FIRST lat/lon in the grid
    # 
    # terrain.py does: lats = linspace(south, north, rows)
    # so lats[0] = south, meaning vertex 0 is at SOUTH edge
    # 
    # if this is wrong, vertex 0 will have wrong elevation
    
    print("\nCORNER ELEVATION TEST:")
    print(f"elevation_data shape: {rows} x {cols}")
    print()
    
    # vertex 0: should be at (south, west) based on terrain.py logic
    print(f"vertex 0:")
    print(f"  position: x={vertices[0, 0]:.2f}, y={vertices[0, 1]:.2f}, z={vertices[0, 2]:.2f}")
    print(f"  elevation_data[0, 0] = {elevation_data[0, 0]:.2f}m (NW corner from mapbox)")
    print(f"  elevation_data[{rows-1}, 0] = {elevation_data[rows-1, 0]:.2f}m (SW corner from mapbox)")
    print(f"  vertex y-value: {vertices[0, 1]:.2f}m")
    
    # if terrain.py is correct, vertex 0 should match elevation_data[rows-1, 0] (SW)
    # if terrain.py is wrong, vertex 0 will match elevation_data[0, 0] (NW)
    
    matches_nw = np.isclose(vertices[0, 1], elevation_data[0, 0], atol=0.1)
    matches_sw = np.isclose(vertices[0, 1], elevation_data[rows-1, 0], atol=0.1)
    
    print(f"  matches NW corner: {matches_nw}")
    print(f"  matches SW corner: {matches_sw}")
    print()
    
    # vertex at top-right (col=cols-1, row=0)
    v_tr = vertices[cols - 1]
    print(f"vertex {cols-1} (top-right of grid):")
    print(f"  position: x={v_tr[0]:.2f}, y={v_tr[1]:.2f}, z={v_tr[2]:.2f}")
    print(f"  elevation_data[0, {cols-1}] = {elevation_data[0, cols-1]:.2f}m (NE corner from mapbox)")
    print(f"  elevation_data[{rows-1}, {cols-1}] = {elevation_data[rows-1, cols-1]:.2f}m (SE corner from mapbox)")
    print(f"  vertex y-value: {v_tr[1]:.2f}m")
    
    matches_ne = np.isclose(v_tr[1], elevation_data[0, cols-1], atol=0.1)
    matches_se = np.isclose(v_tr[1], elevation_data[rows-1, cols-1], atol=0.1)
    
    print(f"  matches NE corner: {matches_ne}")
    print(f"  matches SE corner: {matches_se}")
    print()
    
    # the test: vertex 0 should match SW corner (not NW)
    # because terrain.py starts from south
    assert matches_sw, (
        f"vertex 0 elevation mismatch: "
        f"expected {elevation_data[rows-1, 0]:.2f}m (SW corner), "
        f"got {vertices[0, 1]:.2f}m"
    )
    
    assert matches_se, (
        f"vertex {cols-1} elevation mismatch: "
        f"expected {elevation_data[rows-1, cols-1]:.2f}m (SE corner), "
        f"got {v_tr[1]:.2f}m"
    )


def test_terrain_all_vertices_match_mapbox():
    """
    test that ALL terrain vertices have correct elevations
    by sampling the mesh and comparing to source data
    """
    test_area, elevation_data = load_test_data()
    bbox = test_area["bbox"]
    
    rows, cols = elevation_data.shape
    
    # generate terrain mesh
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    vertices = terrain_mesh.vertices
    
    # verify every vertex matches its corresponding elevation pixel
    mismatches = []
    
    for row in range(rows):
        for col in range(cols):
            vertex_idx = row * cols + col
            vertex = vertices[vertex_idx]
            
            # what elevation should this vertex have?
            # terrain.py creates vertices from meshgrid of linspace(south, north)
            # so row 0 = south, row (rows-1) = north
            # but mapbox has row 0 = north, row (rows-1) = south
            # 
            # so we need to flip: mapbox_row = (rows - 1 - terrain_row)
            mapbox_row = (rows - 1 - row)
            expected_elevation = elevation_data[mapbox_row, col]
            actual_elevation = vertex[1]
            
            diff = abs(actual_elevation - expected_elevation)
            
            if diff > 0.1:  # tolerance for floating point
                mismatches.append({
                    "vertex_idx": vertex_idx,
                    "row": row,
                    "col": col,
                    "expected": expected_elevation,
                    "actual": actual_elevation,
                    "diff": diff
                })
    
    if mismatches:
        print(f"\nFOUND {len(mismatches)} ELEVATION MISMATCHES:")
        for i, m in enumerate(mismatches[:10]):  # show first 10
            print(f"  vertex {m['vertex_idx']} (row={m['row']}, col={m['col']}): "
                  f"expected {m['expected']:.2f}m, got {m['actual']:.2f}m, "
                  f"diff={m['diff']:.2f}m")
        if len(mismatches) > 10:
            print(f"  ... and {len(mismatches) - 10} more")
    
    # calculate stats
    total_vertices = rows * cols
    match_rate = (total_vertices - len(mismatches)) / total_vertices * 100
    
    print(f"\nELEVATION ACCURACY:")
    print(f"  total vertices: {total_vertices}")
    print(f"  matches: {total_vertices - len(mismatches)}")
    print(f"  mismatches: {len(mismatches)}")
    print(f"  accuracy: {match_rate:.2f}%")
    
    # test passes if all vertices match
    assert len(mismatches) == 0, (
        f"{len(mismatches)} vertices have incorrect elevations. "
        f"terrain mesh does not match mapbox source data."
    )


if __name__ == "__main__":
    # run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
