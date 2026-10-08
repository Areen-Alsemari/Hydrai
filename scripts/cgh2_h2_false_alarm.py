"""CGH2 hydrogen-detector false-alarm check across many healthy units (step 3): 2,000 units x 14 days, both detector modes.

Replicates the detector channel of hydrai_twin/cgh2/sensor_view.py exactly (per-unit bias draw, OU drift, 5-sample aggregation, range clip)
with the registry values: alarm 25 %LFL, trip 50 %LFL (INL). Modes:
  lfl                       realistic 0-100 %LFL detector, +/-5 %LFL, generic split                      (the CGH2 default)
  spec (generic split)      workbook Sec. 9 model: 0-100 %vol, +/-2 %vol; the alarm is the same 25 %LFL = 1 %vol
  spec + zero-ref workaround  as above with the zero-referenced offset assumption (bias and drift 0.1 x accuracy)

    python scripts/cgh2_h2_false_alarm.py [--units 2000] [--days 14]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.sensor_view import ou_drift_unit

DT, N_AGG = 60.0, 5


def run(name, mode, bias_frac, drift_frac, units, days, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, days * 86400.0, DT)
    lfl_per_vol = 100.0 / R.value("h2_lfl_vol_pct")
    noise_frac, tau = R.value("sensor_noise_sigma_frac"), R.value("sensor_drift_tau_days") * 86400.0
    if mode == "lfl":
        A, scale, lim = R.value("h2_detector_accuracy_lfl"), lfl_per_vol, {"H": R.value("h2_alarm_lfl"), "HH": R.value("h2_trip_lfl")}
        unit = "%LFL"
    else:
        A, scale = 2.0, 1.0
        lim = {"H": R.value("h2_alarm_lfl") / lfl_per_vol, "HH": R.value("h2_trip_lfl") / lfl_per_vol}
        unit = "%vol"
    ev, uw, worst = {"H": 0, "HH": 0}, {"H": 0, "HH": 0}, 0.0
    for _ in range(units):
        u = rng.uniform(-1, 1)
        drift = ou_drift_unit(drift_frac, tau, t, rng)
        true_vol = np.abs(rng.normal(0.0, 0.02, len(t)))
        x = np.clip(true_vol * scale + A * (u * bias_frac + drift + rng.normal(0.0, noise_frac / np.sqrt(N_AGG), len(t))), 0.0, 100.0)
        worst = max(worst, float(x.max()))
        for k, L in lim.items():
            f = x > L
            n = int(np.sum(np.diff(f.astype(int)) == 1) + f[0])
            ev[k] += n
            uw[k] += int(n > 0)
    weeks = units * days / 7.0
    return dict(name=name, unit=unit, limits=lim, worst=worst, units_with=uw, per_week={k: ev[k] / weeks for k in ev}, noise=noise_frac * A / np.sqrt(N_AGG), bias=bias_frac * A)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", type=int, default=2000)
    ap.add_argument("--days", type=float, default=14.0)
    a = ap.parse_args()
    b, d = R.value("sensor_bias_frac"), R.value("sensor_drift_frac")
    rows = [run("lfl (realistic default)", "lfl", b, d, a.units, a.days, 1), run("spec, generic split", "spec", b, d, a.units, a.days, 2),
            run("spec + zero-ref workaround", "spec", 0.1, 0.1, a.units, a.days, 3)]
    print(f"{a.units} healthy units x {a.days:g} days; alarm 25 %LFL, trip 50 %LFL (INL), 1-sample, no persistence\n")
    print(f"{'mode':28}{'unit':>6}{'alarm':>8}{'noise sd':>10}{'bias bound':>11}{'worst reading':>14}{'units alarming':>15}{'alarm /unit-wk':>15}{'units tripping':>15}{'trip /unit-wk':>14}")
    for r in rows:
        print(f"{r['name']:28}{r['unit']:>6}{r['limits']['H']:>8.2f}{r['noise']:>10.3f}{r['bias']:>11.2f}{r['worst']:>14.2f}{r['units_with']['H']:>15d}{r['per_week']['H']:>15.4f}{r['units_with']['HH']:>15d}{r['per_week']['HH']:>14.4f}")


if __name__ == "__main__":
    main()
