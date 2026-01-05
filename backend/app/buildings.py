"""
building extrusion from osm footprints
creates 3d building meshes from 2d footprints
"""
import trimesh
import numpy as np
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon
from app.utils.coords import CoordinateTransformer


class BuildingExtruder:
    """
    extrudes building footprints to 3d meshes
    target: unity coordinate system (x=east, y=up, z=north)
    """
    
    def __init__(self, center_lat: float, center_lon: float, terrain_mesh: Optional[trimesh.Trimesh] = None):
        """
        initialize building extruder
        
        args:
            center_lat: center latitude for coordinate transformation
            center_lon: center longitude for coordinate transformation
            terrain_mesh: optional terrain mesh to sample elevation from
        """
        self.transformer = CoordinateTransformer(center_lat, center_lon)
        self.terrain_mesh = terrain_mesh
        
        self.grid_params = None
        self._init_grid_acceleration()
    
    def _init_grid_acceleration(self):
        """
        initialize acceleration structure for O(1) terrain lookup
        assumes terrain mesh is roughly a grid
        """
        if self.terrain_mesh is None:
            return
            
        # check if mesh has grid metadata (added in terrain.py)
        grid_dims = self.terrain_mesh.metadata.get('grid_dims')
        if not grid_dims:
            return
            
        rows, cols = grid_dims
        vertices = self.terrain_mesh.vertices
        
        # probe corners to determine grid parameters for the X/Z plane (y is up)
        # terrain.py creates vertices row-by-row
        v0 = vertices[0]                       # Top-Left (North-West approx)
        v_col_end = vertices[cols - 1]         # Top-Right (North-East approx)
        v_row_end = vertices[(rows - 1) * cols] # Bottom-Left (South-West approx)
        
        # Verify orientation
        # With new system: X=East, Z=North.
        # Mapbox fetch usually goes:
        # Rows: North -> South (Z decreases)
        # Cols: West -> East (X increases)
        
        total_dx = v_col_end[0] - v0[0]      # Should be positive
        total_dz = v_row_end[2] - v0[2]      # Should be negative
        
        dx_per_col = total_dx / (cols - 1)
        dz_per_row = total_dz / (rows - 1)
        
        self.grid_params = {
            'origin_x': v0[0],
            'origin_z': v0[2],
            'dx_per_col': dx_per_col,
            'dz_per_row': dz_per_row,
            'rows': rows,
            'cols': cols,
            'vertices': vertices
        }
        print(f"✅ Grid acceleration initialized: {rows} x {cols} grid")
    
    def extrude_buildings(
        self,
        building_data: List[Dict[str, Any]],
        min_height: float = 3.0
    ) -> List[trimesh.Trimesh]:
        """
        extrude building footprints to 3d meshes
        """
        meshes = []
        stats = {
            "total": len(building_data),
            "success": 0,
            "dropped": 0,
            "failed": 0
        }
        
        for building in building_data:
            try:
                mesh = self._extrude_single_building(building, min_height)
                if mesh is not None:
                    meshes.append(mesh)
                    stats["success"] += 1
                else:
                    stats["dropped"] += 1
            except Exception as e:
                print(f"Error processing building {building.get('id')}: {e}")
                stats["failed"] += 1
                continue
        
        return meshes
    
    def _extrude_single_building(
        self,
        building: Dict[str, Any],
        min_height: float
    ) -> Optional[trimesh.Trimesh]:
        """
        extrude a single building footprint to 3d
        """
        coordinates = building.get("coordinates", [])
        if len(coordinates) < 3:
            return None
        
        # 1. Height Resolution
        height = building.get("height")
        if height is None:
            height = self.estimate_height(
                building.get("building_type", "yes"),
                building.get("levels")
            )
        height = max(height, min_height)
        
        # 2. Coordinate Transformation (Lat/Lon -> X/Z)
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        # xs = Easting, zs = Northing
        xs, zs = self.transformer.latlon_array_to_local(
            np.array(lats),
            np.array(lons)
        )
        
        # 3. Create Footprint Polygon (2D)
        # We pass (x, z) to polygon.
        footprint_2d = np.column_stack([xs, zs])
        
        # Handle holes
        holes_2d = []
        for hole in building.get("holes", []):
            if len(hole) >= 3:
                h_lons = [c[0] for c in hole]
                h_lats = [c[1] for c in hole]
                h_xs, h_zs = self.transformer.latlon_array_to_local(
                    np.array(h_lats), np.array(h_lons)
                )
                holes_2d.append(np.column_stack([h_xs, h_zs]))
        
        # 4. Sample Terrain Ground Height
        # We need the building base to sit on the terrain
        base_elevation = 0.0
        if self.terrain_mesh is not None:
            # Pass simple x, z centroid
            cx, cz = np.mean(xs), np.mean(zs)
            elevation = self._sample_terrain_elevation(cx, cz)
            if elevation is None:
                # Building is strictly outside our terrain data
                return None
            base_elevation = elevation

        # 5. Extrude
        # trimesh.creation.extrude_polygon assumes input is XY plane and extrudes Z.
        # Input: (x, z) points.
        # Output vertices columns: [x, z, extrusion_height]
        try:
            if holes_2d:
                poly = Polygon(footprint_2d, holes_2d)
            else:
                poly = Polygon(footprint_2d)
                
            if not poly.is_valid:
                poly = poly.buffer(0)
            
            mesh = trimesh.creation.extrude_polygon(poly, height=height)
        except Exception:
            return None
            
        # 6. Reorient Axes (The Crucial Fix)
        # Current mesh state:
        #   Column 0: x (Easting) - Correct
        #   Column 1: z (Northing) - Currently in Y position
        #   Column 2: height (Extrusion) - Currently in Z position
        #
        # Desired mesh state (Unity Y-Up):
        #   Column 0: x (Easting)
        #   Column 1: height (Up) - Needs to move here
        #   Column 2: z (Northing) - Needs to move here
        
        # Swap Y and Z columns
        mesh.vertices[:, [1, 2]] = mesh.vertices[:, [2, 1]]
        
        # Fix normals (swapping axes flips winding/normals)
        # Trimesh normals are likely invalid after manual vertex shuffle
        mesh.fix_normals()
        
        # 7. Apply UVs (Box Mapping)
        self._apply_uv_mapping(mesh)
        
        # 8. Apply Base Elevation
        # Move building 'Up' (Y axis) to sit on terrain
        mesh.vertices[:, 1] += base_elevation
        
        return mesh

    def _sample_terrain_elevation(self, x: float, z: float) -> Optional[float]:
        """
        sample terrain height at x, z
        """
        # Try O(1) Grid Lookup
        if self.grid_params:
            p = self.grid_params
            
            col_f = (x - p['origin_x']) / p['dx_per_col']
            row_f = (z - p['origin_z']) / p['dz_per_row']
            
            if 0 <= col_f <= p['cols']-1 and 0 <= row_f <= p['rows']-1:
                # Bilinear interp
                c0 = int(col_f)
                r0 = int(row_f)
                # clamp
                c0 = min(c0, p['cols'] - 2)
                r0 = min(r0, p['rows'] - 2)
                
                u = col_f - c0
                v = row_f - r0
                
                cols = p['cols']
                idx00 = r0 * cols + c0
                idx10 = idx00 + 1
                idx01 = (r0 + 1) * cols + c0
                idx11 = idx01 + 1
                
                h00 = p['vertices'][idx00, 1]
                h10 = p['vertices'][idx10, 1]
                h01 = p['vertices'][idx01, 1]
                h11 = p['vertices'][idx11, 1]
                
                h_top = h00 * (1-u) + h10 * u
                h_bot = h01 * (1-u) + h11 * u
                return float(h_top * (1-v) + h_bot * v)
        
        # Fallback: Nearest Neighbor Search (Slow but robust)
        # In a real heavy app, use KDTree. Here, brute force on small subset or failed
        # actually, if grid failed, we are confusingly out of bounds or unstructured.
        # Let's skip fallback for now to keep things clean and performant. 
        # If it's outside the grid, it's outside the map.
        return None

    def _apply_uv_mapping(self, mesh: trimesh.Trimesh, scale: float = 0.2):
        """
        simple box uv mapping
        """
        # Explode to flat faces for hard edges
        # (This increases vertex count but looks correct for buildings)
        # Manually explode vertices so each face has unique vertices
        new_vertices = mesh.vertices[mesh.faces].reshape(-1, 3)
        new_faces = np.arange(len(new_vertices)).reshape(-1, 3)
        
        mesh.vertices = new_vertices
        mesh.faces = new_faces
        mesh.fix_normals()
        
        vertices = mesh.vertices
        normals = mesh.face_normals
        
        # repeat normals for each vertex of the face
        # trimesh stores face_normals: (N, 3). vertices: (3N, 3) (if exploded)
        # Actually simplest way: use vertex normals if valid, or just based on position
        
        uvs = np.zeros((len(vertices), 2))
        
        # Box Projection Logic
        # n = normal
        # if n approx (0, 1, 0) or (0, -1, 0) -> Roof/Floor -> Use XZ
        # if n approx (1, 0, 0) -> Side -> Use ZY
        # if n approx (0, 0, 1) -> Front -> Use XY
        
        # Since we exploded, we can use vertex normals (which are just face normals repeated)
        # But let's just use the position for robustness
        
        # Actually, for buildings, let's just use World XZ for Roofs, and World/Height for Walls
        # We need to know which faces are walls.
        # A simple dot product with Up (0, 1, 0) works.
        
        # Re-calc vertex normals
        mesh.fix_normals()
        v_normals = mesh.vertex_normals
        
        dot_up = np.abs(v_normals[:, 1]) # Dot with Y axis
        is_roof = dot_up > 0.7
        is_wall = ~is_roof
        
        # Roofs: Project from World XZ to 0-1 UV space (matching the terrain map)
        if self.grid_params:
            # Normalize X and Z based on Grid Bounds
            # U = (x - origin_x) / (total_width)
            # V = (z - origin_z) / (total_height)
            # Note: total_width = dx * rows? No.
            # V0 [0, 0] is top-left (Origin).
            # Grid extends Positive X, Negative Z (North->South).
            # Wait, bounds are simpler:
            # min_x, max_x, min_z, max_z.
            
            p = self.grid_params
            # We probed corners in init:
            # v0 = Top-Left. v_col_end = Top-Right.
            # v_row_end = Bottom-Left.
            # width = v_col_end[0] - v0[0]
            # height = v_row_end[2] - v0[2] (Negative if Z decreases?)
            
            # Let's re-calculate precise bounds from the stored vertices to be safe
            terrain_verts = p['vertices']
            min_x, min_y, min_z = np.min(terrain_verts, axis=0)
            max_x, max_y, max_z = np.max(terrain_verts, axis=0)
            
            width = max_x - min_x
            depth = max_z - min_z
            
            # Normalize Roof Coordinates
            # Note: Mapbox image (V=0 is bottom, V=1 is top)
            # Terrain: Z+ is North (Top of standard map, or V=1?)
            # Standard Map: North=Top.
            # Terrain X/Z: X=East, Z=North.
            # So U = (x - min_x) / width  (West -> East : 0 -> 1)
            # V = (z - min_z) / depth     (South -> North : 0 -> 1)
            
            roof_u = (vertices[is_roof, 0] - min_x) / width
            roof_v = (vertices[is_roof, 2] - min_z) / depth
            
            uvs[is_roof, 0] = roof_u
            uvs[is_roof, 1] = roof_v
        
        else:
            # Fallback if no terrain bounds (shouldn't happen in this pipeline)
            uvs[is_roof, 0] = vertices[is_roof, 0] * 0.001
            uvs[is_roof, 1] = vertices[is_roof, 2] * 0.001
            
        # Walls: Map to (0,0) -> The "Grey Swatch" corner
        # We'll paint a small grey square at 0,0 of the texture
        uvs[is_wall, 0] = 0.005 # Small offset to hit the pixel center
        uvs[is_wall, 1] = 0.005
        
        mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)

    def estimate_height(self, building_type: str, levels: int = None) -> float:
        if levels:
            return float(levels) * 3.5
        defaults = {
            "residential": 8.0,
            "commercial": 12.0,
            "industrial": 10.0,
            "apartments": 18.0,
            "office": 25.0
        }
        return defaults.get(building_type, 10.0)
