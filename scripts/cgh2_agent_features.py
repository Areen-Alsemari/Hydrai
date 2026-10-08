"""Cross-fitted tool parameters and per-unit feature matrices for the agent (dev + commissioning).

For each dev module h: the tools are fitted on healthy standard units of the OTHER dev modules; the unit's per-module commissioning baseline (E2) comes from
the commissioning run of module h scored with that fit; features of every unit of module h are computed with that fit and cached. Held-out/unseen/OOD
units are handled by `--final` (fit on all dev modules). Run from this file (multiprocessing).
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2_agent.features import FEATURES, feature_matrix
from hydrai_twin.cgh2_agent.fit import fit_tools
from hydrai_twin.cgh2_agent.loader import load_all
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools

OUT = Path(__file__).resolve().parents[1] / "output" / "cgh2_cache" / "agent"
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")


def calibration_unit(u) -> bool:
    e = u.entry
    return e["fault_id"] == 0 and e["scenario_class"] == "standard" and "dark" not in e["variant_tag"]


def baseline_for(fit, comm_unit) -> dict:
    mm = Ctx(comm_unit, fit).monitor("T2_inventory_leak")
    return {"L_off": float(np.median(mm["L_kgh"][1440:]))}


def run_module(h: str) -> tuple[str, int, float]:
    t0 = time.time()
    load_all_tools()
    _, U = load_all()
    train = [u for u in U.values() if calibration_unit(u) and u.entry["module_id"] != h and u.entry["role"] == "dev"]
    fit = fit_tools(train)
    comm = [u for u in U.values() if u.entry["role"] == "commissioning" and u.entry["module_id"] == h][0]
    base = baseline_for(fit, comm)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"fit_{h}.pkl", "wb") as f:
        pickle.dump({"fit": fit, "baseline": base}, f)
    n = 0
    for name, u in U.items():
        if u.entry["module_id"] != h:
            continue
        X = feature_matrix(Ctx(u, fit, base))
        np.savez_compressed(OUT / f"feat_{name}.npz", X=X, t=u.t)
        n += 1
    return h, n, time.time() - t0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for h, n, dt in ex.map(run_module, MODULES):
            print(f"{h}: {n} units in {dt:.0f} s", flush=True)
    print("features:", len(FEATURES))
