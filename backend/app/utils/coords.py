"""
coordinate transformation utilities
converts between wgs84 and local tangent plane coordinates

coordinate system standard (unity/blender convention):
- x axis: east-west (positive = west, negative = east)
- y axis: elevation/up-down (positive = up)
- z axis: north-south (positive = south, negative = north)

note: x and z are negated from utm to match unity/blender bird's eye view orientation.
this y-up, left-handed system is standard for unity and blender.
"""
import pyproj
from typing import Tuple
import numpy as np


class CoordinateTransformer:
    """
    handles coordinate transformations for mesh generation
    """
    
    def __init__(self, center_lat: float, center_lon: float):
        """
        initialize transformer with center point
        
        args:
            center_lat: center latitude of the area
            center_lon: center longitude of the area
        """
        self.center_lat = center_lat
        self.center_lon = center_lon
        
        # wgs84 (gps coordinates)
        self.wgs84 = pyproj.CRS("EPSG:4326")
        
        # local tangent plane (meters from center)
        # using utm or custom local projection
        self.local_proj = self._create_local_projection()
        
        self.transformer = pyproj.Transformer.from_crs(
            self.wgs84,
            self.local_proj,
            always_xy=True
        )
        
        # calculate center point in projected coordinates
        self.center_x, self.center_y = self.transformer.transform(center_lon, center_lat)
    
    def _create_local_projection(self) -> pyproj.CRS:
        """
        create a local projection centered on the area
        
        returns:
            pyproj.crs for local coordinate system
        """
        # use utm zone for the center point
        utm_zone = int((self.center_lon + 180) / 6) + 1
        hemisphere = "north" if self.center_lat >= 0 else "south"
        
        # epsg code for utm zones
        if hemisphere == "north":
            epsg_code = 32600 + utm_zone
        else:
            epsg_code = 32700 + utm_zone
        
        return pyproj.CRS(f"EPSG:{epsg_code}")
    
    def latlon_to_local(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        convert lat/lon to local coordinates (meters from center)
        
        args:
            lat: latitude
            lon: longitude
        
        returns:
            (x, z) in meters from center
            x = east-west position
            z = north-south position
            (note: y-axis is reserved for elevation in 3d meshes)
        """
        x, y = self.transformer.transform(lon, lat)
        # subtract center to get relative coordinates
        return x - self.center_x, y - self.center_y
    
    def latlon_array_to_local(
        self,
        lats: np.ndarray,
        lons: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        convert arrays of lat/lon to local coordinates (meters from center)
        
        args:
            lats: array of latitudes
            lons: array of longitudes
        
        returns:
            (x_array, z_array) in meters from center
            x = east-west positions
            z = north-south positions
            (note: y-axis is reserved for elevation in 3d meshes)
        """
        xs, ys = self.transformer.transform(lons, lats)
        # subtract center to get relative coordinates
        return xs - self.center_x, ys - self.center_y

