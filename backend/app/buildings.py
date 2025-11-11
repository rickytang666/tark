"""
Building extrusion from OSM footprints
Creates 3D building meshes from 2D footprints
"""
import trimesh
import numpy as np
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon
from app.utils.coords import CoordinateTransformer


class BuildingExtruder:
    """
    Extrudes building footprints to 3D meshes
    """
    
    def __init__(self, center_lat: float, center_lon: float):
        """
        Initialize building extruder
        
        Args:
            center_lat: Center latitude for coordinate transformation
            center_lon: Center longitude for coordinate transformation
        """
        self.transformer = CoordinateTransformer(center_lat, center_lon)
    
    def extrude_buildings(
        self,
        building_data: List[Dict[str, Any]],
        min_height: float = 3.0
    ) -> List[trimesh.Trimesh]:
        """
        Extrude building footprints to 3D meshes
        
        Args:
            building_data: List of building dictionaries from OSM
                Each contains: coordinates, height, levels, building_type
            min_height: Minimum building height in meters
        
        Returns:
            List of trimesh.Trimesh objects for each building
        """
        meshes = []
        
        for building in building_data:
            try:
                mesh = self._extrude_single_building(building, min_height)
                if mesh is not None:
                    meshes.append(mesh)
            except Exception as e:
                # Skip buildings that fail to extrude
                print(f"Warning: Failed to extrude building {building.get('id')}: {e}")
                continue
        
        return meshes
    
    def _extrude_single_building(
        self,
        building: Dict[str, Any],
        min_height: float
    ) -> Optional[trimesh.Trimesh]:
        """
        Extrude a single building footprint to 3D
        
        Args:
            building: Building dictionary with coordinates and metadata
            min_height: Minimum height
        
        Returns:
            trimesh.Trimesh or None if invalid
        """
        coordinates = building.get("coordinates", [])
        
        if len(coordinates) < 3:
            return None
        
        # Get building height
        height = building.get("height")
        if height is None:
            height = self.estimate_height(
                building.get("building_type", "yes"),
                building.get("levels")
            )
        
        # Ensure minimum height
        height = max(height, min_height)
        
        # Convert lat/lon coordinates to local meters
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        xs, ys = self.transformer.latlon_array_to_local(
            np.array(lats),
            np.array(lons)
        )
        
        # Create 2D polygon
        footprint_2d = np.column_stack([xs, ys])
        
        # Extrude to 3D
        mesh = self._extrude_polygon(footprint_2d, height)
        
        return mesh
    
    def _extrude_polygon(
        self,
        footprint_2d: np.ndarray,
        height: float
    ) -> trimesh.Trimesh:
        """
        Extrude a 2D polygon to create a 3D box mesh
        
        Args:
            footprint_2d: 2D polygon vertices (N x 2)
            height: Extrusion height in meters
        
        Returns:
            trimesh.Trimesh of extruded building
        """
        n_points = len(footprint_2d)
        
        # Create bottom vertices (z=0) and top vertices (z=height)
        bottom_verts = np.column_stack([footprint_2d, np.zeros(n_points)])
        top_verts = np.column_stack([footprint_2d, np.full(n_points, height)])
        
        # Combine all vertices
        vertices = np.vstack([bottom_verts, top_verts])
        
        # Generate faces
        faces = []
        
        # Bottom face (reversed winding for correct normal)
        if n_points >= 3:
            # Triangulate bottom face
            for i in range(1, n_points - 1):
                faces.append([0, i + 1, i])
        
        # Top face
        if n_points >= 3:
            # Triangulate top face
            for i in range(1, n_points - 1):
                faces.append([n_points, n_points + i, n_points + i + 1])
        
        # Side faces (walls)
        for i in range(n_points):
            next_i = (i + 1) % n_points
            
            # Two triangles per wall segment
            # Triangle 1
            faces.append([i, next_i, n_points + i])
            # Triangle 2
            faces.append([next_i, n_points + next_i, n_points + i])
        
        faces = np.array(faces)
        
        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        return mesh
    
    def estimate_height(self, building_type: str, levels: int = None) -> float:
        """
        Estimate building height from type or levels
        
        Args:
            building_type: OSM building type (residential, commercial, etc.)
            levels: Number of levels/floors if available
        
        Returns:
            Estimated height in meters
        """
        if levels:
            return levels * 3.5  # Assume 3.5m per floor
        
        # Default heights by building type
        height_defaults = {
            "residential": 10.0,
            "commercial": 15.0,
            "industrial": 12.0,
            "retail": 8.0,
            "house": 6.0,
            "apartments": 20.0,
            "office": 25.0,
        }
        
        return height_defaults.get(building_type, 10.0)

