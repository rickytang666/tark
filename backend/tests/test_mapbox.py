"""
Test script for Mapbox Terrain-RGB fetcher
Tests fetching elevation data for a small area
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.mapbox import MapboxTerrainFetcher

# Load environment variables from .env file
load_dotenv()

def test_mapbox_fetcher():
    """Test the Mapbox terrain fetcher with a small area"""
    
    # Get access token from environment
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    
    if not access_token:
        print("❌ Error: MAPBOX_ACCESS_TOKEN not found")
        print("\nTo set it up:")
        print("  1. Copy .env.example to .env:")
        print("     cp .env.example .env")
        print("  2. Edit .env and add your Mapbox token")
        print("  3. Get a free token from: https://account.mapbox.com/access-tokens/")
        return False
    
    print("🗺️  Testing Mapbox Terrain-RGB Fetcher\n")
    
    # Test area: University of Waterloo, Ontario (2km × 2km)
    north = 43.482620
    south = 43.464602
    east = -80.525265
    west = -80.550290
    
    print(f"📍 Fetching elevation data for:")
    print(f"   North: {north}")
    print(f"   South: {south}")
    print(f"   East: {east}")
    print(f"   West: {west}")
    print(f"   Area: ~{((north-south)*111)*((east-west)*111):.2f} km²\n")
    
    try:
        # Initialize fetcher
        fetcher = MapboxTerrainFetcher(access_token)
        
        # Fetch elevation data
        print("⏳ Fetching tiles from Mapbox...")
        elevation_array, metadata = fetcher.fetch_elevation(
            north=north,
            south=south,
            east=east,
            west=west,
            zoom=12  # ~30m resolution
        )
        
        print("✅ Successfully fetched elevation data!\n")
        
        # Display results
        print("📊 Results:")
        print(f"   Array shape: {metadata['shape']}")
        print(f"   Tiles fetched: {metadata['tiles_fetched']}")
        print(f"   Min elevation: {metadata['min_elevation']:.2f} meters")
        print(f"   Max elevation: {metadata['max_elevation']:.2f} meters")
        print(f"   Elevation range: {metadata['max_elevation'] - metadata['min_elevation']:.2f} meters")
        
        # Sanity checks
        print("\n🔍 Sanity checks:")
        
        if elevation_array.shape[0] > 0 and elevation_array.shape[1] > 0:
            print("   ✅ Array has valid dimensions")
        else:
            print("   ❌ Array has invalid dimensions")
            return False
        
        # San Francisco area should have elevations roughly between 0-300m
        if -100 < metadata['min_elevation'] < 500 and 0 < metadata['max_elevation'] < 500:
            print("   ✅ Elevation values look reasonable for SF area")
        else:
            print(f"   ⚠️  Elevation values seem unusual (expected 0-300m range)")
        
        if metadata['tiles_fetched'] > 0:
            print(f"   ✅ Fetched {metadata['tiles_fetched']} tile(s)")
        else:
            print("   ❌ No tiles fetched")
            return False
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during fetch: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mapbox_fetcher()
    sys.exit(0 if success else 1)

