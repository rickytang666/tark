import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from io import BytesIO
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.textures import MapboxSatelliteFetcher
from app.terrain import TerrainGenerator

@pytest.fixture
def fetcher():
    return MapboxSatelliteFetcher(access_token="fake_token")

@patch('requests.get')
def test_fetch_satellite_image(mock_get, fetcher, tmp_path):
    """Test fetching satellite imagery with mocked API"""
    # Create mock image
    width, height = 512, 512
    mock_image = Image.new('RGB', (width, height), color='green')
    img_byte_arr = BytesIO()
    mock_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = img_byte_arr.getvalue()
    mock_get.return_value = mock_response
    
    output_path = tmp_path / "satellite.png"
    
    image, saved_path = fetcher.fetch_satellite_image(
        north=43.5, south=43.4, east=-80.4, west=-80.5,
        width=512, height=512,
        output_path=str(output_path)
    )
    
    assert isinstance(image, Image.Image)
    assert image.size == (512, 512)
    assert saved_path == str(output_path)
    assert output_path.exists()

def test_terrain_uv_generation():
    """Test that generated terrain has 0-1 UV coordinates"""
    
    # Synthetic terrain
    elevation_data = np.zeros((10, 10))
    # Bounds doesn't strictly matter for UVs as UVs are normalized to 0-1 based on bounds
    bounds = (-80.5, 43.4, -80.4, 43.5)
    
    terrain_gen = TerrainGenerator()
    mesh = terrain_gen.generate_mesh(
        elevation_data, 
        bounds, 
        resolution=100.0,
        generate_uvs=True
    )
    
    # Check that UVs exist
    assert mesh.visual.uv is not None
    uvs = mesh.visual.uv
    
    assert len(uvs) == len(mesh.vertices)
    
    # Check range 0-1
    assert uvs.min() >= 0.0 - 1e-6
    assert uvs.max() <= 1.0 + 1e-6
    
    # Check distribution
    # U should cover full range
    assert np.isclose(uvs[:, 0].min(), 0.0)
    assert np.isclose(uvs[:, 0].max(), 1.0)
    # V should cover full range
    assert np.isclose(uvs[:, 1].min(), 0.0)
    assert np.isclose(uvs[:, 1].max(), 1.0)
