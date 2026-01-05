# floating building issue (the z-inversion mystery)

**status**: mitigated

## what was the problem?

for a while, we had a bug where buildings would appear to be "floating" at sea level (y=0) instead of sitting nicely on top of the terrain. this happened because our code couldn't find the correct ground height for the buildings, so it defaulted to 0.

## the logic

our project uses a coordinate system similar to unity or blender:

- **y-axis**: up/down (elevation)
- **z-axis**: north/south
- **x-axis**: east/west

when we generate the world, we do two things:

1.  **direct the terrain**: we take satellite elevation data and convert it into a 3d mesh.
2.  **place the buildings**: we take building footprints from openstreetmap and place them on that mesh.

logically, if a building is at `lat: 45.0, lon: -80.0`, and the terrain has a height at `lat: 45.0, lon: -80.0`, they should match perfectly.

## the "z-inversion" anomaly

during testing, we found that they _didn't_ match. when we asked the terrain "what is the height at coordinate `z`?", it would often say "out of bounds" for valid buildings.

after debugging, we discovered a strange fix: **we had to flip the sign of the z-coordinate.**

if a building was at `z = -500` (north), we had to search the terrain at `z = +500` (south) to get the correct height. this doesn't make geometric sense at first glance, but it works perfectly (100% success rate).

## why does this happen?

we suspect it comes down to how different parts of our pipeline handle "north" versus "south":

1.  **image data**: satellite images are stored top-to-bottom. row 0 is the northernmost edge.
2.  **coordinate math**: our math converts latitude (north) to a positive number, but then we negate it (`-z`) to match the 3d engine's convention.
3.  **the mismatch**: somewhere in that chain—likely when we flatten the 2d grid of the terrain into a list of vertices—the logical "north" and the coordinate "north" got swapped or mirrored relative to the buildings.

## the solution

for now, we have codified this fix in `buildings.py`:

```python
target_z = -centroid_z
```

by explicitly flipping the z-coordinate when looking up heights, the buildings find their correct place on the ground, and the "floating" issue is solved. be careful if you ever refactor the `coordinatetransformer` or `terraingenerator`—you might accidentally "fix" the root cause and break this workaround!
