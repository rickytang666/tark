"""
Test script for Overpass API building fetcher
Tests fetching building data from OpenStreetMap
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.overpass import OverpassFetcher


def test_overpass_fetcher():
    """Test the Overpass building fetcher with a small area"""
    
    print("🏢 Testing Overpass API Building Fetcher\n")
    
    # Test area: University of Waterloo, Ontario (2km × 2km)
    north = 43.482620
    south = 43.464602
    east = -80.525265
    west = -80.550290
    
    print(f"📍 Fetching building data for:")
    print(f"   North: {north}")
    print(f"   South: {south}")
    print(f"   East: {east}")
    print(f"   West: {west}\n")
    
    try:
        # Initialize fetcher
        fetcher = OverpassFetcher(timeout=25)
        
        # Fetch buildings
        print("⏳ Querying Overpass API...")
        buildings = fetcher.fetch_buildings(
            north=north,
            south=south,
            east=east,
            west=west
        )
        
        print("✅ Successfully fetched building data!\n")
        
        # Display results
        print("📊 Results:")
        print(f"   Total buildings: {len(buildings)}")
        
        # Count buildings with height data
        with_height = sum(1 for b in buildings if b["height"] is not None)
        with_levels = sum(1 for b in buildings if b["levels"] is not None)
        with_names = sum(1 for b in buildings if b["name"] is not None)
        
        print(f"   With height data: {with_height}")
        print(f"   With level data: {with_levels}")
        print(f"   With names: {with_names}")
        
        # Building types
        types = {}
        for b in buildings:
            btype = b["building_type"]
            types[btype] = types.get(btype, 0) + 1
        
        print(f"\n   Building types:")
        for btype, count in sorted(types.items(), key=lambda x: -x[1])[:5]:
            print(f"     {btype}: {count}")
        
        # Show a few examples
        if buildings:
            print(f"\n   Sample buildings:")
            for i, building in enumerate(buildings[:3]):
                print(f"     {i+1}. Type: {building['building_type']}, "
                      f"Height: {building['height'] or 'N/A'}, "
                      f"Levels: {building['levels'] or 'N/A'}, "
                      f"Coords: {len(building['coordinates'])} points")
        
        # Sanity checks
        print("\n🔍 Sanity checks:")
        
        if len(buildings) > 0:
            print(f"   ✅ Found {len(buildings)} building(s)")
        else:
            print("   ⚠️  No buildings found (area might be sparse)")
        
        # Check coordinate format
        if buildings and len(buildings[0]["coordinates"]) >= 3:
            print("   ✅ Building coordinates are valid polygons")
        
        # Check data structure
        required_keys = ["id", "type", "coordinates", "building_type", "height", "levels"]
        if buildings and all(key in buildings[0] for key in required_keys):
            print("   ✅ Building data structure is correct")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during fetch: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = test_overpass_fetcher()
    sys.exit(0 if success else 1)

