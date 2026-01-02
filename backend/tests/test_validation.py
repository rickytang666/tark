import pytest
import sys
from pathlib import Path

# add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import BoundingBox

def test_bbox_validation_too_small():
    """Test bbox too small (< 1km)"""
    # 100m x 100m
    bbox = BoundingBox(
        north=43.4730,
        south=43.4721,
        east=-80.5430,
        west=-80.5439
    )
    with pytest.raises(ValueError, match="area too small"):
        bbox.validate_bbox()

def test_bbox_validation_too_large():
    """Test bbox too large (> 5km)"""
    # 6km x 6km
    bbox = BoundingBox(
        north=43.5000,
        south=43.4460,
        east=-80.5000,
        west=-80.5800
    )
    with pytest.raises(ValueError, match="area too large"):
        bbox.validate_bbox()

def test_bbox_validation_valid():
    """Test valid bbox (approx 2km x 2km)"""
    bbox = BoundingBox(
        north=43.4822,
        south=43.4642,
        east=-80.5254,
        west=-80.5504
    )
    assert bbox.validate_bbox() is True

def test_bbox_validation_coordinates():
    """Test invalid coordinates logic"""
    # North < South
    bbox = BoundingBox(north=40.0, south=41.0, east=-80.0, west=-80.1)
    with pytest.raises(ValueError, match="north must be greater than south"):
        bbox.validate_bbox()
    
    # East < West
    bbox = BoundingBox(north=41.0, south=40.0, east=-80.1, west=-80.0)
    with pytest.raises(ValueError, match="east must be greater than west"):
        bbox.validate_bbox()
