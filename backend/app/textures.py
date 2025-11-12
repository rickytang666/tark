"""
Texture generation and fetching for meshes
Handles satellite imagery and procedural textures
"""
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional
import os


class MapboxSatelliteFetcher:
    """
    Fetches satellite imagery from Mapbox Static API
    """
    
    def __init__(self, access_token: str):
        """
        Initialize satellite fetcher
        
        Args:
            access_token: Mapbox API access token
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
        Fetch satellite imagery for bounding box
        
        Args:
            north: North latitude
            south: South latitude
            east: East longitude
            west: West longitude
            width: Image width in pixels (max 1280 for free tier)
            height: Image height in pixels (max 1280 for free tier)
            output_path: Optional path to save the image
        
        Returns:
            Tuple of (PIL Image, saved_path)
        """
        # Mapbox static API endpoint
        # Format: /styles/v1/{username}/{style_id}/static/{bbox}/{width}x{height}
        bbox = f"[{west},{south},{east},{north}]"
        
        # Clamp to free tier limits
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
            
            # Load image from response
            image = Image.open(BytesIO(response.content))
            
            # Save if output path provided
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
        Calculate recommended texture resolution based on bbox size
        
        Args:
            north, south, east, west: Bounding box coordinates
        
        Returns:
            Tuple of (width, height) in pixels
        """
        # Calculate approximate bbox dimensions in meters
        center_lat = (north + south) / 2
        lat_meters = abs(north - south) * 111000
        lng_meters = abs(east - west) * 111000 * abs(np.cos(np.radians(center_lat)))
        
        # Target: ~1 meter per pixel for good detail
        # But clamp to Mapbox free tier limit (1280x1280)
        width = min(int(lng_meters), 1280)
        height = min(int(lat_meters), 1280)
        
        # Ensure minimum resolution
        width = max(width, 512)
        height = max(height, 512)
        
        return width, height


class TextureGenerator:
    """
    Generates procedural textures for buildings
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
        Generate procedural texture for building type
        
        Args:
            building_type: OSM building type (residential, commercial, etc.)
            width: Texture width in pixels
            height: Texture height in pixels
        
        Returns:
            PIL Image with procedural texture
        """
        # TODO: Implement procedural texture generation
        # For now, return solid colors based on type
        
        color_map = {
            "residential": (200, 180, 160),  # Beige/tan
            "commercial": (180, 180, 180),   # Light grey
            "industrial": (140, 120, 100),   # Brown
            "retail": (190, 170, 150),       # Light tan
            "office": (160, 160, 170),       # Blue-grey
            "apartments": (210, 190, 170),   # Light beige
            "house": (220, 200, 180),        # Cream
        }
        
        color = color_map.get(building_type, (180, 180, 180))
        image = Image.new('RGB', (width, height), color)
        
        return image

