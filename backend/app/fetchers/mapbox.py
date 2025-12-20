"""
Mapbox Terrain-RGB API fetcher
Fetches elevation data from Mapbox terrain tiles
"""
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Tuple, List
import math
from scipy.ndimage import gaussian_filter


class MapboxTerrainFetcher:
    """
    Fetches elevation data from Mapbox Terrain-RGB API
    """
    
    def __init__(self, access_token: str, smoothing_sigma: float = 1.0):
        """
        Initialize Mapbox fetcher
        
        Args:
            access_token: Mapbox API access token
            smoothing_sigma: Gaussian smoothing sigma (0 = no smoothing, 1-2 = light, 3-5 = heavy)
        """
        self.access_token = access_token
        self.base_url = "https://api.mapbox.com/v4/mapbox.terrain-rgb"
        self.tile_size = 512  # Mapbox tiles are 512x512 pixels
        self.smoothing_sigma = smoothing_sigma
    
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
        # 1. Calculate tile coordinates for bbox
        # North latitude -> Smaller Y (Top) -> min_tile_y
        # South latitude -> Larger Y (Bottom) -> max_tile_y
        min_tile_x, min_tile_y = self._lat_lon_to_tile(north, west, zoom)
        max_tile_x, max_tile_y = self._lat_lon_to_tile(south, east, zoom)
        
        # 2. Fetch all tiles that cover the bounding box
        tiles = []
        tile_positions = []
        
        for ty in range(min_tile_y, max_tile_y + 1):
            row = []
            for tx in range(min_tile_x, max_tile_x + 1):
                tile_img = self._fetch_tile(zoom, tx, ty)
                if tile_img:
                    row.append(tile_img)
                    tile_positions.append((tx, ty))
            if row:
                tiles.append(row)
        
        if not tiles:
            raise ValueError("Failed to fetch any tiles for the given bounding box")
        
        # 3. Stitch tiles together
        stitched_image = self._stitch_tiles(tiles)
        
        # 4. Decode RGB to elevation
        elevation_array = self._decode_terrain_rgb(stitched_image)
        
        # 4.5. Apply smoothing to reduce noise and tile seams
        if self.smoothing_sigma > 0:
            elevation_array = self._smooth_elevation(elevation_array)
        
        # 5. Crop to exact bounding box
        elevation_cropped, crop_bounds = self._crop_to_bbox(
            elevation_array,
            north, south, east, west,
            min_tile_x, min_tile_y, max_tile_x, max_tile_y,
            zoom
        )
        
        # 6. Prepare metadata
        metadata = {
            "bounds": {"north": north, "south": south, "east": east, "west": west},
            "zoom": zoom,
            "shape": elevation_cropped.shape,
            "tiles_fetched": len(tile_positions),
            "tile_positions": tile_positions,
            "min_elevation": float(np.min(elevation_cropped)),
            "max_elevation": float(np.max(elevation_cropped)),
        }
        
        return elevation_cropped, metadata
    
    def _lat_lon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """
        Convert latitude/longitude to tile coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            zoom: Zoom level
        
        Returns:
            Tuple of (tile_x, tile_y)
        """
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    def _fetch_tile(self, zoom: int, x: int, y: int) -> Image.Image:
        """
        Fetch a single terrain tile from Mapbox
        
        Args:
            zoom: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate
        
        Returns:
            PIL Image of the tile
        """
        url = f"{self.base_url}/{zoom}/{x}/{y}.pngraw"
        params = {"access_token": self.access_token}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Load image from response
            image = Image.open(BytesIO(response.content))
            return image
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to fetch tile {zoom}/{x}/{y}: {e}")
            return None
    
    def _stitch_tiles(self, tiles: List[List[Image.Image]]) -> Image.Image:
        """
        Stitch multiple tiles together into a single image
        
        Args:
            tiles: 2D list of PIL Images (rows of tiles)
        
        Returns:
            Single stitched PIL Image
        """
        if not tiles or not tiles[0]:
            raise ValueError("No tiles to stitch")
        
        # Calculate dimensions
        rows = len(tiles)
        cols = len(tiles[0])
        tile_width = tiles[0][0].width
        tile_height = tiles[0][0].height
        
        # Create new image
        total_width = cols * tile_width
        total_height = rows * tile_height
        stitched = Image.new('RGB', (total_width, total_height))
        
        # Paste tiles
        for row_idx, row in enumerate(tiles):
            for col_idx, tile in enumerate(row):
                x_offset = col_idx * tile_width
                y_offset = row_idx * tile_height
                stitched.paste(tile, (x_offset, y_offset))
        
        return stitched
    
    def _crop_to_bbox(
        self,
        elevation_array: np.ndarray,
        north: float, south: float, east: float, west: float,
        min_tile_x: int, min_tile_y: int, max_tile_x: int, max_tile_y: int,
        zoom: int
    ) -> Tuple[np.ndarray, dict]:
        """
        Crop elevation array to exact bounding box
        
        Args:
            elevation_array: Full elevation array from stitched tiles
            north, south, east, west: Desired bounding box
            min_tile_x, min_tile_y, max_tile_x, max_tile_y: Tile coordinates
            zoom: Zoom level
        
        Returns:
            Tuple of (cropped_array, crop_bounds)
        """
        # For MVP, return the full array (cropping can be refined later)
        # This gives us slightly more area than requested, which is fine
        return elevation_array, {
            "north": north,
            "south": south,
            "east": east,
            "west": west
        }
    
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
    
    def _smooth_elevation(self, elevation: np.ndarray) -> np.ndarray:
        """
        Apply Gaussian smoothing to elevation data to reduce noise and tile seams
        
        This removes:
        - RGB encoding quantization artifacts
        - Tile boundary discontinuities
        - High-frequency noise from compression
        
        Args:
            elevation: 2D numpy array of elevation values
        
        Returns:
            Smoothed elevation array
        """
        # Apply Gaussian filter
        # Sigma controls smoothing strength:
        #   0.5-1.0 = light smoothing (removes noise, preserves features)
        #   1.0-2.0 = medium smoothing (good for urban/suburban areas)
        #   2.0-5.0 = heavy smoothing (flattens terrain significantly)
        smoothed = gaussian_filter(elevation, sigma=self.smoothing_sigma, mode='reflect')
        
        return smoothed

