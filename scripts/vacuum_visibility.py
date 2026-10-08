"""How visible is a soft-vacuum step under each vacuum-gauge mode?  (Q6 stays open: the gauge is UNVERIFIED.)

  spec       workbook Sec. 9: linear 0-1000 Pa, +/-1 % FS (10 Pa)
  log_gauge  Pirani-class: +/-20 % of reading + 0.05 Pa floor, range 0.1 Pa - 1e5 Pa   (reference configuration, UNVERIFIED)

Two views of the same question:
  A. analytic, per unit: step size / sqrt(noise^2 + drift^2) of ONE tag against the unit's own healthy baseline (bias cancels),
     for a single sample, at the gauge's 10 s period; and the separability of a step from the FLEET's healthy readings
     (no per-unit baseline: bias and unit-to-unit baseline spread both count).
  B. the ideal-observer first-observable time from real episodes (vacuum faults, both modes, same seeds), vacuum channel only.

    python scripts/vacuum_visibility.py
"""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import placeholders as PH
from hydrai_twin.module_profile import make_profile
from hydrai_twin.physical_episode import DAY, generate_physical_episode
from hydrai_twin.sensor_view import SensorViewConfig
from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs

TAG = "vacuum_pressure_pa"
SP = SensorErrorSplit.from_registry()
BASE = 1.15      # centre of the healthy jacket-pressure range across units (module_profile: 0.3 - 2.0 Pa)


def err_terms(mode: str, x: float):
    """(A, noise sigma, drift sigma, bias bound) at a true value x, in Pa."""
    A = accuracy_abs(TAG) if mode == "spec" else PH.value("vacuum_gauge_rel_accuracy") * x + PH.value("vacuum_gauge_floor_pa")
    return A, SP.get(TAG, "noise_sigma_frac") * A, 0.5 * SP.get(TAG, "drift_frac") * A, SP.get(TAG, "bias_frac") * A


def analytic():
    print("A. one 10 s sample, step added to a 1.15 Pa healthy jacket (z = step / sqrt(noise^2 + drift^2), unit's own baseline)")
    print(f"{'step (added Pa)':>16}{'reading after':>15}{'spec: z':>10}{'log gauge: z':>14}")
    for dp in (0.5, 2.0, 5.0, 13.33):
        x1 = BASE + dp
        zs = []
        for mode in ("spec", "log"):
            _, sn, sd, _ = err_terms(mode, x1)
            _, sn0, sd0, _ = err_terms(mode, BASE)
            zs.append(dp / np.hypot(np.hypot(sn, sd), np.hypot(sn0, sd0)) * np.sqrt(2))
        print(f"{dp:>16.2f}{x1:>15.2f}{zs[0]:>10.1f}{zs[1]:>14.1f}")
    print("\n   Fleet view, NO per-unit baseline (a threshold on the raw reading): healthy units read "
          "0.3 - 2.0 Pa true, plus each unit's bias.")
    for mode in ("spec", "log"):
        A, _, sd, bias = err_terms(mode, 2.0)
        lo_h, hi_h = max(0.0, 0.3 - bias - 2 * sd), 2.0 + bias + 2 * sd
        print(f"   {mode:5}: healthy readings span about {lo_h:.2f} - {hi_h:.2f} Pa (bias bound {bias:.2f} Pa, drift 2-sigma {2 * sd:.2f} Pa); "
              f"a +13.33 Pa step reads {BASE + 13.33 - bias - 2 * sd:.1f} - {BASE + 13.33 + bias + 2 * sd:.1f} Pa -> "
              + ("SEPARABLE" if BASE + 13.33 - bias - 2 * sd > hi_h else "NOT cleanly separable from healthy units"))


def episodes():
    print("\nB. ideal-observer first observable deviation, vacuum channel only (hours after onset; 'never' = not within the episode)")
    print(f"{'variant':26}{'mode':>10}{'k=3 sigma':>12}{'k=10 sigma':>12}")
    prof = make_profile("M01", 20260301)
    for dp, ramp_d in ((2.0, 2.0), (13.33, 2.0), (13.33, 0.5)):
        for mode in ("spec", "log_gauge"):
            view = SensorViewConfig(vacuum_mode=mode)
            r = generate_physical_episode(fault_id=3, seed=11, module_id="M01", profile=prof, storage_days=8.0, onset_day_range=(2.0, 3.0),
                                          vacuum_target_dp_pa=dp, ramp_duration_s=ramp_d * DAY, sensor_view=view)
            pc = r.meta["per_channel_deviation_s"][TAG]
            f = lambda t: "never" if t is None else f"{(t - r.meta['onset_s']) / 3600:.1f} h"
            print(f"{f'+{dp:g} Pa over {ramp_d:g} d':26}{mode:>10}{f(pc['k3']):>12}{f(pc['k10']):>12}")


if __name__ == "__main__":
    analytic()
    episodes()
