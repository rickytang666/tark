"""
coordinate transformation utilities
converts between wgs84 and local unity coordinates

coordinate system standard (unity/blender convention):
- x axis: east-west (positive = east)
- y axis: elevation/up-down (positive = up)
- z axis: north-south (positive = north)

this is a left-handed coordinate system standard for unity.
origin (0,0,0) is defined as the center lat/lon of the requested area.
"""
import pyproj
from typing import Tuple, Union
import numpy as np

class CoordinateTransformer:
    """
    handles coordinate transformations for mesh generation
    target: unity coordinate system (x=east, y=up, z=north)
    """
    
    def __init__(self, center_lat: float, center_lon: float):
        """
        initialize transformer with center point (origin)
        
        args:
            center_lat: center latitude of the area (becomes 0,0,0)
            center_lon: center longitude of the area (becomes 0,0,0)
        """
        self.center_lat = center_lat
        self.center_lon = center_lon
        
        # wgs84 (gps coordinates)
        self.wgs84 = pyproj.CRS("EPSG:4326")
        
        # local tangent plane (meters) using auto-detected UTM zone
        self.local_proj = self._create_local_projection()
        
        self.transformer = pyproj.Transformer.from_crs(
            self.wgs84,
            self.local_proj,
            always_xy=True
        )
        
        # calculate center point in projected coordinates (internal use only)
        self.origin_x, self.origin_y = self.transformer.transform(center_lon, center_lat)
    
    def _create_local_projection(self) -> pyproj.CRS:
        """
        create a local projection centered on the area
        uses standard UTM zones
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
        convert lat/lon to local unity coordinates (meters from center)
        
        args:
            lat: latitude
            lon: longitude
        
        returns:
            (x, z) in meters
            x = east (positive)
            z = north (positive)
        """
        # pyproj transforms (lon, lat) -> (easting, northing)
        easting, northing = self.transformer.transform(lon, lat)
        
        x = -(easting - self.origin_x)
        z = northing - self.origin_y
        
        return x, z
    
    def latlon_array_to_local(
        self,
        lats: np.ndarray,
        lons: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        vectorized conversion for arrays
        """
        eastings, northings = self.transformer.transform(lons, lats)
        
        xs = -(eastings - self.origin_x)
        zs = northings - self.origin_y
        
        return xs, zs
