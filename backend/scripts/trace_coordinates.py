"""
coordinate tracing diagnostic script

traces a single coordinate through the entire pipeline to document
exactly what happens at each step with real data.

usage:
    python scripts/trace_coordinates.py
"""
import sys
import os
from pathlib import Path
import numpy as np

# add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.mapbox import MapboxTerrainFetcher
from app.fetchers.overpass import OverpassFetcher
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
from app.utils.coords import CoordinateTransformer
from dotenv import load_dotenv

# load env
load_dotenv()

def trace_pipeline():
    """trace coordinates through the full pipeline"""
    
    print("=" * 80)
    print("coordinate trace diagnostic")
    print("=" * 80)
    
    # test area: waterloo, canada (small area for fast testing)
    # adjust these to match an area you've actually tested
    center_lat = 43.4723
    center_lon = -80.5449
    
    # small bbox: ~500m x 500m
    offset = 0.0025  # roughly 250m
    north = center_lat + offset
    south = center_lat - offset
    east = center_lon + offset
    west = center_lon - offset
    
    print(f"\ntest area:")
    print(f"  center: {center_lat}, {center_lon}")
    print(f"  bbox: N={north:.6f}, S={south:.6f}, E={east:.6f}, W={west:.6f}")
    
    # ============================================================================
    # STEP 1: FETCH MAPBOX ELEVATION DATA
    # ============================================================================
    print("\n" + "-" * 80)
    print("step 1: mapbox elevation fetch")
    print("-" * 80)
    
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("\n\033[31merror:\033[0m MAPBOX_ACCESS_TOKEN not found in .env")
        return
    
    fetcher = MapboxTerrainFetcher(mapbox_token, smoothing_sigma=1.0)
    elevation_data, metadata = fetcher.fetch_elevation(north, south, east, west, zoom=12)
    
    rows, cols = elevation_data.shape
    print(f"elevation array: {rows} x {cols}")
    
    # probe corners and center
    print("\nelevation data layout:")
    print(f"  [0, 0] (top-left):     {elevation_data[0, 0]:.2f}m")
    print(f"  [0, {cols-1}] (top-right):    {elevation_data[0, cols-1]:.2f}m")
    print(f"  [{rows-1}, 0] (bottom-left):  {elevation_data[rows-1, 0]:.2f}m")
    print(f"  [{rows-1}, {cols-1}] (bottom-right): {elevation_data[rows-1, cols-1]:.2f}m")
    
    print("\nmapbox ordering: rows (N->S), cols (W->E)")
    print(f"  [0,0] = northwest corner (lat={north:.6f}, lon={west:.6f})")
    
    # ============================================================================
    # STEP 2: TERRAIN GENERATION
    # ============================================================================
    print("\n" + "-" * 80)
    print("step 2: terrain mesh generation")
    print("-" * 80)
    
    terrain_gen = TerrainGenerator()
    bounds = (west, south, east, north)
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    print(f"terrain mesh: {len(terrain_mesh.vertices)} vertices, {len(terrain_mesh.faces)} faces")
    
    # probe vertices
    vertices = terrain_mesh.vertices
    print("\nterrain mesh corners:")
    print(f"  vertex 0: x={vertices[0, 0]:.2f}, y={vertices[0, 1]:.2f}, z={vertices[0, 2]:.2f}")
    print(f"  vertex {cols-1}: x={vertices[cols-1, 0]:.2f}, y={vertices[cols-1, 1]:.2f}, z={vertices[cols-1, 2]:.2f}")
    print(f"  vertex {(rows-1)*cols}: x={vertices[(rows-1)*cols, 0]:.2f}, y={vertices[(rows-1)*cols, 1]:.2f}, z={vertices[(rows-1)*cols, 2]:.2f}")
    
    # check what terrain.py does
    print("\nterrain.py logic:")
    print(f"  lats = linspace(south, north) -> [0]={south:.6f}, [-1]={north:.6f}")
    print(f"  lons = linspace(west, east) -> [0]={west:.6f}, [-1]={east:.6f}")
    print(f"  meshgrid creates grid[0,0] = southwest corner")
    print(f"\n  \033[33mwarning:\033[0m elevation_data[0,0] is northwest, but grid[0,0] is southwest")
    print(f"  solution: np.flipud(elevation_data) in terrain.py")
    
    # verify coordinate transform
    transformer = CoordinateTransformer(center_lat, center_lon)
    
    print("\ncoordinate transform verification:")
    x_center, z_center = transformer.latlon_to_local(center_lat, center_lon)
    print(f"  center -> x={x_center:.2f}, z={z_center:.2f} (expected: 0, 0)")
    
    x_north, z_north = transformer.latlon_to_local(north, center_lon)
    print(f"  north  -> x={x_north:.2f}, z={z_north:.2f} (expected: 0, >0)")
    
    x_east, z_east = transformer.latlon_to_local(center_lat, east)
    print(f"  east   -> x={x_east:.2f}, z={z_east:.2f} (expected: >0, 0)")
    
    # check vertex 0 transform
    x_v0, z_v0 = transformer.latlon_to_local(south, west)
    print(f"\nvertex 0 (southwest):")
    print(f"  expected: x={x_v0:.2f}, z={z_v0:.2f}")
    print(f"  actual:   x={vertices[0, 0]:.2f}, z={vertices[0, 2]:.2f}")
    match = np.isclose(x_v0, vertices[0, 0], atol=1.0) and np.isclose(z_v0, vertices[0, 2], atol=1.0)
    print(f"  match: {match}")
    
    # ============================================================================
    # STEP 3: BUILDING FETCH AND PLACEMENT
    # ============================================================================
    print("\n" + "-" * 80)
    print("step 3: building fetch and placement")
    print("-" * 80)
    
    overpass = OverpassFetcher(timeout=30)
    building_data = overpass.fetch_buildings(north, south, east, west)
    print(f"found {len(building_data)} buildings")
    
    if len(building_data) == 0:
        print("\n\033[33mwarning:\033[0m no buildings found")
    else:
        # pick first building
        building = building_data[0]
        coords = building["coordinates"]
        
        # calculate centroid
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroid_lat = np.mean(lats)
        centroid_lon = np.mean(lons)
        
        print(f"\nbuilding 0 (id={building['id']}):")
        print(f"  centroid: lat={centroid_lat:.6f}, lon={centroid_lon:.6f}")
        print(f"  type: {building['building_type']}")
        
        # transform to local coords
        x_building, z_building = transformer.latlon_to_local(centroid_lat, centroid_lon)
        print(f"  mesh coords: x={x_building:.2f}, z={z_building:.2f}")
        
        # sample terrain at this location
        extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
        elevation = extruder._sample_terrain_elevation(x_building, z_building)
        
        print(f"\nterrain sampling:")
        print(f"  elevation at ({x_building:.2f}, {z_building:.2f}): {elevation if elevation is not None else 'None (out of bounds)'}")
        
        if elevation is None:
            print(f"  \033[31merror:\033[0m building outside terrain grid")
            
            if extruder.grid_params:
                p = extruder.grid_params
                col_f = (x_building - p['origin_x']) / p['dx_per_col']
                row_f = (z_building - p['origin_z']) / p['dz_per_row']
                print(f"  grid lookup: col={col_f:.2f}, row={row_f:.2f}")
                print(f"  valid range: col=[0, {p['cols']-1}], row=[0, {p['rows']-1}]")
                
                if col_f < 0 or col_f > p['cols']-1:
                    print(f"  \033[31merror:\033[0m col out of bounds")
                if row_f < 0 or row_f > p['rows']-1:
                    print(f"  \033[31merror:\033[0m row out of bounds")
        else:
            print(f"  \033[32msuccess:\033[0m elevation = {elevation:.2f}m")
            
            if extruder.grid_params:
                p = extruder.grid_params
                col_f = (x_building - p['origin_x']) / p['dx_per_col']
                row_f = (z_building - p['origin_z']) / p['dz_per_row']
                
                if 0 <= col_f <= p['cols']-1 and 0 <= row_f <= p['rows']-1:
                    row_idx = int(row_f)
                    col_idx = int(col_f)
                    row_idx = min(row_idx, rows-1)
                    col_idx = min(col_idx, cols-1)
                    
                    raw_elevation = elevation_data[row_idx, col_idx]
                    print(f"  raw data: elevation_data[{row_idx}, {col_idx}] = {raw_elevation:.2f}m")
                    print(f"  interpolated: {elevation:.2f}m")
                    print(f"  difference: {abs(elevation - raw_elevation):.2f}m")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("summary")
    print("=" * 80)
    print("\nkey checks:")
    print("1. elevation_data[0,0] = northwest corner (mapbox ordering)")
    print("2. terrain.py creates grid from southwest (linspace ordering)")
    print("3. solution: np.flipud(elevation_data) aligns the two")
    print("4. coordinate transform centers at (0,0) correctly")
    print("5. building grid lookup uses correct x/z to row/col mapping")

if __name__ == "__main__":
    trace_pipeline()
