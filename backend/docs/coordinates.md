# coordinate system

## basics

- **y-up** coordinate system (unity/blender standard)
- **1 unit = 1 meter** in obj export
- **right-handed** coordinate system

## axis layout

```
Y (up)
|
|     Z (south)
|    /
|   /
|  /
| /
+---------- X (west)
```

- **x axis**: east-west (negative = east, positive = west)
- **y axis**: elevation (positive = up)
- **z axis**: north-south (negative = north, positive = south)

## transformation pipeline

```
WGS84 (lat/lon) → UTM (meters) → local coords → negate X & Z → final mesh
```

### why negate x and z?

makes the bird's eye view orientation match expectations:
- north at top of screen
- east on right
- terrain/buildings align correctly

## implementation notes

- terrain and buildings generated in same coordinate space
- single centering operation at the end (x-z only, preserve y elevations)
- face winding reversed to compensate for negated coordinates
- uv coordinates stay normal (texture handles orientation)

