# coordinate system

## setup

- **y-up** (unity/blender standard)
- **1 unit = 1 meter**
- **right-handed** coordinate system

## axes

```
y (up)
|
|    z (north)
|   /
|  /
| /
+------ x (east)
```

- **x**: east (positive = east, negative = west)
- **y**: elevation (positive = up)
- **z**: north (positive = north, negative = south)

## transformation

```
lat/lon (WGS84) → UTM projection → local meters → mesh coordinates
```

**key steps:**
1. center bbox at origin (0, 0, 0)
2. use UTM projection for accurate meter conversion
3. negate x in `coords.py` to match unity conventions

## mapbox data ordering

**critical:** mapbox returns elevation data as:
- row 0 = north edge
- row -1 = south edge

**but** terrain.py creates vertices as:
- row 0 = south edge  
- row -1 = north edge

**solution:** `np.flipud(elevation_data)` in `terrain.py` line 46

## implementation

see `app/utils/coords.py` for `CoordinateTransformer` class
