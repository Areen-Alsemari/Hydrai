"""H2 false-alarm check across many simulated healthy units, for each detector mode.

Replicates the hydrogen channel of hydrai_twin/sensor_view.py exactly (per-unit bias draw, OU drift, aggregated white noise,
range clip, the real SensorErrorSplit and registry values) for N units over a healthy episode, with the twin's healthy
hydrogen background (|N(0, 0.02)| %vol) and counts alarm events against the H / HH limits.

Modes
  lfl            realistic 0-100 %LFL detector, +/-5 %LFL, generic error split; H = 20 / HH = 40 %LFL (UNVERIFIED)
  spec+workaround  workbook Sec. 9 (0-100 %vol, +/-2 %vol FS) with the zero-referenced offset workaround (bias/drift 0.1 x accuracy)
  spec+generic   workbook Sec. 9 with the generic 0.5 / 0.3 split (no workaround)
Alarm limits in %vol for the spec modes are the same 20 / 40 %LFL (0.8 / 1.6 %vol).

    python scripts/h2_false_alarm_check.py [--units 2000] [--days 14]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import placeholders as PH
from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs, drift_series

TAG = "h2_concentration_pct"
DT = 60.0                 # slow-layer sample spacing
N_AGG = 5                 # 0.2 s detector averaged to the 1 s grid


def run_mode(name: str, mode: str, split: SensorErrorSplit, units: int, days: float, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, days * 86400.0, DT)
    lfl_per_vol = 100.0 / PH.value("h2_lfl_vol_pct")
    if mode == "lfl":
        A, lo, hi, scale = PH.value("h2_detector_accuracy_lfl"), 0.0, 100.0, lfl_per_vol
        lim = {"H": PH.value("h2_alarm_h_lfl"), "HH": PH.value("h2_alarm_hh_lfl")}
        unit = "%LFL"
    else:
        A, lo, hi, scale = accuracy_abs(TAG), 0.0, 100.0, 1.0
        lim = {"H": PH.value("h2_alarm_h_lfl") / lfl_per_vol, "HH": PH.value("h2_alarm_hh_lfl") / lfl_per_vol}
        unit = "%vol"
    bias_frac, noise_frac = split.get(TAG, "bias_frac"), split.get(TAG, "noise_sigma_frac")
    ev = {"H": 0, "HH": 0}
    units_with = {"H": 0, "HH": 0}
    worst = 0.0
    for _ in range(units):
        u = rng.uniform(-1.0, 1.0)
        drift_units = drift_series(TAG, t, rng, split) / accuracy_abs(TAG)
        true_vol = np.abs(rng.normal(0.0, 0.02, len(t)))
        x = np.clip(true_vol * scale + A * (u * bias_frac + drift_units + rng.normal(0.0, noise_frac / np.sqrt(N_AGG), len(t))), lo, hi)
        worst = max(worst, float(x.max()))
        for k, L in lim.items():
            f = x > L
            n_ev = int(np.sum(np.diff(f.astype(int)) == 1) + f[0])
            ev[k] += n_ev
            units_with[k] += int(n_ev > 0)
    weeks = units * days / 7.0
    return {"name": name, "unit": unit, "limits": lim, "units": units, "days": days, "worst_reading": worst,
            "units_with_event": units_with, "events": ev, "events_per_unit_week": {k: ev[k] / weeks for k in ev},
            "bias_bound": split.bias_bound(TAG) if mode == "spec" else bias_frac * A,
            "noise_sigma_per_sample": noise_frac * A / np.sqrt(N_AGG)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", type=int, default=2000)
    ap.add_argument("--days", type=float, default=14.0)
    args = ap.parse_args()
    reg = SensorErrorSplit.from_registry()
    generic = SensorErrorSplit(reg.bias_frac, reg.drift_frac, reg.noise_sigma_frac, reg.drift_tau_s)
    rows = [run_mode("lfl (realistic default)", "lfl", generic, args.units, args.days, 1),
            run_mode("spec + zero-ref workaround", "spec", reg, args.units, args.days, 2),
            run_mode("spec + generic split", "spec", generic, args.units, args.days, 3)]
    print(f"{args.units} healthy units x {args.days:g} days; alarm limits H = 20 %LFL, HH = 40 %LFL (UNVERIFIED), 1-sample, no persistence\n")
    print(f"{'mode':30}{'unit':>6}{'H limit':>9}{'noise sd':>10}{'bias bound':>11}{'worst reading':>14}{'units w/ H':>11}{'H /unit-wk':>11}{'units w/ HH':>12}{'HH /unit-wk':>12}")
    for r in rows:
        print(f"{r['name']:30}{r['unit']:>6}{r['limits']['H']:>9.2f}{r['noise_sigma_per_sample']:>10.3f}{r['bias_bound']:>11.2f}{r['worst_reading']:>14.2f}"
              f"{r['units_with_event']['H']:>11d}{r['events_per_unit_week']['H']:>11.4f}{r['units_with_event']['HH']:>12d}{r['events_per_unit_week']['HH']:>12.4f}")


if __name__ == "__main__":
    main()
