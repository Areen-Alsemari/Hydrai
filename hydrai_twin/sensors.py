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
  - THIS LEGACY MODEL (`measure`) spends the whole accuracy as per-sample white noise. It is kept for the legacy
    generators; the physical generator uses the split model at the bottom of this file (bias + drift + small noise).
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


def accuracy_abs(sensor_name: str) -> float:
    """The Sec.9 stated accuracy as an absolute +/- value in the sensor's units."""
    return ACCURACY_SIGMA_DIVISOR * _sigma_for(sensor_name)


def measure(sensor_name: str, true_value: float, rng: np.random.Generator, bias: float = 0.0) -> float:
    """Return a noisy reading for `sensor_name` given the true simulated value.

    `bias` is a fixed per-module calibration offset (see module_profile.py);
    it is added before clipping, so a biased sensor still saturates at its
    stated range."""
    lo, hi, _unit, _kind, _value, _hz = SENSOR_SPECS[sensor_name]
    sigma = _sigma_for(sensor_name)
    noisy = true_value + bias + rng.normal(0.0, sigma)
    return float(np.clip(noisy, lo, hi))


# ---------------------------------------------------------------------------
# Split error model (physical generator; the legacy generators keep `measure`)
# ---------------------------------------------------------------------------
# The legacy model above spends the WHOLE stated accuracy as independent per-sample noise (sigma = accuracy/2),
# which makes every channel several times noisier than a real instrument's random error and gives none of the
# slow error a real one has. The split model divides the accuracy A (a bound on TOTAL instrument error) into:
#
#   per-unit calibration bias : fixed for the unit, uniform in +/- bias_frac*A    (hard-bounded by the spec)
#   slow drift                : Ornstein-Uhlenbeck, 2-sigma = drift_frac*A, tau days, clipped at drift_frac*A
#   random noise              : white, sigma = noise_sigma_frac*A
#
# With the defaults 0.5 / 0.3 / 0.1, bias + drift + 2-sigma noise = 1.0*A, so total error stays inside the spec.
# THE SPLIT IS A PLACEHOLDER (placeholders.py, question Q12): Sec. 9 states only the total.

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SensorErrorSplit:
    bias_frac: float = 0.5
    drift_frac: float = 0.3
    noise_sigma_frac: float = 0.1
    drift_tau_s: float = 3.0 * 86400.0
    per_channel: dict = field(default_factory=dict)   # {tag: {"bias_frac": .., "drift_frac": .., "noise_sigma_frac": ..}}

    @classmethod
    def from_registry(cls) -> "SensorErrorSplit":
        from hydrai_twin import placeholders as PH   # reading marks them as used in the manifest
        return cls(PH.value("sensor_bias_frac"), PH.value("sensor_drift_frac"), PH.value("sensor_noise_sigma_frac"),
                   PH.value("sensor_drift_tau_days") * 86400.0,
                   per_channel={"h2_concentration_pct": {"bias_frac": PH.value("sensor_h2_zero_bias_frac"),
                                                          "drift_frac": PH.value("sensor_h2_zero_drift_frac")}})

    def get(self, tag: str, key: str) -> float:
        return float(self.per_channel.get(tag, {}).get(key, getattr(self, key)))

    def sigma_noise(self, tag: str) -> float:
        return self.get(tag, "noise_sigma_frac") * accuracy_abs(tag)

    def drift_sigma(self, tag: str) -> float:
        return 0.5 * self.get(tag, "drift_frac") * accuracy_abs(tag)       # 2-sigma = drift_frac * A

    def drift_bound(self, tag: str) -> float:
        return self.get(tag, "drift_frac") * accuracy_abs(tag)

    def bias_bound(self, tag: str) -> float:
        return self.get(tag, "bias_frac") * accuracy_abs(tag)

    def to_dict(self) -> dict:
        return {"bias_frac": self.bias_frac, "drift_frac": self.drift_frac, "noise_sigma_frac": self.noise_sigma_frac,
                "drift_tau_days": self.drift_tau_s / 86400.0, "per_channel": self.per_channel, "level": "placeholder (Q12)"}


def drift_series(tag: str, t_s: np.ndarray, rng: np.random.Generator, split: SensorErrorSplit) -> np.ndarray:
    """Exact-discretisation OU drift on the (uniform-ish) grid `t_s`, stationary start, clipped at the drift bound."""
    sd = split.drift_sigma(tag)
    out = np.empty(len(t_s))
    x = rng.normal(0.0, sd)
    xi = rng.normal(0.0, 1.0, len(t_s))
    out[0] = x
    for k in range(1, len(t_s)):
        a = np.exp(-(t_s[k] - t_s[k - 1]) / split.drift_tau_s)
        x = a * x + sd * np.sqrt(1.0 - a * a) * xi[k]
        out[k] = x
    return np.clip(out, -split.drift_bound(tag), split.drift_bound(tag))


def measure_split(sensor_name: str, true_value: float, rng: np.random.Generator, split: SensorErrorSplit,
                  unit_bias: float, drift: float) -> float:
    """true + per-unit bias + current drift + white noise, clipped to the range. `unit_bias` must already be inside
    +/- split.bias_bound (see rescale_unit_bias)."""
    lo, hi = SENSOR_SPECS[sensor_name][0], SENSOR_SPECS[sensor_name][1]
    return float(np.clip(true_value + unit_bias + drift + rng.normal(0.0, split.sigma_noise(sensor_name)), lo, hi))


def rescale_unit_bias(profile_bias: float, tag: str, split: SensorErrorSplit) -> float:
    """Module profiles store bias drawn uniform in +/-0.5*A (module_profile.SENSOR_BIAS_FRACTION_OF_ACCURACY). Rescale to
    this split's bound so the SAME unit draw gives a bias inside +/- bias_frac*A."""
    from hydrai_twin.module_profile import SENSOR_BIAS_FRACTION_OF_ACCURACY as F
    return profile_bias * (split.get(tag, "bias_frac") / F)
