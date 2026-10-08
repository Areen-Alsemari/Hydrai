"""Paired lead times for the 'earlier' claims: for each class, episodes where BOTH detectors fire within the episode, median lead = (other detector's first alarm) -
(agent's first alarm), hours, positive = the agent was earlier, with a 95 % bootstrap interval over episodes, the episode counts (both fired / agent only / other only),
the detectors' healthy false alarms per week (the cost of the lead) and the physical floor. Against the static alarms (A), the best classical baseline per class
(highest 24 h detection, then lowest median delay), and the single learned model. Reads the same caches as cgh2_agent_eval.py; new file, does not alter any frozen file.

    python scripts/cgh2_agent_lead_times.py --set dev|unseen|low|high
"""

import argparse
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ev", ROOT / "scripts" / "cgh2_agent_eval.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
import pickle

from hydrai_twin.cgh2_agent import fusion as F
from ml.headline_metrics import summarize

H = 3600.0
rng = np.random.default_rng(1)


def boot_med(x, n=1000):
    a = np.array(x)
    bs = [np.median(rng.choice(a, len(a))) for _ in range(n)]
    return float(np.median(a)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="dev", choices=["dev", "unseen", "low", "high"])
    a = ap.parse_args()
    if a.set == "dev":
        D = ev.Data(ev.load_runs("full"))
    else:
        D = ev.Data(pickle.load(open(F.CACHE / f"final_{a.set}.pkl", "rb")), a.set)
    dets = ["static_A", "roc", "ewma", "cusum", "inv", "learned", "agent_alert"]
    S = ev.score_all(D, dets)
    fa = {d: summarize(list(S[d].values()))["false_alarms"]["per_week"] for d in dets}
    groups = defaultdict(list)
    for n, u in D.units.items():
        e = u.entry
        if e["fault_id"] != 0 and e["scenario_class"] == "standard":
            for g in ev.group_of(e):
                groups[g].append(n)
    out = [f"# Paired lead times of the tool agent ({a.set}): when is it EARLIER, at what false-alarm cost", "",
           "Lead = other detector's first alarm - the agent's first alarm (hours); positive = the agent warned earlier. Only episodes where both fired count in the median; the counts of agent-only / other-only / "
           "neither show what a median would hide. Intervals: 95 % bootstrap over episodes. The cost is each detector's realized healthy false alarms per week on the same exposure: "
           + ", ".join(f"{d} {fa[d]:.2f}" for d in dets) + ". 'Floor' = median first-observable time after onset (ideal-observer bound).", ""]
    classical = ("roc", "ewma", "cusum", "inv")
    for g in sorted(groups, key=lambda g: (g.split()[0].lstrip("-").rjust(3, "0") if g[0] != "-" else "999", g)):
        el = groups[g]
        floor = [D.entries[n]["first_observable_s"] - D.entries[n]["onset_s"] for n in el if D.entries[n]["first_observable_s"] is not None]
        best = min(classical, key=lambda d: (-sum(S[d][n].first_alarm_s is not None and S[d][n].delay_vs_onset_s <= 24 * H for n in el), np.median([S[d][n].delay_vs_onset_s for n in el if S[d][n].first_alarm_s is not None] or [9e9])))
        out += [f"### {g} (n = {len(el)}, floor {np.median(floor) / H:.1f} h)" if floor else f"### {g} (n = {len(el)})", "",
                "| agent vs | both fired | agent only | other only | neither | median lead h (95 % CI) |", "|---|---|---|---|---|---|"]
        for other, label in (("static_A", "static A"), (best, f"best classical ({best})"), ("learned", "single learned model")):
            if other == "static_A" and g.startswith("6 "):
                continue
            both, ag, ot, ne, lead = 0, 0, 0, 0, []
            for n in el:
                x, y = S["agent_alert"][n].first_alarm_s, S[other][n].first_alarm_s
                if x is not None and y is not None:
                    both += 1
                    lead.append((y - x) / H)
                elif x is not None:
                    ag += 1
                elif y is not None:
                    ot += 1
                else:
                    ne += 1
            ci = boot_med(lead) if lead else None
            out.append(f"| {label} | {both} | {ag} | {ot} | {ne} | " + (f"{ci[0]:+.1f} ({ci[1]:+.1f} to {ci[2]:+.1f})" if ci else "-") + " |")
        out.append("")
    p = ROOT / "output" / "reports" / f"cgh2_agent_lead_times_{a.set}.md"
    p.write_text("\n".join(out) + "\n")
    print(p)
