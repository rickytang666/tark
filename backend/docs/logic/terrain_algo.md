# terrain generation algorithm

this document details how the elevation raster is converted into a 3d mesh.

## grid generation

1.  input is a 2d numpy array of elevation values.
2.  we generate regular grids of latitude and longitude values matching the array shape.
3.  these are converted to local x/z meters using the logic in `coordinates.md`.

## vertex creation

vertices are created as `(x, y, z)` tuples:

- `x`: horizontal position (derived from longitude).
- `y`: elevation value (directly from input array).
- `z`: depth position (derived from latitude).

## triangulation (faces)

for each square cell in the grid defined by `(r, c)`, we create two triangles to form a quad.

vertices:

- `v0 = (r, c)`
- `v1 = (r, c+1)`
- `v2 = (r+1, c)`
- `v3 = (r+1, c+1)`

triangles:

- `t1 = [v0, v1, v2]`
- `t2 = [v1, v3, v2]`

_note: the winding order is specific to the negated coordinate system to ensure face normals point upwards._

## uv mapping

we generate uv coordinates for texturing using **planar projection**.
we map the x and z bounds of the mesh to the 0-1 uv space by normalizing the values. this means the texture is projected straight down onto the terrain, ignoring elevation changes, which is standard for satellite map overlays.
