"""
terrain mesh generation from elevation data
converts elevation raster to 3d mesh
"""
import numpy as np
import trimesh
from app.utils.coords import CoordinateTransformer


class TerrainGenerator:
    """
    generates terrain mesh from elevation data
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
        generate terrain mesh from elevation data
        
        args:
            elevation_data: 2d numpy array of elevation values (meters)
            bounds: (west, south, east, north) in degrees
            resolution: resolution in meters (default: 30m for mapbox)
            generate_uvs: whether to generate uv texture coordinates
        
        returns:
            trimesh.trimesh object representing the terrain
        """
        west, south, east, north = bounds
        rows, cols = elevation_data.shape
        
        # 1. create coordinate transformer centered on bbox
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        transformer = CoordinateTransformer(center_lat, center_lon)
        
        # 2. generate lat/lon grid
        lats = np.linspace(north, south, rows)
        lons = np.linspace(west, east, cols)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # 3. transform to local coordinates (meters)
        # see docs/logic/coordinates.md
        x_grid, z_grid = transformer.latlon_array_to_local(lat_grid, lon_grid)
        
        # 4. create vertices (x, y, z) with y-up coordinate system
        # unity/blender convention: negate x and z to match bird's eye view
        vertices = np.zeros((rows * cols, 3))
        vertices[:, 0] = -x_grid.flatten()  # x (negated)
        vertices[:, 1] = elevation_data.flatten()  # y (elevation - up)
        vertices[:, 2] = -z_grid.flatten()  # z (negated)
        
        # 5. generate triangle faces
        faces = self._generate_faces(rows, cols)
        
        # 6. generate uv coordinates if requested
        uvs = None
        if generate_uvs:
            # pass the actual x-z coordinates for planar projection
            uvs = self._generate_uvs_from_positions(vertices[:, [0, 2]])
        
        # 7. create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Store grid dimensions for O(1) elevation lookup
        mesh.metadata['grid_dims'] = (rows, cols)
        
        # 8. attach uv coordinates to mesh
        if uvs is not None:
            mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
        
        # note: do not center here - centering happens once at the end in generator.py
        
        return mesh
    
    def _generate_faces(self, rows: int, cols: int) -> np.ndarray:
        """
        generate triangle faces for a regular grid
        see docs/logic/terrain_algo.md for winding order details
        """
        faces = []
        
        for r in range(rows - 1):
            for c in range(cols - 1):
                # vertex indices for current cell
                v0 = r * cols + c
                v1 = r * cols + (c + 1)
                v2 = (r + 1) * cols + c
                v3 = (r + 1) * cols + (c + 1)
                
                # two triangles per cell (reversed winding for negated coords)
                faces.append([v0, v1, v2])
                faces.append([v1, v3, v2])
        
        return np.array(faces)
    
    def _generate_uvs_from_positions(self, xz_positions: np.ndarray) -> np.ndarray:
        """
        generate uv texture coordinates based on actual x-z positions
        uses planar projection (ignores elevation)
        """
        # get min/max of x and z coordinates
        min_x = xz_positions[:, 0].min()
        max_x = xz_positions[:, 0].max()
        min_z = xz_positions[:, 1].min()
        max_z = xz_positions[:, 1].max()
        
        # normalize x and z to 0-1 range for uv coordinates
        # both u and v flipped because mesh x and z are both negated
        # this creates a 180 degree rotation to match the negated coordinate system
        uvs = np.zeros((len(xz_positions), 2))
        uvs[:, 0] = 1.0 - (xz_positions[:, 0] - min_x) / (max_x - min_x)  # u flipped
        uvs[:, 1] = (xz_positions[:, 1] - min_z) / (max_z - min_z)  # v normal
        
        return uvs


