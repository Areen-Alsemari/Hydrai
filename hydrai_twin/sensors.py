"""
Sensor noise injection, per Sec. 9's instrument specs (hydrai_twin.constants.SENSOR_SPECS).

Sec. 9 gives an accuracy figure per sensor (e.g. "pressure +/-0.25% FS") but
no noise *model* -- that mapping is a simulation design choice, made
explicit here rather than left implicit:

  - We treat the stated accuracy as a 95% (~2-sigma) bound on instrument
    error, so sigma = accuracy / 2. This is a common, conservative
    convention for "accuracy" specs on instrument datasheets, but it is a
    choice, not a workbook-given number -- flagged so it can be swapped for
    a vendor-specific model later without hunting through the sim code.
  - Noise is modeled as zero-mean Gaussian, independent per tick. Real
    instrument error usually has both a random and a slowly-varying bias
    component; only the random component is modeled in this phase-1
    generator (no per-episode sensor bias/drift yet).
  - Readings are clipped to the sensor's stated range (Sec. 9), matching
    real instrument saturation behavior.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.constants import SENSOR_SPECS

ACCURACY_SIGMA_DIVISOR = 2.0  # accuracy spec treated as a ~2-sigma (95%) bound


def _sigma_for(sensor_name: str) -> float:
    lo, hi, _unit, kind, value, _hz = SENSOR_SPECS[sensor_name]
    if kind == "pct_fs":
        span = hi - lo
        return (value / 100.0) * span / ACCURACY_SIGMA_DIVISOR
    if kind == "abs":
        return value / ACCURACY_SIGMA_DIVISOR
    raise ValueError(f"unknown accuracy kind '{kind}' for sensor '{sensor_name}'")


def measure(sensor_name: str, true_value: float, rng: np.random.Generator) -> float:
    """Return a noisy reading for `sensor_name` given the true simulated value."""
    lo, hi, _unit, _kind, _value, _hz = SENSOR_SPECS[sensor_name]
    sigma = _sigma_for(sensor_name)
    noisy = true_value + rng.normal(0.0, sigma)
    return float(np.clip(noisy, lo, hi))
