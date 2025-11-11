"""
Test script for building extrusion
Tests converting building footprints to 3D meshes
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetchers.overpass import OverpassFetcher
from app.buildings import BuildingExtruder
from app.utils.mesh import merge_meshes


def test_building_extrusion():
    """Test building extrusion with real OSM data"""
    
    print("🏢 Testing Building Extrusion\n")
    
    # Test area: Small SF region
    north = 37.7779
    south = 37.7719
    east = -122.4294
    west = -122.4394
    
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2
    
    print(f"📍 Test area:")
    print(f"   Center: ({center_lat:.4f}, {center_lon:.4f})\n")
    
    try:
        # 1. Fetch building data
        print("⏳ Fetching building data from OSM...")
        fetcher = OverpassFetcher(timeout=25)
        buildings = fetcher.fetch_buildings(
            north=north, south=south, east=east, west=west
        )
        print(f"✅ Fetched {len(buildings)} buildings\n")
        
        # 2. Extrude buildings
        print("⏳ Extruding buildings to 3D meshes...")
        extruder = BuildingExtruder(center_lat, center_lon)
        building_meshes = extruder.extrude_buildings(buildings, min_height=3.0)
        print(f"✅ Extruded {len(building_meshes)} buildings\n")
        
        # 3. Display results
        print("📊 Extrusion Statistics:")
        print(f"   Total buildings fetched: {len(buildings)}")
        print(f"   Successfully extruded: {len(building_meshes)}")
        print(f"   Success rate: {len(building_meshes)/len(buildings)*100:.1f}%")
        
        if building_meshes:
            total_vertices = sum(len(m.vertices) for m in building_meshes)
            total_faces = sum(len(m.faces) for m in building_meshes)
            print(f"   Total vertices: {total_vertices:,}")
            print(f"   Total faces: {total_faces:,}")
            
            # Sample building stats
            print(f"\n   Sample buildings:")
            for i, mesh in enumerate(building_meshes[:3]):
                building = buildings[i]
                height = building.get("height") or extruder.estimate_height(
                    building.get("building_type", "yes"),
                    building.get("levels")
                )
                print(f"     {i+1}. Type: {building['building_type']}, "
                      f"Height: {height:.1f}m, "
                      f"Vertices: {len(mesh.vertices)}, "
                      f"Faces: {len(mesh.faces)}")
        
        # 4. Sanity checks
        print("\n🔍 Sanity checks:")
        
        if len(building_meshes) > 0:
            print(f"   ✅ Extruded {len(building_meshes)} building meshes")
        else:
            print("   ❌ No buildings extruded")
            return False
        
        # Check success rate
        success_rate = len(building_meshes) / len(buildings)
        if success_rate > 0.8:
            print(f"   ✅ High success rate: {success_rate*100:.1f}%")
        else:
            print(f"   ⚠️  Low success rate: {success_rate*100:.1f}%")
        
        # Check meshes are valid
        valid_count = sum(1 for m in building_meshes if len(m.vertices) > 0 and len(m.faces) > 0)
        if valid_count == len(building_meshes):
            print(f"   ✅ All meshes have vertices and faces")
        
        # Check buildings have height
        avg_height = sum(m.vertices[:, 2].max() for m in building_meshes) / len(building_meshes)
        print(f"   ✅ Average building height: {avg_height:.1f}m")
        
        # 5. Merge all buildings into single mesh
        print("\n⏳ Merging all buildings into single mesh...")
        merged_mesh = merge_meshes(building_meshes)
        print(f"✅ Merged mesh: {len(merged_mesh.vertices):,} vertices, {len(merged_mesh.faces):,} faces")
        
        # 6. Export to file
        output_path = Path(__file__).parent.parent / "temp" / "test_buildings.obj"
        output_path.parent.mkdir(exist_ok=True)
        merged_mesh.export(str(output_path))
        print(f"\n💾 Exported buildings to: {output_path}")
        print("   Import into Blender/Unity to visualize!")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_building_extrusion()
    sys.exit(0 if success else 1)

