"""cgh2_agent_vs_static.md: the frozen agent against the static alarms (A and B) and against the MODELLED operator, per fault class and severity, on dev, unseen, OOD low / high and the
slow-drift set. Same episodes and rules as the existing reports; nothing is tuned here (the operator thresholds were set once on healthy dev data).

    python scripts/cgh2_agent_vs_static.py

Definitions
  * detected = the detector's first alarm event at or after the onset, within DET_WINDOW_H (72 h) of it. A window is needed because every detector with healthy false alarms (static B, the operator,
    the agent) would otherwise 'detect' almost anything in a 14-day episode by chance (see the drift report's chance column).
  * both / agent only / other only / neither: counts of episodes by who detected it within the window; lead = (other's first alarm) - (agent's first alarm) in hours where both fired,
    positive = the agent was earlier; 95 % bootstrap interval over those episodes.
  * kg released before detection: the twin's leaked + vented mass between onset and the first alarm (evaluation only), agent vs static A where both fired.
  * cost: healthy false alarms per week on the same healthy exposure (normal episodes in full + the pre-onset part of every fault episode).
  * floor: the ideal-observer first-observable time after onset (median over episodes that have one).
  * static A = the reference DCS alarms; static B = A plus the PROPOSED low-pressure alarm at 70 % MOP (register open decision).
  * operator proxy = a MODELLED operator, not a human study (hydrai_twin/cgh2_agent/operator_proxy.py): looks at the raw dashboard every 15 (or 60) minutes; acts when the raw pressure is below the
    compressor's working band by more than X or the gas temperature is more than Y above ambient; 'expert' reads the temperature-compensated inventory instead of the raw pressure.
"""

from __future__ import annotations

import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent import operator_proxy as OP
from hydrai_twin.cgh2_agent.session import get_units
from ml.headline_metrics import score_episode, summarize

H = 3600.0
DET_WINDOW_H = 72.0
PAL = 0.70
rng = np.random.default_rng(3)
SETS = [("dev", "output/cgh2/medium", "dev", "runs_full.pkl"), ("unseen", "output/cgh2/medium", "unseen", "final_unseen.pkl"), ("OOD low", "output/cgh2/low", "ood", "final_low.pkl"),
        ("OOD high", "output/cgh2/high", "ood", "final_high.pkl"),
        ("OOD low, per-class recalibrated on healthy low-class data (cross-fitted by module; the agent column only, extra rows beside the frozen OOD low numbers)", "output/cgh2/low", "ood", "final_low_recal.pkl"),
        ("OOD high, per-class recalibrated on healthy high-class data (cross-fitted by module; the agent column only, extra rows beside the frozen OOD high numbers)", "output/cgh2/high", "ood", "final_high_recal.pkl"),
        ("slow drift (new)", "output/cgh2_drift/medium", "drift", "final_drift.pkl")]
CLS = {1: "1 sensor fault", 2: "2 thermal anomaly", 3: "3 small leak", 4: "4 abnormal pressure", 5: "5 containment", 6: "6 structural", -1: "-1 composite (two faults)"}


def groups_of(e: dict) -> list[str]:
    tag, fid = e["variant_tag"], e["fault_id"]
    g = []
    if e["family"] == "drift":
        sens = "pressure transmitter" if "pressure" in tag else "gas-temperature probe"
        pct = float(re.search(r"[pm]([\d.]+)$", tag).group(1))
        return [f"1d slow drift (all)", f"1d drift: {sens}", f"1d drift {pct:g} % FS"]
    if fid == 1:
        return ["1 sensor fault: spikes on the gas-temperature probe"]
    if fid == 2:
        return ["2 thermal anomaly (all)", "2 thermal: " + ("intercooler failure" if "intercooler" in tag else "external heat")]
    if fid == 3:
        mm = re.search(r"([\d.]+)mm", tag).group(1)
        return [f"3 leak {mm} mm" + (" (stress, expected miss)" if e["expected_miss"] else ""), "3 leaks 0.1-1 mm (all)"] if not e["expected_miss"] else [f"3s stress leak {mm} mm (expected miss)"]
    if fid == 4:
        return ["4 abnormal pressure (all)", "4 pressure: " + tag.split("-", 1)[1]]
    if fid == 5:
        if e["family"] == "rupture":
            return ["5r rupture 50 mm"]
        mm = re.search(r"([0-9.]+)mm", tag).group(1)
        return ["5 containment (all)", f"5 containment {mm} mm"]
    if fid == 6:
        return ["6 structural (all)", "6 structural severity " + tag.split("sev")[1]]
    return [CLS.get(fid, str(fid))]


