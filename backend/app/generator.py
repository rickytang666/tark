"""
Main mesh generation pipeline
Orchestrates the entire process from bbox to 3D mesh
"""
from typing import Tuple, Optional, List
import os
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
        include_textures: bool = True
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
        
        Returns:
            Tuple of (obj_file_path, mtl_file_path, texture_file_paths)
        """
        print("🚀 Starting mesh generation pipeline...\n")
        
        # Calculate center for coordinate transformation
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        
        texture_files = []
        
        # 1. Fetch satellite texture (if textures enabled)
        terrain_texture_path = None
        if include_textures:
            print("⏳ Fetching satellite imagery from Mapbox...")
            satellite_fetcher = MapboxSatelliteFetcher(self.mapbox_token)
            terrain_texture_path = os.path.join(self.temp_dir, "terrain.png")
            try:
                _, saved_path = satellite_fetcher.fetch_satellite_image(
                    north=north, south=south, east=east, west=west,
                    width=1280, height=1280,
                    output_path=terrain_texture_path
                )
                if saved_path:
                    texture_files.append(saved_path)
            except Exception as e:
                print(f"⚠️  Warning: Failed to fetch satellite imagery: {e}")
                print("    Continuing without terrain texture...\n")
                terrain_texture_path = None
        
        # 2. Fetch elevation data from Mapbox
        print("⏳ Fetching elevation data from Mapbox...")
        mapbox_fetcher = MapboxTerrainFetcher(self.mapbox_token)
        elevation_data, elev_metadata = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        print(f"✅ Fetched elevation: {elevation_data.shape}\n")
        
        # 3. Generate terrain mesh with UVs
        print("⏳ Generating terrain mesh...")
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0,
            generate_uvs=include_textures
        )
        print(f"✅ Terrain: {len(terrain_mesh.vertices):,} vertices, {len(terrain_mesh.faces):,} faces")
        if include_textures and hasattr(terrain_mesh.visual, 'uv'):
            print(f"   UV coordinates: {len(terrain_mesh.visual.uv):,} points\n")
        else:
            print()
        
        meshes_to_merge = [terrain_mesh]
        
        # 4. Fetch and extrude buildings (if requested)
        if include_buildings:
            print("⏳ Fetching building data from OSM...")
            overpass_fetcher = OverpassFetcher(timeout=60)
            building_data = overpass_fetcher.fetch_buildings(
                north=north, south=south, east=east, west=west
            )
            print(f"✅ Fetched {len(building_data)} buildings\n")
            
            if building_data:
                print("⏳ Extruding buildings...")
                # Pass terrain mesh so buildings can sit on terrain
                building_extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh)
                building_meshes = building_extruder.extrude_buildings(
                    building_data, min_height=3.0
                )
                print(f"✅ Extruded {len(building_meshes)} buildings\n")
                
                if building_meshes:
                    meshes_to_merge.extend(building_meshes)
        
        # 5. Merge all meshes
        print("⏳ Merging meshes...")
        final_mesh = merge_meshes(meshes_to_merge)
        
        # Center XY at origin, but preserve Z elevations
        centroid_xy = final_mesh.centroid.copy()
        centroid_xy[2] = 0  # Don't center Z
        final_mesh.vertices -= centroid_xy
        
        print(f"✅ Final mesh: {len(final_mesh.vertices):,} vertices, {len(final_mesh.faces):,} faces\n")
        
        # 6. Export to OBJ with texture reference
        print("⏳ Exporting to OBJ...")
        output_path = os.path.join(self.temp_dir, "scene")
        
        # If we have a terrain texture, set it in the mesh visual
        if terrain_texture_path and os.path.exists(terrain_texture_path):
            # Trimesh will reference the texture in the MTL file
            if hasattr(final_mesh.visual, 'material'):
                final_mesh.visual.material.image = terrain_texture_path
        
        obj_path = export_obj(final_mesh, output_path, include_normals=True)
        print(f"✅ Exported to: {obj_path}\n")
        
        # MTL file path (if created by trimesh)
        mtl_path = f"{output_path}.mtl"
        if not os.path.exists(mtl_path):
            mtl_path = None
        
        return obj_path, mtl_path, texture_files

