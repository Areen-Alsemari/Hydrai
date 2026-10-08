"""CGH2 agent, CHECKPOINT 1: features (step 1), learned slow layer (2B) against static / ROC / EWMA / CUSUM / inventory baselines on dev
leave-one-module-out, plus the E1 gap analysis (delay vs onset AND vs the first-observable floor, ratios, operating curves).

Unseen and the low/high OOD sets are NOT touched here. Everything is set on dev only; thresholds on healthy units only.

    python scripts/cgh2_agent_checkpoint1.py [output/cgh2/medium]
"""

import argparse
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.cgh2.dashboard import PROVISIONAL_NOTE, CGH2Dashboard
from hydrai_twin.physical_dataset import static_flags_from_parquet
from ml import cgh2_agent as AG
from ml import cgh2_baselines as BL
from ml.cgh2_features import build, load_raw
from ml.headline_metrics import score_episode, summarize

ROOT = Path(__file__).resolve().parent.parent
BUDGETS = {"1/day": 7.0, "1/wk": 1.0, "1/4wk": 0.25}
CLASSICAL = ("roc", "ewma", "cusum", "inv")
H = 3600.0
rng = np.random.default_rng(0)


def group_of(e: dict) -> list[str]:
    """Report groups an episode belongs to: its class, class 3 by leak size, and class 3 with/without the expected-miss stress leaks."""
    fid = e["fault_id"]
    names = {1: "1 sensor_fault", 2: "2 thermal_anomaly", 3: "3 small_slow_leak", 4: "4 abnormal_pressure_behaviour", 5: "5 containment_anomaly",
             6: "6 structural_concern", -1: "-1 unknown_anomaly"}
    g = [names[fid]]
    if fid == 3:
        d = e["variant_tag"].split("-")[-1]
        g.append(f"3{'s' if e['expected_miss'] else ''} leak {d}")
        if not e["expected_miss"]:
            g.append("3 small_slow_leak, WITHOUT expected-miss (0.1-1 mm)")
    if fid == 5 and e["family"] == "rupture":
        g.append("5r rupture (50 mm)")
    return g


