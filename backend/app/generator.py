"""
Main mesh generation pipeline
Orchestrates the entire process from bbox to 3D mesh
"""
from typing import Tuple, Optional, List, Callable
import os
import math
import time
import trimesh
from app.fetchers.mapbox import MapboxTerrainFetcher
from app.fetchers.overpass import OverpassFetcher
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
from app.textures import MapboxSatelliteFetcher
from app.utils.mesh import merge_meshes, export_obj


class MeshGenerator:
    """
    Orchestrates the mesh generation pipeline
    """
    
    def __init__(self, temp_dir: str, mapbox_token: str):
        """
        Initialize the mesh generator
        
        Args:
            temp_dir: Directory for temporary file storage
            mapbox_token: Mapbox API access token
        """
        self.temp_dir = temp_dir
        self.mapbox_token = mapbox_token
        os.makedirs(temp_dir, exist_ok=True)
    
    def generate(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        include_buildings: bool = True,
        include_textures: bool = True,
        zoom_level: int = 12,
        texture_max_dimension: int = 1280,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[str, Optional[str], List[str]]:
        """
        Generate mesh for the given bounding box
        
        Args:
            north: North latitude
            south: South latitude
            east: East longitude
            west: West longitude
            include_buildings: Whether to include buildings (default: True)
            include_textures: Whether to generate textures (default: True)
            zoom_level: Mapbox zoom level for terrain detail (default: 12)
            texture_max_dimension: Maximum texture dimension in pixels (default: 1280)
            progress_callback: Optional callback function(percent, message)
        
        Returns:
            Tuple of (obj_file_path, mtl_file_path, texture_file_paths)
        """
        start_time = time.time()
        print("\n" + "="*60)
        print("🚀 MESH GENERATION PIPELINE STARTED")
        print("="*60)
        print(f"📍 Area: {north:.4f}°N, {south:.4f}°S, {east:.4f}°E, {west:.4f}°W")
        print(f"🎯 Quality: Zoom {zoom_level}, Texture {texture_max_dimension}px")
        print("="*60 + "\n")
        
        if progress_callback:
            progress_callback(0, "Starting mesh generation...")
        
        # Calculate center for coordinate transformation
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        
        texture_files = []
        
        # 1. Fetch satellite texture (if textures enabled)
        terrain_texture_path = None
        if include_textures:
            print("[1/6] 📸 Fetching satellite imagery...")
            if progress_callback:
                progress_callback(5, "Fetching satellite imagery...")
            satellite_fetcher = MapboxSatelliteFetcher(self.mapbox_token)
            
            # Calculate aspect ratio of bounding box to fetch correct image dimensions
            # This prevents distortion from square texture on rectangular area
            lat_span = north - south
            lon_span = east - west
            
            # Convert to approximate meters for aspect ratio
            lat_meters = lat_span * 111000  # 1 degree lat ≈ 111km
            lon_meters = lon_span * 111000 * abs(math.cos(math.radians(center_lat)))
            
            # Calculate aspect ratio
            aspect_ratio = lon_meters / lat_meters if lat_meters > 0 else 1.0
            
            # Calculate image dimensions maintaining aspect ratio
            if aspect_ratio >= 1.0:
                # Wider than tall
                width = texture_max_dimension
                height = int(texture_max_dimension / aspect_ratio)
            else:
                # Taller than wide
                height = texture_max_dimension
                width = int(texture_max_dimension * aspect_ratio)
            
            terrain_texture_path = os.path.join(self.temp_dir, "terrain.png")
            try:
                _, saved_path = satellite_fetcher.fetch_satellite_image(
                    north=north, south=south, east=east, west=west,
                    width=width, height=height,
                    output_path=terrain_texture_path
                )
                if saved_path:
                    texture_files.append(saved_path)
                    print(f"      ✅ Saved texture: {width}x{height}px\n")
            except Exception as e:
                print(f"      ⚠️  Warning: Failed to fetch satellite imagery: {e}")
                print("      Continuing without terrain texture...\n")
                terrain_texture_path = None
        
        # 2. Fetch elevation data from Mapbox
        print(f"[2/6] 🏔️  Fetching elevation data (zoom {zoom_level})...")
        if progress_callback:
            progress_callback(15, "Fetching elevation data...")
        # Use smoothing_sigma=1.5 for good balance between noise reduction and feature preservation
        mapbox_fetcher = MapboxTerrainFetcher(self.mapbox_token, smoothing_sigma=1.5)
        elevation_data, elev_metadata = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=zoom_level
        )
        print(f"      ✅ Elevation grid: {elevation_data.shape[0]}x{elevation_data.shape[1]} points\n")
        
        # 3. Generate terrain mesh with UVs
        print("[3/6] 🗺️  Generating terrain mesh...")
        if progress_callback:
            progress_callback(35, "Generating terrain mesh...")
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=include_textures
        )
        print(f"      ✅ Terrain mesh: {len(terrain_mesh.vertices):,} vertices, {len(terrain_mesh.faces):,} faces")
        if include_textures and hasattr(terrain_mesh.visual, 'uv'):
            print(f"      ✅ UV coordinates: {len(terrain_mesh.visual.uv):,} points\n")
        else:
            print()
        
        # Center terrain X and Z BEFORE buildings sample elevations
        # This ensures buildings and terrain are in the same coordinate space
        terrain_centroid_xz = terrain_mesh.centroid.copy()
        terrain_centroid_xz[1] = 0  # Don't center Y - keep real elevations
        terrain_mesh.vertices -= terrain_centroid_xz
        print(f"      ℹ️  Centered terrain at origin (X: {terrain_centroid_xz[0]:.1f}m, Z: {terrain_centroid_xz[2]:.1f}m)\n")
        
        meshes_to_merge = [terrain_mesh]
        
        # 4. Fetch and extrude buildings (if requested)
        if include_buildings:
            print("[4/6] 🏢 Fetching building data from OpenStreetMap...")
            if progress_callback:
                progress_callback(55, "Fetching buildings from OSM...")
            overpass_fetcher = OverpassFetcher(timeout=60)
            building_data = overpass_fetcher.fetch_buildings(
                north=north, south=south, east=east, west=west
            )
            print(f"      ✅ Found {len(building_data)} buildings\n")
            
            if building_data:
                print("[5/6] 🏗️  Extruding buildings...")
                if progress_callback:
                    progress_callback(70, f"Extruding {len(building_data)} buildings...")
                # Pass terrain mesh so buildings can sit on terrain correctly
                # Don't pass offset - buildings and terrain use same coordinate transformer
                building_extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh)
                building_meshes = building_extruder.extrude_buildings(
                    building_data, min_height=3.0
                )
                print(f"      ✅ Created {len(building_meshes)} building meshes\n")
                
                if building_meshes:
                    meshes_to_merge.extend(building_meshes)
        else:
            print("[4-5/6] ⏭️  Skipping buildings...\n")
            if progress_callback:
                progress_callback(70, "Skipping buildings...")
        
        # 5. Merge all meshes
        print("[6/6] 🔧 Merging and finalizing mesh...")
        if progress_callback:
            progress_callback(85, "Merging meshes...")
        final_mesh = merge_meshes(meshes_to_merge)
        
        # Center the final merged mesh (terrain is already centered, but buildings aren't)
        final_centroid_xz = final_mesh.centroid.copy()
        final_centroid_xz[1] = 0  # Don't center Y
        final_mesh.vertices -= final_centroid_xz
        print(f"      ℹ️  Final offset: X: {final_centroid_xz[0]:.1f}m, Z: {final_centroid_xz[2]:.1f}m")
        
        print(f"      ✅ Final mesh: {len(final_mesh.vertices):,} vertices, {len(final_mesh.faces):,} faces\n")
        
        # 6. Export to OBJ with texture reference
        print("💾 Exporting to OBJ format...")
        if progress_callback:
            progress_callback(95, "Exporting to OBJ...")
        output_path = os.path.join(self.temp_dir, "scene")
        
        # If we have a terrain texture, set it in the mesh visual
        # Need to recreate TextureVisuals after merge since merge loses visual data
        if terrain_texture_path and os.path.exists(terrain_texture_path):
            from PIL import Image
            
            # Load the texture image
            texture_image = Image.open(terrain_texture_path)
            
            # Recreate visual with texture
            # Only the first mesh (terrain) has UVs, so we need to preserve those
            if hasattr(terrain_mesh.visual, 'uv') and terrain_mesh.visual.uv is not None:
                # Create UV array for final mesh (pad with zeros for building vertices)
                import numpy as np
                terrain_vertex_count = len(terrain_mesh.vertices)
                final_vertex_count = len(final_mesh.vertices)
                
                # Create UV array: terrain UVs + zeros for buildings
                final_uvs = np.zeros((final_vertex_count, 2))
                final_uvs[:terrain_vertex_count] = terrain_mesh.visual.uv
                
                # Create TextureVisuals with UVs and material
                final_mesh.visual = trimesh.visual.TextureVisuals(
                    uv=final_uvs,
                    image=texture_image
                )
        
        obj_path = export_obj(final_mesh, output_path, include_normals=True)
        
        # MTL file path (trimesh creates it as material.mtl in the same directory)
        obj_dir = os.path.dirname(obj_path)
        mtl_path = os.path.join(obj_dir, "material.mtl")
        if not os.path.exists(mtl_path):
            # Fallback to scene.mtl
            mtl_path = os.path.join(obj_dir, "scene.mtl")
        if not os.path.exists(mtl_path):
            mtl_path = None
        
        elapsed = time.time() - start_time
        
        print(f"      ✅ Exported: {os.path.basename(obj_path)}")
        if mtl_path:
            print(f"      ✅ Material: {os.path.basename(mtl_path)}")
        if texture_files:
            for tex in texture_files:
                print(f"      ✅ Texture: {os.path.basename(tex)}")
        
        print("\n" + "="*60)
        print(f"✨ GENERATION COMPLETE IN {elapsed:.1f}s")
        print("="*60 + "\n")
        
        if progress_callback:
            progress_callback(100, "Complete!")
        
        return obj_path, mtl_path, texture_files

