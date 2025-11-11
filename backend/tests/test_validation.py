"""
Test bbox validation with proper size constraints
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import BoundingBox


def test_bbox_validation():
    """Test bbox size validation"""
    
    print("🔍 Testing BBox Validation\n")
    
    # Test 1: Too small (100m × 100m) - should FAIL
    print("Test 1: 100m × 100m (too small)")
    try:
        bbox = BoundingBox(
            north=37.7749,
            south=37.7739,  # ~100m
            east=-122.4334,
            west=-122.4344  # ~100m
        )
        bbox.validate_bbox()
        print("   ❌ Should have failed but didn't\n")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {e}\n")
    
    # Test 2: Just right (1.5km × 1.5km) - should PASS
    print("Test 2: 1.5km × 1.5km (good size)")
    try:
        bbox = BoundingBox(
            north=37.7814,
            south=37.7679,  # ~1.5km
            east=-122.4244,
            west=-122.4424  # ~1.5km
        )
        bbox.validate_bbox()
        print("   ✅ Accepted\n")
    except ValueError as e:
        print(f"   ❌ Should have passed: {e}\n")
    
    # Test 3: Too large (6km × 6km) - should FAIL
    print("Test 3: 6km × 6km (too large)")
    try:
        bbox = BoundingBox(
            north=37.8000,
            south=37.7460,  # ~6km
            east=-122.3800,
            west=-122.4600  # ~6km
        )
        bbox.validate_bbox()
        print("   ❌ Should have failed but didn't\n")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {e}\n")
    
    # Test 4: Exactly 2km × 2km (ideal) - should PASS
    print("Test 4: 2km × 2km (ideal size)")
    try:
        bbox = BoundingBox(
            north=37.7839,
            south=37.7659,  # ~2km
            east=-122.4144,
            west=-122.4424  # ~2km
        )
        bbox.validate_bbox()
        print("   ✅ Accepted (ideal size for realistic terrain)\n")
    except ValueError as e:
        print(f"   ❌ Should have passed: {e}\n")
    
    print("✅ Validation tests complete!")


if __name__ == "__main__":
    test_bbox_validation()