def boot_frac(flags: list[bool], n: int = 1000) -> tuple[float, float, float]:
    a = np.array(flags, dtype=float)
    if len(a) == 0:
        return (float("nan"),) * 3
    bs = [rng.choice(a, len(a)).mean() for _ in range(n)]
    return a.mean(), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def med_ci(x: list[float], n: int = 1000):
    if not x:
        return None, None, None
    a = np.array(x)
    bs = [np.median(rng.choice(a, len(a))) for _ in range(n)]
    return float(np.median(a)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def fh(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x / H:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/cgh2/medium")
    args = ap.parse_args()
    root = ROOT / args.dataset
    m = json.loads((root / "manifest.json").read_text())
    dash = CGH2Dashboard.from_dict(m["dashboard"])
    cls = m["class_parameters"]
    dev = m["config"]["dev_modules"]
    t0 = time.time()

    # ---- load everything dashboard-visible --------------------------------------------------------------------------------------
    eps: dict[str, AG.Ep] = {}
    bl: dict[str, BL.Episode] = {}
    for e in m["episodes"]:
        if e["role"] == "unseen":
            continue                                           # unseen is touched once, later
        raw = load_raw(root, e, cls)
        names, X = build(raw)
        _, sf = static_flags_from_parquet(root / e["slow_file"], dash)
        eps[e["name"]] = AG.Ep(e, raw.t, X, np.array(sf, dtype=bool), raw.has_data_fault)
        b = BL.load_episode(root, e, cls["volume_m3"])
        b.static_flags = np.array(sf, dtype=bool)
        bl[e["name"]] = b
    print(f"loaded {len(eps)} dev/commissioning episodes, {len(names)} features ({time.time() - t0:.0f}s)", flush=True)
    comm_bl = {b.entry["module_id"]: b for b in bl.values() if b.entry["role"] == "commissioning"}
    dev_eps = [e for e in eps.values() if e.entry["role"] == "dev"]

    # ---- flags per (budget, detector, episode) ------------------------------------------------------------------------------------
    flags: dict[tuple[str, str], dict[str, np.ndarray]] = defaultdict(dict)
    healthy_bl = lambda mods: [b for b in bl.values() if b.entry["module_id"] in mods and b.entry["fault_id"] == 0 and b.entry["scenario_class"] == "standard"
                               and b.entry["role"] in ("dev", "commissioning") and "dark" not in b.entry["variant_tag"]]
    for hold in dev:
        tr = [x for x in dev if x != hold]
        for bname, rate in BUDGETS.items():
            model = BL.train(healthy_bl(tr), {x: comm_bl[x] for x in tr}, rate)
            for nm, b in bl.items():
                if b.entry["module_id"] == hold and b.entry["role"] == "dev":
                    for det, f in BL.detect(model, b, comm_bl[hold]).items():
                        flags[(bname, det)][nm] = f
    print(f"classical baselines done ({time.time() - t0:.0f}s)", flush=True)

    train_pool = lambda mods: [e for e in eps.values() if e.entry["module_id"] in mods and e.entry["role"] in ("dev", "commissioning")]
    for hold in dev:
        tr = [x for x in dev if x != hold]
        pool = train_pool(tr)
        oof = AG.oof_healthy_scores(pool, tr)
        thr = AG.thresholds(oof, BUDGETS)
        model = AG.fit(pool)
        for e in dev_eps:
            if e.entry["module_id"] != hold:
                continue
            s = AG.score(model, e)
            for bname in BUDGETS:
                flags[(bname, "learned")][e.entry["name"]] = AG.alarm_flags(s, thr[bname])
        no_h2 = np.array([i for i, nme in enumerate(names) if not nme.startswith("h2_")])        # ablation: the leak->hydrogen coupling is a placeholder (JUDGE)
        oof2 = AG.oof_healthy_scores(pool, tr, no_h2)
        thr2 = AG.thresholds(oof2, BUDGETS)
        model2 = AG.fit(pool, no_h2)
        for e in dev_eps:
            if e.entry["module_id"] == hold:
                s2 = AG.score(model2, e, no_h2)
                for bname in BUDGETS:
                    flags[(bname, "learned_noH2")][e.entry["name"]] = AG.alarm_flags(s2, thr2[bname])
        print(f"  learned layer: held-out {hold} done; thresholds {({k: round(v, 3) for k, v in thr.items()})} ({time.time() - t0:.0f}s)", flush=True)

    # ---- scoring --------------------------------------------------------------------------------------------------------------------
    DETS = ("static",) + CLASSICAL + ("learned", "learned_noH2")
    scores: dict[tuple[str, str], list] = defaultdict(list)
    for bname in BUDGETS:
        for e in dev_eps:
            nm = e.entry["name"]
            scores[(bname, "static")].append(score_episode(e.entry, e.t, e.static, e.static, "static", data_fault_flags=e.has_df))
            for det in CLASSICAL + ("learned", "learned_noH2"):
                scores[(bname, det)].append(score_episode(e.entry, e.t, flags[(bname, det)][nm], e.static, det, data_fault_flags=e.has_df))
    entries = {e.entry["name"]: e.entry for e in dev_eps}
    by_name = lambda bname, det: {s.episode_id: s for s in scores[(bname, det)]}
    ep_of = {e.entry["episode_id"]: e.entry for e in dev_eps}
    (ROOT / "output" / "cgh2_cache").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "output" / "cgh2_cache" / "checkpoint1_scores.pkl", "wb") as f:
        pickle.dump({"scores": dict(scores), "entries": entries, "flags": {k: v for k, v in flags.items()}, "t": {nm: e.t for nm, e in eps.items()}}, f)

    # ---- null reference: the same detectors on HEALTHY episodes with a random pseudo-onset (what chance 'detection' looks like) ------------
    from ml.headline_metrics import alarm_events
    null = {}
    healthy_eps = [e for e in dev_eps if e.entry["fault_id"] == 0 and e.entry["scenario_class"] == "standard"]
    for bname in BUDGETS:
        for det in ("static",) + CLASSICAL + ("learned", "learned_noH2"):
            hit, hit24, hit48, delays = [], [], [], []
            for e in healthy_eps:
                f = e.static if det == "static" else flags[(bname, det)][e.entry["name"]]
                ev = np.array(alarm_events(e.t, f, 3600.0))
                for _ in range(5):
                    on = rng.uniform(3, 5) * 86400.0
                    nxt = ev[ev >= on]
                    hit.append(len(nxt) > 0)
                    hit24.append(bool(len(nxt) and nxt[0] - on <= 24 * H))
                    hit48.append(bool(len(nxt) and nxt[0] - on <= 48 * H))
                    if len(nxt):
                        delays.append(nxt[0] - on)
            null[(bname, det)] = dict(any=float(np.mean(hit)), h24=float(np.mean(hit24)), h48=float(np.mean(hit48)), med=float(np.median(delays)) if delays else None, n=len(hit))

    # ---- tables -----------------------------------------------------------------------------------------------------------------------
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in dev_eps:
        if e.entry["fault_id"] != 0 and e.entry["scenario_class"] == "standard":
            for g in group_of(e.entry):
                groups[g].append(e.entry)
    order = sorted(groups, key=lambda g: (g.split()[0].lstrip("-").rjust(3, "0") if g[0] != "-" else "999", g))
    out = [f"# CGH2 agent - checkpoint 1 (dev leave-one-module-out, medium class)", "",
           f"Reference configuration, not a verified Saudi system. {PROVISIONAL_NOTE}. The static baseline has NO low-pressure alarm (see cgh2_register_diff.md).", "",
           "Thresholds of every detector are set on healthy dev units only (classical: normal episodes + commissioning of the training modules; learned: out-of-fold scores of the "
           "training modules' normal episodes). Unseen and OOD are untouched. 'delay' = first alarm event at/after onset; 'floor' = first observable deviation of the paired "
           "healthy twin (an ideal-observer bound, k = 3 sigma). Intervals are 95 % bootstrap over episodes.", ""]

    def cell(bname, det, eps_list):
        sc = by_name(bname, det)
        S = [sc[e["episode_id"]] for e in eps_list]
        det_f = [s.first_alarm_s is not None for s in S]
        frac, lo, hi = boot_frac(det_f)
        d_obs = [s.delay_vs_observable_s for s in S if s.first_alarm_s is not None and s.delay_vs_observable_s is not None]
        d_on = [s.delay_vs_onset_s for s in S if s.first_alarm_s is not None]
        k24 = sum(1 for s_ in S if s_.first_alarm_s is not None and s_.delay_vs_onset_s <= 24 * H)
        return dict(k=sum(det_f), n=len(S), frac=frac, lo=lo, hi=hi, obs=d_obs, on=d_on, S=S, k24=k24)

    for bname in ("1/wk",):
        out += [f"## Table 1. Per-class results at a false-alarm budget of {bname}", "",
                "Realized false alarms per week on the scored healthy exposure (normal episodes + pre-onset time):", ""]
        fa = {}
        for det in DETS:
            d = summarize(scores[(bname, det)])
            fa[det] = d["false_alarms"]["per_week"]
        out += ["| detector | " + " | ".join(DETS) + " |", "|---|" + "---|" * len(DETS),
                "| false alarms / week | " + " | ".join(f"{fa[d]:.2f}" for d in DETS) + " |",
                "| NULL: healthy episodes, a pseudo-onset on day 3-5: 'detected' by chance (any time) | " + " | ".join(f"{100 * null[(bname, d)]['any']:.0f} %" for d in DETS) + " |",
                "| NULL: ... within 24 h | " + " | ".join(f"{100 * null[(bname, d)]['h24']:.0f} %" for d in DETS) + " |",
                "| NULL: ... within 48 h | " + " | ".join(f"{100 * null[(bname, d)]['h48']:.0f} %" for d in DETS) + " |", "",
                "**Read the detection columns against the NULL rows.** A detector with about 1 false alarm per week 'detects' a pseudo-fault on a healthy tank in the 'any time' row's share of cases within the "
                "~10 days left in the episode, so a detection delayed by days is indistinguishable from chance. 'Detected within 24 h' is the column to trust.", ""]
        out += ["Detection = k/n (95 % CI); 'after floor' = median delay after the first-observable time, hours (negative = alarm before the ideal-observer floor); "
                "lead = median over episodes where both fire (n), hours, positive = the learned layer / this detector alarmed EARLIER.", ""]
        for g in order:
            el = groups[g]
            cells = {d: cell(bname, d, el) for d in DETS}
            floor = [(e["first_observable_s"] - e["onset_s"]) for e in el if e["first_observable_s"] is not None]
            # best classical = highest detection rate, then lowest median delay
            def key(d):
                c = cells[d]
                return (-c["k"], np.median(c["on"]) if c["on"] else 9e9)
            best = min(CLASSICAL, key=key)
            out += [f"### {g}  (n = {len(el)}; floor: first observable {fh(np.median(floor)) if floor else '-'} h after onset for {len(floor)}/{len(el)})", "",
                    "| detector | detected (95 % CI) | detected within 24 h | median delay after onset h (IQR) | median delay after floor h | lead vs static h (n) | lead vs best classical (" + best + ") h (n) |", "|---|---|---|---|---|---|---|"]
            for d in DETS:
                c = cells[d]
                if d == "static" and g.startswith("6 "):
                    out.append(f"| static | no alarm defined | | | | | |")
                    continue
                iqr = f"{fh(np.percentile(c['on'], 25))}-{fh(np.percentile(c['on'], 75))}" if c["on"] else "-"
                lead_s = [s_static.first_alarm_s - s.first_alarm_s for s, s_static in zip(c["S"], cells["static"]["S"]) if s.first_alarm_s is not None and s_static.first_alarm_s is not None]
                lead_b = [s_b.first_alarm_s - s.first_alarm_s for s, s_b in zip(c["S"], cells[best]["S"]) if s.first_alarm_s is not None and s_b.first_alarm_s is not None]
                out.append(f"| {d} | {c['k']}/{c['n']} ({c['lo']:.2f}-{c['hi']:.2f}) | {c['k24']}/{c['n']} | {fh(np.median(c['on'])) if c['on'] else '-'} ({iqr}) | {fh(np.median(c['obs'])) if c['obs'] else '-'} | "
                           f"{(fh(np.median(lead_s)) + f' ({len(lead_s)})') if lead_s and d != 'static' else '-'} | {(fh(np.median(lead_b)) + f' ({len(lead_b)})') if lead_b and d not in (best, 'static') else '-'} |")
            out.append("")

    out += ["## Table 2 (E1). Gap analysis: delay versus the physical floor, and operating curves", "",
            "Ratio = detection delay after onset / (first-observable time after onset), median over episodes detected and observable; 1.0 = at the floor, >1 = later. "
            "Operating curve = detection rate and median delay after onset (h) as the false-alarm budget loosens.", ""]
    for g in order:
        el = groups[g]
        floor = [(e["first_observable_s"] - e["onset_s"]) for e in el if e["first_observable_s"] is not None]
        out += [f"### {g}  (floor median {fh(np.median(floor)) if floor else '-'} h, IQR {fh(np.percentile(floor, 25)) + '-' + fh(np.percentile(floor, 75)) if floor else '-'})", "",
                "| detector | ratio delay/floor (median) | 1/day: detected, delay h | 1/wk: detected, delay h | 1/4wk: detected, delay h |", "|---|---|---|---|---|"]
        for d in DETS:
            if d == "static" and g.startswith("6 "):
                continue
            row = []
            for bname in BUDGETS:
                c = cell(bname, d, el)
                row.append(f"{c['k']}/{c['n']}, {fh(np.median(c['on'])) if c['on'] else '-'}")
                if bname == "1/wk":
                    rat = [s.delay_vs_onset_s / (s.first_observable_s - s.onset_s) for s in c["S"]
                           if s.first_alarm_s is not None and s.first_observable_s is not None and s.first_observable_s > s.onset_s]
                    rs = f"{np.median(rat):.1f} (n={len(rat)})" if rat else "-"
            out.append(f"| {d} | {rs} | " + " | ".join(row) + " |")
        out.append("")
    text = "\n".join(out)
    (ROOT / "output" / "reports" / "cgh2_checkpoint1.md").write_text(text + "\n")
    print(text[:6000])
    print(f"\ntotal {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
