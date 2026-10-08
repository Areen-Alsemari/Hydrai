"""CGH2 step 5f: static alarms per hour in HEALTHY operation vs ISA-18.2 / EEMUA 191 (6/h manageable, 12/h busy ceiling), and the agent's
alert-rate target (about 1 per hour). PROVISIONAL limits. A zero static-alarm load is a SIMULATOR ARTIFACT: the twin has no trips, mode
changes, comms flaps or maintenance, so it says nothing about a real plant. The classical baselines' alert rates at their false-alarm budgets
are in cgh2_baselines.txt; no agent has been trained on this dataset.

    python scripts/cgh2_alarm_load.py [output/cgh2/medium]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.cgh2.dashboard import PROVISIONAL_NOTE, CGH2Dashboard
from hydrai_twin.physical_dataset import static_flags_from_parquet
from ml.headline_metrics import (AGENT_TARGET_PER_H, EEMUA_BUSY_CEILING_PER_H, EEMUA_MANAGEABLE_PER_H, HOUR_S, alarm_events, alarm_load_verdict)

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/cgh2/medium")
    ap.add_argument("--merge-gap", type=float, default=300.0)
    a = ap.parse_args()
    root = ROOT / a.dataset
    m = json.loads((root / "manifest.json").read_text())
    dash = CGH2Dashboard.from_dict(m["dashboard"])
    print(f"dashboard: {m['dashboard_label']} (class {m['config']['pressure_class']})\n{PROVISIONAL_NOTE}\n")
    print(f"ISA-18.2 / EEMUA 191: {EEMUA_MANAGEABLE_PER_H:g}/h manageable, {EEMUA_BUSY_CEILING_PER_H:g}/h busy ceiling; agent target about {AGENT_TARGET_PER_H:g} alert/h of healthy operation\n")
    groups = {}
    for e in m["episodes"]:
        if e["role"] == "commissioning":
            continue
        for level in (None, "warning", "critical"):
            ts, flags = static_flags_from_parquet(root / e["slow_file"], dash, level)
            cut = e["onset_s"] if e["onset_s"] is not None else float("inf")
            n = len([x for x in alarm_events(ts, flags, a.merge_gap) if x < cut])
            g = groups.setdefault(e["scenario_class"], {}).setdefault(level or "any", [0, 0.0])
            g[0] += n
        groups[e["scenario_class"]].setdefault("_h", [0, 0.0])[1] += e["healthy_exposure_s"] / HOUR_S
    print(f"{'scenario class':26}{'level':>10}{'events':>8}{'healthy hours':>15}{'per hour':>10}   vs ISA-18.2 / EEMUA 191")
    for cls, g in groups.items():
        hours = g["_h"][1]
        for lvl in ("any", "warning", "critical"):
            n = g[lvl][0]
            rate = n / hours if hours else None
            print(f"{cls:26}{lvl:>10}{n:>8d}{hours:>15.1f}{rate:>10.4f}   {alarm_load_verdict(rate, 'operator')}")
    print("\nNOTE: a zero or near-zero static-alarm load here is a simulator artifact (no trips, mode changes, comms flaps, maintenance or operator action).")
    print(f"Agent alert rate: not reported (no agent trained on this dataset yet); target about {AGENT_TARGET_PER_H:g} alert/h.")
    print(f"\n{PROVISIONAL_NOTE}")


if __name__ == "__main__":
    main()
