"""
Test script to verify building placement fix
Checks that buildings are placed in the same coordinate system as terrain
"""
import numpy as np
import trimesh
from app.terrain import TerrainGenerator
from app.buildings import BuildingExtruder
from app.utils.coords import CoordinateTransformer


def test_coordinate_alignment():
    """Test that buildings and terrain are in the same coordinate system"""
    
    # Create synthetic elevation data (simple slope)
    elevation_data = np.array([
        [100, 100, 100, 100],
        [105, 105, 105, 105],
        [110, 110, 110, 110],
        [115, 115, 115, 115],
    ])
    
    # Test bounds (small area)
    west, south, east, north = -0.001, 51.5, 0.001, 51.502
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2
    
    # Generate terrain
    terrain_gen = TerrainGenerator()
    terrain_mesh = terrain_gen.generate_mesh(
        elevation_data=elevation_data,
        bounds=(west, south, east, north),
        resolution=30.0,
        generate_uvs=False
    )
    
    print("🔍 Before centering:")
    print(f"   Terrain X range: {terrain_mesh.vertices[:, 0].min():.2f} to {terrain_mesh.vertices[:, 0].max():.2f}")
    print(f"   Terrain Y range: {terrain_mesh.vertices[:, 1].min():.2f} to {terrain_mesh.vertices[:, 1].max():.2f}")
    print(f"   Terrain Z range: {terrain_mesh.vertices[:, 2].min():.2f} to {terrain_mesh.vertices[:, 2].max():.2f}")
    
    # Center terrain (as done in generator.py)
    terrain_centroid_xz = terrain_mesh.centroid.copy()
    terrain_centroid_xz[1] = 0  # Don't center Y
    terrain_mesh.vertices -= terrain_centroid_xz
    
    print("\n✅ After centering:")
    print(f"   Terrain X range: {terrain_mesh.vertices[:, 0].min():.2f} to {terrain_mesh.vertices[:, 0].max():.2f}")
    print(f"   Terrain Y range: {terrain_mesh.vertices[:, 1].min():.2f} to {terrain_mesh.vertices[:, 1].max():.2f}")
    print(f"   Terrain Z range: {terrain_mesh.vertices[:, 2].min():.2f} to {terrain_mesh.vertices[:, 2].max():.2f}")
    print(f"   Centering offset: X={terrain_centroid_xz[0]:.2f}, Z={terrain_centroid_xz[2]:.2f}")
    
    # Create a test building at the center
    building_data = [{
        "id": 1,
        "type": "way",
        "coordinates": [
            [center_lon - 0.0001, center_lat - 0.0001],
            [center_lon + 0.0001, center_lat - 0.0001],
            [center_lon + 0.0001, center_lat + 0.0001],
            [center_lon - 0.0001, center_lat + 0.0001],
            [center_lon - 0.0001, center_lat - 0.0001],
        ],
        "building_type": "yes",
        "height": None,
        "levels": 3,
        "name": "Test Building",
        "tags": {}
    }]
    
    # Extrude buildings with terrain offset
    building_extruder = BuildingExtruder(center_lat, center_lon, terrain_mesh, terrain_centroid_xz)
    building_meshes = building_extruder.extrude_buildings(building_data, min_height=3.0)
    
    if building_meshes:
        building_mesh = building_meshes[0]
        print("\n🏢 Building placement:")
        print(f"   Building X range: {building_mesh.vertices[:, 0].min():.2f} to {building_mesh.vertices[:, 0].max():.2f}")
        print(f"   Building Y range: {building_mesh.vertices[:, 1].min():.2f} to {building_mesh.vertices[:, 1].max():.2f}")
        print(f"   Building Z range: {building_mesh.vertices[:, 2].min():.2f} to {building_mesh.vertices[:, 2].max():.2f}")
        
        # Check if building X-Z coordinates are in the same range as terrain
        terrain_x_range = (terrain_mesh.vertices[:, 0].min(), terrain_mesh.vertices[:, 0].max())
        terrain_z_range = (terrain_mesh.vertices[:, 2].min(), terrain_mesh.vertices[:, 2].max())
        building_x_center = (building_mesh.vertices[:, 0].min() + building_mesh.vertices[:, 0].max()) / 2
        building_z_center = (building_mesh.vertices[:, 2].min() + building_mesh.vertices[:, 2].max()) / 2
        
        print("\n✅ Coordinate system check:")
        x_in_range = terrain_x_range[0] <= building_x_center <= terrain_x_range[1]
        z_in_range = terrain_z_range[0] <= building_z_center <= terrain_z_range[1]
        
        print(f"   Building X center ({building_x_center:.2f}) in terrain X range ({terrain_x_range[0]:.2f}, {terrain_x_range[1]:.2f}): {x_in_range}")
        print(f"   Building Z center ({building_z_center:.2f}) in terrain Z range ({terrain_z_range[0]:.2f}, {terrain_z_range[1]:.2f}): {z_in_range}")
        
        # Check if building Y (elevation) is reasonable
        terrain_y_range = (terrain_mesh.vertices[:, 1].min(), terrain_mesh.vertices[:, 1].max())
        building_base_y = building_mesh.vertices[:, 1].min()
        y_reasonable = terrain_y_range[0] - 5 <= building_base_y <= terrain_y_range[1] + 5
        
        print(f"   Building base Y ({building_base_y:.2f}) near terrain Y range ({terrain_y_range[0]:.2f}, {terrain_y_range[1]:.2f}): {y_reasonable}")
        
        if x_in_range and z_in_range and y_reasonable:
            print("\n✅ SUCCESS: Building is correctly placed in the same coordinate system as terrain!")
            return True
        else:
            print("\n❌ FAILURE: Building coordinate system mismatch detected!")
            return False
    else:
        print("\n❌ FAILURE: No buildings were generated!")
        return False


if __name__ == "__main__":
    success = test_coordinate_alignment()
    exit(0 if success else 1)

