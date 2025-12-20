import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.overpass import OverpassFetcher

@pytest.fixture
def fetcher():
    return OverpassFetcher(timeout=10)

def test_extract_height(fetcher):
    """Test height extraction logic"""
    assert fetcher._extract_height({"height": "10.5"}) == 10.5
    assert fetcher._extract_height({"height": "10m"}) == 10.0
    assert fetcher._extract_height({"building:height": "20"}) == 20.0
    assert fetcher._extract_height({}) is None
    assert fetcher._extract_height({"height": "invalid"}) is None

def test_extract_levels(fetcher):
    """Test levels extraction logic"""
    assert fetcher._extract_levels({"building:levels": "5"}) == 5
    assert fetcher._extract_levels({"levels": "3"}) == 3
    assert fetcher._extract_levels({}) is None
    assert fetcher._extract_levels({"levels": "invalid"}) is None

@patch('requests.post')
def test_fetch_buildings(mock_post, fetcher):
    """Test full fetch flow with mocked API"""
    # Mock Overpass response
    mock_data = {
        "elements": [
            # Nodes for a square building
            {"type": "node", "id": 1, "lat": 43.0, "lon": -80.0},
            {"type": "node", "id": 2, "lat": 43.0, "lon": -80.01},
            {"type": "node", "id": 3, "lat": 43.01, "lon": -80.01},
            {"type": "node", "id": 4, "lat": 43.01, "lon": -80.0},
            # Way using these nodes
            {
                "type": "way",
                "id": 100,
                "nodes": [1, 2, 3, 4, 1],
                "tags": {
                    "building": "yes",
                    "height": "15"
                }
            }
        ]
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    mock_post.return_value = mock_response
    
    buildings = fetcher.fetch_buildings(43.1, 42.9, -79.9, -80.1)
    
    assert len(buildings) == 1
    b = buildings[0]
    assert b["id"] == 100
    assert b["type"] == "way"
    assert b["height"] == 15.0
    assert len(b["coordinates"]) == 5  # Closed loop
    
    # Verify coordinates match nodes
    expected_coords = [
        [-80.0, 43.0],    # Node 1
        [-80.01, 43.0],   # Node 2
        [-80.01, 43.01],  # Node 3
        [-80.0, 43.01],   # Node 4
        [-80.0, 43.0]     # Node 1
    ]
    assert b["coordinates"] == expected_coords
