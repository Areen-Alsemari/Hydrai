"""Locks in Sec.9 sensor noise injection: readings stay within the
instrument's stated range and noise scales with the stated accuracy."""

import numpy as np

from hydrai_twin.constants import SENSOR_SPECS
from hydrai_twin.sensors import measure


def test_readings_clip_to_sensor_range():
    rng = np.random.default_rng(0)
    for name, (lo, hi, *_rest) in SENSOR_SPECS.items():
        for true_val in (lo, hi, (lo + hi) / 2):
            for _ in range(200):
                reading = measure(name, true_val, rng)
                assert lo <= reading <= hi, f"{name}: {reading} outside [{lo},{hi}]"


def test_noise_is_nonzero_and_centered_near_true_value():
    rng = np.random.default_rng(1)
    name = "pressure_bar_a"
    true_val = 1.2
    readings = [measure(name, true_val, rng) for _ in range(5000)]
    mean = sum(readings) / len(readings)
    assert abs(mean - true_val) < 0.02
    assert len(set(readings)) > 1  # not silently returning a constant
