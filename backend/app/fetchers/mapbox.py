"""
mapbox terrain-rgb api fetcher
fetches elevation data from mapbox terrain tiles
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
    fetches elevation data from mapbox terrain-rgb api
    """
    
    def __init__(self, access_token: str, smoothing_sigma: float = 1.0):
        """
        initialize mapbox fetcher
        
        args:
            access_token: mapbox api access token
            smoothing_sigma: gaussian smoothing sigma (0 = no smoothing, 1-2 = light, 3-5 = heavy)
        """
        self.access_token = access_token
        self.base_url = "https://api.mapbox.com/v4/mapbox.terrain-rgb"
        self.tile_size = 512  # mapbox tiles are 512x512 pixels
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
        fetch elevation data for bounding box
        
        args:
            north: north latitude
            south: south latitude
            east: east longitude
            west: west longitude
            zoom: zoom level (higher = more detail, default 12 approx 30m resolution)
        
        returns:
            tuple of (elevation_array, metadata)
            elevation_array: 2d numpy array of elevation values in meters
            metadata: dict with bounds, resolution, etc.
        """
        # 1. calculate tile coordinates for bbox
        # north latitude -> smaller y (top) -> min_tile_y
        # south latitude -> larger y (bottom) -> max_tile_y
        min_tile_x, min_tile_y = self._lat_lon_to_tile(north, west, zoom)
        max_tile_x, max_tile_y = self._lat_lon_to_tile(south, east, zoom)
        
        # 2. fetch all tiles that cover the bounding box
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
        
        # 3. stitch tiles together
        stitched_image = self._stitch_tiles(tiles)
        
        # 4. decode rgb to elevation
        elevation_array = self._decode_terrain_rgb(stitched_image)
        
        # 4.5. apply smoothing to reduce noise and tile seams
        if self.smoothing_sigma > 0:
            elevation_array = self._smooth_elevation(elevation_array)
        
        # 5. crop to exact bounding box
        elevation_cropped, crop_bounds = self._crop_to_bbox(
            elevation_array,
            north, south, east, west,
            min_tile_x, min_tile_y, max_tile_x, max_tile_y,
            zoom
        )
        
        # 6. prepare metadata
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
        convert latitude/longitude to tile coordinates
        
        args:
            lat: latitude
            lon: longitude
            zoom: zoom level
        
        returns:
            tuple of (tile_x, tile_y)
        """
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    def _fetch_tile(self, zoom: int, x: int, y: int) -> Image.Image:
        """
        fetch a single terrain tile from mapbox
        
        args:
            zoom: zoom level
            x: tile x coordinate
            y: tile y coordinate
        
        returns:
            pil image of the tile
        """
        url = f"{self.base_url}/{zoom}/{x}/{y}.pngraw"
        params = {"access_token": self.access_token}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # load image from response
            image = Image.open(BytesIO(response.content))
            return image
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to fetch tile {zoom}/{x}/{y}: {e}")
            return None
    
    def _stitch_tiles(self, tiles: List[List[Image.Image]]) -> Image.Image:
        """
        stitch multiple tiles together into a single image
        
        args:
            tiles: 2d list of pil images (rows of tiles)
        
        returns:
            single stitched pil image
        """
        if not tiles or not tiles[0]:
            raise ValueError("No tiles to stitch")
        
        # calculate dimensions
        rows = len(tiles)
        cols = len(tiles[0])
        tile_width = tiles[0][0].width
        tile_height = tiles[0][0].height
        
        # create new image
        total_width = cols * tile_width
        total_height = rows * tile_height
        stitched = Image.new('RGB', (total_width, total_height))
        
        # paste tiles
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
        crop elevation array to exact bounding box
        
        args:
            elevation_array: full elevation array from stitched tiles
            north, south, east, west: desired bounding box
            min_tile_x, min_tile_y, max_tile_x, max_tile_y: tile coordinates
            zoom: zoom level
        
        returns:
            tuple of (cropped_array, crop_bounds)
        """
        # for mvp, return the full array (cropping can be refined later)
        # this gives us slightly more area than requested, which is fine
        return elevation_array, {
            "north": north,
            "south": south,
            "east": east,
            "west": west
        }
    
    def _decode_terrain_rgb(self, image: Image.Image) -> np.ndarray:
        """
        decode terrain-rgb image to elevation values
        
        mapbox terrain-rgb encoding:
        height = -10000 + ((r * 256 * 256 + g * 256 + b) * 0.1)
        
        args:
            image: pil image in rgb format
        
        returns:
            2d numpy array of elevation values in meters
        """
        img_array = np.array(image)
        r = img_array[:, :, 0].astype(np.float32)
        g = img_array[:, :, 1].astype(np.float32)
        b = img_array[:, :, 2].astype(np.float32)
        
        elevation = -10000 + ((r * 256 * 256 + g * 256 + b) * 0.1)
        return elevation
    
    def _smooth_elevation(self, elevation: np.ndarray) -> np.ndarray:
        """
        apply gaussian smoothing to elevation data to reduce noise and tile seams
        
        this removes:
        - rgb encoding quantization artifacts
        - tile boundary discontinuities
        - high-frequency noise from compression
        
        args:
            elevation: 2d numpy array of elevation values
        
        returns:
            smoothed elevation array
        """
        # apply gaussian filter
        # sigma controls smoothing strength:
        #   0.5-1.0 = light smoothing (removes noise, preserves features)
        #   1.0-2.0 = medium smoothing (good for urban/suburban areas)
        #   2.0-5.0 = heavy smoothing (flattens terrain significantly)
        smoothed = gaussian_filter(elevation, sigma=self.smoothing_sigma, mode='reflect')
        
        return smoothed

