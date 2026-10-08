"""Evaluation of the HYDRAI tool agent on dev (leave-one-module-out). Writes output/reports/<out>.md and .json.

    python scripts/cgh2_agent_eval.py --runs full --out cgh2_agent_dev
    python scripts/cgh2_agent_eval.py --ablation full,noT9,... --out cgh2_agent_ablation

Compared: static A (the reference DCS alarms), static B (A + the PROPOSED low-pressure alarm at 70 % MOP, a register open decision), ROC, EWMA, CUSUM, inventory baseline,
the single learned model of checkpoint 1 (66 features, one model), the fusion score alone (tool features, no investigation), and the tool agent at its watch and alert tiers.
Baseline flags are the checkpoint-1 flags at the same 1-per-week healthy budget. Everything is dev only; unseen / OOD are not touched.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.session import get_units
from hydrai_twin.cgh2_agent.tools.t13_procedures import CLASS_NAMES
from ml.headline_metrics import alarm_events, score_episode, summarize

ROOT = Path(__file__).resolve().parents[1]
H = 3600.0
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")
rng = np.random.default_rng(0)
PAL_FRAC = 0.70


def group_of(e: dict) -> list[str]:
    fid = e["fault_id"]
    names = {1: "1 sensor_fault", 2: "2 thermal_anomaly", 3: "3 small_slow_leak", 4: "4 abnormal_pressure_behaviour", 5: "5 containment_anomaly", 6: "6 structural_concern", -1: "-1 unknown_anomaly (composite)"}
    g = [names[fid]]
    if fid == 3:
        d = e["variant_tag"].split("-")[-1]
        g.append(f"3{'s' if e['expected_miss'] else ''} leak {d}")
        if not e["expected_miss"]:
            g.append("3 small_slow_leak WITHOUT expected-miss (0.1-1 mm)")
    if fid == 5 and e["family"] == "rupture":
        g.append("5r rupture (50 mm)")
    return g


def boot_frac(flags, n=1000):
    a = np.array(flags, dtype=float)
    if len(a) == 0:
        return float("nan"), float("nan"), float("nan")
    bs = [rng.choice(a, len(a)).mean() for _ in range(n)]
    return a.mean(), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def med_ci(x, n=500):
    if len(x) == 0:
        return None
    a = np.array(x)
    bs = [np.median(rng.choice(a, len(a))) for _ in range(n)]
    return float(np.median(a)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


fh = lambda x: "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x / H:.1f}"


def load_runs(tag: str) -> dict:
    with open(F.CACHE / f"runs_{tag}.pkl", "rb") as f:
        return pickle.load(f)


FINAL_SETS = {"unseen": ("output/cgh2/medium", "unseen"), "low": ("output/cgh2/low", "ood"), "high": ("output/cgh2/high", "ood")}


class Data:
    """Everything the scoring needs for the dev episodes (leave-one-module-out) or, with `final`, for the one-shot unseen / OOD sets."""
    def __init__(self, runs: dict, final: str | None = None):
        self.final = final
        if final:
            dataset, role = FINAL_SETS[final]
            self.manifest, units = get_units(dataset, (role, "commissioning"))
            self.units = {k: u for k, u in units.items() if u.entry["role"] == role}
            self.base_flags = pickle.load(open(F.CACHE / f"final_{final}_baselines.pkl", "rb"))
            thr = pickle.load(open(F.CACHE / "meta_final.pkl", "rb"))["thr"]
            self.thr = defaultdict(lambda: thr)
        else:
            self.manifest, units = get_units()
            self.units = {k: u for k, u in units.items() if u.entry["role"] == "dev"}
            ck = pickle.load(open(ROOT / "output" / "cgh2_cache" / "checkpoint1_scores.pkl", "rb"))
            self.base_flags = ck["flags"]                           # {(budget, detector): {name: bool array}}
            self.thr = {h: pickle.load(open(F.CACHE / f"meta_{h}.pkl", "rb"))["thr"] for h in MODULES}
        self.entries = {k: u.entry for k, u in self.units.items()}
        self.runs = runs
        self.cum_rel = {}
        for k, u in self.units.items():
            self.cum_rel[k] = np.concatenate([[0.0], np.cumsum((np.nan_to_num(u.truth["mdot_leak"]) + np.nan_to_num(u.truth["mdot_prv"])) * 60.0)])

    def released_between(self, name: str, t0: float, t1: float) -> float:
        u = self.units[name]
        i0, i1 = int(np.searchsorted(u.t, t0)), int(np.searchsorted(u.t, t1))
        c = self.cum_rel[name]
        return float(c[min(i1, len(c) - 1)] - c[min(i0, len(c) - 1)])

    def probs(self, name: str) -> np.ndarray:
        return np.load((F.CACHE / "final" / f"probs_{name}.npy") if self.final else (F.CACHE / f"probs_{name}.npy"))

    def flags(self, det: str, name: str) -> np.ndarray:
        u = self.units[name]
        e = u.entry
        n = u.n
        if det == "static_A":
            return u.static
        if det == "static_B":
            pal = (u.raw.x["P"] < PAL_FRAC * u.cls["mop_bar"]) & (u.t > 86400.0)
            return u.static | pal
        if det in ("roc", "ewma", "cusum", "inv", "learned", "learned_noH2"):
            return self.base_flags[("1/wk", det)][name]
        thr = self.thr[e["module_id"]]
        if det == "fusion_alert" or det == "fusion_watch":
            P = self.probs(name)
            return (1 - P[:, 0]) > thr["alert" if det == "fusion_alert" else "watch"]
        if det == "fusion_4wk":
            P = self.probs(name)
            return (1 - P[:, 0]) > thr["alert_4wk"]
        if det in ("agent_alert", "agent_watch"):
            f = np.zeros(n, dtype=bool)
            for ev in self.runs[name]["events"]:
                t = ev["t_alert_s"] if det == "agent_alert" else ev["t_watch_s"]
                if t is not None:
                    f[min(int(np.searchsorted(u.t, t)), n - 1)] = True
            return f
        raise KeyError(det)


def score_all(D: Data, dets):
    S = {}
    for det in dets:
        S[det] = {name: score_episode(u.entry, u.t, D.flags(det, name), u.static, det, data_fault_flags=u.truth["has_data_fault"]) for name, u in D.units.items()}
    return S


def first_diag(run: dict, e: dict, min_tier=("alert", "critical")):
    """First decision of tier >= alert whose class is correct (composites: open-set rejection is the correct answer)."""
    true = e["fault_id"]
    for d in run["decisions"]:
        if d["t_s"] < e["onset_s"]:
            continue
        if d["tier"] in min_tier and d["cls"] == true:
            return d["t_s"]
    return None


def first_alert_decision(run: dict, e: dict):
    for d in run["decisions"]:
        if d["t_s"] >= e["onset_s"] and d["tier"] in ("alert", "critical"):
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="full")
    ap.add_argument("--out", default="cgh2_agent_dev")
    ap.add_argument("--ablation", default="")
    ap.add_argument("--final", default="", choices=["", "unseen", "low", "high"], help="score the one-shot unseen / OOD set instead of dev")
    a = ap.parse_args()
    if a.ablation:
        return ablation(a)
    if a.final:
        with open(F.CACHE / f"final_{a.final}.pkl", "rb") as f:
            D = Data(pickle.load(f), a.final)
    else:
        D = Data(load_runs(a.runs))
    dets = ["static_A", "static_B", "roc", "ewma", "cusum", "inv", "learned", "fusion_alert", "agent_watch", "agent_alert"]
    S = score_all(D, dets)
    names = list(D.units)
    faults = [n for n in names if D.entries[n]["fault_id"] != 0 and D.entries[n]["scenario_class"] == "standard"]
    groups: dict[str, list[str]] = defaultdict(list)
    for n in faults:
        for g in group_of(D.entries[n]):
            groups[g].append(n)
    order = sorted(groups, key=lambda g: (g.split()[0].lstrip("-").rjust(3, "0") if g[0] != "-" else "999", g))
    scope = ("dev evaluation (leave-one-module-out, medium class)" if not a.final else f"ONE-SHOT {a.final} set ({'medium class, modules never seen in dev' if a.final == 'unseen' else a.final + ' pressure class, out of distribution'}); frozen configuration, trained on all dev")
    out = [f"# HYDRAI tool agent: {scope}", "",
           ("Reference configuration, not a verified Saudi system. All numbers are dev only (6 modules x leave-one-module-out). Unseen and OOD are NOT used. " if not a.final else "Reference configuration, not a verified Saudi system. Touched ONCE, after the configuration was frozen; nothing was tuned on these units. ") + "Intervals are 95 % bootstrap over episodes. "
           "Small n is shown as k/n with its interval. 'floor' = first observable deviation of the paired healthy twin (an ideal-observer bound, not a hard physical limit).", "",
           "Detectors: **static A** = the reference DCS alarms (no low-pressure alarm); **static B** = A plus the PROPOSED low-pressure alarm at 70 % MOP (register open decision; would false-alarm in the healthy twin); "
           "ROC / EWMA / CUSUM / inventory = classical baselines (checkpoint 1, 1 healthy false alarm per week); **learned** = the single learned model of checkpoint 1 (66 features, one model); "
           "**fusion only** = the tool features' meta-model score alone (no investigation); **agent watch / alert** = the orchestrator tiers. Thresholds for all of them come from healthy dev data only.", ""]
    # ---- false alarms
    out += ["## 1. False alarms on healthy exposure", "", "| detector | events | healthy exposure (weeks) | false alarms per week (95 % CI) | per healthy hour |", "|---|---|---|---|---|"]
    fa_res = {}
    for det in dets:
        sm = summarize(list(S[det].values()))
        f = sm["false_alarms"]
        fa_res[det] = f
        out.append(f"| {det} | {f['events']} | {f['healthy_exposure_weeks']:.1f} | {f['per_week']:.2f} ({f['per_week_ci95'][0]:.2f}-{f['per_week_ci95'][1]:.2f}) | {f['events'] / (f['healthy_exposure_weeks'] * 168):.4f} |")
    out += ["", "Alarm-load reference: EEMUA 191 / ISA-18.2 manageable <= 6 per hour; agent target about 1 alert per hour. Healthy exposure includes the dark-vessel stress variants (not used for thresholds).", ""]
    # watch/alert per hour
    # ---- per-group detection table
    out += ["## 2. Detection per class (alert level; tier definitions fixed before the results were seen)", ""]
    results: dict[str, dict] = {}
    for g in order:
        el = groups[g]
        floor = [D.entries[n]["first_observable_s"] - D.entries[n]["onset_s"] for n in el if D.entries[n]["first_observable_s"] is not None]
        stress = el and all(D.entries[n]["expected_miss"] for n in el)
        out += [f"### {g}  (n = {len(el)}; floor: first observable {fh(np.median(floor)) if floor else '-'} h after onset for {len(floor)}/{len(el)})", "",
                "| detector | detected within 24 h (95 % CI) | " + ("within 72 h | within 3x floor | " if stress else "") + "median delay after onset h (IQR) | median delay after floor h | kg released before detection (median, detected) |", "|---|---|" + ("---|---|" if stress else "") + "---|---|---|"]
        for det in dets:
            if det.startswith("static") and g.startswith("6 "):
                out.append(f"| {det} | no alarm defined |" + (" | |" if stress else "") + " | | |")
                continue
            sc = [S[det][n] for n in el]
            k24 = [s.first_alarm_s is not None and s.delay_vs_onset_s <= 24 * H for s in sc]
            fr, lo, hi = boot_frac(k24)
            dl = [s.delay_vs_onset_s for s in sc if s.first_alarm_s is not None]
            do = [s.delay_vs_observable_s for s in sc if s.first_alarm_s is not None and s.delay_vs_observable_s is not None]
            kg = [D.released_between(n, D.entries[n]["onset_s"], S[det][n].first_alarm_s) for n in el if S[det][n].first_alarm_s is not None]
            extra = ""
            if stress:
                k72 = sum(1 for s in sc if s.first_alarm_s is not None and s.delay_vs_onset_s <= 72 * H)
                k3 = 0
                n3 = 0
                for n in el:
                    e = D.entries[n]
                    if e["first_observable_s"] is None:
                        continue
                    n3 += 1
                    s_ = S[det][n]
                    if s_.first_alarm_s is not None and s_.delay_vs_onset_s <= 3 * (e["first_observable_s"] - e["onset_s"]):
                        k3 += 1
                extra = f"{k72}/{len(el)} | {k3}/{n3} (floor exists) | "
            iqr = f"{fh(np.percentile(dl, 25))}-{fh(np.percentile(dl, 75))}" if dl else "-"
            out.append(f"| {det} | {sum(k24)}/{len(el)} ({lo:.2f}-{hi:.2f}) | {extra}{fh(np.median(dl)) if dl else '-'} ({iqr}) | {fh(np.median(do)) if do else '-'} | {np.median(kg):.2f} (n={len(kg)}) |" if kg else
                       f"| {det} | {sum(k24)}/{len(el)} ({lo:.2f}-{hi:.2f}) | {extra}- | - | - |")
            results.setdefault(g, {})[det] = {"k24": int(sum(k24)), "n": len(el), "median_delay_h": (float(np.median(dl)) / H if dl else None)}
        out.append("")
    # ---- operating curves: detection within 24 h at three false-alarm budgets
    if not a.final:
        curve_dets = [("learned @1/day", "1/day", "learned"), ("learned @1/wk", "1/wk", "learned"), ("learned @1/4wk", "1/4wk", "learned"), ("fusion @watch", None, "fusion_watch"), ("fusion @alert", None, "fusion_alert"), ("fusion @4wk", None, "fusion_4wk")]
        cs = {}
        for lab, bud, det in curve_dets:
            def flg(n, bud=bud, det=det):
                return D.base_flags[(bud, det)][n] if bud else D.flags(det, n)
            cs[lab] = {n: score_episode(D.entries[n], D.units[n].t, flg(n), D.units[n].static, det, data_fault_flags=D.units[n].truth["has_data_fault"]) for n in D.units}
        out += ["## 2b. Operating curves: detected within 24 h and healthy false alarms per week at three budgets", "",
                "Equal-cost reading of any 'earlier' claim: compare detectors at the same realized false-alarm rate (last row). The orchestrated agent's alert tier adds evidence-based escalations on top of the fusion score.", "",
                "| group | " + " | ".join(l for l, _, _ in curve_dets) + " | agent alert |", "|---|" + "---|" * (len(curve_dets) + 1)]
        for g in order:
            el = groups[g]
            row = []
            for lab, _, _ in curve_dets:
                row.append(f"{sum(1 for n in el if cs[lab][n].first_alarm_s is not None and cs[lab][n].delay_vs_onset_s <= 24 * H)}/{len(el)}")
            row.append(f"{sum(1 for n in el if S['agent_alert'][n].first_alarm_s is not None and S['agent_alert'][n].delay_vs_onset_s <= 24 * H)}/{len(el)}")
            out.append(f"| {g} | " + " | ".join(row) + " |")
        fa_row = [f"{summarize(list(cs[lab].values()))['false_alarms']['per_week']:.2f}" for lab, _, _ in curve_dets] + [f"{fa_res['agent_alert']['per_week']:.2f}"]
        out += ["| **healthy false alarms / week** | " + " | ".join(fa_row) + " |", ""]
    # ---- union coverage
    out += ["## 3. Union coverage within 24 h (static A OR agent alert)", "", "| class | n | static A | agent alert | static OR agent | agent only | static only | neither |", "|---|---|---|---|---|---|---|---|"]
    tot = np.zeros(6, dtype=int)
    for g in order:
        if g.startswith("6 ") or not any(g.startswith(x) for x in ("1 ", "2 ", "3 small", "4 ", "5 cont", "6 ", "-1")):
            if not g.startswith("6 "):
                continue
        el = groups[g]
        if g.startswith("3 small_slow_leak WITHOUT"):
            continue
        sa = [S["static_A"][n].first_alarm_s is not None and S["static_A"][n].delay_vs_onset_s <= 24 * H for n in el]
        ag = [S["agent_alert"][n].first_alarm_s is not None and S["agent_alert"][n].delay_vs_onset_s <= 24 * H for n in el]
        c = np.array([sum(sa), sum(ag), sum(x or y for x, y in zip(sa, ag)), sum(y and not x for x, y in zip(sa, ag)), sum(x and not y for x, y in zip(sa, ag)), sum(not x and not y for x, y in zip(sa, ag))])
        tot += c
        out.append(f"| {g} | {len(el)} | {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} |")
    n_all = sum(len(groups[g]) for g in order if g[0].isdigit() and g.split()[0] in ("1", "2", "3", "4", "5", "6") and "leak" not in g.split()[0] and not g.startswith("3s") and not g.startswith("3 small_slow_leak WITHOUT") and not g.startswith("5r") and not (g.startswith("3 leak")))
    out += [f"| **all classes (rows above)** | {n_all} | {tot[0]} | {tot[1]} | {tot[2]} | {tot[3]} | {tot[4]} | {tot[5]} |", ""]
    # ---- diagnosis
    cm = np.zeros((8, 8), dtype=int)                       # rows: true 0..6 + composite(-1 as 7); cols: predicted 0..6 + unknown(7)
    diag_rows = []
    kg_diag, t_diag = defaultdict(list), defaultdict(list)
    diag_ok = defaultdict(lambda: [0, 0])
    for n in names:
        e = D.entries[n]
        if e["fault_id"] == 0 or e["scenario_class"] != "standard" and e["fault_id"] > 0:
            continue
        r = D.runs[n]
        d = first_alert_decision(r, e)
        tr = 7 if e["fault_id"] < 0 else e["fault_id"]
        if d is None:
            continue
        pc = 7 if d["cls"] == -1 else d["cls"]
        cm[tr, pc] += 1
        g = group_of(e)[0]
        diag_ok[g][1] += 1
        diag_ok[g][0] += int(d["cls"] == e["fault_id"])
        td = first_diag(r, e)
        if td is not None:
            t_diag[g].append(td - e["onset_s"])
            kg_diag[g].append(D.released_between(n, e["onset_s"], td))
    out += ["## 4. Diagnosis (decision at the first alert; time to the first CORRECT alert-level diagnosis)", "",
            "Static alarms and the classical baselines give no diagnosis: for them 'time to correct diagnosis' is never. A composite (two simultaneous faults) is not a trained class: the correct answer is the open-set 'unknown pattern'.", "",
            "| class | episodes alerted | correct class at first alert | median time to correct diagnosis h (n) | median kg released before correct diagnosis |", "|---|---|---|---|---|"]
    for g in sorted(diag_ok, key=lambda x: x):
        ok, n_ = diag_ok[g]
        td = t_diag[g]
        out.append(f"| {g} | {n_} | {ok}/{n_} | {fh(np.median(td)) if td else 'never'} ({len(td)}) | {np.median(kg_diag[g]):.2f} |" if td else f"| {g} | {n_} | {ok}/{n_} | never (0) | - |")
    labs = ["healthy", "sensor", "thermal", "leak", "pressure", "contain.", "struct.", "unknown"]
    rows = ["healthy", "1 sensor", "2 thermal", "3 leak", "4 pressure", "5 contain.", "6 struct.", "composite"]
    out += ["", "Confusion matrix at the first alert decision (rows true, columns decided):", "", "| true \\ decided | " + " | ".join(labs) + " |", "|---|" + "---|" * 8]
    for i in range(1, 8):
        out.append(f"| {rows[i]} | " + " | ".join(str(cm[i, j]) for j in range(8)) + " |")
    comp_ok = comp_n = 0
    for n in names:
        e = D.entries[n]
        if e["fault_id"] < 0:
            d = first_alert_decision(D.runs[n], e)
            if d is not None:
                comp_n += 1
                comp_ok += int(d["cls"] in e["unknown_sub_faults"])
    n_fault_classed = int(cm[1:7].sum())
    out += ["", f"Overall accuracy over known-class episodes alerted: {int(sum(cm[i, i] for i in range(1, 7)))}/{n_fault_classed}. Open-set: composites answered 'unknown pattern': {cm[7, 7]}/{int(cm[7].sum())}. Composites whose decided class is one of their two real components: {comp_ok}/{comp_n} (partial credit; the agent has no novelty detector: an isolation forest on the tool features separated composites from single faults at AUC 0.58, i.e. almost chance, so T8 was not built).", ""]
    # ---- leaks and containment: what the agent knows in the first minutes after its first alert
    out += ["## 4b. Leaks and containment: class, size and advice in the first half hour after the first alert", "",
            "The static alarms (gas detector) fire within about a minute of a large leak, so the agent cannot be earlier; the target is a correct class, a leak-size estimate and isolation advice in the same minutes. "
            "Decisions are made at the trigger tick and re-made at +10 and +30 min. True rate = the twin's leak mass flow at that moment (evaluation only).", "",
            "| group | n alerted | correct class at first alert | correct class at +30 min | median est/true rate at +30 min (n) | est within a factor 2 at +30 min | median time to a factor-2 estimate, min (n) | isolation advice by +30 min |", "|---|---|---|---|---|---|---|---|"]
    for g in ["3 leak 0.5mm", "3 leak 1mm", "5 containment_anomaly"]:
        el = groups[g]
        n_al = c0 = c30 = adv = f2 = 0
        ratios, tt = [], []
        for n in el:
            e, u, r = D.entries[n], D.units[n], D.runs[n]
            d0 = first_alert_decision(r, e)
            if d0 is None:
                continue
            n_al += 1
            c0 += int(d0["cls"] == e["fault_id"])
            later = [d for d in r["decisions"] if d0["t_s"] <= d["t_s"] <= d0["t_s"] + 30 * 60 + 1 and d["tier"] in ("alert", "critical")]
            d30 = later[-1]
            c30 += int(d30["cls"] == e["fault_id"])
            adv += int(any(d["cls"] in (5,) or d["tier"] == "critical" or (d["cls"] == 3 and d["tier"] in ("alert", "critical") and d["leak"] is not None and d["leak"]["leak_rate"]["value"] >= 5.0) for d in later))
            i30 = int(np.searchsorted(u.t, d30["t_s"]))
            true = float(u.truth["mdot_leak"][i30] * 3600.0)
            est = d30["leak"]["leak_rate"]["value"] if d30["leak"] else None
            if est is not None and true > 0:
                ratios.append(est / true)
                f2 += int(0.5 <= est / true <= 2.0)
            for d in r["decisions"]:
                if d["t_s"] < d0["t_s"] or not d["leak"]:
                    continue
                tr = float(u.truth["mdot_leak"][int(np.searchsorted(u.t, d["t_s"]))] * 3600.0)
                if tr > 0 and 0.5 <= d["leak"]["leak_rate"]["value"] / tr <= 2.0:
                    tt.append((d["t_s"] - d0["t_s"]) / 60.0)
                    break
        out.append(f"| {g} | {n_al} | {c0}/{n_al} | {c30}/{n_al} | {(f'{np.median(ratios):.2f}') if ratios else '-'} ({len(ratios)}) | {f2}/{n_al} | {(f'{np.median(tt):.0f}') if tt else 'never'} ({len(tt)}) | {adv}/{n_al} |")
    out.append("")
    # ---- agent effort
    first_calls, first_ms, watch_ms = [], [], []
    for n in names:
        for ev in D.runs[n]["events"]:
            if not ev["decisions"]:
                continue
            d0 = D.runs[n]["decisions"][ev["decisions"][0]]
            (first_calls if True else None).append(d0["n_calls"])
            first_ms.append(d0["runtime_ms"])
    out += ["## 5. Investigation effort", "", f"Per investigated event (first decision): mean {np.mean(first_calls):.1f} tool calls (max {max(first_calls)}), mean tool runtime {np.mean(first_ms):.0f} ms (95th percentile {np.percentile(first_ms, 95):.0f} ms, max {max(first_ms):.0f} ms), over {len(first_calls)} events.",
            "Tool runtime is the compute time of the tools; the always-on monitor series are vectorised and cost ~2 s per 14-day unit in total.", ""]
    # ---- forecast scoring
    fc_leak, fc_pres = [], []
    for n in names:
        e = D.entries[n]
        if e["fault_id"] not in (3, 5):
            continue
        d = first_alert_decision(D.runs[n], e) if e["fault_id"] > 0 else None
        if d is None or d["forecast"] is None or "released_in_6h" not in d["forecast"]:
            continue
        u = D.units[n]
        act = D.released_between(n, d["t_s"], min(d["t_s"] + 6 * H, u.t[-1]))
        f = d["forecast"]["released_in_6h"]
        if u.t[-1] - d["t_s"] >= 6 * H - 120:
            fc_leak.append((f["value"], f["lo"], f["hi"], act))
    out += ["## 6. Forecast error", "", "Leak cases: kg released in the 6 h after the first alert, forecast (unchecked, no refill, isothermal pressure decay) vs the twin's actual leaked mass. The forecast ignores compressor refills that keep the pressure (and the leak rate) higher, so it is a lower bound when the vessel is topped up.", ""]
    if fc_leak:
        a_ = np.array(fc_leak)
        ratio = a_[:, 0] / np.maximum(a_[:, 3], 1e-6)
        cov = np.mean((a_[:, 3] >= a_[:, 1]) & (a_[:, 3] <= a_[:, 2]))
        out += [f"n = {len(a_)}; median forecast/actual = {np.median(ratio):.2f} (IQR {np.percentile(ratio, 25):.2f}-{np.percentile(ratio, 75):.2f}); median absolute error {np.median(np.abs(a_[:, 0] - a_[:, 3])):.2f} kg; actual inside the forecast interval in {100 * cov:.0f} % of cases.", ""]
    else:
        out += ["No scorable leak forecasts.", ""]
    # time to PAH forecasts for pressure faults
    ttl_rows = []
    for n in names:
        e = D.entries[n]
        if e["fault_id"] != 4:
            continue
        for d in D.runs[n]["decisions"]:
            if d["t_s"] >= e["onset_s"] and d["forecast"] and "time_to_PAH" in d["forecast"]:
                u = D.units[n]
                P = u.truth["pressure"]
                i0 = int(np.searchsorted(u.t, d["t_s"]))
                cross = np.flatnonzero(P[i0:] >= u.cls["pah_bar"])
                if len(cross) and P[min(i0, len(P) - 1)] < u.cls["pah_bar"]:
                    act = (cross[0]) * 60.0 / H
                    f = d["forecast"]["time_to_PAH"]
                    ttl_rows.append((f["value"], f["lo"], f["hi"], act))
                break
    out += ["Pressure-rise cases: time to PAH forecast at the first alert-time forecast vs the time the true pressure actually crossed PAH:", ""]
    if ttl_rows:
        a_ = np.array(ttl_rows)
        out += [f"n = {len(a_)}; median absolute error {np.median(np.abs(a_[:, 0] - a_[:, 3])):.2f} h; median forecast {np.median(a_[:, 0]):.2f} h vs actual {np.median(a_[:, 3]):.2f} h; actual inside interval {100 * np.mean((a_[:, 3] >= a_[:, 1]) & (a_[:, 3] <= a_[:, 2])):.0f} %.", ""]
    else:
        out += ["No scorable time-to-PAH forecasts (pressure faults whose true pressure crossed PAH after a forecast).", ""]
    # ---- sensor subtypes
    sens = [n for n in names if D.entries[n]["family"] == "sensor"]
    out += ["## 7. Sensor faults by subtype", "", f"The dataset's sensor-fault episodes are all spike faults on the gas-temperature probe ({len(sens)} dev episodes). **Episodes of subtle slow drift (0.5-2 % FS over days): 0.** The T5 drift estimator is therefore not evaluated; stopping here as instructed (no regeneration without approval).", ""]
    text = "\n".join(out)
    (ROOT / "output" / "reports" / f"{a.out}.md").write_text(text + "\n")
    with open(ROOT / "output" / "reports" / f"{a.out}.json", "w") as f:
        json.dump({"false_alarms": {k: {kk: (vv if not isinstance(vv, np.floating) else float(vv)) for kk, vv in v.items()} for k, v in fa_res.items()}, "groups": results,
                   "confusion_rows_true_1to6_composite_cols_0to6_unknown": cm.tolist()}, f, indent=1, default=float)
    print(text)


def ablation(a):
    tags = a.ablation.split(",")
    out = ["# HYDRAI tool agent: ablations (dev, leave-one-module-out)", "",
           "Each row removes a tool (or a group) from the agent. 'Investigation-only' removals change what the orchestrator may call and the evidence it uses; removals that also remove the tool's monitor features retrain the fusion model without them (tag shows which).", "",
           "| variant | healthy false alarms / week (alert) | detected within 24 h (all classes 1-6 standard) | by class (k/n) 1 / 2 / 3 / 4 / 5 / 6 | correct class at first alert | calls per event |", "|---|---|---|---|---|---|"]
    for tag in tags:
        D = Data(load_runs(tag))
        S = score_all(D, ["agent_alert"])["agent_alert"]
        sm = summarize(list(S.values()))
        names = [n for n in D.units if D.entries[n]["fault_id"] > 0 and D.entries[n]["scenario_class"] == "standard"]
        k24 = lambda n: S[n].first_alarm_s is not None and S[n].delay_vs_onset_s <= 24 * H
        per = [f"{sum(k24(n) for n in names if D.entries[n]['fault_id'] == c)}/{sum(1 for n in names if D.entries[n]['fault_id'] == c)}" for c in range(1, 7)]
        ok = tot = 0
        for n in names:
            d = first_alert_decision(D.runs[n], D.entries[n])
            if d is not None:
                tot += 1
                ok += int(d["cls"] == D.entries[n]["fault_id"])
        calls = [D.runs[n]["decisions"][ev["decisions"][0]]["n_calls"] for n in D.units for ev in D.runs[n]["events"] if ev["decisions"]]
        out.append(f"| {tag} | {sm['false_alarms']['per_week']:.2f} | {sum(k24(n) for n in names)}/{len(names)} | {' / '.join(per)} | {ok}/{tot} | {np.mean(calls):.1f} |")
    text = "\n".join(out)
    (ROOT / "output" / "reports" / f"{a.out}.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
