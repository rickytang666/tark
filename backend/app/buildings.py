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
        assumes terrain mesh is a structured grid (row-major)
        """
        if self.terrain_mesh is None:
            return
            
        # check if mesh has grid metadata (added in terrain.py)
        grid_dims = self.terrain_mesh.metadata.get('grid_dims')
        if not grid_dims:
            return
            
        rows, cols = grid_dims
        vertices = self.terrain_mesh.vertices
        
        if len(vertices) != rows * cols:
            print("Warning: Terrain vertex count doesn't match grid dimensions. Disabling acceleration.")
            return
            
        # probe corners to determine grid layout
        v0 = vertices[0]
        v_col_end = vertices[cols - 1]
        v_row_end = vertices[(rows - 1) * cols]
        
        # calculate steps
        total_dx = v_col_end[0] - v0[0]
        total_dz = v_row_end[2] - v0[2]
        
        dx_per_col = total_dx / (cols - 1)
        dz_per_row = total_dz / (rows - 1)
        
        # safety check for degenerate grid
        if abs(dx_per_col) < 1e-6 or abs(dz_per_row) < 1e-6:
            return
            
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
        
        args:
            building_data: list of building dictionaries from osm
            min_height: minimum building height in meters
        
        returns:
            list of trimesh.trimesh objects for each building
        """
        meshes = []
        stats = {
            "total": len(building_data),
            "success": 0,
            "fallback": 0,
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
                    # try fallback to bounding box
                    fallback_mesh = self._create_bounding_box_fallback(building, min_height)
                    if fallback_mesh is not None:
                        meshes.append(fallback_mesh)
                        stats["fallback"] += 1
                    else:
                        # building was dropped (outside terrain bounds)
                        stats["dropped"] += 1
            except Exception as e:
                # try fallback before giving up
                print(f"Warning: Failed to extrude building {building.get('id')}: {e}")
                try:
                    fallback_mesh = self._create_bounding_box_fallback(building, min_height)
                    if fallback_mesh is not None:
                        meshes.append(fallback_mesh)
                        stats["fallback"] += 1
                    else:
                        # building was dropped (outside terrain bounds)
                        stats["dropped"] += 1
                except Exception as fallback_error:
                    print(f"Error: Bounding box fallback also failed for {building.get('id')}: {fallback_error}")
                    stats["failed"] += 1
                continue
        
        # print statistics
        if stats["total"] > 0:
            print(f"\n📊 Building Extrusion Statistics:")
            print(f"   Total buildings: {stats['total']}")
            print(f"   ✅ Successfully extruded: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
            if stats['fallback'] > 0:
                print(f"   📦 Bounding box fallback: {stats['fallback']} ({stats['fallback']/stats['total']*100:.1f}%)")
            if stats['dropped'] > 0:
                print(f"   🗑️  Dropped (outside terrain): {stats['dropped']} ({stats['dropped']/stats['total']*100:.1f}%)")
            if stats['failed'] > 0:
                print(f"   ❌ Failed: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
        
        return meshes
    
    def _extrude_single_building(
        self,
        building: Dict[str, Any],
        min_height: float
    ) -> Optional[trimesh.Trimesh]:
        """
        extrude a single building footprint to 3d
        see docs/logic/building_algo.md for algorithm details
        """
        coordinates = building.get("coordinates", [])
        
        if len(coordinates) < 3:
            return None
        
        # get building height
        height = building.get("height")
        if height is None:
            height = self.estimate_height(
                building.get("building_type", "yes"),
                building.get("levels")
            )
        
        # ensure minimum height
        height = max(height, min_height)
        
        # convert lat/lon coordinates to local meters (outer boundary)
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        xs, zs = self.transformer.latlon_array_to_local(
            np.array(lats),
            np.array(lons)
        )
        
        # negate x and z for unity/blender convention
        xs = -xs
        zs = -zs
        
        # create 2d polygon (x-z plane, since y is up)
        footprint_2d = np.column_stack([xs, zs])
        
        # convert holes (courtyards) to local meters
        holes_2d = []
        holes_coords = building.get("holes", [])
        for hole in holes_coords:
            if len(hole) >= 3:
                hole_lons = [coord[0] for coord in hole]
                hole_lats = [coord[1] for coord in hole]
                
                hole_xs, hole_zs = self.transformer.latlon_array_to_local(
                    np.array(hole_lats),
                    np.array(hole_lons)
                )
                
                # negate x and z
                hole_xs = -hole_xs
                hole_zs = -hole_zs
                
                holes_2d.append(np.column_stack([hole_xs, hole_zs]))
        
        # sample terrain elevation if available
        base_elevation = 0.0
        if self.terrain_mesh is not None:
            # see docs/logic/building_algo.md for sampling logic
            sampled_elevation = self._sample_terrain_elevation(footprint_2d)
            if sampled_elevation is None:
                # building is outside terrain bounds - drop it
                return None
            base_elevation = sampled_elevation
        
        # extrude to 3d (with holes if present)
        mesh = self._extrude_polygon(footprint_2d, height, holes_2d)
        
        # offset mesh to sit on terrain (y is up, so offset y coordinate)
        if base_elevation != 0.0:
            mesh.vertices[:, 1] += base_elevation
        
        return mesh
    
    def _extrude_polygon(
        self,
        footprint_2d: np.ndarray,
        height: float,
        holes_2d: List[np.ndarray] = None
    ) -> trimesh.Trimesh:
        """
        extrude a 2d polygon to create a 3d box mesh
        uses trimesh's built-in extrude_polygon which handles concave shapes and holes
        """
        # create shapely polygon with holes if present
        if holes_2d and len(holes_2d) > 0:
            # polygon constructor: polygon(exterior, [list of holes])
            polygon = Polygon(footprint_2d, holes_2d)
        else:
            polygon = Polygon(footprint_2d)
        
        # validate polygon
        if not polygon.is_valid or polygon.is_empty:
            # fallback: try to fix invalid polygons
            polygon = polygon.buffer(0)
            if not polygon.is_valid:
                raise ValueError("invalid polygon footprint")
        
        # use trimesh's built-in extrusion with proper triangulation
        # note: extrude_polygon extrudes along z-axis by default
        mesh = trimesh.creation.extrude_polygon(polygon, height=height)
        
        # APPLY UV MAPPING (Box Projection)
        # do this before rotation while Z is still "up" relative to the extrusion
        self._apply_uv_mapping(mesh)
        
        # rotate mesh to align with y-up coordinate system
        # trimesh extrudes along z, but we want y-up
        # so we need to rotate: z->y, y->-z (90 degrees around x-axis)
        rotation_matrix = trimesh.transformations.rotation_matrix(
            angle=np.radians(-90),  # -90 degrees
            direction=[1, 0, 0],     # around x-axis
            point=[0, 0, 0]
        )
        mesh.apply_transform(rotation_matrix)
        
        return mesh

    def _apply_uv_mapping(self, mesh: trimesh.Trimesh, scale: float = 0.2):
        """
        apply box-projected uv mapping to the mesh
        see building_algo.md for full algo details
        """
        # explode mesh for flat shading (unique vertices per face)
        new_vertices = mesh.vertices[mesh.faces].reshape(-1, 3)
        new_faces = np.arange(len(new_vertices)).reshape(-1, 3)
        
        mesh.vertices = new_vertices
        mesh.faces = new_faces
        
        # fix normals for flat faces
        mesh.fix_normals()
        normals = mesh.face_normals
        vertices = mesh.vertices
        
        # initialize uv array
        uvs = np.zeros((len(vertices), 2))
        
        # expand normals to match vertex count
        vertex_normals = np.repeat(normals, 3, axis=0)
        
        # determine orientation (z is up before rotation)
        dot_z = np.abs(vertex_normals[:, 2])
        is_roof = dot_z > 0.7
        is_wall = ~is_roof
        
        # --- ROOFS (Planar XY) ---
        uvs[is_roof, 0] = vertices[is_roof, 0] * scale
        uvs[is_roof, 1] = vertices[is_roof, 1] * scale
        
        # --- WALLS (Box Mapping) ---
        dot_x = np.abs(vertex_normals[is_wall, 0])
        dot_y = np.abs(vertex_normals[is_wall, 1])
        is_x_facing = dot_x > dot_y
        
        wall_indices = np.where(is_wall)[0]
        x_wall_indices = wall_indices[is_x_facing]
        y_wall_indices = wall_indices[~is_x_facing]
        
        # X-facing: YZ plane
        uvs[x_wall_indices, 0] = vertices[x_wall_indices, 1] * scale
        uvs[x_wall_indices, 1] = vertices[x_wall_indices, 2] * scale
        
        # Y-facing: XZ plane
        uvs[y_wall_indices, 0] = vertices[y_wall_indices, 0] * scale
        uvs[y_wall_indices, 1] = vertices[y_wall_indices, 2] * scale
        
        mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
    
    def _sample_terrain_elevation(self, footprint_2d: np.ndarray) -> Optional[float]:
        """
        sample the terrain elevation at a building's footprint
        """
        if self.terrain_mesh is None:
            return 0.0
            
        # use centroid for sampling
        centroid_x = np.mean(footprint_2d[:, 0])
        centroid_z = np.mean(footprint_2d[:, 1])
        
        # Restore original Z-negation logic
        # The terrain mesh and building footprints apparently have opposing Z coordinates
        # due to the legacy pipeline logic. 
        target_z = -centroid_z
        
        # Try O(1) Fast Lookup first
        if self.grid_params:
            elevation = self._sample_grid_elevation(centroid_x, target_z)
            if elevation is not None:
                return elevation
        
        # Fallback to Ray Casting
        # Pass the ALREADY negated z (target_z) to avoid double negation confusion
        return self._sample_fallback_elevation(centroid_x, target_z)

    def _sample_grid_elevation(self, x: float, z: float) -> Optional[float]:
        """O(1) elevation lookup using grid coordinates"""
        p = self.grid_params
        
        # calculate grid indices (float)
        col_f = (x - p['origin_x']) / p['dx_per_col']
        row_f = (z - p['origin_z']) / p['dz_per_row']
        
        # check bounds (with small epsilon buffer)
        if col_f < -0.01 or col_f > p['cols'] - 0.99 or \
           row_f < -0.01 or row_f > p['rows'] - 0.99:
            return None
            
        # integer indices (top-left of the cell)
        # clamp to valid range
        c0 = int(max(0, min(col_f, p['cols'] - 2)))
        r0 = int(max(0, min(row_f, p['rows'] - 2)))
        
        # bilinear interpolation weights
        u = col_f - c0
        v = row_f - r0
        
        # clamp weights
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        
        # get 4 corner heights
        cols = p['cols']
        idx_00 = r0 * cols + c0
        idx_10 = idx_00 + 1
        idx_01 = (r0 + 1) * cols + c0
        idx_11 = idx_01 + 1
        
        h00 = p['vertices'][idx_00, 1]
        h10 = p['vertices'][idx_10, 1]
        h01 = p['vertices'][idx_01, 1]
        h11 = p['vertices'][idx_11, 1]
        
        # interpolate
        h_top = h00 * (1 - u) + h10 * u
        h_bot = h01 * (1 - u) + h11 * u
        height = h_top * (1 - v) + h_bot * v
        
        return float(height)

    def _sample_fallback_elevation(self, centroid_x: float, search_z: float) -> Optional[float]:
        """Original O(N) logic for fallback area matching"""
        # get terrain vertices
        terrain_vertices = self.terrain_mesh.vertices
        terrain_xz = terrain_vertices[:, [0, 2]]
        
        dx = terrain_xz[:, 0] - centroid_x
        dz = terrain_xz[:, 1] - search_z
        squared_distances = dx * dx + dz * dz
        
        # get 16 nearest
        nearest_16_indices = np.argsort(squared_distances)[:16]
        nearest_16_vertices = terrain_vertices[nearest_16_indices]
        
        # simple IDW of 4 nearest for robustness
        nearest_4 = nearest_16_vertices[:4]
        dists = np.sqrt(squared_distances[nearest_16_indices[:4]])
        
        if dists[0] > 50:
            return None
            
        weights = 1.0 / (dists + 1e-6)
        weights /= weights.sum()
        elevation = np.sum(weights * nearest_4[:, 1])
        
        return float(elevation)
    
    def _create_bounding_box_fallback(
        self,
        building: Dict[str, Any],
        min_height: float
    ) -> Optional[trimesh.Trimesh]:
        """
        create a simple bounding box mesh as fallback for failed extrusions
        """
        try:
            coordinates = building.get("coordinates", [])
            if len(coordinates) < 3:
                return None
            
            # get building height
            height = building.get("height")
            if height is None:
                height = self.estimate_height(
                    building.get("building_type", "yes"),
                    building.get("levels")
                )
            height = max(height, min_height)
            
            # convert to local coordinates
            lons = [coord[0] for coord in coordinates]
            lats = [coord[1] for coord in coordinates]
            
            xs, zs = self.transformer.latlon_array_to_local(
                np.array(lats),
                np.array(lons)
            )
            
            # negate x and z
            xs = -xs
            zs = -zs
            
            # get bounding box (in x-z plane)
            min_x, max_x = np.min(xs), np.max(xs)
            min_z, max_z = np.min(zs), np.max(zs)
            
            # sample terrain elevation
            base_elevation = 0.0
            if self.terrain_mesh is not None:
                centroid_2d = np.array([[np.mean(xs), np.mean(zs)]])
                sampled_elevation = self._sample_terrain_elevation(centroid_2d)
                if sampled_elevation is None:
                    return None
                base_elevation = sampled_elevation
            
            # create simple box (in x-z plane)
            box_coords = np.array([
                [min_x, min_z],
                [max_x, min_z],
                [max_x, max_z],
                [min_x, max_z],
                [min_x, min_z]
            ])
            
            # extrude simple box
            polygon = Polygon(box_coords)
            mesh = trimesh.creation.extrude_polygon(polygon, height=height)
            
            # APPLY UV MAPPING
            self._apply_uv_mapping(mesh)
            
            # rotate to y-up coordinate system
            rotation_matrix = trimesh.transformations.rotation_matrix(
                angle=np.radians(-90),
                direction=[1, 0, 0],
                point=[0, 0, 0]
            )
            mesh.apply_transform(rotation_matrix)
            
            # offset to terrain
            if base_elevation != 0.0:
                mesh.vertices[:, 1] += base_elevation
            
            return mesh
            
        except Exception as e:
            print(f"bounding box fallback failed: {e}")
            return None
    
    def estimate_height(self, building_type: str, levels: int = None) -> float:
        """
        estimate building height from type or levels
        """
        if levels:
            return levels * 3.5  # assume 3.5m per floor
        
        # default heights by building type
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

