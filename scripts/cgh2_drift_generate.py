"""Slow sensor-drift episodes (fault 1 variant), a SEPARATE folder, never used for tuning: output/cgh2_drift/medium/.

12 fault episodes on the medium class, 6 slow pressure-transmitter drifts and 6 slow gas-temperature-probe drifts, each a measurement-layer bias that ramps linearly from
the onset (day 3-5) to 0.5 / 1 / 2 % of the channel's full-scale span after 5 days and then holds (14-day episodes). The physical vessel is healthy; only the
dashboard reading is wrong. One commissioning run per module (same seed as the dev commissioning runs) provides the per-unit baselines. Existing generator behaviour is
unchanged when the drift fields are off (checked by hash). The ideal-observer floor of a drift is analytic: the time its magnitude first exceeds 3 sigma of the
channel (sigma = accuracy / 2, the definition used for every other fault).

    python scripts/cgh2_drift_generate.py
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.dataset import DAY, DEV_BASE_SEED, CGH2DatasetConfig, Job, Variant, run_job
from hydrai_twin.cgh2.profile import make_profile
from hydrai_twin.cgh2.sensor_view import obs_sigma_fn
from hydrai_twin.seeding import stable_seed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "cgh2_drift" / "medium"
DRIFT_BASE_SEED = 20280401                 # new seeds: none of these episodes exists in dev, unseen or OOD
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")
PCT = {"pressure_bar_a": (0.5, 1.0, 2.0, 0.5, 1.0, 2.0), "gas_temp_c": (1.0, 2.0, 0.5, 1.0, 2.0, 0.5)}
SHORT = {"pressure_bar_a": "pressure", "gas_temp_c": "gastemp"}


def jobs() -> list[Job]:
    cfg = CGH2DatasetConfig()
    ov, dash = cfg.overrides(), cfg.dashboard().to_dict()
    out: list[Job] = []
    for k, m in enumerate(MODULES):
        profile = make_profile(m, DEV_BASE_SEED, cfg.variation_scale)
        for tag in ("pressure_bar_a", "gas_temp_c"):
            pct, sign = PCT[tag][k], (1.0 if k % 2 == 0 else -1.0)
            key = f"drift-{SHORT[tag]}-{'p' if sign > 0 else 'm'}{pct:g}"
            var = Variant(key, dict(fault_id=1, drift_tag=tag, drift_pct_fs=pct, drift_sign=sign, drift_days=5.0, compute_observability=False), "drift")
            out.append(Job(f"{m}__{key}", "drift", m, var, stable_seed(DRIFT_BASE_SEED, m, key, "medium"), profile, ov, dash, cfg.view(), cfg.historian, str(OUT / "drift" / m), True, cfg.start_time))
        cvar = Variant("commissioning", dict(fault_id=0), "commissioning")
        out.append(Job(f"{m}__commissioning", "commissioning", m, cvar, stable_seed(DEV_BASE_SEED, m, "commissioning", "medium"), profile, ov, dash, cfg.view(), cfg.historian,
                       str(OUT / "commissioning" / m), True, cfg.start_time))
    return out


def floor_s(entry: dict, view, p_range: float) -> float | None:
    """Ideal-observer floor of a drift: first time |drift| > 3 sigma (sigma = accuracy / 2), analytic, on the noise-free ramp."""
    tag, pct = entry["drift_tag"], entry["drift_pct_fs"]
    span = p_range if tag == "pressure_bar_a" else (R.value("gas_temp_range_c")[1] - R.value("gas_temp_range_c")[0])
    final = pct / 100.0 * span
    sigma = float(obs_sigma_fn(view, p_range)(tag, np.array([0.0])))
    if final <= 3.0 * sigma:
        return None
    return entry["onset_s"] + 3.0 * sigma / final * 5.0 * DAY


if __name__ == "__main__":
    t0 = time.time()
    js = jobs()
    with ProcessPoolExecutor(max_workers=6) as ex:
        entries = list(ex.map(run_job, js))
    cfg = CGH2DatasetConfig()
    base = json.loads((ROOT / "output/cgh2/medium/manifest.json").read_text())
    for e in entries:
        e.pop("_registry"), e.pop("_class"), e.pop("_split")
        if e["family"] == "drift":
            job = next(j for j in js if j.name == e["name"])
            kw = job.variant.kwargs
            e.update(drift_tag=kw["drift_tag"], drift_pct_fs=kw["drift_pct_fs"], drift_sign=kw["drift_sign"], drift_days=kw["drift_days"])
            e["first_observable_s"] = floor_s(e, cfg.view(), base["class_parameters"]["transmitter_range_bar"])
            e["floor_note"] = "analytic: first time the noise-free drift exceeds 3 sigma of the channel (sigma = accuracy/2); None = the drift never exceeds it"
    manifest = {k: base[k] for k in ("schema", "system", "dashboard_label", "class_parameters", "dashboard", "dashboard_tag_names", "sample_periods_s", "measurement_units",
                                     "sensor_view", "sensor_split", "model_visible_channels", "valve_states", "channels_without_static_alarm", "historian", "static_alarm_basis",
                                     "static_alarm_status")}
    manifest.update(episodes=sorted(entries, key=lambda e: (e["role"], e["module_id"], e["name"])), n_episodes=len(entries),
                    generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    note="SLOW SENSOR-DRIFT episodes: separate from dev/unseen/OOD, never used for tuning; generated after the agent configuration was frozen.",
                    regen_command="python scripts/cgh2_drift_generate.py", wall_seconds=round(time.time() - t0, 1))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print(f"{len(entries)} episodes in {time.time() - t0:.0f} s -> {OUT}")
    for e in entries:
        if e["family"] == "drift":
            fl = "-" if e["first_observable_s"] is None else f"{(e['first_observable_s'] - e['onset_s']) / 3600:.1f} h"
            print(f"  {e['name']:34s} onset day {e['onset_s'] / DAY:.2f}  drift {e['drift_sign'] * e['drift_pct_fs']:+.1f} % FS  floor {fl}")
