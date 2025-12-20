import pytest
import numpy as np
from scipy.ndimage import gaussian_filter

def test_gaussian_smoothing():
    """Test gaussian filter reduces noise significantly"""
    np.random.seed(42)
    rows, cols = 50, 50
    
    # Create smooth base signal
    x = np.linspace(0, 10, cols)
    y = np.linspace(0, 10, rows)
    X, Y = np.meshgrid(x, y)
    base_signal = X + Y
    
    # Add noise
    noise = np.random.normal(0, 1.0, (rows, cols))
    noisy_signal = base_signal + noise
    
    # Apply smoothing
    smoothed = gaussian_filter(noisy_signal, sigma=2.0)
    
    # Check that standard deviation of the difference (residual noise) is reduced
    # Ideally, smooth signal should be closer to base_signal than noisy_signal
    
    error_noisy = np.std(noisy_signal - base_signal)
    error_smoothed = np.std(smoothed - base_signal)
    
    # Assert noise reduction
    assert error_smoothed < error_noisy
    assert error_smoothed < 0.5 * error_noisy  # Should reduce noise by at least half with sigma=2
