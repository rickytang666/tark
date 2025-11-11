"""
Terrain mesh generation from elevation data
Converts elevation raster to 3D mesh
"""
import numpy as np
import trimesh
from app.utils.coords import CoordinateTransformer


class TerrainGenerator:
    """
    Generates terrain mesh from elevation data
    """
    
    def __init__(self):
        pass
    
    def generate_mesh(
        self,
        elevation_data: np.ndarray,
        bounds: tuple,
        resolution: float = 30.0
    ) -> trimesh.Trimesh:
        """
        Generate terrain mesh from elevation data
        
        Args:
            elevation_data: 2D numpy array of elevation values (meters)
            bounds: (west, south, east, north) in degrees
            resolution: Resolution in meters (default: 30m for Mapbox)
        
        Returns:
            trimesh.Trimesh object representing the terrain
        """
        west, south, east, north = bounds
        rows, cols = elevation_data.shape
        
        # 1. Create coordinate transformer centered on bbox
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        transformer = CoordinateTransformer(center_lat, center_lon)
        
        # 2. Generate lat/lon grid
        lats = np.linspace(north, south, rows)
        lons = np.linspace(west, east, cols)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # 3. Transform to local coordinates (meters)
        x_grid, y_grid = transformer.latlon_array_to_local(lat_grid, lon_grid)
        
        # 4. Create vertices (x, y, z)
        vertices = np.zeros((rows * cols, 3))
        vertices[:, 0] = x_grid.flatten()  # X (east-west)
        vertices[:, 1] = y_grid.flatten()  # Y (north-south)
        vertices[:, 2] = elevation_data.flatten()  # Z (elevation)
        
        # 5. Generate triangle faces
        faces = self._generate_faces(rows, cols)
        
        # 6. Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # 7. Center at origin
        mesh.vertices -= mesh.centroid
        
        return mesh
    
    def _generate_faces(self, rows: int, cols: int) -> np.ndarray:
        """
        Generate triangle faces for a regular grid
        
        For each grid cell, create 2 triangles:
        
        v0---v1
        |  / |
        | /  |
        v2---v3
        
        Triangle 1: (v0, v2, v1)
        Triangle 2: (v1, v2, v3)
        
        Args:
            rows: Number of rows in grid
            cols: Number of columns in grid
        
        Returns:
            Array of triangle face indices
        """
        faces = []
        
        for r in range(rows - 1):
            for c in range(cols - 1):
                # Vertex indices for current cell
                v0 = r * cols + c
                v1 = r * cols + (c + 1)
                v2 = (r + 1) * cols + c
                v3 = (r + 1) * cols + (c + 1)
                
                # Two triangles per cell
                faces.append([v0, v2, v1])
                faces.append([v1, v2, v3])
        
        return np.array(faces)

