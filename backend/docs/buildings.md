# building placement

## the problem

buildings were floating because of coordinate system mismatch between terrain and building meshes.

## solution

1. center terrain **before** buildings sample elevations
2. pass terrain offset to building extruder
3. apply same offset to building coordinates
4. ensures buildings and terrain are in same coordinate space

## elevation sampling

buildings sample terrain height using:
- search 16 nearest terrain vertices
- check triangles for barycentric interpolation
- fallback to inverse distance weighting if no containing triangle
- use closest vertex if elevation variance > 15m
- drop buildings if > 50m from nearest terrain vertex

## remaining issues

- buildings have flat bases (don't follow slopes)
- ~2-3% of buildings may extend outside terrain bounds
- single-point sampling (centroid only)

## future improvements

- multi-point elevation sampling (all corners)
- sloped building foundations
- clip building footprints to terrain bounds

