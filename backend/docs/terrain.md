# terrain smoothing

## the problem

mapbox terrain-rgb tiles contain noise from:
- rgb encoding quantization
- png compression artifacts
- tile stitching seams

measured: ~1m bumps between adjacent vertices on flat areas.

## solution

apply gaussian smoothing filter to elevation data after decoding.

```python
from scipy.ndimage import gaussian_filter
smoothed = gaussian_filter(elevation, sigma=1.5)
```

## sigma values

- **0**: no smoothing (noisy)
- **1.0**: light smoothing
- **1.5**: medium smoothing (default, recommended)
- **3.0**: heavy smoothing (too much)

## what it does

**removes:**
- quantization artifacts
- tile boundary seams
- compression noise
- small spikes/dips (<1m)

**preserves:**
- overall terrain shape
- major elevation changes
- building placement accuracy

## performance

+50-100ms for typical 512×512 grid. negligible impact.

