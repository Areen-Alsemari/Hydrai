"""Healthy-drift visibility table (PHYSICAL_MODEL_CUTOVER_PROPOSAL.md Sec. 1).

How many sensor-noise sigmas does the healthy physical pressure drift (the PCV-sawtooth rise; 0.24 kPa/h at the 0.30 %/day default, 0.073 at the 0.10 spec value) stand above the
least-squares SLOPE noise of the pressure channel, for each feature window? Computed two ways for the same windows:

  legacy_white : the whole Sec. 9 accuracy as per-sample white noise (sigma = 7.5 mbar)   [what the old table used]
  split        : per-unit bias (no effect on a slope) + slow OU drift + small white noise  [hydrai_twin/sensors.py]

Slope noise is MEASURED by Monte Carlo over the actual noise processes, with the analytic white-noise value alongside
as a check. Also prints the same table for the liquid-temperature channel, and the rate each window can resolve at 3 sigma.

    python scripts/healthy_drift_visibility.py [--trials 4000]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs, drift_series

# Healthy PCV-sawtooth pressure rise between openings (1.43 -> 1.50 bar), measured by scripts/timescale_tables.py for each boil-off tier:
HEALTHY_DRIFT_KPA_H = {"baseline 0.30 %/day (default)": 0.241, "target 0.10 %/day (spec)": 0.073}
WINDOWS = [("2 min @ 1 s", 120, 1.0), ("10 min @ 1 s", 600, 1.0), ("30 min @ 60 s", 30, 60.0), ("1 h @ 60 s", 60, 60.0),
           ("2 h @ 60 s", 120, 60.0), ("6 h @ 60 s", 360, 60.0), ("24 h @ 60 s", 1440, 60.0)]


def ols_slope(y: np.ndarray, dt: float) -> np.ndarray:
    """OLS slope per unit time for each row of y (trials x N)."""
    n = y.shape[1]
    x = (np.arange(n) - (n - 1) / 2.0) * dt
    return (y * x).sum(axis=1) / (x * x).sum()


def white_slope_sigma(sig: float, n: int, dt: float) -> float:
    return sig * np.sqrt(12.0 / (n * (n * n - 1.0))) / dt


def measured_slope_sigma(tag: str, n: int, dt: float, split: SensorErrorSplit | None, trials: int, rng) -> float:
    """std of the OLS slope (units/s) of measured-minus-true over a window, many independent windows."""
    if split is None:
        y = rng.normal(0.0, accuracy_abs(tag) / 2.0, (trials, n))
    else:
        y = rng.normal(0.0, split.sigma_noise(tag), (trials, n))
        # drift: stationary OU sampled on the window grid; window position inside a long run is irrelevant (stationary)
        t = np.arange(n) * dt
        for i in range(trials):
            y[i] += drift_series(tag, t, rng, split)
    return float(ols_slope(y, dt).std())


def table(tag: str, drifts: dict[str, float], unit: str, scale: float, trials: int, rng, split) -> None:
    u = unit.split("/")[0]
    print(f"\n{tag}   (legacy white sigma {accuracy_abs(tag)/2*scale:.4g} {u}; split: noise sigma {split.sigma_noise(tag)*scale:.4g}, "
          f"drift bound {split.drift_bound(tag)*scale:.4g}, bias bound {split.bias_bound(tag)*scale:.4g} {u})")
    names = list(drifts)
    head = f"{'window':16}{'legacy slope noise':>20}{'split slope noise':>19}{'white-only':>12}{'resolvable @3 sigma':>21}"
    for n in names:
        head += f"   drift {drifts[n]:g} {unit}: in sigma ({n.split()[0]})"
    print(head)
    for name, n, dt in WINDOWS:
        leg = white_slope_sigma(accuracy_abs(tag) / 2.0, n, dt) * 3600 * scale
        sp = measured_slope_sigma(tag, n, dt, split, trials, rng) * 3600 * scale
        wh = white_slope_sigma(split.sigma_noise(tag), n, dt) * 3600 * scale
        row = f"{name:16}{leg:>18.4g}/h{sp:>17.4g}/h{wh:>10.4g}/h{3 * sp:>19.4g}/h"
        for k in names:
            row += f"   {drifts[k] / sp:>30.2f}"
        print(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=3000)
    args = ap.parse_args()
    rng = np.random.default_rng(12345)
    split = SensorErrorSplit.from_registry()
    # check legacy rows against the old table by simulation too
    table("pressure_bar_a", HEALTHY_DRIFT_KPA_H, "kPa/h", 100.0, args.trials, rng, split)   # bar -> kPa
    # liquid temperature healthy drift: saturation T follows pressure; dT/dp at 1.5 bar ~ 5.4 K/bar (1 kPa/h = 0.01 bar/h)
    table("liquid_temp_c", {k: v * 0.01 * 5.4 for k, v in HEALTHY_DRIFT_KPA_H.items()}, "K/h", 1.0, args.trials, rng, split)


if __name__ == "__main__":
    main()
