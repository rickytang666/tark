#!/usr/bin/env python3
"""
Test script to verify smoothing functionality
"""
from scipy.ndimage import gaussian_filter
import numpy as np

# Test that the import works
print('✅ scipy.ndimage.gaussian_filter is available')

# Simulate noisy elevation data (like what Mapbox gives us)
np.random.seed(42)
rows, cols = 100, 100

# Create a smooth slope with added noise
x = np.linspace(0, 10, cols)
y = np.linspace(0, 10, rows)
X, Y = np.meshgrid(x, y)
smooth_terrain = 300 + 5 * X + 3 * Y  # Smooth slope

# Add realistic noise (±1 meter, like your data shows)
noise = np.random.normal(0, 1.0, (rows, cols))
noisy_terrain = smooth_terrain + noise

# Apply smoothing with different sigma values
smoothed_light = gaussian_filter(noisy_terrain, sigma=1.0)
smoothed_medium = gaussian_filter(noisy_terrain, sigma=1.5)
smoothed_heavy = gaussian_filter(noisy_terrain, sigma=3.0)

print(f'\n📊 Smoothing Results:')
print(f'   Original noise std dev: {noise.std():.3f}m')
print(f'   Noisy terrain std dev: {noisy_terrain.std():.3f}m')
print(f'   Light smoothing (σ=1.0): {smoothed_light.std():.3f}m')
print(f'   Medium smoothing (σ=1.5): {smoothed_medium.std():.3f}m')
print(f'   Heavy smoothing (σ=3.0): {smoothed_heavy.std():.3f}m')

# Calculate how much noise was removed
noise_removed_medium = noisy_terrain - smoothed_medium
print(f'\n🎯 Noise removed (σ=1.5): mean={noise_removed_medium.mean():.3f}m, std={noise_removed_medium.std():.3f}m')

print('\n✅ Smoothing test completed successfully!')

