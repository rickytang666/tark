# mesh generation pipeline

this document details the logic flow of the `generate` pipeline in `generator.py`.

## overview

the pipeline converts a geographic bounding box into a textured 3d mesh file (.obj).

## steps

1.  **fetch textures (satellite imagery)**:

    - fetches a high-res satellite image from mapbox static api.
    - calculates width/height to maintain correct aspect ratio of the bounding box.
    - saves as `temp/terrain.png`.

2.  **fetch elevation (terrain-rgb)**:

    - fetches elevation tiles (terrain-rgb) from mapbox at specified zoom level.
    - stitches tiles together into a single numpy array.
    - applies gaussian smoothing (sigma=1.5) to reduce noise.

3.  **generate terrain mesh**:

    - creates a grid of vertices from the elevation data.
    - transforms lat/lon coordinates to local meters relative to the center.
    - negates x and z to align with unity/blender coordinate systems.
    - generates triangle faces with correct winding order.
    - generates uv coordinates based on x/z position (planar projection).
    - centers the terrain mesh X and Z at (0,0).

4.  **fetch buildings (osm)**:

    - queries openstreetmap (overpass api) for building footprints within the bbox.
    - parses building metadata (height, levels, type).

5.  **extrude buildings**:

    - converts building footprints to local meters (same coordinate system as terrain).
    - samples terrain height at the building location (ray casting or nearest neighbor).
    - extrudes the footprint to 3d height.
    - offsets the building vertically to sit on top of the terrain.

6.  **merge and export**:
    - combines terrain mesh and all building meshes into one `trimesh` object.
    - applies the texture material to the terrain portion.
    - exports to `.obj` with `.mtl` material file.
