"""Per-class recalibration for the OOD classes (low, high): the agent's watch / alert thresholds re-fitted on HEALTHY data of that class only, shown as separate rows beside the frozen OOD numbers
(the frozen numbers are unchanged). Cross-fitted by module (the thresholds applied to a module come from the healthy episodes of the other two modules and the commissioning runs), so the
healthy false-alarm rate is not measured on the data that set the threshold. Everything else (tool fit, fusion model) stays the frozen all-dev one. Fault episodes are never used.

    python scripts/cgh2_ood_recalibrate.py            # writes final_low_recal.pkl / final_high_recal.pkl (read by cgh2_agent_vs_static.py)
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.agent import Orchestrator
from hydrai_twin.cgh2_agent.features import feature_matrix
from hydrai_twin.cgh2_agent.session import get_units, slim_decision
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools
from ml.cgh2_baselines import fit_threshold_bounded

SETS = {"low": "output/cgh2/low", "high": "output/cgh2/high"}
WEEK = 7 * 86400.0


def run_set(key: str):
    load_all_tools()
    _, units = get_units(SETS[key], ("ood", "commissioning"))
    fit = pickle.load(open(F.CACHE / "fit_final.pkl", "rb"))["fit"]
    meta = pickle.load(open(F.CACHE / "meta_final.pkl", "rb"))
    base = {u.entry["module_id"]: {"L_off": float(np.median(Ctx(u, fit).monitor("T2_inventory_leak")["L_kgh"][1440:]))} for u in units.values() if u.entry["role"] == "commissioning"}
    probs, fus = {}, {}                                          # computed on the fly with the frozen model (episode names repeat across the low / high sets, so no name-keyed cache)
    for n, u in units.items():
        fus[n] = F.FUnit(u.entry, u.t, feature_matrix(Ctx(u, fit, base[u.entry["module_id"]])))
        probs[n] = F.probs(meta["model"], fus[n])
    healthy = lambda u: u.entry["fault_id"] == 0 and u.entry["scenario_class"] == "standard" and "dark" not in u.entry["variant_tag"]
    mods = sorted({u.entry["module_id"] for u in units.values()})
    out, thr_used = {}, {}
    for m in mods:
        cal = []
        for n, u in units.items():
            if u.entry["module_id"] == m or not healthy(u):
                continue
            P = probs[n]
            cal.append((u.t[F.WARMUP:], (1 - P[:, 0])[F.WARMUP:]))
        weeks = sum(t[-1] - t[0] for t, _ in cal) / WEEK
        thr = {k: fit_threshold_bounded(cal, rate * weeks) for k, rate in F.BUDGETS.items()}
        thr_used[m] = thr
        for n, u in units.items():
            if u.entry["module_id"] != m or u.entry["role"] != "ood":
                continue
            ctx = Ctx(u, fit, base[m])
            r = Orchestrator(thr).run(ctx, probs[n], P_fast=F.raw_probs(meta["model"], fus[n]))
            out[n] = {"events": r["events"], "decisions": [slim_decision(d) for d in r["decisions"]], "first_traces": {}}
    pickle.dump(out, open(F.CACHE / f"final_{key}_recal.pkl", "wb"))
    print(key, len(out), "units; thresholds per module:", {m: {k: round(v, 3) for k, v in t.items()} for m, t in thr_used.items()})


if __name__ == "__main__":
    for k in SETS:
        run_set(k)
