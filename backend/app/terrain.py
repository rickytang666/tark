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
    target: unity coordinate system (x=east, y=up, z=north)
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
        
        # flip elevation data to match coordinate system
        # mapbox returns: row 0 = north, row -1 = south
        # terrain mesh needs: row 0 = south, row -1 = north
        # so we flip the array vertically
        elevation_data = np.flipud(elevation_data)
        
        # 1. create coordinate transformer centered on bbox
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        transformer = CoordinateTransformer(center_lat, center_lon)
        
        # 2. generate lat/lon grid
        # note: mapbox elevation data usually comes ordered from north to south (rows)
        # and west to east (cols)
        lats = np.linspace(south, north, rows)
        lons = np.linspace(west, east, cols)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # 3. transform to local coordinates (meters)
        # x = easting (positive), z = northing (positive)
        x_grid, z_grid = transformer.latlon_array_to_local(lat_grid, lon_grid)
        
        # 4. create vertices (x, y, z)
        # y = elevation (up)
        vertices = np.zeros((rows * cols, 3))
        vertices[:, 0] = x_grid.flatten()
        vertices[:, 1] = elevation_data.flatten()
        vertices[:, 2] = z_grid.flatten()
        
        # 5. generate triangle faces
        faces = self._generate_faces(rows, cols)
        
        # 6. generate uv coordinates if requested
        uvs = None
        if generate_uvs:
            uvs = self._generate_uvs(rows, cols)
        
        # 7. create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Store grid metadata for building placement logic
        mesh.metadata['grid_dims'] = (rows, cols)
        mesh.metadata['bounds'] = bounds
        mesh.metadata['elevation'] = elevation_data
        
        # 8. attach uv coordinates to mesh
        if uvs is not None:
            mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
        
        return mesh
    
    def _generate_faces(self, rows: int, cols: int) -> np.ndarray:
        """
        generate triangle faces for a regular grid
        standard counter-clockwise winding order
        """
        faces = []
        
        for r in range(rows - 1):
            for c in range(cols - 1):
                # vertex indices for current cell
                # grid is flattened row by row
                v0 = r * cols + c           # top-left
                v1 = r * cols + (c + 1)     # top-right
                v2 = (r + 1) * cols + c     # bottom-left
                v3 = (r + 1) * cols + (c + 1) # bottom-right
                
                # two triangles per cell
                # Reversed winding to fix "facing core" issue
                # 1. top-left -> top-right -> bottom-left
                faces.append([v0, v1, v2])
                
                # 2. top-right -> bottom-right -> bottom-left
                faces.append([v1, v3, v2])
        
        return np.array(faces)
    
    def _generate_uvs(self, rows: int, cols: int) -> np.ndarray:
        """
        generate standard 0-1 uv coordinates based on grid index
        (0,0) = bottom-left, (1,1) = top-right
        """
        uvs = np.zeros((rows * cols, 2))
        
        # generate grid of indices
        c_indices = np.linspace(0, 1, cols)
        r_indices = np.linspace(0, 1, rows)
        
        u_grid, v_grid = np.meshgrid(c_indices, r_indices)
        
        uvs[:, 0] = u_grid.flatten() # u (x)
        uvs[:, 1] = v_grid.flatten() # v (y)
        
        return uvs
