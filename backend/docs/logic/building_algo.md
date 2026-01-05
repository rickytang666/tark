# building extrusion algorithm

this document explains how 2d building footprints are converted to 3d meshes.

## 1. polygon preparation

- input: list of lat/lon coordinates from openstreetmap.
- conversion: converted to local x/z meters using `coordinates.md` logic.
- holes: internal polygons (courtyards) are also converted.
- validation: shapely is used to validate and fix polygon geometry.

## 2. height estimation

if specific height data is missing from osm, we estimate it:

- `levels * 3.5m`: if floor count is known.
- building type lookup: defaults based on type (e.g., house=6m, office=25m).

## 3. terrain anchor sampling

buildings must sit _on_ the terrain, not inside it or floating above it at y=0.

- we compute the 2d centroid of the building.
- we sample the terrain mesh height at that x/z location.
  - **method**: ray casting (barycentric interpolation) for precision.
  - **fallback**: inverse distance weighting of nearest vertices.
- this gives us the `base_elevation`.

## 4. extrusion and positioning

1.  **extrude**: we use `trimesh.creation.extrude_polygon` to create a prism of height `h`.
2.  **rotate**: the default extrusion is along z; we rotate 90 degrees so it's along y (up).
3.  **offset**: we add `base_elevation` to all y-coordinates to place the building on the terrain surface.
4.  **UV Mapping (Box Projection)**:
    - We "explode" the mesh so each face has unique vertices (flat shading).
    - **Roofs**: Mapped Planar XY (Top-down) using world coordinates.
    - **Walls**: Mapped using Box Mapping (Triplanar) logic to tile textures based on wall dimensions.
    - Scale: 0.2 UV units per meter (repeats every 5m) to create a "concrete/stucco" detail look from satellite noise.
