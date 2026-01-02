# coordinate systems

this document explains the coordinate transformations used in the project.

## geographic vs cartesian

we start with **geographic coordinates** (latitude, longitude) on a sphere (earth).
we need **cartesian coordinates** (x, y, z) for a 3d engine.

## transformation steps

1.  **center point**:

    - we define the center of the bounding box as `(center_lat, center_lon)`.
    - this point becomes `(0, 0)` in our local meter space.

2.  **meters conversion**:
    - `y` (north-south distance) = `(lat - center_lat) * 111,000` (meters per degree).
    - `x` (east-west distance) = `(lon - center_lon) * 111,000 * cos(center_lat)`.

## 3d engine conventions (unity/blender)

unity and many 3d engines use a specific coordinate system that differs from standard math graphs.

- **y-up**: the y-axis represents vertical height (elevation).
- **x-z plane**: the ground plane.
- **negation**: to match the "bird's eye view" orientation correctly in unity:
  - we negate the calculated `x` values.
  - we negate the calculated `z` values.

## result

- **x**: east-west axis (negated).
- **y**: elevation (altitude).
- **z**: north-south axis (negated).
