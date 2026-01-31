# terrain generation

## smoothing

mapbox terrain-rgb has noise from compression/quantization. apply gaussian smoothing:

```python
smoothed = gaussian_filter(elevation, sigma=2.5)
```

**sigma values:**
- `1.0`: light (noisy in urban areas)
- `2.5`: medium (recommended default)
- `5.0`: heavy (very smooth, loses detail)

measured: urban areas have 3-6m artifacts between adjacent pixels without smoothing.

## mesh generation

1. flip elevation data (`np.flipud`) to match coordinate system
2. create lat/lon grid with `np.linspace(south, north, rows)`
3. transform to local x/z coordinates via UTM
4. create vertices: `(x, elevation, z)`
5. triangulate grid into faces
6. generate UVs for texture mapping

## grid metadata

terrain mesh stores:
- `grid_dims`: (rows, cols) for building placement
- `bounds`: original lat/lon bbox
- `elevation`: flipped elevation array

buildings use this for O(1) elevation lookup.

## known issues

- mapbox data has bumps under buildings (not real terrain)
- increase smoothing (sigma=5) for flatter urban areas
- unavoidable with free data sources
