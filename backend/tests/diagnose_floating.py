"""
Diagnostic script to analyze the floating buildings issue
Reads the generated OBJ file and analyzes coordinate distributions
"""
import numpy as np
import re

def analyze_obj(filepath):
    """Analyze vertex coordinates in an OBJ file"""
    vertices = []
    
    print(f"📖 Reading {filepath}...")
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.strip().split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append([x, y, z])
    
    vertices = np.array(vertices)
    print(f"✅ Read {len(vertices):,} vertices\n")
    
    # Analyze distributions
    print("📊 Coordinate Ranges:")
    print(f"   X: {vertices[:, 0].min():.2f} to {vertices[:, 0].max():.2f}")
    print(f"   Y: {vertices[:, 1].min():.2f} to {vertices[:, 1].max():.2f}")
    print(f"   Z: {vertices[:, 2].min():.2f} to {vertices[:, 2].max():.2f}\n")
    
    # Assume first 65536 vertices are terrain (256x256 grid)
    terrain_count = 65536
    if len(vertices) > terrain_count:
        terrain_verts = vertices[:terrain_count]
        building_verts = vertices[terrain_count:]
        
        print(f"🏔️  Terrain vertices ({len(terrain_verts):,}):")
        print(f"   X: {terrain_verts[:, 0].min():.2f} to {terrain_verts[:, 0].max():.2f}")
        print(f"   Y: {terrain_verts[:, 1].min():.2f} to {terrain_verts[:, 1].max():.2f}")
        print(f"   Z: {terrain_verts[:, 2].min():.2f} to {terrain_verts[:, 2].max():.2f}\n")
        
        print(f"🏢 Building vertices ({len(building_verts):,}):")
        print(f"   X: {building_verts[:, 0].min():.2f} to {building_verts[:, 0].max():.2f}")
        print(f"   Y: {building_verts[:, 1].min():.2f} to {building_verts[:, 1].max():.2f}")
        print(f"   Z: {building_verts[:, 2].min():.2f} to {building_verts[:, 2].max():.2f}")
        
        # Group building vertices by Y coordinate to find base elevations
        # Buildings are extruded vertically, so vertices with the same Y are likely on the same floor
        unique_y = np.unique(np.round(building_verts[:, 1], 1))
        print(f"   Unique Y levels: {len(unique_y)}")
        print(f"   Likely building base elevations (lowest ~10): {sorted(unique_y)[:10]}\n")
        
        # Check for buildings outside terrain bounds
        terrain_x_min, terrain_x_max = terrain_verts[:, 0].min(), terrain_verts[:, 0].max()
        terrain_z_min, terrain_z_max = terrain_verts[:, 2].min(), terrain_verts[:, 2].max()
        
        buildings_outside_x = np.sum((building_verts[:, 0] < terrain_x_min) | (building_verts[:, 0] > terrain_x_max))
        buildings_outside_z = np.sum((building_verts[:, 2] < terrain_z_min) | (building_verts[:, 2] > terrain_z_max))
        
        print("🔍 Overlap Analysis:")
        print(f"   Building vertices outside terrain X bounds: {buildings_outside_x} ({buildings_outside_x/len(building_verts)*100:.1f}%)")
        print(f"   Building vertices outside terrain Z bounds: {buildings_outside_z} ({buildings_outside_z/len(building_verts)*100:.1f}%)\n")
        
        # Analyze Y (elevation) distribution
        print("📈 Elevation Analysis:")
        terrain_y_mean = terrain_verts[:, 1].mean()
        terrain_y_std = terrain_verts[:, 1].std()
        building_y_min = building_verts[:, 1].min()
        building_y_max = building_verts[:, 1].max()
        
        print(f"   Terrain Y mean: {terrain_y_mean:.2f}m ± {terrain_y_std:.2f}m")
        print(f"   Building base Y range: {building_y_min:.2f}m to {building_y_max:.2f}m")
        
        # Check how many buildings are significantly above terrain
        buildings_too_high = np.sum(building_verts[:, 1] > terrain_y_mean + 3 * terrain_y_std)
        buildings_too_low = np.sum(building_verts[:, 1] < terrain_verts[:, 1].min() - 5)
        
        print(f"   Building vertices >3σ above terrain mean: {buildings_too_high} ({buildings_too_high/len(building_verts)*100:.1f}%)")
        print(f"   Building vertices below terrain minimum: {buildings_too_low} ({buildings_too_low/len(building_verts)*100:.1f}%)\n")
        
        if buildings_too_high > len(building_verts) * 0.1:
            print("❌ ISSUE DETECTED: Many buildings are significantly elevated above terrain!")
            print("   This suggests elevation sampling is using wrong terrain vertices.\n")
        elif buildings_outside_x > len(building_verts) * 0.1 or buildings_outside_z > len(building_verts) * 0.1:
            print("❌ ISSUE DETECTED: Many buildings are outside terrain bounds!")
            print("   This means buildings can't sample correct terrain elevation.\n")
        else:
            print("✅ Buildings appear to be within reasonable bounds.\n")

if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "temp/scene.obj"
    analyze_obj(filepath)

