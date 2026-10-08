"""Injected data-fault rates per channel-day, separately for the 60 s (slow) and 1 s (fast) layers, from the dataset manifest.

Both layers must show the SAME rates: the fault windows are scheduled once per tag in time (historian.fault_windows, minimum window
60 s so the slow layer can see every event) and both layers read them. Per layer:

  runs / channel-day   fault RUN STARTS (a run whose first row has a contiguous predecessor, so a run that merely resumes after a
                       burst boundary in the 1 s layer is not counted again) / exposure, exposure = rows with a contiguous
                       predecessor x layer period, per tag, summed over tags and episodes
  % of time in fault   fault rows / rows

and the nominal injection rate (events per channel-day) for reference.

    python scripts/data_fault_rates.py [output/physical_dataset]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.historian import FAULT_TYPES, HistorianConfig

ROOT = Path(__file__).resolve().parent.parent


def rates(manifest: dict) -> dict:
    out = {}
    for layer in ("slow", "fast"):
        runs = defaultdict(int)
        samples = defaultdict(int)
        rows = 0
        days = 0.0
        per_tag = defaultdict(lambda: [0, 0.0])
        for e in manifest["episodes"]:
            for tag, v in e["historian"]["layers"][layer].items():
                days += v["exposure_channel_days"]
                rows += v["n_samples"]
                per_tag[tag][1] += v["exposure_channel_days"]
                for ft in FAULT_TYPES:
                    runs[ft] += v["fault_run_starts"][ft]
                    samples[ft] += v["fault_samples"][ft]
                    per_tag[tag][0] += v["fault_run_starts"][ft]
        out[layer] = {"channel_days": days, "rows": rows, "runs": dict(runs), "samples": dict(samples),
                      "per_day": {ft: runs[ft] / days for ft in FAULT_TYPES}, "pct_time": {ft: 100.0 * samples[ft] / rows for ft in FAULT_TYPES},
                      "per_tag_per_day": {t: c[0] / c[1] for t, c in per_tag.items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/physical_dataset")
    args = ap.parse_args()
    m = json.loads((ROOT / args.dataset / "manifest.json").read_text())
    r = rates(m)
    nominal = HistorianConfig.from_registry().fault_rates
    print(f"{m['n_episodes']} episodes. Nominal injection: " + ", ".join(f"{k} {v[0]:g}/channel-day, mean {v[1]:g} s" for k, v in nominal.items()) + "\n")
    for layer, label in (("slow", "60 s layer"), ("fast", "1 s layer")):
        L = r[layer]
        print(f"{label}: {L['rows']:,} tag-rows, {L['channel_days']:,.1f} channel-days of exposure")
        print(f"   {'type':14}{'run starts':>11}{'per channel-day':>17}{'nominal':>9}{'% of time in fault':>20}")
        for ft in FAULT_TYPES:
            print(f"   {ft:14}{L['runs'][ft]:>11}{L['per_day'][ft]:>17.4f}{nominal[ft][0]:>9g}{L['pct_time'][ft]:>20.3f}")
        print()
    print("all types, per tag (run starts per channel-day):")
    print(f"   {'tag':28}{'60 s layer':>12}{'1 s layer':>12}")
    for t in r["slow"]["per_tag_per_day"]:
        print(f"   {t:28}{r['slow']['per_tag_per_day'][t]:>12.4f}{r['fast']['per_tag_per_day'].get(t, float('nan')):>12.4f}")
    tot = sum(nominal[ft][0] for ft in FAULT_TYPES)
    print(f"   {'nominal (sum of types)':28}{tot:>12.4f}{tot:>12.4f}")


if __name__ == "__main__":
    main()
