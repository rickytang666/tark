"""
main mesh generation pipeline
orchestrates the entire process from bbox to 3d mesh
"""
from typing import Tuple, Optional, List, Callable
import os
import math
import time
import trimesh
import numpy as np
from PIL import Image

from app.fetchers.mapbox import MapboxTerrainFetcher
from app.fetchers.overpass import OverpassFetcher
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
from app.textures import MapboxSatelliteFetcher
from app.utils.mesh import merge_meshes, export_obj


class MeshGenerator:
    """
    orchestrates the mesh generation pipeline
    """
    
    def __init__(self, temp_dir: str, mapbox_token: str):
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
        progress_callback: Optional[Callable[[int, str], None]] = None,
        debug: bool = False
    ) -> Tuple[str, Optional[str], List[str]]:
        
        start_time = time.time()
        print("\n" + "="*60)
        print("🚀 BACKEND 2.0 MESH PIPELINE")
        print("="*60)
        
        if progress_callback:
            progress_callback(0, "starting generation...")
            
        # Central Definition of Origin
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        
        texture_files = []
        
        # ---------------------------------------------------------
        # 1. GENERATE TERRAIN
        # ---------------------------------------------------------
        print("[1/5] 🏔️  Fetching elevation & Building Terrain...")
        if progress_callback: progress_callback(10, "building terrain...")
        
        mapbox_fetcher = MapboxTerrainFetcher(self.mapbox_token, smoothing_sigma=1.5)
        elevation_data, _ = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=zoom_level
        )
        
        terrain_gen = TerrainGenerator()
        # Terrain is generated already centered at (0,0) via CoordinateTransformer
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=include_textures
        )
        
        print(f"      ✅ Terrain: {len(terrain_mesh.vertices)} verts")
        
        if debug:
            print("      🐞 DEBUG: Exporting terrain_only.obj")
            export_obj(terrain_mesh, os.path.join(self.temp_dir, "debug_terrain_only"))
        
        # ---------------------------------------------------------
        # 2. FETCH & APPLY SATELLITE TEXTURE
        # ---------------------------------------------------------
        terrain_texture_path = None
        if include_textures:
            print("[2/5] 📸 Fetching satellite imagery...")
            if progress_callback: progress_callback(30, "fetching imagery...")
            
            sat_fetcher = MapboxSatelliteFetcher(self.mapbox_token)
            
            # Aspect Ratio Calculation for minimal distortion
            lat_dist = north - south
            lon_dist = east - west
            # approximate meters (simple spherical assumption for ratio)
            h_meters = lat_dist * 111000
            w_meters = lon_dist * 111000 * math.cos(math.radians(center_lat))
            aspect = w_meters / h_meters if h_meters > 0 else 1.0
            
            if aspect >= 1.0:
                width = texture_max_dimension
                height = int(texture_max_dimension / aspect)
            else:
                height = texture_max_dimension
                width = int(texture_max_dimension * aspect)
                
            tex_path = os.path.join(self.temp_dir, "terrain_texture.png")
            
            try:
                _, saved_path = sat_fetcher.fetch_satellite_image(
                    north, south, east, west, width, height, tex_path
                )
                if saved_path:
                    texture_files.append(saved_path)
                    terrain_texture_path = saved_path
                    
                    # Apply to generic visual for now (will be baked into material on export)
                    # Terrain UVs are 0-1, image is WxH
                    img = Image.open(saved_path)
                    terrain_mesh.visual = trimesh.visual.TextureVisuals(
                        uv=terrain_mesh.visual.uv,
                        image=img
                    )
            except Exception as e:
                print(f"      ⚠️ Failed to fetch texture: {e}")

        # ---------------------------------------------------------
        # 3. BUILDINGS
        # ---------------------------------------------------------
        meshes_to_merge = [terrain_mesh]
        
        if include_buildings:
            print("[3/5] 🏢 Fetching & Extruding Buildings...")
            if progress_callback: progress_callback(50, "processing buildings...")
            
            overpass = OverpassFetcher()
            buildings_data = overpass.fetch_buildings(north, south, east, west)
            
            print(f"      ✅ Found {len(buildings_data)} footprints")
            
            if buildings_data:
                # Initialize Extruder with SAME center
                extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh)
                building_meshes = extruder.extrude_buildings(buildings_data)
                
                print(f"      ✅ Generated {len(building_meshes)} 3D buildings")
                
                if debug and building_meshes:
                    print(f"      🐞 DEBUG: Exporting {len(building_meshes)} buildings to debug_buildings_only.obj")
                    # Temporarily merge just buildings for debug export
                    # We accept the cost of an extra merge for debugging safety
                    debug_buildings = trimesh.util.concatenate(building_meshes)
                    export_obj(debug_buildings, os.path.join(self.temp_dir, "debug_buildings_only"))

                meshes_to_merge.extend(building_meshes)
        
        # ---------------------------------------------------------
        # 4. MERGE
        # ---------------------------------------------------------
        print("[4/5] 🔧 Merging Scene...")
        if progress_callback: progress_callback(80, "merging...")
        
        final_mesh = merge_meshes(meshes_to_merge)
        
        # ---------------------------------------------------------
        # 5. EXPORT
        # ---------------------------------------------------------
        print("[5/5] 💾 Exporting...")
        if progress_callback: progress_callback(90, "exporting...")
        
        # Re-apply texture if it was lost during merge
        # merge_meshes usually strips complicated texture visuals unless handled carefully
        # Simple fix: if terrain was textured, we need to map the combined UVs
        if terrain_texture_path and include_textures:
            # We assume terrain is the first mesh in merge list.
            # Terrain vertices are first N vertices of final_mesh
            n_terrain = len(terrain_mesh.vertices)
            total_verts = len(final_mesh.vertices)
            
            # Create a big UV buffer
            final_uvs = np.zeros((total_verts, 2))
            
            # Copy terrain UVs
            if hasattr(terrain_mesh.visual, 'uv') and terrain_mesh.visual.uv is not None:
                final_uvs[:n_terrain] = terrain_mesh.visual.uv
            
            # Buildings have their own UVs?
            # BuildingExtruder generates UVs.
            # Trimesh merge concatenates UVs if all source meshes have UVs.
            # app.utils.mesh.merge_meshes needs to handle this.
            # If standard trimesh.util.concatenate was used, UVs are preserved.
            
            # Let's check if final_mesh has UVs
            if hasattr(final_mesh.visual, 'uv') and final_mesh.visual.uv is not None:
                 print("      ℹ️  UVs preserved during merge.")
            else:
                 # If merge dropped UVs, we at least restore terrain UVs
                 final_mesh.visual = trimesh.visual.TextureVisuals(uv=final_uvs)
            
            # Load image again for the final mesh material
            final_mesh.visual.material = trimesh.visual.material.SimpleMaterial(
                image=Image.open(terrain_texture_path)
            )

        output_path = os.path.join(self.temp_dir, "scene")
        obj_path = export_obj(final_mesh, output_path, include_normals=True)
        
        mtl_path = obj_path.replace(".obj", ".mtl")
        if not os.path.exists(mtl_path): mtl_path = None
        
        print(f"\n✅ GENERATION COMPLETE")
        print(f"Files: {os.path.basename(obj_path)}")
        
        if progress_callback: progress_callback(100, "Done")
        
        return obj_path, mtl_path, texture_files
