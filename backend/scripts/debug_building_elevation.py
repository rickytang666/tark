"""
debug building elevation sampling

traces exactly what happens when we sample terrain elevation
for a specific building
"""
import sys
import os
import json
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.overpass import OverpassFetcher
from app.buildings import BuildingExtruder
from app.terrain import TerrainGenerator
from app.utils.coords import CoordinateTransformer
from dotenv import load_dotenv

load_dotenv()

def debug_building_elevation():
    """debug building elevation sampling"""
    
    # load test config
    config_path = Path(__file__).parent.parent / "tests" / "fixtures" / "test_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    test_area = config["test_area"]
    bbox = test_area["bbox"]
    center_lat = test_area["center_lat"]
    center_lon = test_area["center_lon"]
    
    # load elevation data
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    elevation_data = np.load(fixtures_dir / "test_elevation_data.npy")
    
    rows, cols = elevation_data.shape
    print(f"elevation data: {rows} x {cols}")
    print(f"  [0, 0] = {elevation_data[0, 0]:.2f}m (original NW corner)")
    print(f"  [{rows-1}, 0] = {elevation_data[rows-1, 0]:.2f}m (original SW corner)")
    print()
    
    # generate terrain
    print("generating terrain...")
    terrain_gen = TerrainGenerator()
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    terrain_mesh = terrain_gen.generate_mesh(elevation_data, bounds, resolution=30.0)
    
    vertices = terrain_mesh.vertices
    print(f"terrain mesh: {len(vertices)} vertices")
    print(f"  vertex 0: x={vertices[0, 0]:.2f}, y={vertices[0, 1]:.2f}, z={vertices[0, 2]:.2f}")
    print(f"  vertex {cols-1}: x={vertices[cols-1, 0]:.2f}, y={vertices[cols-1, 1]:.2f}, z={vertices[cols-1, 2]:.2f}")
    print(f"  vertex {(rows-1)*cols}: x={vertices[(rows-1)*cols, 0]:.2f}, y={vertices[(rows-1)*cols, 1]:.2f}, z={vertices[(rows-1)*cols, 2]:.2f}")
    print()
    
    # fetch buildings
    print("fetching buildings...")
    overpass = OverpassFetcher(timeout=30)
    building_data = overpass.fetch_buildings(
        bbox["north"],
        bbox["south"],
        bbox["east"],
        bbox["west"]
    )
    print(f"found {len(building_data)} buildings")
    print()
    
    # pick first building
    building = building_data[0]
    coords = building["coordinates"]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    centroid_lat = np.mean(lats)
    centroid_lon = np.mean(lons)
    
    print(f"BUILDING {building['id']}:")
    print(f"  centroid: lat={centroid_lat:.6f}, lon={centroid_lon:.6f}")
    print()
    
    # transform to mesh coordinates
    transformer = CoordinateTransformer(center_lat, center_lon)
    x, z = transformer.latlon_to_local(centroid_lat, centroid_lon)
    print(f"  mesh position: x={x:.2f}, z={z:.2f}")
    print()
    
    # initialize extruder
    extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh=terrain_mesh)
    
    # check grid params
    if extruder.grid_params:
        p = extruder.grid_params
        print("GRID PARAMETERS:")
        print(f"  origin: x={p['origin_x']:.2f}, z={p['origin_z']:.2f}")
        print(f"  dx_per_col: {p['dx_per_col']:.2f}")
        print(f"  dz_per_row: {p['dz_per_row']:.2f}")
        print(f"  rows: {p['rows']}, cols: {p['cols']}")
        print()
        
        # calculate grid indices
        col_f = (x - p['origin_x']) / p['dx_per_col']
        row_f = (z - p['origin_z']) / p['dz_per_row']
        
        print("GRID LOOKUP:")
        print(f"  col_f = (x - origin_x) / dx_per_col = ({x:.2f} - {p['origin_x']:.2f}) / {p['dx_per_col']:.2f} = {col_f:.2f}")
        print(f"  row_f = (z - origin_z) / dz_per_row = ({z:.2f} - {p['origin_z']:.2f}) / {p['dz_per_row']:.2f} = {row_f:.2f}")
        print()
        
        if 0 <= col_f <= p['cols']-1 and 0 <= row_f <= p['rows']-1:
            c0 = int(col_f)
            r0 = int(row_f)
            c0 = min(c0, p['cols'] - 2)
            r0 = min(r0, p['rows'] - 2)
            
            print(f"  grid cell: row={r0}, col={c0}")
            print()
            
            # get vertex indices
            cols_count = p['cols']
            idx00 = r0 * cols_count + c0
            idx10 = idx00 + 1
            idx01 = (r0 + 1) * cols_count + c0
            idx11 = idx01 + 1
            
            print("VERTEX INDICES:")
            print(f"  idx00 (r={r0}, c={c0}): {idx00}")
            print(f"  idx10 (r={r0}, c={c0+1}): {idx10}")
            print(f"  idx01 (r={r0+1}, c={c0}): {idx01}")
            print(f"  idx11 (r={r0+1}, c={c0+1}): {idx11}")
            print()
            
            # get elevations
            h00 = p['vertices'][idx00, 1]
            h10 = p['vertices'][idx10, 1]
            h01 = p['vertices'][idx01, 1]
            h11 = p['vertices'][idx11, 1]
            
            print("VERTEX ELEVATIONS:")
            print(f"  h00: {h00:.2f}m")
            print(f"  h10: {h10:.2f}m")
            print(f"  h01: {h01:.2f}m")
            print(f"  h11: {h11:.2f}m")
            print()
            
            # interpolate
            u = col_f - c0
            v = row_f - r0
            h_top = h00 * (1-u) + h10 * u
            h_bot = h01 * (1-u) + h11 * u
            interpolated = h_top * (1-v) + h_bot * v
            
            print("INTERPOLATION:")
            print(f"  u = {u:.3f}, v = {v:.3f}")
            print(f"  h_top = {h_top:.2f}m")
            print(f"  h_bot = {h_bot:.2f}m")
            print(f"  interpolated = {interpolated:.2f}m")
            print()
            
            # what should it be?
            # the building is at (centroid_lat, centroid_lon)
            # we need to find what elevation_data pixel that corresponds to
            
            # terrain.py does:
            # lats = linspace(south, north, rows)  -> lats[0] = south
            # lons = linspace(west, east, cols)    -> lons[0] = west
            # then meshgrid, then flatten
            # so vertex at row r, col c corresponds to:
            #   lat = south + r * (north - south) / (rows - 1)
            #   lon = west + c * (east - west) / (cols - 1)
            
            south = bbox["south"]
            north = bbox["north"]
            west_lon = bbox["west"]
            east_lon = bbox["east"]
            
            # what row/col in the lat/lon grid does this building correspond to?
            lat_frac = (centroid_lat - south) / (north - south)
            lon_frac = (centroid_lon - west_lon) / (east_lon - west_lon)
            
            lat_row = lat_frac * (rows - 1)
            lon_col = lon_frac * (cols - 1)
            
            print("EXPECTED FROM ELEVATION DATA:")
            print(f"  building lat: {centroid_lat:.6f}")
            print(f"  bbox: south={south:.6f}, north={north:.6f}")
            print(f"  lat_frac = (lat - south) / (north - south) = {lat_frac:.4f}")
            print(f"  lat_row in terrain grid = {lat_row:.2f}")
            print()
            print(f"  building lon: {centroid_lon:.6f}")
            print(f"  bbox: west={west_lon:.6f}, east={east_lon:.6f}")
            print(f"  lon_frac = (lon - west) / (east - west) = {lon_frac:.4f}")
            print(f"  lon_col in terrain grid = {lon_col:.2f}")
            print()
            
            # after flip, elevation_data is upside down
            # so elevation_data[0, :] corresponds to terrain row (rows-1)
            # and elevation_data[rows-1, :] corresponds to terrain row 0
            
            # terrain row r corresponds to elevation_data row (rows - 1 - r)
            elev_row = rows - 1 - int(lat_row)
            elev_col = int(lon_col)
            
            print(f"  terrain grid position: row={lat_row:.2f}, col={lon_col:.2f}")
            print(f"  after flip, elevation_data position: row={elev_row}, col={elev_col}")
            print(f"  elevation_data[{elev_row}, {elev_col}] = {elevation_data[elev_row, elev_col]:.2f}m")
            print()
            
            print("COMPARISON:")
            print(f"  sampled from terrain: {interpolated:.2f}m")
            print(f"  expected from elevation_data: {elevation_data[elev_row, elev_col]:.2f}m")
            print(f"  difference: {abs(interpolated - elevation_data[elev_row, elev_col]):.2f}m")
            
        else:
            print("  building outside grid bounds")

if __name__ == "__main__":
    debug_building_elevation()
