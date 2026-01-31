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
    print("COORDINATE TRACE DIAGNOSTIC")
    print("=" * 80)
    print()
    
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
    
    print(f"TEST AREA:")
    print(f"  center: {center_lat}, {center_lon}")
    print(f"  bbox: N={north:.6f}, S={south:.6f}, E={east:.6f}, W={west:.6f}")
    print()
    
    # ============================================================================
    # STEP 1: FETCH MAPBOX ELEVATION DATA
    # ============================================================================
    print("-" * 80)
    print("STEP 1: MAPBOX ELEVATION FETCH")
    print("-" * 80)
    
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("ERROR: MAPBOX_ACCESS_TOKEN not found in .env")
        return
    
    fetcher = MapboxTerrainFetcher(mapbox_token, smoothing_sigma=1.0)
    elevation_data, metadata = fetcher.fetch_elevation(north, south, east, west, zoom=12)
    
    rows, cols = elevation_data.shape
    print(f"elevation array shape: {rows} rows x {cols} cols")
    print()
    
    # probe corners and center
    print("ELEVATION DATA LAYOUT:")
    print(f"  [0, 0] (top-left):     {elevation_data[0, 0]:.2f}m")
    print(f"  [0, {cols-1}] (top-right):    {elevation_data[0, cols-1]:.2f}m")
    print(f"  [{rows-1}, 0] (bottom-left):  {elevation_data[rows-1, 0]:.2f}m")
    print(f"  [{rows-1}, {cols-1}] (bottom-right): {elevation_data[rows-1, cols-1]:.2f}m")
    print(f"  [{rows//2}, {cols//2}] (center):      {elevation_data[rows//2, cols//2]:.2f}m")
    print()
    
    print("QUESTION: What lat/lon does [0, 0] correspond to?")
    print("  Mapbox tiles are typically ordered:")
    print("    - Rows: North -> South (top to bottom)")
    print("    - Cols: West -> East (left to right)")
    print("  So [0, 0] should be the NORTHWEST corner")
    print(f"  Expected: lat={north:.6f}, lon={west:.6f}")
    print()
    
    # ============================================================================
    # STEP 2: TERRAIN GENERATION
    # ============================================================================
    print("-" * 80)
    print("STEP 2: TERRAIN MESH GENERATION")
    print("-" * 80)
    
    terrain_gen = TerrainGenerator()
    bounds = (west, south, east, north)
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    print(f"terrain mesh vertices: {len(terrain_mesh.vertices)}")
    print(f"terrain mesh faces: {len(terrain_mesh.faces)}")
    print()
    
    # probe vertices
    vertices = terrain_mesh.vertices
    print("TERRAIN MESH VERTEX LAYOUT:")
    print(f"  vertex 0: x={vertices[0, 0]:.2f}, y={vertices[0, 1]:.2f}, z={vertices[0, 2]:.2f}")
    print(f"  vertex {cols-1}: x={vertices[cols-1, 0]:.2f}, y={vertices[cols-1, 1]:.2f}, z={vertices[cols-1, 2]:.2f}")
    print(f"  vertex {(rows-1)*cols}: x={vertices[(rows-1)*cols, 0]:.2f}, y={vertices[(rows-1)*cols, 1]:.2f}, z={vertices[(rows-1)*cols, 2]:.2f}")
    print(f"  vertex {rows*cols-1}: x={vertices[rows*cols-1, 0]:.2f}, y={vertices[rows*cols-1, 1]:.2f}, z={vertices[rows*cols-1, 2]:.2f}")
    print()
    
    # check what terrain.py does
    print("TERRAIN.PY LOGIC CHECK:")
    print(f"  Line 49: lats = np.linspace(south, north, rows)")
    print(f"           -> lats[0] = {south:.6f} (SOUTH)")
    print(f"           -> lats[-1] = {north:.6f} (NORTH)")
    print(f"  Line 50: lons = np.linspace(west, east, cols)")
    print(f"           -> lons[0] = {west:.6f} (WEST)")
    print(f"           -> lons[-1] = {east:.6f} (EAST)")
    print()
    print("  Line 51: lon_grid, lat_grid = np.meshgrid(lons, lats)")
    print("           meshgrid creates:")
    print("           - lat_grid[0, 0] = lats[0] = SOUTH")
    print("           - lon_grid[0, 0] = lons[0] = WEST")
    print(f"           So grid[0, 0] = (lat={south:.6f}, lon={west:.6f}) = SOUTHWEST corner")
    print()
    print("  BUT elevation_data[0, 0] from Mapbox is NORTHWEST corner!")
    print("  ⚠️  POTENTIAL MISMATCH: elevation array vs lat/lon grid ordering")
    print()
    
    # verify coordinate transform
    transformer = CoordinateTransformer(center_lat, center_lon)
    
    print("COORDINATE TRANSFORM VERIFICATION:")
    x_center, z_center = transformer.latlon_to_local(center_lat, center_lon)
    print(f"  center ({center_lat:.6f}, {center_lon:.6f}) -> x={x_center:.2f}, z={z_center:.2f}")
    print(f"  expected: x=0.00, z=0.00")
    print()
    
    x_north, z_north = transformer.latlon_to_local(north, center_lon)
    print(f"  north ({north:.6f}, {center_lon:.6f}) -> x={x_north:.2f}, z={z_north:.2f}")
    print(f"  expected: x≈0, z>0 (north is positive Z)")
    print()
    
    x_east, z_east = transformer.latlon_to_local(center_lat, east)
    print(f"  east ({center_lat:.6f}, {east:.6f}) -> x={x_east:.2f}, z={z_east:.2f}")
    print(f"  expected: x>0 (but coords.py negates it!), z≈0")
    print()
    
    # check vertex 0 transform
    # terrain.py creates vertex 0 from lat_grid[0,0], lon_grid[0,0]
    # which is (south, west) after the meshgrid
    x_v0, z_v0 = transformer.latlon_to_local(south, west)
    print(f"  vertex 0 should be at ({south:.6f}, {west:.6f})")
    print(f"  transformed: x={x_v0:.2f}, z={z_v0:.2f}")
    print(f"  actual mesh: x={vertices[0, 0]:.2f}, z={vertices[0, 2]:.2f}")
    print(f"  match: {np.isclose(x_v0, vertices[0, 0], atol=1.0) and np.isclose(z_v0, vertices[0, 2], atol=1.0)}")
    print()
    
    # ============================================================================
    # STEP 3: BUILDING FETCH AND PLACEMENT
    # ============================================================================
    print("-" * 80)
    print("STEP 3: BUILDING FETCH AND PLACEMENT")
    print("-" * 80)
    
    overpass = OverpassFetcher(timeout=30)
    print("fetching buildings from OSM...")
    building_data = overpass.fetch_buildings(north, south, east, west)
    print(f"found {len(building_data)} buildings")
    print()
    
    if len(building_data) == 0:
        print("⚠️  No buildings found in this area. Try a different bbox with known buildings.")
        print()
    else:
        # pick first building
        building = building_data[0]
        coords = building["coordinates"]
        
        # calculate centroid
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroid_lat = np.mean(lats)
        centroid_lon = np.mean(lons)
        
        print(f"BUILDING 0 (id={building['id']}):")
        print(f"  centroid: lat={centroid_lat:.6f}, lon={centroid_lon:.6f}")
        print(f"  type: {building['building_type']}")
        print(f"  height: {building.get('height', 'estimated')}")
        print()
        
        # transform to local coords
        x_building, z_building = transformer.latlon_to_local(centroid_lat, centroid_lon)
        print(f"  transformed: x={x_building:.2f}, z={z_building:.2f}")
        print()
        
        # sample terrain at this location
        extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
        elevation = extruder._sample_terrain_elevation(x_building, z_building)
        
        print(f"TERRAIN SAMPLING:")
        print(f"  querying terrain at x={x_building:.2f}, z={z_building:.2f}")
        print(f"  returned elevation: {elevation if elevation is not None else 'None (out of bounds)'}")
        print()
        
        if elevation is None:
            print("⚠️  Building is outside terrain grid!")
            print("     This means the grid lookup failed.")
            print()
            
            # debug grid params
            if extruder.grid_params:
                p = extruder.grid_params
                print("  GRID PARAMETERS:")
                print(f"    origin_x: {p['origin_x']:.2f}")
                print(f"    origin_z: {p['origin_z']:.2f}")
                print(f"    dx_per_col: {p['dx_per_col']:.2f}")
                print(f"    dz_per_row: {p['dz_per_row']:.2f}")
                print(f"    rows: {p['rows']}, cols: {p['cols']}")
                print()
                
                # calculate grid indices
                col_f = (x_building - p['origin_x']) / p['dx_per_col']
                row_f = (z_building - p['origin_z']) / p['dz_per_row']
                print(f"  GRID LOOKUP:")
                print(f"    col_f: {col_f:.2f} (valid: 0 to {p['cols']-1})")
                print(f"    row_f: {row_f:.2f} (valid: 0 to {p['rows']-1})")
                print()
                
                if col_f < 0 or col_f > p['cols']-1:
                    print("    ❌ col_f out of bounds")
                if row_f < 0 or row_f > p['rows']-1:
                    print("    ❌ row_f out of bounds")
        else:
            print(f"  ✅ Elevation sampled successfully: {elevation:.2f}m")
            print()
            
            # compare with expected elevation from raw data
            # we need to figure out which cell this corresponds to
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
                    print(f"  RAW ELEVATION DATA:")
                    print(f"    elevation_data[{row_idx}, {col_idx}] = {raw_elevation:.2f}m")
                    print(f"    interpolated from terrain: {elevation:.2f}m")
                    print(f"    difference: {abs(elevation - raw_elevation):.2f}m")
                    print()
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Key questions to answer:")
    print("1. Does elevation_data[0, 0] correspond to NW or SW corner?")
    print("2. Does terrain.py's linspace ordering match Mapbox's data ordering?")
    print("3. Does the coordinate transform correctly map lat/lon to x/z?")
    print("4. Does the building grid lookup use the correct x/z to row/col mapping?")
    print()
    print("Save this output to backend/docs/coordinate_trace_output.txt")
    print("Then analyze the mismatches to find the root cause.")
    print()

if __name__ == "__main__":
    trace_pipeline()
