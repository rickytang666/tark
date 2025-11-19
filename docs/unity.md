# unity import guide

## quick start

1. download and extract the zip file from tark
2. in unity, drag the `.obj` file into your assets folder
3. textures load automatically

## what you get

the zip contains:

- `scene.obj` - 3d mesh (terrain + buildings)
- `material.mtl` - material definitions
- `material_0.png` - satellite texture
- `terrain.png` - original texture (optional)

keep all files in the same folder for textures to work.

## import settings

unity should auto-detect:

- **scale factor:** 1 (already in meters)
- **up axis:** y
- **forward axis:** z

if the mesh is too small/large, adjust scale factor in import settings.

## coordinate system

- **1 unit = 1 meter** in real world
- **y-up** coordinate system
- mesh is centered at origin (x=0, z=0)
- elevation is preserved (y values = real meters above sea level)

## tips

**performance:**

- terrain meshes can be dense (100k+ vertices)
- consider using lod groups for large areas
- split buildings into separate layer for occlusion culling

**materials:**

- default material is applied automatically
- satellite texture is already mapped
- you can replace with your own materials

**colliders:**

- add mesh collider to terrain for physics
- add box colliders to individual buildings for better performance

## orientation

top-down view (bird's eye):

- **north:** top of screen
- **east:** right side
- **south:** bottom
- **west:** left side

## troubleshooting

**mesh appears flipped or rotated:**

- check import settings → rotation
- try rotating 180° around y-axis

**textures don't load:**

- ensure all files from zip are in same folder
- check material.mtl references correct texture file
- reimport the obj file

**mesh is tiny/huge:**

- adjust scale factor in import settings
- default should be 1 (1 unity unit = 1 meter)

**buildings floating or underground:**

- this is a known issue on steep slopes
- buildings use elevation sampling but have flat bases
- you can adjust individual building positions manually

## example workflow

1. generate mesh for your location (1-2km area recommended)
2. extract zip to unity project folder
3. drag obj into assets
4. add mesh collider to terrain
5. add directional light for better visualization
6. adjust camera position to view area
7. (optional) split buildings into separate gameobjects for manipulation

## performance considerations

**for 2km × 2km area:**

- terrain: ~130k-260k vertices
- buildings: 500-2000 buildings
- total file: 15-35mb
- recommended: use lod for distant terrain

**optimization:**

- reduce terrain resolution in tark settings (use "low" quality)
- use smaller area (1km × 1km)
- apply mesh decimation in blender before import
- split into chunks for streaming

## blender workflow

if you want to edit in blender first:

1. import obj into blender
2. edit as needed (decimate, uv unwrap, add details)
3. export as fbx
4. import fbx into unity

this gives you more control over mesh optimization.
