import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from PIL import Image
from io import BytesIO
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.mapbox import MapboxTerrainFetcher

@pytest.fixture
def mock_terrain_rgb_image():
    """Create a dummy 512x512 Terrain-RGB image"""
    # Create a simple gradient image
    # R * 256*256 + G * 256 + B -> Elevation
    # Let's just make it simple: flat terrain at 0m
    # 0m = -10000 + (val * 0.1) => val = 100000 => 0x0186A0
    # R=1, G=134, B=160
    width, height = 512, 512
    color = (1, 134, 160)
    image = Image.new('RGB', (width, height), color)
    return image

@pytest.fixture
def fetcher():
    return MapboxTerrainFetcher(access_token="fake_token")

def test_lat_lon_to_tile(fetcher):
    """Test coordinate to tile conversion"""
    # Waterloo: ~43.4723, -80.5449
    # Zoom 12
    x, y = fetcher._lat_lon_to_tile(43.4723, -80.5449, 12)
    assert isinstance(x, int)
    assert isinstance(y, int)
    # Expected values for this location at zoom 12
    assert x == 1131
    assert y == 1506

def test_decode_terrain_rgb(fetcher, mock_terrain_rgb_image):
    """Test RGB to elevation decoding"""
    # The mock image is set to 0m elevation
    elevation = fetcher._decode_terrain_rgb(mock_terrain_rgb_image)
    
    assert elevation.shape == (512, 512)
    # Allow small float error
    assert np.allclose(elevation, 0.0, atol=0.1)

@patch('requests.get')
def test_fetch_elevation(mock_get, fetcher, mock_terrain_rgb_image):
    """Test full fetch flow with mocked API"""
    # Setup mock response
    img_byte_arr = BytesIO()
    mock_terrain_rgb_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_byte_arr.getvalue()
    mock_get.return_value = mock_response

    # Call fetch_elevation
    # Bounds roughly matching tile 1131, 1506 at zoom 12
    north, south = 43.5, 43.4
    east, west = -80.5, -80.6
    
    elevation, metadata = fetcher.fetch_elevation(north, south, east, west, zoom=12)
    
    assert isinstance(elevation, np.ndarray)
    assert len(elevation.shape) == 2
    assert metadata['tiles_fetched'] > 0
    assert metadata['min_elevation'] is not None
    assert metadata['max_elevation'] is not None
