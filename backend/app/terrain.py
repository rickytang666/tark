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
            # Pass the actual X-Z coordinates for planar projection
            # This ensures UVs are based on horizontal position, not elevation
            uvs = self._generate_uvs_from_positions(vertices[:, [0, 2]])
        
        # 7. Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # 8. Attach UV coordinates to mesh
        if uvs is not None:
            mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
        
        # Note: Do NOT center here - centering happens once at the end in generator.py
        # This ensures buildings and terrain use the same coordinate system
        
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
    
    def _generate_uvs_from_positions(self, xz_positions: np.ndarray) -> np.ndarray:
        """
        Generate UV texture coordinates based on actual X-Z positions
        
        This creates a planar projection that ignores elevation (Y coordinate).
        UVs are calculated from the horizontal position (X-Z plane) only,
        preventing distortion caused by terrain elevation.
        
        Args:
            xz_positions: Array of X-Z positions (N x 2) where N is number of vertices
        
        Returns:
            Array of UV coordinates (N x 2) normalized to (0,1) range
        """
        # Get min/max of X and Z coordinates
        min_x = xz_positions[:, 0].min()
        max_x = xz_positions[:, 0].max()
        min_z = xz_positions[:, 1].min()
        max_z = xz_positions[:, 1].max()
        
        # Normalize X and Z to 0-1 range for UV coordinates
        # Both U and V flipped because mesh X and Z are both negated
        # This creates a 180 degree rotation to match the negated coordinate system
        uvs = np.zeros((len(xz_positions), 2))
        uvs[:, 0] = 1.0 - (xz_positions[:, 0] - min_x) / (max_x - min_x)  # U flipped (X negated)
        uvs[:, 1] = (xz_positions[:, 1] - min_z) / (max_z - min_z)  # V normal
        
        return uvs


