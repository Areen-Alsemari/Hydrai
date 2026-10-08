"""Alarm-load report: static alarms per hour in HEALTHY operation against EEMUA 191 / ISA-18.2, and the agent's alert rate against
its target of about 1 per hour.

    EEMUA 191: about 6 alarms/hour on average is manageable; 12/hour is the busy ceiling   (reference configuration, source STD)
    agent target: no more than about 1 agent alert per hour of healthy operation

*** PROVISIONAL: static-alarm limits are the workbook's 'simulation threshold' values, on a REFERENCE dashboard. The simulator has
no operational alarm transients (trips, mode changes, comms flaps), so a low static-alarm load here is an artifact of the sim, not
evidence that the real plant is quiet. ***

Healthy exposure = every normal episode (standard fill) in full + the pre-onset part of every fault episode. Overfill-class runs are
reported separately. An alarm that stays active counts once; separate activations closer than --merge-gap seconds merge.

    python scripts/alarm_load_report.py [output/physical_dataset] [--merge-gap 300]

Agent: pass a detector's per-sample flags through ml.headline_metrics.score_episode, then ml.headline_metrics.alerts_per_hour. No agent
has been trained on this dataset yet, so no agent rate is reported.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.channels import PROVISIONAL_NOTE, DashboardConfig
from ml.headline_metrics import (AGENT_TARGET_PER_H, EEMUA_BUSY_CEILING_PER_H, EEMUA_MANAGEABLE_PER_H, HOUR_S, alarm_events,
                                 alarm_load_verdict)
from hydrai_twin.physical_dataset import static_flags_from_parquet

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/physical_dataset")
    ap.add_argument("--merge-gap", type=float, default=300.0)
    args = ap.parse_args()
    root = ROOT / args.dataset
    m = json.loads((root / "manifest.json").read_text())
    dash = DashboardConfig.from_dict(m["dashboard"])
    print(f"dashboard: {m['dashboard_label']}\n{PROVISIONAL_NOTE}\n")
    groups: dict[str, dict] = {}
    for e in m["episodes"]:
        if e["role"] == "commissioning":
            continue
        for level in (None, "warning", "critical"):
            ts, flags = static_flags_from_parquet(root / e["slow_file"], dash, level)
            onset = e["onset_s"]
            cut = onset if onset is not None else float("inf")
            events = [x for x in alarm_events(ts, flags, args.merge_gap) if x < cut]
            exposure = e["healthy_exposure_s"]
            g = groups.setdefault(f"{e['scenario_class']}", {}).setdefault(level or "any", [0, 0.0])
            g[0] += len(events)
        groups[e["scenario_class"]].setdefault("_exposure", [0, 0.0])[1] += e["healthy_exposure_s"]
    print(f"EEMUA 191: {EEMUA_MANAGEABLE_PER_H:g}/h manageable, {EEMUA_BUSY_CEILING_PER_H:g}/h busy ceiling; agent target ~{AGENT_TARGET_PER_H:g}/h\n")
    print(f"{'scenario class':26}{'level':>10}{'events':>8}{'healthy hours':>15}{'per hour':>10}   vs EEMUA 191")
    for cls, g in groups.items():
        hours = g["_exposure"][1] / HOUR_S
        for lvl in ("any", "warning", "critical"):
            n = g[lvl][0]
            rate = n / hours if hours else None
            print(f"{cls:26}{lvl:>10}{n:>8d}{hours:>15.1f}{rate:>10.4f}   {alarm_load_verdict(rate, 'operator')}")
    print(f"\nAgent alert rate: not reported (no agent trained on this dataset yet); target about {AGENT_TARGET_PER_H:g} alert/h of healthy operation.")
    print(f"\n{PROVISIONAL_NOTE}")


if __name__ == "__main__":
    main()
