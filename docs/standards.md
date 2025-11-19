# standards & specifications

## coordinate system

- **input:** wgs84 (lat/lon degrees)
- **processing:** utm projection (meters)
- **output:** local tangent plane (meters, centered)
- **format:** y-up, right-handed, 1 unit = 1 meter

## bounding box constraints

- **minimum:** 1km × 1km (prevents mapbox tile distortion)
- **recommended:** 2km × 2km (best balance)
- **maximum:** 5km × 5km (prevents timeout/memory issues)

### why 1km minimum?

mapbox tiles cover larger areas than small bboxes. areas <1km may include elevation from outside the requested area, causing unrealistic vertical exaggeration.

## data sources

### terrain
- **source:** mapbox terrain-rgb v1
- **resolution:** ~30m per pixel at zoom 12
- **accuracy:** ±10m typical
- **format:** rgb-encoded png tiles
- **processing:** gaussian smoothing (σ=1.5) to reduce noise

### buildings
- **source:** openstreetmap via overpass api
- **data:** footprints + height/levels metadata
- **extrusion:** simple box models
- **height estimation:** 3.5m per floor if levels known

## output specifications

### file format
- **format:** wavefront obj + mtl
- **scale:** 1:1 (1 unit = 1 meter)
- **coordinate system:** y-up, right-handed
- **normals:** included
- **uvs:** included for terrain texture
- **textures:** satellite imagery png

### typical mesh stats (2km × 2km)
- **terrain vertices:** ~130k-260k
- **terrain faces:** ~260k-520k
- **buildings:** 500-2000 (urban areas)
- **building vertices:** ~30k-60k
- **total file size:** 15-35mb

## quality settings

| quality | zoom | terrain res | texture size | use case |
|---------|------|-------------|--------------|----------|
| low | 11 | ~60m | 512px | fast preview |
| medium | 12 | ~30m | 1024px | default |
| high | 13 | ~15m | 1280px | detailed |
| ultra | 14 | ~7.5m | 1280px | very detailed |

## validation

for realistic meshes:
- bbox must be 1-5km per side
- elevation range should make sense for location
- buildings should be within terrain elevation range
- mesh centered at origin (x-z only, y preserved)
- file size < 50mb

## known limitations

### terrain
- tiles not cropped to exact bbox
- small areas may show elevation from nearby features
- 30m resolution misses small details

### buildings
- simple box extrusion only
- no architectural details
- height estimation may be inaccurate
- some buildings missing from osm
- flat bases don't follow slopes

### performance
- overpass api can timeout (60s timeout set)
- large areas (>3km) may take 2+ minutes
- memory usage scales with area size

