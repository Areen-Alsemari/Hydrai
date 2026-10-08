"""Classical baselines next to the static alarms: rate-of-rise (ROC), EWMA and CUSUM, thresholds set on HEALTHY units only to a fixed
false-alarm budget (1 per week and 1 per 4 weeks). PROVISIONAL: the static limits are the workbook's 'simulation threshold'
values on a reference dashboard (not a verified Saudi system).

Protocol: dev = leave-one-module-out (thresholds from the other five modules' healthy normal episodes + commissioning runs, scored on the
held-out module); unseen = thresholds from all six dev modules, scored once on U01-U03. Standard-fill episodes only. No model or threshold
is tuned on fault episodes.

    python scripts/classical_baselines.py [output/physical_dataset]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import constants as C
from hydrai_twin.channels import PROVISIONAL_NOTE, DashboardConfig
from hydrai_twin.physical_dataset import static_flags_from_parquet
from ml.classical_baselines import DETECTORS, detect, load_episode, train
from ml.headline_metrics import score_episode, summarize

ROOT = Path(__file__).resolve().parent.parent
BUDGETS = {"1/wk": 1.0, "1/4wk": 0.25}
H = 3600.0
# spec Sec. 10 signature channels per fault, and whether the spec / reference dashboard defines a static limit on them
STATIC_NOTE = {
    1: "temperature erratic: limit exists (TAH -248/-245 C) but a spike must exceed it",
    2: "pressure/temperature high: limits exist (PAH 2.0 bar, TAH); not reached within the episode",
    3: "vacuum gauge: NO static limit defined; pressure/temperature limits exist (PAH, TAH), reached only when severe",
    4: "pressure high: limit exists (PAH 2.0 bar); not reached within the episode",
    5: "H2 (20/40 %LFL, unverified) and pressure: limits exist",
    6: "strain: NO static limit defined (spec has none); pressure/temperature 'variable'",
    -1: "variable: limits on pressure/temperature/H2 only",
}
NO_STATIC_DEFINED = {6}      # signature channel has no static alarm at all


def fmt_h(x):
    return "-" if x is None else f"{x / H:.1f}"


def table(scores_by_det: dict[str, list], names: dict[int, str]) -> list[str]:
    lines = []
    fids = sorted({s.fault_id for ss in scores_by_det.values() for s in ss if s.fault_id != 0}, key=lambda x: (x < 0, x))
    for fid in fids:
        lines.append(f"  fault {fid:>2} {names[fid]}")
        for det, ss in scores_by_det.items():
            sub = [s for s in ss if s.fault_id == fid]
            det_s = [s for s in sub if s.first_alarm_s is not None]
            delays = [s.delay_vs_onset_s for s in det_s]
            leads = [s.lead_vs_static_s for s in sub if s.lead_vs_static_s is not None]
            only = sum(1 for s in sub if s.outcome == "agent_only")
            if det == "static" and fid in NO_STATIC_DEFINED:
                lines.append(f"      {det:14} n={len(sub):<3} no static alarm defined (not 'missed')")
                continue
            tail = ("(reference)" if det == "static" else
                    f"lead vs static {fmt_h(np.median(leads) if leads else None):>6} h (n={len(leads)})   baseline fired, static never: {only}")
            lines.append(f"      {det:14} n={len(sub):<3} detected {len(det_s):>3}/{len(sub):<3} ({100 * len(det_s) / max(len(sub), 1):4.0f}%)  "
                         f"median delay {fmt_h(np.median(delays) if delays else None):>6} h   {tail}")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/physical_dataset")
    args = ap.parse_args()
    root = ROOT / args.dataset
    m = json.loads((root / "manifest.json").read_text())
    dash = DashboardConfig.from_dict(m["dashboard"])
    names = {fid: C.FAULT_LABELS[fid] for fid in C.FAULT_LABELS}

    eps = {}
    for e in m["episodes"]:
        ep = load_episode(root, e)
        _, sf = static_flags_from_parquet(root / e["slow_file"], dash)
        ep.static_flags = np.array(sf, dtype=bool)
        eps[e["name"]] = ep
    comm_of = {e.entry["module_id"]: e for e in eps.values() if e.entry["role"] == "commissioning"}
    dev_modules = m["config"]["dev_modules"]
    unseen_modules = m["config"]["unseen_modules"]

    def healthy_train(mods):
        return [e for e in eps.values() if e.entry["module_id"] in mods and e.entry["fault_id"] == 0 and e.entry["scenario_class"] == "standard"
                and e.entry["role"] in ("dev", "commissioning")]

    results = {}      # (split, budget) -> detector -> [scores]
    thresholds = {}
    for bname, budget in BUDGETS.items():
        dev_scores = defaultdict(list)
        for hold in dev_modules:
            tr_mods = [x for x in dev_modules if x != hold]
            model = train(healthy_train(tr_mods), {x: comm_of[x] for x in tr_mods}, budget)
            thresholds[(bname, hold)] = model["thr"]
            for e in eps.values():
                if e.entry["module_id"] != hold or e.entry["role"] != "dev" or e.entry["scenario_class"] != "standard":
                    continue
                flags = detect(model, e, comm_of[hold])
                for det, f in flags.items():
                    dev_scores[det].append(score_episode(e.entry, e.full_t, f, e.static_flags, det, data_fault_flags=e.has_data_fault))
                dev_scores["static"].append(score_episode(e.entry, e.full_t, e.static_flags, e.static_flags, "static", data_fault_flags=e.has_data_fault))
        results[("dev (LOMO)", bname)] = dev_scores
        model = train(healthy_train(dev_modules), {x: comm_of[x] for x in dev_modules}, budget)
        thresholds[(bname, "all-dev")] = model["thr"]
        un_scores = defaultdict(list)
        for e in eps.values():
            if e.entry["module_id"] not in unseen_modules or e.entry["role"] != "unseen" or e.entry["scenario_class"] != "standard":
                continue
            flags = detect(model, e, comm_of[e.entry["module_id"]])
            for det, f in flags.items():
                un_scores[det].append(score_episode(e.entry, e.full_t, f, e.static_flags, det, data_fault_flags=e.has_data_fault))
            un_scores["static"].append(score_episode(e.entry, e.full_t, e.static_flags, e.static_flags, "static", data_fault_flags=e.has_data_fault))
        results[("unseen", bname)] = un_scores

    out_lines = [f"CLASSICAL BASELINES vs STATIC ALARMS   [{m['dashboard_label']}]", PROVISIONAL_NOTE, "",
                 "Thresholds from healthy units only. ROC = 2 h rate-of-rise on pressure and temperature; EWMA lambda 0.02 and CUSUM k = 0.5 sigma on "
                 "healthy-trained residuals of pressure, temperature and log vacuum. Detectors run in the storage phase; historian view, OPC Good only.",
                 "Static baseline: spec Sec. 5/6 limits exist ONLY for pressure and the four temperatures (hydrogen 20/40 %LFL is an unverified reference value);"
                 " none for vacuum, strain, level or flows.", ""]
    realized = []
    for split in ("dev (LOMO)", "unseen"):
        for bname in BUDGETS:
            sc = results[(split, bname)]
            out_lines.append(f"=== {split}, false-alarm budget {bname} (per week of healthy exposure, split over each detector's channels) ===")
            out_lines.append("  realized false alarms per week on the scored healthy exposure (normal episodes + pre-onset time):")
            for det in ("static", "roc", "ewma", "cusum"):
                d = summarize(sc[det])
                fa = d["false_alarms"]
                out_lines.append(f"      {det:8} {fa['per_week']:.3f}/wk  ({fa['events']} events / {fa['healthy_exposure_weeks']:.1f} wk)   "
                                 f"alarms starting inside a data fault: {fa['data_fault_alarm_events']}")
                realized.append({"split": split, "budget": bname, "detector": det, **fa})
            out_lines += table({k: sc[k] for k in ("static", "roc", "ewma", "cusum")}, names)
            out_lines.append("")
    out_lines.append("static-alarm note per fault type:")
    for fid, txt in STATIC_NOTE.items():
        out_lines.append(f"   fault {fid:>2} {names[fid]:24} {txt}")
    out_lines += ["", PROVISIONAL_NOTE]
    text = "\n".join(out_lines)
    print(text)
    rep = ROOT / "output" / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / "classical_baselines.txt").write_text(text + "\n")
    (rep / "classical_baselines_thresholds.json").write_text(json.dumps({f"{b}|{h}": t for (b, h), t in thresholds.items()}, indent=1))


if __name__ == "__main__":
    main()
