"""Score the EXISTING static alarms with the headline metrics (false alarms per week, detection delay), so any agent is
compared against what operators already have. No tuning.

*** PROVISIONAL: the limits are the workbook's 'simulation threshold' values (Sec. 5/6; hydrogen 20/40 %LFL unverified), not the
plant's real alarm settings, on a REFERENCE dashboard (not a verified Saudi system). ***

Static alarms act on the LIVE DCS value (`live__` columns), not on the historian copy.

    python scripts/static_alarm_baseline.py [output/physical_dataset] [--level warning|critical]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.channels import PROVISIONAL_NOTE, DashboardConfig
from hydrai_twin.physical_dataset import static_flags_from_parquet
from ml.headline_metrics import score_episode, summarize, summarize_by_fault

ROOT = Path(__file__).resolve().parent.parent


def fmt(d):
    fa, det = d["false_alarms"], d["detection"]
    md = det["delay_vs_onset_h"]["median"]
    return (f"episodes={d['n_episodes']} faults={d['n_fault_episodes']}  false alarms/week={fa['per_week']:.3f} "
            f"(95% CI {fa['per_week_ci95'][0]:.3f}-{fa['per_week_ci95'][1]:.3f}; {fa['events']} events / {fa['healthy_exposure_weeks']:.1f} wk)  "
            f"detected {det['detected']}/{d['n_fault_episodes']}  median delay vs onset {'-' if md is None else f'{md:.1f} h'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/physical_dataset")
    ap.add_argument("--level", choices=["warning", "critical"], default=None)
    args = ap.parse_args()
    root = ROOT / args.dataset
    m = json.loads((root / "manifest.json").read_text())
    dash = DashboardConfig.from_dict(m["dashboard"])
    print(f"dashboard: {m['dashboard_label']}\n{PROVISIONAL_NOTE}\nstatic alarm level: {args.level or 'any'}\n")
    scores = {}
    for e in m["episodes"]:
        ts, flags = static_flags_from_parquet(root / e["slow_file"], dash, args.level)
        scores[e["name"]] = (e, score_episode(e, ts, flags, flags, detector="static"))
    for role in ("dev", "unseen", "commissioning"):
        for cls in ("standard", "overfill_hydraulic_lock"):
            sc = [s for e, s in scores.values() if e["role"] == role and e["scenario_class"] == cls]
            if sc:
                print(f"[{role:13s} {cls:24s}] {fmt(summarize(sc))}")
    print("\nper fault type (dev, standard):")
    dev = [s for e, s in scores.values() if e["role"] == "dev" and e["scenario_class"] == "standard"]
    names = {e["fault_id"]: e["scenario"] for e, _ in scores.values()}
    for fid, d in summarize_by_fault(dev).items():
        det = d["detection"]
        md = det["delay_vs_onset_h"]["median"]
        print(f"  fault {fid:>2} {names[fid]:24s} n={d['n']:3d} detected {det['detected']:3d}/{d['n']:<3d} median delay {'-' if md is None else f'{md:.1f} h'}")
    print(f"\n{PROVISIONAL_NOTE}")


if __name__ == "__main__":
    main()
