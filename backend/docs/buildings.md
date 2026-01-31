# building placement

## elevation sampling

buildings sample terrain height using grid acceleration:

1. extract grid params from terrain mesh metadata
2. convert building centroid (x, z) to grid (row, col)
3. bilinear interpolation of 4 nearest vertices
4. O(1) lookup, no ray casting needed

## extrusion

1. transform OSM footprint from lat/lon to local x/z
2. sample terrain elevation at centroid
3. extrude polygon to height using `trimesh.creation.extrude_polygon`
4. swap y/z axes (extrude creates XY plane, we need XZ)
5. offset by base elevation

## uv mapping

all building faces (roofs + walls) map to UV (0.005, 0.005):
- samples grey corner of satellite texture
- solid grey buildings
- clean bird's eye view

## height estimation

if OSM data missing:
- `levels * 3.5m` if floor count known
- fallback to type defaults (residential=8m, office=25m, etc.)

## index alignment

`extrude_buildings()` returns list with `None` for failed buildings.
preserves indices so `building_data[i]` matches `building_meshes[i]`.

critical for testing/validation.
