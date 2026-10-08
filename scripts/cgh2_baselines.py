"""CGH2 step 5e: static alarms (PROVISIONAL) next to ROC, EWMA, CUSUM and a temperature-compensated inventory residual, thresholds set on
HEALTHY units only to a false-alarm budget of 1 per week and 1 per 4 weeks. Reports detection rate and median lead time per fault class,
dev (leave-one-module-out) and unseen (one shot). Classes with no static alarm on their signature channel are reported as 'no alarm
defined', not 'missed'.

    python scripts/cgh2_baselines.py [output/cgh2/medium]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.cgh2.dashboard import PROVISIONAL_NOTE, CGH2Dashboard
from hydrai_twin.cgh2.episode import FAULT_LABELS
from hydrai_twin.physical_dataset import static_flags_from_parquet
from ml.cgh2_baselines import DETECTORS, detect, load_episode, train
from ml.headline_metrics import alarm_load_verdict, score_episode, summarize

ROOT = Path(__file__).resolve().parent.parent
BUDGETS = {"1/wk": 1.0, "1/4wk": 0.25}
H = 3600.0
DETS = ("static", "roc", "ewma", "cusum", "inv")
STATIC_NOTE = {
    1: "gas temperature spike: TAH 85 C exists; only a large spike crosses it",
    2: "gas temperature / pressure: TAH, PAH exist; a moderate thermal anomaly stays below them",
    3: "NO alarm on its primary signature (pressure fall, inventory): there is no low-pressure or inventory alarm; the H2 alarm (25 %LFL) exists and picks up >= ~1 mm only",
    4: "pressure high: PAH / PAHH exist (overrun, blocked relief, fire); the stuck-open discharge valve shows only on the flow meter and inventory: no alarm defined",
    5: "H2 detector alarm 25 / 50 %LFL exists",
    6: "strain: NO static alarm defined",
    -1: "variable",
}
NO_ALARM_DEFINED = {6}


def fmt_h(x):
    return "-" if x is None else f"{x / H:.1f}"


def table(scores_by_det, label_of):
    lines = []
    for fid in sorted({s.fault_id for ss in scores_by_det.values() for s in ss if s.fault_id != 0}, key=lambda x: (x < 0, x)):
        lines.append(f"  class {fid:>2} {label_of[fid]}")
        for det, ss in scores_by_det.items():
            sub = [s for s in ss if s.fault_id == fid]
            det_s = [s for s in sub if s.first_alarm_s is not None]
            delays = [s.delay_vs_onset_s for s in det_s]
            leads = [s.lead_vs_static_s for s in sub if s.lead_vs_static_s is not None]
            only = sum(1 for s in sub if s.outcome == "agent_only")
            if det == "static" and fid in NO_ALARM_DEFINED:
                lines.append(f"      {det:7} n={len(sub):<3} no alarm defined (not 'missed')")
                continue
            tail = "(reference)" if det == "static" else f"lead vs static {fmt_h(np.median(leads) if leads else None):>6} h (n={len(leads)}), fired where static never did: {only}"
            lines.append(f"      {det:7} n={len(sub):<3} detected {len(det_s):>3}/{len(sub):<3} ({100 * len(det_s) / max(len(sub), 1):4.0f}%)  median delay {fmt_h(np.median(delays) if delays else None):>6} h   {tail}")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/cgh2/medium")
    args = ap.parse_args()
    root = ROOT / args.dataset
    m = json.loads((root / "manifest.json").read_text())
    dash = CGH2Dashboard.from_dict(m["dashboard"])
    eps = {}
    for e in m["episodes"]:
        ep = load_episode(root, e, m["class_parameters"]["volume_m3"])
        _, sf = static_flags_from_parquet(root / e["slow_file"], dash)
        ep.static_flags = np.array(sf, dtype=bool)
        eps[e["name"]] = ep
    comm_of = {e.entry["module_id"]: e for e in eps.values() if e.entry["role"] == "commissioning"}
    dev, unseen = m["config"]["dev_modules"], m["config"]["unseen_modules"]
    healthy = lambda mods: [e for e in eps.values() if e.entry["module_id"] in mods and e.entry["fault_id"] == 0 and e.entry["scenario_class"] == "standard"
                            and e.entry["role"] in ("dev", "commissioning") and e.entry["family"] != "normal-dark-vessel" and "dark" not in e.entry["variant_tag"]]
    results = {}
    for bname, budget in BUDGETS.items():
        ds = defaultdict(list)
        for hold in dev:
            tr = [x for x in dev if x != hold]
            model = train(healthy(tr), {x: comm_of[x] for x in tr}, budget)
            for e in eps.values():
                if e.entry["module_id"] != hold or e.entry["role"] != "dev":
                    continue
                for det, f in detect(model, e, comm_of[hold]).items():
                    full = f
                    ds[det].append(score_episode(e.entry, e.t, full, e.static_flags, det, data_fault_flags=e.has_data_fault))
                ds["static"].append(score_episode(e.entry, e.t, e.static_flags, e.static_flags, "static", data_fault_flags=e.has_data_fault))
        results[("dev (LOMO)", bname)] = ds
        model = train(healthy(dev), {x: comm_of[x] for x in dev}, budget)
        us = defaultdict(list)
        for e in eps.values():
            if e.entry["role"] != "unseen":
                continue
            for det, f in detect(model, e, comm_of[e.entry["module_id"]]).items():
                us[det].append(score_episode(e.entry, e.t, f, e.static_flags, det, data_fault_flags=e.has_data_fault))
            us["static"].append(score_episode(e.entry, e.t, e.static_flags, e.static_flags, "static", data_fault_flags=e.has_data_fault))
        results[("unseen", bname)] = us

    out = [f"CGH2 CLASSICAL BASELINES vs STATIC ALARMS   [{m['dashboard_label']}; pressure class {m['config']['pressure_class']}]", PROVISIONAL_NOTE, "",
           "Thresholds from healthy units only (normal episodes + commissioning runs of the training modules; the dark-vessel stress runs are excluded).",
           "ROC = |2 h rate of change| of pressure and gas temperature; EWMA / CUSUM on residuals of temperature-compensated pressure and of gas temperature",
           "(regressed on shell temperature, ambient and compressor status); INV = CUSUM of the temperature-compensated inventory slope during hold windows.",
           "Channels with NO static alarm: " + ", ".join(m["channels_without_static_alarm"]), ""]
    label_of = {k: v for k, v in FAULT_LABELS.items()}
    for split in ("dev (LOMO)", "unseen"):
        for bname in BUDGETS:
            sc = results[(split, bname)]
            out.append(f"=== {split}, false-alarm budget {bname} ===")
            out.append("  realized false alarms per week on the scored healthy exposure (normal episodes + pre-onset time):")
            for det in DETS:
                fa = summarize(sc[det])["false_alarms"]
                aph = summarize(sc[det])["alerts_per_hour_healthy"]
                out.append(f"      {det:7} {fa['per_week']:.3f}/wk = {aph:.4f} per hour ({alarm_load_verdict(aph, 'agent')} vs ~1/h target; EEMUA 6/h manageable); "
                           f"({fa['events']} events / {fa['healthy_exposure_weeks']:.1f} wk); alarms starting inside a data fault: {fa['data_fault_alarm_events']}")
            out += table({d: sc[d] for d in DETS}, label_of)
            out.append("")
    out.append("static-alarm note per fault class:")
    for fid, txt in STATIC_NOTE.items():
        out.append(f"   class {fid:>2} {label_of[fid]:30} {txt}")
    out += ["", PROVISIONAL_NOTE]
    text = "\n".join(out)
    print(text)
    rep = ROOT / "output" / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / "cgh2_baselines.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
