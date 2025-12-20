import pytest
import numpy as np
import trimesh
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.terrain import TerrainGenerator

def test_terrain_generation_simple_plane():
    """Test generating a simple flat plane"""
    # 10x10 grid of 100m elevation
    elevation_data = np.full((10, 10), 100.0)
    
    # 1km x 1km bounds
    bounds = (-80.0, 43.0, -79.99, 43.01)
    
    generator = TerrainGenerator()
    mesh = generator.generate_mesh(
        elevation_data=elevation_data,
        bounds=bounds,
        resolution=100.0,
        generate_uvs=False
    )
    
    assert isinstance(mesh, trimesh.Trimesh)
    
    # Check vertex count: 10*10 = 100
    assert len(mesh.vertices) == 100
    
    # Check face count: (10-1)*(10-1)*2 = 81*2 = 162
    assert len(mesh.faces) == 162
    
    # Check elevation (z-axis)
    # It should be 100.0 everywhere
    # Note: generator might center the mesh or keep absolute coords.
    # Looking at previous implementation, it likely keeps absolute unless centered later.
    # Actually, let's just check the Z range equals 0 (flat) 
    # OR if it uses the values directly, Z min/max should be 100.
    
    z_values = mesh.vertices[:, 2]
    assert np.allclose(z_values, 100.0)

def test_terrain_generation_slope():
    """Test generating a slope"""
    # 10x10 gradient
    x = np.linspace(0, 10, 10)
    y = np.linspace(0, 10, 10)
    xv, yv = np.meshgrid(x, y)
    elevation_data = xv + yv  # simple slope
    
    bounds = (-80.0, 43.0, -79.99, 43.01)
    
    generator = TerrainGenerator()
    mesh = generator.generate_mesh(
        elevation_data=elevation_data,
        bounds=bounds,
        resolution=100.0
    )
    
    assert len(mesh.vertices) == 100
    
    # Check range
    z_values = mesh.vertices[:, 2]
    assert np.isclose(z_values.min(), 0.0)
    assert np.isclose(z_values.max(), 20.0)
