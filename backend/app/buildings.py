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
    
    def _sample_terrain_elevation(self, footprint_2d: np.ndarray) -> Optional[float]:
        """
        sample the terrain elevation at a building's footprint using ray casting
        see docs/logic/building_algo.md for detailed explanation
        """
        if self.terrain_mesh is None:
            return 0.0
        
        # use centroid for sampling
        centroid_x = np.mean(footprint_2d[:, 0])
        centroid_z = np.mean(footprint_2d[:, 1])
        
        # get terrain vertices
        terrain_vertices = self.terrain_mesh.vertices
        terrain_xz = terrain_vertices[:, [0, 2]]  # x-z positions
        
        # critical fix: negate z when searching terrain!
        # terrain was centered which flips the z coordinate system
        # buildings need to search with negated z to match
        search_z = -centroid_z
        
        # fast search: find nearest vertices using squared distances
        dx = terrain_xz[:, 0] - centroid_x
        dz = terrain_xz[:, 1] - search_z
        squared_distances = dx * dx + dz * dz
        
        # get 16 nearest vertices to have more triangles to check
        nearest_16_indices = np.argsort(squared_distances)[:16]
        nearest_16_vertices = terrain_vertices[nearest_16_indices]
        nearest_16_xz = terrain_xz[nearest_16_indices]
        
        # find the triangle containing the point using barycentric coordinates
        point = np.array([centroid_x, search_z])
        
        # check all possible triangles from the 16 nearest vertices
        for i in range(16):
            for j in range(i + 1, 16):
                for k in range(j + 1, 16):
                    v0 = nearest_16_vertices[i]
                    v1 = nearest_16_vertices[j]
                    v2 = nearest_16_vertices[k]
                    
                    # project to x-z plane
                    a = np.array([v0[0], v0[2]])
                    b = np.array([v1[0], v1[2]])
                    c = np.array([v2[0], v2[2]])
                    
                    # barycentric coordinates
                    v0_v1 = b - a
                    v0_v2 = c - a
                    v0_p = point - a
                    
                    dot00 = np.dot(v0_v2, v0_v2)
                    dot01 = np.dot(v0_v2, v0_v1)
                    dot02 = np.dot(v0_v2, v0_p)
                    dot11 = np.dot(v0_v1, v0_v1)
                    dot12 = np.dot(v0_v1, v0_p)
                    
                    denom = dot00 * dot11 - dot01 * dot01
                    if abs(denom) < 1e-10:
                        continue
                    
                    inv_denom = 1.0 / denom
                    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
                    v = (dot00 * dot12 - dot01 * dot02) * inv_denom
                    w = 1 - u - v
                    
                    if u >= 0 and v >= 0 and w >= 0:
                        # point is inside triangle - interpolate elevation
                        elevation = w * v0[1] + u * v1[1] + v * v2[1]
                        return float(elevation)
        
        # fallback: inverse distance weighted average of 4 nearest vertices
        nearest_4_indices = nearest_16_indices[:4]
        nearest_4_vertices = nearest_16_vertices[:4]
        distances = np.sqrt(squared_distances[nearest_4_indices])
        
        # check if nearest vertices are reasonable
        max_distance = distances.max()
        min_distance = distances[0]  # closest vertex
        
        # if the closest vertex is very far (>50m), the building is likely outside terrain bounds
        if min_distance > 50:
            print(f"⚠️  Warning: Building outside terrain bounds ({min_distance:.1f}m away). Dropping.")
            return None
        
        # check elevation variance
        elevation_variance = np.std(nearest_4_vertices[:, 1])
        if elevation_variance > 15:
            # use only the closest vertex instead of averaging
            return float(nearest_4_vertices[0, 1])
        
        # use inverse distance weighting
        weights = 1.0 / (distances + 1e-6)
        weights /= weights.sum()
        elevation = np.sum(weights * nearest_4_vertices[:, 1])
        
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

