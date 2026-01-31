"""
fetch and save test data for regression testing

downloads mapbox elevation data for test area and saves it
so we can run tests without hitting the API every time
"""
import sys
import os
import json
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.mapbox import MapboxTerrainFetcher
from dotenv import load_dotenv

load_dotenv()

def fetch_test_data():
    """fetch and save test elevation data"""
    
    # load test config
    config_path = Path(__file__).parent.parent / "tests" / "fixtures" / "test_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    test_area = config["test_area"]
    bbox = test_area["bbox"]
    
    print(f"fetching test data for: {test_area['name']}")
    print(f"  bbox: N={bbox['north']}, S={bbox['south']}, E={bbox['east']}, W={bbox['west']}")
    print(f"  zoom: {test_area['zoom']}")
    
    # fetch elevation data
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("ERROR: MAPBOX_ACCESS_TOKEN not found in .env")
        return
    
    fetcher = MapboxTerrainFetcher(mapbox_token, smoothing_sigma=1.0)
    elevation_data, metadata = fetcher.fetch_elevation(
        bbox["north"],
        bbox["south"],
        bbox["east"],
        bbox["west"],
        zoom=test_area["zoom"]
    )
    
    print(f"  fetched: {elevation_data.shape[0]} x {elevation_data.shape[1]} pixels")
    print(f"  elevation range: {metadata['min_elevation']:.2f}m to {metadata['max_elevation']:.2f}m")
    
    # save elevation data
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    
    output_path = fixtures_dir / "test_elevation_data.npy"
    np.save(output_path, elevation_data)
    
    # save metadata
    metadata_path = fixtures_dir / "test_elevation_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nsaved:")
    print(f"  {output_path}")
    print(f"  {metadata_path}")
    print("\nready for testing")

if __name__ == "__main__":
    fetch_test_data()
