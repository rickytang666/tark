"""
analyze elevation data to understand terrain roughness
"""
import sys
from pathlib import Path
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_elevation():
    """analyze elevation data statistics"""
    
    # load test elevation data
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    elevation_data = np.load(fixtures_dir / "test_elevation_data.npy")
    
    print("elevation data analysis")
    print("=" * 60)
    
    rows, cols = elevation_data.shape
    print(f"\nshape: {rows} x {cols}")
    print(f"min: {np.min(elevation_data):.2f}m")
    print(f"max: {np.max(elevation_data):.2f}m")
    print(f"mean: {np.mean(elevation_data):.2f}m")
    print(f"std: {np.std(elevation_data):.2f}m")
    
    # calculate gradients (elevation changes between adjacent pixels)
    grad_y = np.abs(np.diff(elevation_data, axis=0))
    grad_x = np.abs(np.diff(elevation_data, axis=1))
    
    print(f"\ngradients (pixel-to-pixel):")
    print(f"  vertical mean: {np.mean(grad_y):.2f}m, max: {np.max(grad_y):.2f}m")
    print(f"  horizontal mean: {np.mean(grad_x):.2f}m, max: {np.max(grad_x):.2f}m")
    
    # find areas with large gradients (noise/artifacts)
    threshold = 5.0
    large_grad_y = np.sum(grad_y > threshold)
    large_grad_x = np.sum(grad_x > threshold)
    
    print(f"\nsuspicious gradients (>{threshold}m):")
    print(f"  vertical: {large_grad_y} locations")
    print(f"  horizontal: {large_grad_x} locations")
    
    # sample a few locations to see actual values
    print(f"\nsample elevations (5x5 center):")
    center_r, center_c = rows // 2, cols // 2
    sample = elevation_data[center_r-2:center_r+3, center_c-2:center_c+3]
    for i, row in enumerate(sample):
        print(f"  row {center_r-2+i}: " + " ".join(f"{val:6.1f}" for val in row))
    
    # recommendation
    print(f"\nrecommendation:")
    std = np.std(elevation_data)
    if std < 5:
        print("  very flat terrain - use sigma=2-3")
    elif std < 20:
        print("  relatively flat - use sigma=2-3 for cleaner terrain")
    else:
        print("  significant elevation changes - current smoothing ok")

if __name__ == "__main__":
    analyze_elevation()
