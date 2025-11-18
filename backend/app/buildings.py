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
    
    def __init__(self, center_lat: float, center_lon: float, terrain_mesh: Optional[trimesh.Trimesh] = None):
        """
        Initialize building extruder
        
        Args:
            center_lat: Center latitude for coordinate transformation
            center_lon: Center longitude for coordinate transformation
            terrain_mesh: Optional terrain mesh to sample elevation from
        """
        self.transformer = CoordinateTransformer(center_lat, center_lon)
        self.terrain_mesh = terrain_mesh
    
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
        stats = {
            "total": len(building_data),
            "success": 0,
            "fallback": 0,
            "failed": 0
        }
        
        for building in building_data:
            try:
                mesh = self._extrude_single_building(building, min_height)
                if mesh is not None:
                    meshes.append(mesh)
                    stats["success"] += 1
                else:
                    # Try fallback to bounding box
                    fallback_mesh = self._create_bounding_box_fallback(building, min_height)
                    if fallback_mesh is not None:
                        meshes.append(fallback_mesh)
                        stats["fallback"] += 1
                    else:
                        stats["failed"] += 1
            except Exception as e:
                # Try fallback before giving up
                print(f"Warning: Failed to extrude building {building.get('id')}: {e}")
                try:
                    fallback_mesh = self._create_bounding_box_fallback(building, min_height)
                    if fallback_mesh is not None:
                        meshes.append(fallback_mesh)
                        stats["fallback"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as fallback_error:
                    print(f"Error: Bounding box fallback also failed for {building.get('id')}: {fallback_error}")
                    stats["failed"] += 1
                continue
        
        # Print statistics
        if stats["total"] > 0:
            print(f"\n📊 Building Extrusion Statistics:")
            print(f"   Total buildings: {stats['total']}")
            print(f"   ✅ Successfully extruded: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
            if stats['fallback'] > 0:
                print(f"   📦 Bounding box fallback: {stats['fallback']} ({stats['fallback']/stats['total']*100:.1f}%)")
            if stats['failed'] > 0:
                print(f"   ❌ Failed: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
        
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
        
        # Convert lat/lon coordinates to local meters (outer boundary)
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        xs, zs = self.transformer.latlon_array_to_local(
            np.array(lats),
            np.array(lons)
        )
        
        # Negate X and Z for Unity/Blender convention
        xs = -xs
        zs = -zs
        
        # Create 2D polygon (X-Z plane, since Y is up)
        footprint_2d = np.column_stack([xs, zs])
        
        # Convert holes (courtyards) to local meters
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
                
                # Negate X and Z for Unity/Blender convention
                hole_xs = -hole_xs
                hole_zs = -hole_zs
                
                holes_2d.append(np.column_stack([hole_xs, hole_zs]))
        
        # Sample terrain elevation if available
        base_elevation = 0.0
        if self.terrain_mesh is not None:
            base_elevation = self._sample_terrain_elevation(footprint_2d)
        
        # Extrude to 3D (with holes if present)
        mesh = self._extrude_polygon(footprint_2d, height, holes_2d)
        
        # Offset mesh to sit on terrain (Y is up, so offset Y coordinate)
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
        Extrude a 2D polygon to create a 3D box mesh
        
        Uses trimesh's built-in extrude_polygon which properly handles:
        - Concave polygons (L-shapes, U-shapes, etc.)
        - Complex shapes with proper triangulation
        - Polygons with holes (courtyards)
        - Correct face winding and normals
        
        Args:
            footprint_2d: 2D polygon vertices (N x 2) in X-Z plane
            height: Extrusion height in meters (along Y-axis)
            holes_2d: List of hole polygons for courtyards (optional)
        
        Returns:
            trimesh.Trimesh of extruded building with Y-up coordinate system
        """
        # Create Shapely polygon with holes if present
        if holes_2d and len(holes_2d) > 0:
            # Polygon constructor: Polygon(exterior, [list of holes])
            polygon = Polygon(footprint_2d, holes_2d)
        else:
            polygon = Polygon(footprint_2d)
        
        # Validate polygon
        if not polygon.is_valid or polygon.is_empty:
            # Fallback: try to fix invalid polygons
            polygon = polygon.buffer(0)
            if not polygon.is_valid:
                raise ValueError("Invalid polygon footprint")
        
        # Use trimesh's built-in extrusion with proper triangulation
        # This handles concave polygons and holes correctly
        # Note: extrude_polygon extrudes along Z-axis by default
        mesh = trimesh.creation.extrude_polygon(polygon, height=height)
        
        # Rotate mesh to align with Y-up coordinate system
        # trimesh extrudes along Z, but we want Y-up
        # So we need to rotate: Z->Y, Y->-Z (90 degrees around X-axis)
        rotation_matrix = trimesh.transformations.rotation_matrix(
            angle=np.radians(-90),  # -90 degrees
            direction=[1, 0, 0],     # around X-axis
            point=[0, 0, 0]
        )
        mesh.apply_transform(rotation_matrix)
        
        return mesh
    
    def _sample_terrain_elevation(self, footprint_2d: np.ndarray) -> float:
        """
        Sample the terrain elevation at a building's footprint
        
        Uses the center point of the footprint to query terrain mesh elevation.
        
        Args:
            footprint_2d: 2D building footprint (N x 2) in X-Z plane
        
        Returns:
            Base elevation in meters (Y coordinate in Y-up system)
        """
        if self.terrain_mesh is None:
            return 0.0
        
        # Calculate centroid of footprint (X-Z plane)
        centroid_x = np.mean(footprint_2d[:, 0])
        centroid_z = np.mean(footprint_2d[:, 1])
        
        # Find nearest terrain vertex to building centroid
        # Terrain uses Y-up: X=east-west, Y=elevation, Z=north-south
        terrain_xz = self.terrain_mesh.vertices[:, [0, 2]]  # Just X, Z
        terrain_y = self.terrain_mesh.vertices[:, 1]        # Just Y (elevation)
        
        # Calculate distances to all terrain vertices (in X-Z plane)
        distances = np.sqrt(
            (terrain_xz[:, 0] - centroid_x)**2 +
            (terrain_xz[:, 1] - centroid_z)**2
        )
        
        # Find nearest vertex
        nearest_idx = np.argmin(distances)
        base_elevation = terrain_y[nearest_idx]
        
        return float(base_elevation)
    
    def _create_bounding_box_fallback(
        self,
        building: Dict[str, Any],
        min_height: float
    ) -> Optional[trimesh.Trimesh]:
        """
        Create a simple bounding box mesh as fallback for failed extrusions
        
        When complex polygon extrusion fails, this creates a simple rectangular
        box using the building's bounding coordinates.
        
        Args:
            building: Building dictionary with coordinates
            min_height: Minimum building height
        
        Returns:
            Simple box mesh or None if unable to create
        """
        try:
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
            height = max(height, min_height)
            
            # Convert to local coordinates
            lons = [coord[0] for coord in coordinates]
            lats = [coord[1] for coord in coordinates]
            
            xs, zs = self.transformer.latlon_array_to_local(
                np.array(lats),
                np.array(lons)
            )
            
            # Negate X and Z for Unity/Blender convention
            xs = -xs
            zs = -zs
            
            # Get bounding box (in X-Z plane)
            min_x, max_x = np.min(xs), np.max(xs)
            min_z, max_z = np.min(zs), np.max(zs)
            
            # Sample terrain elevation
            base_elevation = 0.0
            if self.terrain_mesh is not None:
                centroid_2d = np.array([[np.mean(xs), np.mean(zs)]])
                base_elevation = self._sample_terrain_elevation(centroid_2d)
            
            # Create simple box (in X-Z plane)
            box_coords = np.array([
                [min_x, min_z],
                [max_x, min_z],
                [max_x, max_z],
                [min_x, max_z],
                [min_x, min_z]  # Close the polygon
            ])
            
            # Extrude simple box
            polygon = Polygon(box_coords)
            mesh = trimesh.creation.extrude_polygon(polygon, height=height)
            
            # Rotate to Y-up coordinate system
            rotation_matrix = trimesh.transformations.rotation_matrix(
                angle=np.radians(-90),
                direction=[1, 0, 0],
                point=[0, 0, 0]
            )
            mesh.apply_transform(rotation_matrix)
            
            # Offset to terrain (Y is up)
            if base_elevation != 0.0:
                mesh.vertices[:, 1] += base_elevation
            
            return mesh
            
        except Exception as e:
            print(f"Bounding box fallback failed: {e}")
            return None
    
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

