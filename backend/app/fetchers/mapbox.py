"""
Mapbox Terrain-RGB API fetcher
Fetches elevation data from Mapbox terrain tiles
"""
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Tuple


class MapboxTerrainFetcher:
    """
    Fetches elevation data from Mapbox Terrain-RGB API
    """
    
    def __init__(self, access_token: str):
        """
        Initialize Mapbox fetcher
        
        Args:
            access_token: Mapbox API access token
        """
        self.access_token = access_token
        self.base_url = "https://api.mapbox.com/v4/mapbox.terrain-rgb"
    
    def fetch_elevation(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        zoom: int = 12
    ) -> Tuple[np.ndarray, dict]:
        """
        Fetch elevation data for bounding box
        
        Args:
            north: North latitude
            south: South latitude
            east: East longitude
            west: West longitude
            zoom: Zoom level (higher = more detail, default 12 ≈ 30m resolution)
        
        Returns:
            Tuple of (elevation_array, metadata)
            elevation_array: 2D numpy array of elevation values in meters
            metadata: Dict with bounds, resolution, etc.
        """
        # TODO: Implement Mapbox Terrain-RGB fetching
        # 1. Calculate tile coordinates for bbox
        # 2. Fetch tiles from Mapbox API
        # 3. Decode RGB values to elevation (formula: height = -10000 + ((R * 256 * 256 + G * 256 + B) * 0.1))
        # 4. Stitch tiles together if multiple
        # 5. Return elevation array
        
        raise NotImplementedError("Mapbox terrain fetching not yet implemented")
    
    def _decode_terrain_rgb(self, image: Image.Image) -> np.ndarray:
        """
        Decode Terrain-RGB image to elevation values
        
        Mapbox Terrain-RGB encoding:
        height = -10000 + ((R * 256 * 256 + G * 256 + B) * 0.1)
        
        Args:
            image: PIL Image in RGB format
        
        Returns:
            2D numpy array of elevation values in meters
        """
        img_array = np.array(image)
        r = img_array[:, :, 0].astype(np.float32)
        g = img_array[:, :, 1].astype(np.float32)
        b = img_array[:, :, 2].astype(np.float32)
        
        elevation = -10000 + ((r * 256 * 256 + g * 256 + b) * 0.1)
        return elevation

