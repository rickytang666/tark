"""
Test ZIP export functionality
Verifies that all files are included in the ZIP
"""
import sys
import os
import zipfile
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.generator import MeshGenerator

load_dotenv()


def test_zip_export():
    """Test that generator creates all necessary files for ZIP export"""
    
    print("📦 Testing ZIP Export\n")
    
    # Get Mapbox token
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not access_token:
        print("❌ MAPBOX_ACCESS_TOKEN not found in .env")
        return False
    
    # Test area: small area for quick test
    north = 43.475
    south = 43.470
    east = -80.535
    west = -80.545
    
    print(f"📍 Test area:")
    print(f"   North: {north}, South: {south}")
    print(f"   East: {east}, West: {west}\n")
    
    try:
        import tempfile
        # use system temp dir to avoid cluttering workspace
        system_temp = tempfile.gettempdir()
        temp_dir = Path(system_temp) / "tark_gen_test"
        temp_dir.mkdir(exist_ok=True)
        
        # Generate mesh
        print("⏳ Generating mesh with textures (terrain only)...")
        generator = MeshGenerator(str(temp_dir), access_token)
        obj_path, mtl_path, texture_files = generator.generate(
            north=north, south=south, east=east, west=west,
            include_buildings=False,  # Skip buildings to avoid Overpass timeout
            include_textures=True
        )
        
        print(f"\n📊 Generated files:")
        print(f"   OBJ: {obj_path}")
        print(f"   MTL: {mtl_path}")
        print(f"   Textures: {texture_files}")
        
        # Collect all files for ZIP
        files_to_zip = [obj_path]
        
        if mtl_path and os.path.exists(mtl_path):
            files_to_zip.append(mtl_path)
        
        for texture_path in texture_files:
            if os.path.exists(texture_path):
                files_to_zip.append(texture_path)
        
        # Check for material_0.png (created by trimesh)
        obj_dir = os.path.dirname(obj_path)
        material_png = os.path.join(obj_dir, "material_0.png")
        if os.path.exists(material_png) and material_png not in files_to_zip:
            files_to_zip.append(material_png)
        
        print(f"\n📦 Files to include in ZIP:")
        for f in files_to_zip:
            if os.path.exists(f):
                size_kb = os.path.getsize(f) / 1024
                print(f"   ✅ {os.path.basename(f)} ({size_kb:.2f} KB)")
            else:
                print(f"   ❌ {os.path.basename(f)} (NOT FOUND)")
        
        # Create ZIP
        zip_path = temp_dir / "test_export.zip"
        print(f"\n⏳ Creating ZIP: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_zip:
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=os.path.basename(file_path))
        
        # Verify ZIP contents
        print(f"\n📊 ZIP contents:")
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for info in zipf.infolist():
                size_kb = info.file_size / 1024
                compressed_kb = info.compress_size / 1024
                ratio = (1 - info.compress_size / info.file_size) * 100 if info.file_size > 0 else 0
                print(f"   {info.filename}")
                print(f"      Size: {size_kb:.2f} KB → {compressed_kb:.2f} KB ({ratio:.1f}% compression)")
        
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"\n✅ ZIP created successfully!")
        print(f"   Total size: {zip_size_mb:.2f} MB")
        print(f"   Location: {zip_path}")
        
        # Verify minimum required files
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            names = zipf.namelist()
            has_obj = any(name.endswith('.obj') for name in names)
            has_mtl = any(name.endswith('.mtl') for name in names)
            has_png = any(name.endswith('.png') for name in names)
            
            if has_obj and has_mtl and has_png:
                print(f"\n✅ All required files present (OBJ, MTL, PNG)")
                return True
            else:
                print(f"\n❌ Missing files:")
                if not has_obj: print("   - OBJ file")
                if not has_mtl: print("   - MTL file")
                if not has_png: print("   - PNG texture")
                return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("ZIP EXPORT TEST")
    print("=" * 60)
    
    success = test_zip_export()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test passed!")
    else:
        print("⚠️  Test failed")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

