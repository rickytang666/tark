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
        
        xs, ys = self.transformer.latlon_array_to_local(
            np.array(lats),
            np.array(lons)
        )
        
        # Create 2D polygon
        footprint_2d = np.column_stack([xs, ys])
        
        # Convert holes (courtyards) to local meters
        holes_2d = []
        holes_coords = building.get("holes", [])
        for hole in holes_coords:
            if len(hole) >= 3:
                hole_lons = [coord[0] for coord in hole]
                hole_lats = [coord[1] for coord in hole]
                
                hole_xs, hole_ys = self.transformer.latlon_array_to_local(
                    np.array(hole_lats),
                    np.array(hole_lons)
                )
                holes_2d.append(np.column_stack([hole_xs, hole_ys]))
        
        # Sample terrain elevation if available
        base_elevation = 0.0
        if self.terrain_mesh is not None:
            base_elevation = self._sample_terrain_elevation(footprint_2d)
        
        # Extrude to 3D (with holes if present)
        mesh = self._extrude_polygon(footprint_2d, height, holes_2d)
        
        # Offset mesh to sit on terrain
        if base_elevation != 0.0:
            mesh.vertices[:, 2] += base_elevation
        
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
            footprint_2d: 2D polygon vertices (N x 2)
            height: Extrusion height in meters
            holes_2d: List of hole polygons for courtyards (optional)
        
        Returns:
            trimesh.Trimesh of extruded building
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
        mesh = trimesh.creation.extrude_polygon(polygon, height=height)
        
        return mesh
    
    def _sample_terrain_elevation(self, footprint_2d: np.ndarray) -> float:
        """
        Sample the terrain elevation at a building's footprint
        
        Uses the center point of the footprint to query terrain mesh elevation.
        
        Args:
            footprint_2d: 2D building footprint (N x 2)
        
        Returns:
            Base elevation in meters (Z coordinate)
        """
        if self.terrain_mesh is None:
            return 0.0
        
        # Calculate centroid of footprint
        centroid_x = np.mean(footprint_2d[:, 0])
        centroid_y = np.mean(footprint_2d[:, 1])
        
        # Find nearest terrain vertex to building centroid
        # We use the terrain mesh vertices as elevation samples
        terrain_xy = self.terrain_mesh.vertices[:, :2]  # Just X, Y
        terrain_z = self.terrain_mesh.vertices[:, 2]    # Just Z
        
        # Calculate distances to all terrain vertices
        distances = np.sqrt(
            (terrain_xy[:, 0] - centroid_x)**2 + 
            (terrain_xy[:, 1] - centroid_y)**2
        )
        
        # Find nearest vertex
        nearest_idx = np.argmin(distances)
        base_elevation = terrain_z[nearest_idx]
        
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
            
            xs, ys = self.transformer.latlon_array_to_local(
                np.array(lats),
                np.array(lons)
            )
            
            # Get bounding box
            min_x, max_x = np.min(xs), np.max(xs)
            min_y, max_y = np.min(ys), np.max(ys)
            
            # Sample terrain elevation
            base_elevation = 0.0
            if self.terrain_mesh is not None:
                centroid_2d = np.array([[np.mean(xs), np.mean(ys)]])
                base_elevation = self._sample_terrain_elevation(centroid_2d)
            
            # Create simple box
            box_coords = np.array([
                [min_x, min_y],
                [max_x, min_y],
                [max_x, max_y],
                [min_x, max_y],
                [min_x, min_y]  # Close the polygon
            ])
            
            # Extrude simple box
            polygon = Polygon(box_coords)
            mesh = trimesh.creation.extrude_polygon(polygon, height=height)
            
            # Offset to terrain
            if base_elevation != 0.0:
                mesh.vertices[:, 2] += base_elevation
            
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

