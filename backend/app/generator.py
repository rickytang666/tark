"""
Main mesh generation pipeline
Orchestrates the entire process from bbox to 3D mesh
"""
from typing import Tuple, Optional
import os
import trimesh
from app.fetchers.mapbox import MapboxTerrainFetcher
from app.fetchers.overpass import OverpassFetcher
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
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
        include_buildings: bool = True
    ) -> Tuple[str, Optional[str]]:
        """
        Generate mesh for the given bounding box
        
        Args:
            north: North latitude
            south: South latitude
            east: East longitude
            west: West longitude
            include_buildings: Whether to include buildings (default: True)
        
        Returns:
            Tuple of (obj_file_path, mtl_file_path)
        """
        print("🚀 Starting mesh generation pipeline...\n")
        
        # Calculate center for coordinate transformation
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        
        # 1. Fetch elevation data from Mapbox
        print("⏳ Fetching elevation data from Mapbox...")
        mapbox_fetcher = MapboxTerrainFetcher(self.mapbox_token)
        elevation_data, elev_metadata = mapbox_fetcher.fetch_elevation(
            north=north, south=south, east=east, west=west, zoom=12
        )
        print(f"✅ Fetched elevation: {elevation_data.shape}\n")
        
        # 2. Generate terrain mesh
        print("⏳ Generating terrain mesh...")
        terrain_gen = TerrainGenerator()
        terrain_mesh = terrain_gen.generate_mesh(
            elevation_data=elevation_data,
            bounds=(west, south, east, north),
            resolution=30.0
        )
        print(f"✅ Terrain: {len(terrain_mesh.vertices):,} vertices, {len(terrain_mesh.faces):,} faces\n")
        
        meshes_to_merge = [terrain_mesh]
        
        # 3. Fetch and extrude buildings (if requested)
        if include_buildings:
            print("⏳ Fetching building data from OSM...")
            overpass_fetcher = OverpassFetcher(timeout=60)
            building_data = overpass_fetcher.fetch_buildings(
                north=north, south=south, east=east, west=west
            )
            print(f"✅ Fetched {len(building_data)} buildings\n")
            
            if building_data:
                print("⏳ Extruding buildings...")
                building_extruder = BuildingExtruder(center_lat, center_lon)
                building_meshes = building_extruder.extrude_buildings(
                    building_data, min_height=3.0
                )
                print(f"✅ Extruded {len(building_meshes)} buildings\n")
                
                if building_meshes:
                    meshes_to_merge.extend(building_meshes)
        
        # 4. Merge all meshes
        print("⏳ Merging meshes...")
        final_mesh = merge_meshes(meshes_to_merge)
        
        # Center XY at origin, but preserve Z elevations
        centroid_xy = final_mesh.centroid.copy()
        centroid_xy[2] = 0  # Don't center Z
        final_mesh.vertices -= centroid_xy
        
        print(f"✅ Final mesh: {len(final_mesh.vertices):,} vertices, {len(final_mesh.faces):,} faces\n")
        
        # 5. Export to OBJ
        print("⏳ Exporting to OBJ...")
        output_path = os.path.join(self.temp_dir, "scene")
        obj_path = export_obj(final_mesh, output_path, include_normals=True)
        print(f"✅ Exported to: {obj_path}\n")
        
        # MTL file path (if created by trimesh)
        mtl_path = f"{output_path}.mtl"
        if not os.path.exists(mtl_path):
            mtl_path = None
        
        return obj_path, mtl_path

