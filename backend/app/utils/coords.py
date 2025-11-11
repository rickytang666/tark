"""
Coordinate transformation utilities
Converts between WGS84 and local tangent plane coordinates
"""
import pyproj
from typing import Tuple
import numpy as np


class CoordinateTransformer:
    """
    Handles coordinate transformations for mesh generation
    """
    
    def __init__(self, center_lat: float, center_lon: float):
        """
        Initialize transformer with center point
        
        Args:
            center_lat: Center latitude of the area
            center_lon: Center longitude of the area
        """
        self.center_lat = center_lat
        self.center_lon = center_lon
        
        # WGS84 (GPS coordinates)
        self.wgs84 = pyproj.CRS("EPSG:4326")
        
        # Local tangent plane (meters from center)
        # Using UTM or custom local projection
        self.local_proj = self._create_local_projection()
        
        self.transformer = pyproj.Transformer.from_crs(
            self.wgs84,
            self.local_proj,
            always_xy=True
        )
        
        # Calculate center point in projected coordinates
        self.center_x, self.center_y = self.transformer.transform(center_lon, center_lat)
    
    def _create_local_projection(self) -> pyproj.CRS:
        """
        Create a local projection centered on the area
        
        Returns:
            pyproj.CRS for local coordinate system
        """
        # Use UTM zone for the center point
        utm_zone = int((self.center_lon + 180) / 6) + 1
        hemisphere = "north" if self.center_lat >= 0 else "south"
        
        # EPSG code for UTM zones
        if hemisphere == "north":
            epsg_code = 32600 + utm_zone
        else:
            epsg_code = 32700 + utm_zone
        
        return pyproj.CRS(f"EPSG:{epsg_code}")
    
    def latlon_to_local(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Convert lat/lon to local coordinates (meters from center)
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            (x, y) in meters from center
        """
        x, y = self.transformer.transform(lon, lat)
        # Subtract center to get relative coordinates
        return x - self.center_x, y - self.center_y
    
    def latlon_array_to_local(
        self,
        lats: np.ndarray,
        lons: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert arrays of lat/lon to local coordinates (meters from center)
        
        Args:
            lats: Array of latitudes
            lons: Array of longitudes
        
        Returns:
            (x_array, y_array) in meters from center
        """
        xs, ys = self.transformer.transform(lons, lats)
        # Subtract center to get relative coordinates
        return xs - self.center_x, ys - self.center_y

