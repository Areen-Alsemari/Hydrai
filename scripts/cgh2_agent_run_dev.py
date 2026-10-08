"""Run the orchestrator (policy mode) over every dev unit with leave-one-module-out parameters and cache slim per-unit results.

    python scripts/cgh2_agent_run_dev.py [--tag full] [--off T9_twin_verifier,T10_forecast_consequence] [--probs-tag ablT2]

`--off` removes tools from the investigation/decision (tools whose monitor series feed the fusion model also need `--meta-tag`, a fusion retrained without their features).
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.agent import Orchestrator
from hydrai_twin.cgh2_agent.session import AgentSession, get_units, slim_decision as slim
from hydrai_twin.cgh2_agent.tools import REGISTRY, load_all_tools

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")
ALL_TOOLS = None


def run_module(args):
    h, tag, off, meta_tag, use_static = args
    load_all_tools()
    enabled = set(REGISTRY) - set(off)
    _, units = get_units()
    out = {}
    t0 = time.time()
    for name, u in units.items():
        if u.entry["module_id"] != h or u.entry["role"] != "dev":
            continue
        s = AgentSession(name, enabled_tools=enabled, meta_tag=meta_tag or None, use_static=use_static)
        r = s.run()
        res = {"events": r["events"], "decisions": [slim(d) for d in r["decisions"]]}
        res["first_traces"] = {ev["event"]: r["decisions"][ev["decisions"][0]].to_json() for ev in r["events"][:2]}
        out[name] = res
    return h, out, time.time() - t0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="full")
    ap.add_argument("--off", default="")
    ap.add_argument("--meta-tag", default="", help="fusion variant trained by cgh2_agent_meta.py --tag")
    ap.add_argument("--no-static", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    off = [x for x in a.off.split(",") if x]
    allres = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for h, out, dt in ex.map(run_module, [(m, a.tag, off, a.meta_tag, not a.no_static) for m in MODULES]):
            allres.update(out)
            print(h, len(out), f"{dt:.0f} s", flush=True)
    with open(F.CACHE / f"runs_{a.tag}.pkl", "wb") as f:
        pickle.dump(allres, f)
    print("saved", F.CACHE / f"runs_{a.tag}.pkl", len(allres))
