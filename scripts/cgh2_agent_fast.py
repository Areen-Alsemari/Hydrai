"""CGH2 agent, fast layer (step 2A) evaluated on dev: severe events at 1 s (detector alarm / rise, relief lift, pressure collapse, rupture signature).

Rule-based: the only numbers are limits from HEALTHY 1 s data of the OTHER dev modules (leave-one-module-out), the largest healthy 30 s pressure
drop and 10 s hydrogen rise. The 1 s layer exists only around dispenser fills, compressor transitions and events, so false alarms are per hour of
RECORDED healthy 1 s data (not per week) and a slow fault has no 1 s rows to evaluate: the table covers the severe classes.

    python scripts/cgh2_agent_fast.py [output/cgh2/medium]
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml import cgh2_fast as F

ROOT = Path(__file__).resolve().parent.parent


def _read(args):
    root, e = args
    d = F.read_fast(root / e["fast_file"])
    return e["name"], d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/cgh2/medium")
    a = ap.parse_args()
    root = ROOT / a.dataset
    m = json.loads((root / "manifest.json").read_text())
    mop = m["class_parameters"]["mop_bar"]
    dev = m["config"]["dev_modules"]
    eps = [e for e in m["episodes"] if e["role"] in ("dev", "commissioning")]
    with ProcessPoolExecutor(6) as ex:
        data = dict(ex.map(_read, [(root, e) for e in eps]))
    ent = {e["name"]: e for e in eps}

    def healthy_rows(name):
        e, d = ent[name], data[name]
        cut = e["onset_s"] if e["onset_s"] is not None else np.inf
        k = d["t"] < cut
        return {kk: v[k] for kk, v in d.items()}

    healthy_names = [n for n, e in ent.items() if e["fault_id"] == 0 and e["scenario_class"] == "standard" and "dark" not in e["variant_tag"]]
    per_ep_limits = {n: F.healthy_limits([(healthy_rows(n), mop)]) for n in healthy_names}
    out = ["# CGH2 agent - fast layer (1 s), dev leave-one-module-out", "",
           "Reference configuration, not a verified Saudi system. Limits (largest healthy 30 s pressure drop as a fraction of MOP, largest healthy 10 s hydrogen rise) "
           "come from the other dev modules' healthy 1 s data; margin 1.5x. The 1 s layer covers fills, compressor transitions and events only.", ""]
    det_by_class = defaultdict(list)
    healthy_events = defaultdict(int)
    healthy_hours = 0.0
    lim_log = {}
    for hold in dev:
        others = [n for n in healthy_names if ent[n]["module_id"] != hold]
        lim = {"max_healthy_drop_frac": max(per_ep_limits[n]["max_healthy_drop_frac"] for n in others),
               "max_healthy_h2_rise": max(per_ep_limits[n]["max_healthy_h2_rise"] for n in others)}
        lim_log[hold] = lim
        for n, e in ent.items():
            if e["module_id"] != hold or e["role"] != "dev":
                continue
            d = data[n]
            if len(d["t"]) < 3:
                continue
            ev = F.detect(d, mop, lim, m["class_parameters"]["pahh_bar"])
            if e["fault_id"] == 0:
                if e["scenario_class"] == "standard":
                    healthy_hours += len(d["t"]) / 3600.0
                    for k, f in ev.items():
                        healthy_events[k] += int(np.sum(f & ~np.concatenate([[False], f[:-1]])))
                continue
            if e["scenario_class"] != "standard":
                continue
            ev_time, ev_kind = F.first_event(ev, d["t"], e["onset_s"])
            pre = {k: int(np.sum(f & (d["t"] < e["onset_s"]))) for k, f in ev.items()}
            key = {1: "1 sensor_fault", 2: "2 thermal_anomaly", 3: "3 small_slow_leak", 4: "4 abnormal_pressure_behaviour", 5: "5 containment_anomaly",
                   6: "6 structural_concern", -1: "-1 unknown_anomaly"}[e["fault_id"]]
            if e["family"] == "rupture":
                key = "5r rupture (50 mm)"
            if e["fault_id"] == 4:
                key += f" [{e['variant_tag'].split('-')[-1]}]"
            if e["fault_id"] == 3:
                diam = float(e["variant_tag"].split("-")[-1].replace("mm", ""))
                key += " [stress 0.03-0.05 mm]" if e["expected_miss"] else (" [1 mm]" if diam >= 1.0 else " [0.1-0.5 mm]")
            post_rows = int(np.sum(d["t"] >= e["onset_s"]))
            det_by_class[key].append((ev_time - e["onset_s"] if ev_time is not None else None, ev_kind, post_rows, e["first_observable_s"] - e["onset_s"] if e["first_observable_s"] is not None else None))
    out += ["| class | episodes with 1 s rows after onset | detected by a fast event | median delay s | event types |", "|---|---|---|---|---|"]
    for k in sorted(det_by_class):
        rows = det_by_class[k]
        has = [r for r in rows if r[2] > 5]
        det = [r for r in has if r[0] is not None]
        kinds = defaultdict(int)
        for r in det:
            kinds[r[1]] += 1
        out.append(f"| {k} | {len(has)}/{len(rows)} | {len(det)}/{len(has)} | {np.median([r[0] for r in det]):.0f} | {dict(kinds)} |" if det else f"| {k} | {len(has)}/{len(rows)} | 0/{len(has)} | - | - |")
    out += ["", f"Healthy 1 s data scored: {healthy_hours:,.1f} h recorded; fast events raised there (leave-one-module-out limits): {dict(healthy_events)} -> "
            f"{sum(healthy_events.values()) / max(healthy_hours, 1e-9):.4f} per recorded healthy hour.",
            "", "Healthy limits by held-out module (largest healthy 30 s drop / MOP, largest healthy 10 s hydrogen rise in %LFL):", ""]
    out += [f"- {h}: drop {v['max_healthy_drop_frac']:.4f}, rise {v['max_healthy_h2_rise']:.1f}" for h, v in lim_log.items()]
    text = "\n".join(out)
    (ROOT / "output" / "reports" / "cgh2_agent_fast.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
