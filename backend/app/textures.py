"""
texture generation and fetching for meshes
handles satellite imagery and procedural textures
"""
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional
import os


class MapboxSatelliteFetcher:
    """
    fetches satellite imagery from mapbox static api
    """
    
    def __init__(self, access_token: str):
        """
        initialize satellite fetcher
        
        args:
            access_token: mapbox api access token
        """
        self.access_token = access_token
        self.base_url = "https://api.mapbox.com/styles/v1"
        self.style = "mapbox/satellite-v9"
    
    def fetch_satellite_image(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        width: int = 2048,
        height: int = 2048,
        output_path: Optional[str] = None
    ) -> Tuple[Image.Image, str]:
        """
        fetch satellite imagery for bounding box
        
        args:
            north: north latitude
            south: south latitude
            east: east longitude
            west: west longitude
            width: image width in pixels (max 1280 for free tier)
            height: image height in pixels (max 1280 for free tier)
            output_path: optional path to save the image
        
        returns:
            tuple of (pil image, saved_path)
        """
        # mapbox static api endpoint
        # format: /styles/v1/{username}/{style_id}/static/{bbox}/{width}x{height}
        bbox = f"[{west},{south},{east},{north}]"
        
        # clamp to free tier limits
        width = min(width, 1280)
        height = min(height, 1280)
        
        url = f"{self.base_url}/{self.style}/static/{bbox}/{width}x{height}"
        params = {
            "access_token": self.access_token
        }
        
        print(f"⏳ Fetching satellite imagery ({width}x{height})...")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # load image from response
            image = Image.open(BytesIO(response.content))
            
            # save if output path provided
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                image.save(output_path, format='PNG')
                print(f"✅ Satellite image saved: {output_path}")
                return image, output_path
            
            return image, None
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch satellite imagery: {e}")
    
    def get_recommended_resolution(
        self,
        north: float,
        south: float,
        east: float,
        west: float
    ) -> Tuple[int, int]:
        """
        calculate recommended texture resolution based on bbox size
        
        args:
            north, south, east, west: bounding box coordinates
        
        returns:
            tuple of (width, height) in pixels
        """
        # calculate approximate bbox dimensions in meters
        center_lat = (north + south) / 2
        lat_meters = abs(north - south) * 111000
        lng_meters = abs(east - west) * 111000 * abs(np.cos(np.radians(center_lat)))
        
        # target: ~1 meter per pixel for good detail
        # but clamp to mapbox free tier limit (1280x1280)
        width = min(int(lng_meters), 1280)
        height = min(int(lat_meters), 1280)
        
        # ensure minimum resolution
        width = max(width, 512)
        height = max(height, 512)
        
        return width, height


class TextureGenerator:
    """
    generates procedural textures for buildings
    """
    
    def __init__(self):
        pass
    
    def generate_building_texture(
        self,
        building_type: str,
        width: int = 512,
        height: int = 512
    ) -> Image.Image:
        """
        generate procedural texture for building type
        
        args:
            building_type: osm building type (residential, commercial, etc.)
            width: texture width in pixels
            height: texture height in pixels
        
        returns:
            pil image with procedural texture
        """
        # todo: implement procedural texture generation
        # for now, return solid colors based on type
        
        color_map = {
            "residential": (200, 180, 160),  # beige/tan
            "commercial": (180, 180, 180),   # light grey
            "industrial": (140, 120, 100),   # brown
            "retail": (190, 170, 150),       # light tan
            "office": (160, 160, 170),       # blue-grey
            "apartments": (210, 190, 170),   # light beige
            "house": (220, 200, 180),        # cream
        }
        
        color = color_map.get(building_type, (180, 180, 180))
        image = Image.new('RGB', (width, height), color)
        
        return image

