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
        resolution: float = 30.0,
        generate_uvs: bool = True
    ) -> trimesh.Trimesh:
        """
        Generate terrain mesh from elevation data
        
        Args:
            elevation_data: 2D numpy array of elevation values (meters)
            bounds: (west, south, east, north) in degrees
            resolution: Resolution in meters (default: 30m for Mapbox)
            generate_uvs: Whether to generate UV texture coordinates
        
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
        x_grid, z_grid = transformer.latlon_array_to_local(lat_grid, lon_grid)
        
        # 4. Create vertices (x, y, z) with Y-up coordinate system
        # Unity/Blender convention: negate X and Z to match bird's eye view orientation
        # X = east-west, Y = elevation (up), Z = north-south
        vertices = np.zeros((rows * cols, 3))
        vertices[:, 0] = -x_grid.flatten()  # X (negated for Unity convention)
        vertices[:, 1] = elevation_data.flatten()  # Y (elevation - UP)
        vertices[:, 2] = -z_grid.flatten()  # Z (negated for Unity convention)
        
        # 5. Generate triangle faces
        faces = self._generate_faces(rows, cols)
        
        # 6. Generate UV coordinates if requested
        uvs = None
        if generate_uvs:
            uvs = self._generate_uvs(rows, cols)
        
        # 7. Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # 8. Attach UV coordinates to mesh
        if uvs is not None:
            mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
        
        # 9. Center X and Z at origin (but keep Y elevation intact)
        centroid_xz = mesh.centroid.copy()
        centroid_xz[1] = 0  # Don't center Y - keep real elevations
        mesh.vertices -= centroid_xz
        
        return mesh
    
    def _generate_faces(self, rows: int, cols: int) -> np.ndarray:
        """
        Generate triangle faces for a regular grid
        
        For each grid cell, create 2 triangles:
        
        v0---v1
        |  / |
        | /  |
        v2---v3
        
        Triangle 1: (v0, v1, v2) - reversed winding for negated coordinates
        Triangle 2: (v1, v3, v2) - reversed winding for negated coordinates
        
        Since we negate X and Z, we need to reverse the winding order
        so faces point upward (positive Y direction).
        
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
                
                # Two triangles per cell (reversed winding for negated coords)
                faces.append([v0, v1, v2])
                faces.append([v1, v3, v2])
        
        return np.array(faces)
    
    def _generate_uvs(self, rows: int, cols: int) -> np.ndarray:
        """
        Generate UV texture coordinates for terrain grid
        
        Maps the terrain grid to texture space (0,0) to (1,1)
        U = horizontal (columns), V = vertical (rows)
        
        UV coordinates map directly to the satellite image without flipping.
        The mesh coordinates are negated, but the texture image is not transformed,
        so UV mapping stays normal (0 to 1).
        
        Args:
            rows: Number of rows in grid
            cols: Number of columns in grid
        
        Returns:
            Array of UV coordinates (N x 2) where N = rows * cols
        """
        # Create normalized grid coordinates (0 to 1)
        u = np.linspace(0, 1, cols)
        v = np.linspace(0, 1, rows)
        
        # Create 2D grid
        u_grid, v_grid = np.meshgrid(u, v)
        
        # Flatten to vertex array
        uvs = np.zeros((rows * cols, 2))
        uvs[:, 0] = u_grid.flatten()  # U coordinate
        uvs[:, 1] = v_grid.flatten()  # V coordinate
        
        return uvs


