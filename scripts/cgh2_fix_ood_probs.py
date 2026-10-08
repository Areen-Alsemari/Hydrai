"""Rewrite output/cgh2_cache/agent/final/probs_<name>.npy for ONE OOD set with the frozen model (the low and high sets share episode names; the first one-shot run left the high set's files under
both). Only the 'fusion only' row of the OOD reports reads these files.   python scripts/cgh2_fix_ood_probs.py low|high"""
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.features import feature_matrix
from hydrai_twin.cgh2_agent.session import get_units
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools

if __name__ == "__main__":
    key = sys.argv[1]
    load_all_tools()
    _, units = get_units({"low": "output/cgh2/low", "high": "output/cgh2/high"}[key], ("ood", "commissioning"))
    fit = pickle.load(open(F.CACHE / "fit_final.pkl", "rb"))["fit"]
    meta = pickle.load(open(F.CACHE / "meta_final.pkl", "rb"))
    base = {u.entry["module_id"]: {"L_off": float(np.median(Ctx(u, fit).monitor("T2_inventory_leak")["L_kgh"][1440:]))} for u in units.values() if u.entry["role"] == "commissioning"}
    for n, u in units.items():
        if u.entry["role"] == "ood":
            np.save(F.CACHE / "final" / f"probs_{n}.npy", F.probs(meta["model"], F.FUnit(u.entry, u.t, feature_matrix(Ctx(u, fit, base[u.entry["module_id"]])))))
    print(key, "probabilities rewritten")
