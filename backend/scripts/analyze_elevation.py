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
    
    print("ELEVATION DATA ANALYSIS")
    print("=" * 60)
    print()
    
    rows, cols = elevation_data.shape
    print(f"shape: {rows} x {cols}")
    print(f"min elevation: {np.min(elevation_data):.2f}m")
    print(f"max elevation: {np.max(elevation_data):.2f}m")
    print(f"mean elevation: {np.mean(elevation_data):.2f}m")
    print(f"std deviation: {np.std(elevation_data):.2f}m")
    print()
    
    # calculate gradients (elevation changes between adjacent pixels)
    grad_y = np.abs(np.diff(elevation_data, axis=0))
    grad_x = np.abs(np.diff(elevation_data, axis=1))
    
    print("ELEVATION GRADIENTS (pixel-to-pixel changes):")
    print(f"  vertical gradient mean: {np.mean(grad_y):.2f}m")
    print(f"  vertical gradient max: {np.max(grad_y):.2f}m")
    print(f"  horizontal gradient mean: {np.mean(grad_x):.2f}m")
    print(f"  horizontal gradient max: {np.max(grad_x):.2f}m")
    print()
    
    # find areas with large gradients (noise/artifacts)
    threshold = 5.0  # 5m change between adjacent pixels is suspicious
    large_grad_y = np.sum(grad_y > threshold)
    large_grad_x = np.sum(grad_x > threshold)
    
    print(f"SUSPICIOUS GRADIENTS (>{threshold}m between pixels):")
    print(f"  vertical: {large_grad_y} locations")
    print(f"  horizontal: {large_grad_x} locations")
    print()
    
    # sample a few locations to see actual values
    print("SAMPLE ELEVATIONS (5x5 grid from center):")
    center_r, center_c = rows // 2, cols // 2
    sample = elevation_data[center_r-2:center_r+3, center_c-2:center_c+3]
    for i, row in enumerate(sample):
        print(f"  row {center_r-2+i}: " + " ".join(f"{val:6.1f}" for val in row))
    print()
    
    # check for tile seams (sudden changes at regular intervals)
    print("CHECKING FOR TILE SEAMS:")
    tile_size = 512
    if rows >= tile_size or cols >= tile_size:
        print(f"  data spans multiple tiles (tile_size={tile_size})")
        # check gradients at tile boundaries
        if rows >= tile_size:
            seam_grad = np.abs(elevation_data[tile_size-1, :] - elevation_data[tile_size, :])
            print(f"  horizontal seam gradient (row {tile_size}): mean={np.mean(seam_grad):.2f}m, max={np.max(seam_grad):.2f}m")
    else:
        print(f"  data is within single tile")
    print()
    
    # recommendation
    print("RECOMMENDATION:")
    std = np.std(elevation_data)
    if std < 5:
        print("  terrain is very flat - consider higher smoothing (sigma=2-3)")
    elif std < 20:
        print("  terrain is relatively flat - current smoothing (sigma=1) may show noise")
        print("  suggest sigma=2-3 for cleaner terrain")
    else:
        print("  terrain has significant elevation changes")
        print("  current smoothing should be okay")

if __name__ == "__main__":
    analyze_elevation()