def boot(x, n=1000):
    a = np.array(x, dtype=float)
    if len(a) < 3:
        return None
    bs = [np.median(rng.choice(a, len(a))) for _ in range(n)]
    return float(np.median(a)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def fmt_lead(x):
    if not len(x):
        return "-"
    c = boot(x)
    return f"{np.median(x):+.1f} (n={len(x)})" if c is None else f"{c[0]:+.1f} ({c[1]:+.1f} to {c[2]:+.1f}; n={len(x)})"


class SetData:
    def __init__(self, label, dataset, role, runs_file):
        self.label = label
        _, units = get_units(dataset, (role, "commissioning"))
        self.units = {k: u for k, u in units.items() if u.entry["role"] == role}
        self.runs = pickle.load(open(F.CACHE / runs_file, "rb"))
        thr = OP.thresholds_cached()
        self.thr = thr
        self.cum = {k: np.concatenate([[0.0], np.cumsum((np.nan_to_num(u.truth["mdot_leak"]) + np.nan_to_num(u.truth["mdot_prv"])) * 60.0)]) for k, u in self.units.items()}

    def released(self, n, t0, t1):
        u = self.units[n]
        c = self.cum[n]
        return float(c[min(int(np.searchsorted(u.t, t1)), len(c) - 1)] - c[min(int(np.searchsorted(u.t, t0)), len(c) - 1)])

    def flags(self, det, n):
        u = self.units[n]
        if det == "A":
            return u.static
        if det == "B":
            return u.static | ((u.raw.x["P"] < PAL * u.cls["mop_bar"]) & (u.t > 86400.0))
        if det == "agent":
            f = np.zeros(u.n, dtype=bool)
            for ev in self.runs[n]["events"]:
                if ev["t_alert_s"] is not None:
                    f[min(int(np.searchsorted(u.t, ev["t_alert_s"])), u.n - 1)] = True
            return f
        if det == "agent_watch":
            f = np.zeros(u.n, dtype=bool)
            for ev in self.runs[n]["events"]:
                f[min(int(np.searchsorted(u.t, ev["t_watch_s"])), u.n - 1)] = True
            return f
        per = 15 if det in ("op15", "opx") else 60
        return OP.flags(u, self.thr[per], per, expert=(det == "opx"))

    def score(self):
        dets = ["A", "B", "agent", "agent_watch", "op15", "op60", "opx"]
        self.S = {d: {n: score_episode(u.entry, u.t, self.flags(d, n), u.static, d, data_fault_flags=u.truth["has_data_fault"]) for n, u in self.units.items()} for d in dets}
        self.FA = {d: summarize(list(self.S[d].values()))["false_alarms"] for d in dets}

    def t_det(self, d, n, window_h=DET_WINDOW_H):
        s = self.S[d][n]
        return s.first_alarm_s if (s.first_alarm_s is not None and s.delay_vs_onset_s <= window_h * H) else None


def section(D: SetData) -> list[str]:
    faults = {n: u.entry for n, u in D.units.items() if u.entry["fault_id"] != 0 and u.entry["scenario_class"] == "standard"}
    groups = defaultdict(list)
    for n, e in faults.items():
        for g in groups_of(e):
            groups[g].append(n)
    order = sorted(groups, key=lambda g: (g.split()[0].lstrip("-").rjust(4, "0") if g[0] != "-" else "9999", g))
    out = [f"## {D.label}", ""]
    fa = D.FA
    out += ["Healthy false alarms per week (cost): " + ", ".join(f"{lab} {fa[d]['per_week']:.2f}" for d, lab in (("A", "static A"), ("B", "static B"), ("agent", "agent alert tier"), ("agent_watch", "agent watch tier"),
                                                                                                         ("op15", "operator 15 min"), ("op60", "operator 60 min"), ("opx", "expert operator 15 min"))) +
            f" (healthy exposure {fa['A']['healthy_exposure_weeks']:.1f} weeks).", ""]
    # ---------------- table 1: static
    out += ["### Agent vs the static alarms", "",
            f"Detected = first alarm within {DET_WINDOW_H:.0f} h of onset. Lead in hours, positive = the agent earlier, where both fired. kg = released before detection, agent vs static A where both fired (median).", "",
            "| group | n | floor h | detected: A | B | agent | vs A: both / agent only / A only / neither | lead over A, h (95 % CI) | lead over B, h | kg before detection: agent vs A | union A or agent: 24 h | 72 h | union B or agent: 24 h | 72 h |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in order:
        el = groups[g]
        fl = [faults[n]["first_observable_s"] - faults[n]["onset_s"] for n in el if faults[n]["first_observable_s"] is not None]
        td = {d: {n: D.t_det(d, n) for n in el} for d in ("A", "B", "agent")}
        cnt = lambda d: sum(td[d][n] is not None for n in el)
        both = [n for n in el if td["A"][n] is not None and td["agent"][n] is not None]
        ag_only = sum(td["agent"][n] is not None and td["A"][n] is None for n in el)
        a_only = sum(td["A"][n] is not None and td["agent"][n] is None for n in el)
        neither = sum(td["A"][n] is None and td["agent"][n] is None for n in el)
        leadA = [(td["A"][n] - td["agent"][n]) / H for n in both]
        bothB = [n for n in el if td["B"][n] is not None and td["agent"][n] is not None]
        leadB = [(td["B"][n] - td["agent"][n]) / H for n in bothB]
        kg_ag = [D.released(n, faults[n]["onset_s"], td["agent"][n]) for n in both]
        kg_a = [D.released(n, faults[n]["onset_s"], td["A"][n]) for n in both]
        u24 = lambda s2: sum((D.t_det(s2, n, 24) is not None) or (D.t_det("agent", n, 24) is not None) for n in el)
        u72 = lambda s2: sum((td[s2][n] is not None) or (td["agent"][n] is not None) for n in el)
        out.append(f"| {g} | {len(el)} | {('%.1f' % (np.median(fl) / H)) if fl else '-'} | {cnt('A')} | {cnt('B')} | {cnt('agent')} | {len(both)} / {ag_only} / {a_only} / {neither} | {fmt_lead(leadA)} | {fmt_lead(leadB)} | "
                   f"{(f'{np.median(kg_ag):.2f} vs {np.median(kg_a):.2f}') if both else '-'} | {u24('A')}/{len(el)} | {u72('A')}/{len(el)} | {u24('B')}/{len(el)} | {u72('B')}/{len(el)} |")
    # ---------------- table 2: operator
    out += ["", "### Agent vs the modelled operator (not a human study)", "",
            "Operator: looks every 15 min (op15) or 60 min (op60), raw pressure below the working band by more than X or gas temperature more than Y above ambient (thresholds set once on healthy dev data at 1 false alarm per week per rule); "
            "'expert' reads the temperature-compensated inventory instead of the raw pressure. Lead = operator's first alarm - agent's first alarm.", "",
            "| group | n | detected: op15 | op60 | expert | agent | vs op15: both / agent only / op only / neither | lead over op15, h (95 % CI) | lead over op60, h | lead over expert, h | kg before detection: agent vs op15 | union op15 or agent: 24 h | 72 h |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in order:
        el = groups[g]
        td = {d: {n: D.t_det(d, n) for n in el} for d in ("op15", "op60", "opx", "agent")}
        cnt = lambda d: sum(td[d][n] is not None for n in el)
        bothf = lambda d: [n for n in el if td[d][n] is not None and td["agent"][n] is not None]
        lead = lambda d: [(td[d][n] - td["agent"][n]) / H for n in bothf(d)]
        b = bothf("op15")
        ag_only = sum(td["agent"][n] is not None and td["op15"][n] is None for n in el)
        o_only = sum(td["op15"][n] is not None and td["agent"][n] is None for n in el)
        neither = sum(td["op15"][n] is None and td["agent"][n] is None for n in el)
        kg_ag = [D.released(n, faults[n]["onset_s"], td["agent"][n]) for n in b]
        kg_o = [D.released(n, faults[n]["onset_s"], td["op15"][n]) for n in b]
        u24 = sum((D.t_det("op15", n, 24) is not None) or (D.t_det("agent", n, 24) is not None) for n in el)
        u72 = sum((td["op15"][n] is not None) or (td["agent"][n] is not None) for n in el)
        out.append(f"| {g} | {len(el)} | {cnt('op15')} | {cnt('op60')} | {cnt('opx')} | {cnt('agent')} | {len(b)} / {ag_only} / {o_only} / {neither} | {fmt_lead(lead('op15'))} | {fmt_lead(lead('op60'))} | {fmt_lead(lead('opx'))} | "
                   f"{(f'{np.median(kg_ag):.2f} vs {np.median(kg_o):.2f}') if b else '-'} | {u24}/{len(el)} | {u72}/{len(el)} |")
    out.append("")
    return out


if __name__ == "__main__":
    thr = OP.thresholds_cached()
    head = ["# Agent versus the static alarms and a modelled operator", "",
            "Reference configuration, not a verified Saudi system. The agent is the FROZEN configuration (dev: leave-one-module-out; unseen, OOD low / high and the slow-drift set: scored once, fitted on all dev). "
            f"Detection counts alarms within {DET_WINDOW_H:.0f} h of onset. 'Operator' is a MODELLED operator, not a human study; its thresholds were set once on healthy dev data at 1 false alarm per week per rule and never touched again: "
            + "; ".join(f"look every {p} min: pressure-low {thr[p]['pressure']:.3f} of MOP below the compressor start level, temperature {thr[p]['temperature']:.1f} K above ambient, compensated inventory {thr[p]['inventory']:.3f} of the class inventory below its start level" for p in OP.PERIODS) + ". "
            "The low-pressure rule lands near 70 % of MOP, i.e. close to the proposed low-pressure alarm of static B. Static B = A plus the proposed 70 % MOP low-pressure alarm. "
            "Read the false-alarm line of every section next to its lead times: an earlier alarm that costs more false alarms is not a free win.", ""]
    out = list(head)
    for label, dataset, role, rf in SETS:
        D = SetData(label, dataset, role, rf)
        D.score()
        sec = section(D)
        if label.startswith("slow drift"):
            sec.insert(2, "**Read with the chance column of `cgh2_agent_drift.md`:** an unrelated alarm falls in a 72 h window after a pseudo-onset on a HEALTHY episode about 41 % of the time for static B, 28 % for the agent, 66 % for the 15-minute operator "
                          "and 0 % for static A. So the operator's and static B's 72 h detections below are about what their false-alarm rates alone would produce; only static A's zero and the agent's naming of the sensor (2 of 12, `cgh2_agent_drift.md`) are not chance. "
                          "Many of those alarms come before the drift is observable at all (before the ideal-observer floor).\n")
        out += sec
        print(label, "done", flush=True)
    (ROOT / "output" / "reports" / "cgh2_agent_vs_static.md").write_text("\n".join(out) + "\n")
    print("written")
