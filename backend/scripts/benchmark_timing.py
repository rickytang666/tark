"""
Benchmark script to measure actual mesh generation timing
Measures both total time (with API calls) and computation-only time
"""
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import trimesh
from app.generator import MeshGenerator
from app.fetchers.mapbox import MapboxTerrainFetcher
from app.fetchers.overpass import OverpassFetcher
from app.textures import MapboxSatelliteFetcher
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
from app.utils.mesh import merge_meshes, export_obj

load_dotenv()


def benchmark_full_pipeline():
    """Benchmark the complete pipeline including API calls"""
    
    print("⏱️  BENCHMARK: Full Pipeline (with API calls)\n")
    
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return None
    
    # Test area: University of Waterloo, Ontario (~1km × 1km)
    # Centered around same location, but half the size
    center_lat = 43.473611
    center_lon = -80.5377775
    # 1km ≈ 0.009 degrees latitude, adjusted for longitude at this latitude
    lat_offset = 0.0045  # ~0.5km
    lon_offset = 0.0045 / 0.731  # ~0.5km adjusted for latitude (cos(43.47°) ≈ 0.731)
    
    north = center_lat + lat_offset
    south = center_lat - lat_offset
    east = center_lon + lon_offset
    west = center_lon - lon_offset
    
    print(f"📍 Test area: ~1km × 1km")
    print(f"   North: {north}, South: {south}")
    print(f"   East: {east}, West: {west}\n")
    
    try:
        temp_dir = Path(__file__).parent.parent / "temp"
        generator = MeshGenerator(str(temp_dir), access_token)
        
        # Measure total time
        start_total = time.time()
        
        obj_path, mtl_path, texture_files = generator.generate(
            north=north,
            south=south,
            east=east,
            west=west,
            include_buildings=True,
            include_textures=True,
            zoom_level=12
        )
        
        elapsed_total = time.time() - start_total
        
        # Get mesh stats
        import trimesh
        mesh = trimesh.load(obj_path)
        
        print(f"\n📊 Results:")
        print(f"   Total time: {elapsed_total:.2f}s")
        print(f"   Vertices: {len(mesh.vertices):,}")
        print(f"   Faces: {len(mesh.faces):,}")
        print(f"   OBJ file: {os.path.getsize(obj_path) / (1024*1024):.2f} MB")
        
        return elapsed_total
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def benchmark_computation_only():
    """Benchmark computation time only (using cached/pre-fetched data)"""
    
    print("\n\n⏱️  BENCHMARK: Computation Only (excluding API calls)\n")
    
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return None
    
    # Test area: University of Waterloo, Ontario (~1km × 1km)
    # Centered around same location, but half the size
    center_lat = 43.473611
    center_lon = -80.5377775
    # 1km ≈ 0.009 degrees latitude, adjusted for longitude at this latitude
    lat_offset = 0.0045  # ~0.5km
    lon_offset = 0.0045 / 0.731  # ~0.5km adjusted for latitude (cos(43.47°) ≈ 0.731)
    
    north = center_lat + lat_offset
    south = center_lat - lat_offset
    east = center_lon + lon_offset
    west = center_lon - lon_offset
    
    try:
        temp_dir = Path(__file__).parent.parent / "temp"
        
        # Step 1: Fetch data (not timed)
        print("📥 Fetching data (not timed)...")
        mapbox_fetcher = MapboxTerrainFetcher(access_token, smoothing_sigma=1.5)
        elevation_data, elev_metadata = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        
        overpass_fetcher = OverpassFetcher(timeout=60)
        building_data = overpass_fetcher.fetch_buildings(
            north=north, south=south, east=east, west=west
        )
        
        satellite_fetcher = MapboxSatelliteFetcher(access_token)
        terrain_texture_path = os.path.join(temp_dir, "terrain_benchmark.png")
        satellite_fetcher.fetch_satellite_image(
            north=north, south=south, east=east, west=west,
            width=1024, height=1024,
            output_path=terrain_texture_path
        )
        
        print(f"   ✅ Data fetched: {elevation_data.shape[0]}x{elevation_data.shape[1]} elevation, {len(building_data)} buildings\n")
        
        # Step 2: Measure computation time only
        start_compute = time.time()
        
        # Terrain generation
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=True
        )
        
        # Center terrain
        terrain_centroid_xz = terrain_mesh.centroid.copy()
        terrain_centroid_xz[1] = 0
        terrain_mesh.vertices -= terrain_centroid_xz
        
        # Building extrusion
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        building_extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh)
        building_meshes = building_extruder.extrude_buildings(building_data, min_height=3.0)
        
        # Merge meshes
        meshes_to_merge = [terrain_mesh] + building_meshes
        final_mesh = merge_meshes(meshes_to_merge)
        
        # Center final mesh
        final_centroid_xz = final_mesh.centroid.copy()
        final_centroid_xz[1] = 0
        final_mesh.vertices -= final_centroid_xz
        
        # Apply texture
        from PIL import Image
        import numpy as np
        import trimesh
        if os.path.exists(terrain_texture_path):
            texture_image = Image.open(terrain_texture_path)
            terrain_vertex_count = len(terrain_mesh.vertices)
            final_vertex_count = len(final_mesh.vertices)
            final_uvs = np.zeros((final_vertex_count, 2))
            final_uvs[:terrain_vertex_count] = terrain_mesh.visual.uv
            final_mesh.visual = trimesh.visual.TextureVisuals(
                uv=final_uvs,
                image=texture_image
            )
        
        # Export
        output_path = os.path.join(temp_dir, "scene_benchmark")
        obj_path = export_obj(final_mesh, output_path, include_normals=True)
        
        elapsed_compute = time.time() - start_compute
        
        print(f"📊 Computation Results:")
        print(f"   Computation time: {elapsed_compute:.2f}s")
        print(f"   Vertices: {len(final_mesh.vertices):,}")
        print(f"   Faces: {len(final_mesh.faces):,}")
        print(f"   Buildings processed: {len(building_meshes)}")
        
        return elapsed_compute
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("="*60)
    print("🚀 MESH GENERATION TIMING BENCHMARK")
    print("="*60)
    
    # Run both benchmarks
    total_time = benchmark_full_pipeline()
    compute_time = benchmark_computation_only()
    
    print("\n" + "="*60)
    print("📈 SUMMARY")
    print("="*60)
    
    if total_time:
        print(f"Total time (with API calls): {total_time:.2f}s")
    if compute_time:
        print(f"Computation only: {compute_time:.2f}s")
        if total_time:
            api_time = total_time - compute_time
            print(f"API fetch time: {api_time:.2f}s")
            print(f"\n💡 Computation is {compute_time/total_time*100:.1f}% of total time")

