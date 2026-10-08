"""Score the FROZEN agent, the static alarms, the classical baselines and the single learned model ONCE on the slow-drift episodes (output/cgh2_drift/medium).

    python scripts/cgh2_drift_run.py [--force]       # refuses to run twice unless --force; writes final_drift.pkl / final_drift_baselines.pkl and output/reports/cgh2_agent_drift.md

The tool fit and the fusion model are the frozen all-dev ones (fit_final.pkl, meta_final.pkl): nothing is fitted or tuned on these episodes. The freeze manifest is verified first;
the only file allowed to differ is hydrai_twin/cgh2/episode.py, which gained the drift option (off by default, existing episodes hash-identical).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.agent import Orchestrator
from hydrai_twin.cgh2_agent.features import feature_matrix
from hydrai_twin.cgh2_agent.session import get_units, slim_decision
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools

DATASET, ROLE = "output/cgh2_drift/medium", "drift"
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")
# behaviour-neutral or presentation-only: the generator gained the drift option (off by default, existing episodes hash-identical); the operator proxy and the replay viewer are new /
# presentation code that no agent decision reads
ALLOWED_DIFF = {"hydrai_twin/cgh2/episode.py", "hydrai_twin/cgh2_agent/operator_proxy.py", "hydrai_twin/cgh2_agent/replay.py"}


def verify_freeze() -> None:
    spec = importlib.util.spec_from_file_location("freeze", ROOT / "scripts" / "cgh2_agent_freeze.py")
    fz = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fz)
    bad = [b for b in fz.verify() if not any(a in b for a in ALLOWED_DIFF)]
    if bad:
        sys.exit("frozen configuration changed:\n  " + "\n  ".join(bad))


def agent_chunk(args):
    k, n = args
    load_all_tools()
    _, units = get_units(DATASET, (ROLE, "commissioning"))
    fit = pickle.load(open(F.CACHE / "fit_final.pkl", "rb"))["fit"]
    meta = pickle.load(open(F.CACHE / "meta_final.pkl", "rb"))
    base = {u.entry["module_id"]: {"L_off": float(np.median(Ctx(u, fit).monitor("T2_inventory_leak")["L_kgh"][1440:]))} for u in units.values() if u.entry["role"] == "commissioning"}
    out = {}
    names = [nm for nm, u in units.items() if u.entry["role"] == ROLE]
    (F.CACHE / "final").mkdir(exist_ok=True)
    for nm in names[k::n]:
        u = units[nm]
        ctx = Ctx(u, fit, base[u.entry["module_id"]])
        fu = F.FUnit(u.entry, u.t, feature_matrix(ctx))
        P = F.probs(meta["model"], fu)
        np.save(F.CACHE / "final" / f"probs_{nm}.npy", P)
        r = Orchestrator(meta["thr"]).run(ctx, P, P_fast=F.raw_probs(meta["model"], fu))
        out[nm] = {"events": r["events"], "decisions": [slim_decision(d) for d in r["decisions"]], "first_traces": {ev["event"]: r["decisions"][ev["decisions"][0]].to_json() for ev in r["events"][:2]}}
    return out


def baselines():
    from hydrai_twin.cgh2.dashboard import CGH2Dashboard
    from hydrai_twin.physical_dataset import static_flags_from_parquet
    from ml import cgh2_agent as AG
    from ml import cgh2_baselines as BL
    from ml.cgh2_features import build, load_raw
    BUDGETS = {"1/wk": 1.0}
    root, dev_root = ROOT / DATASET, ROOT / "output/cgh2/medium"
    m, dm = json.loads((root / "manifest.json").read_text()), json.loads((dev_root / "manifest.json").read_text())
    dash = CGH2Dashboard.from_dict(dm["dashboard"])
    cls_dev, cls = dm["class_parameters"], m["class_parameters"]
    bl, eps = {}, {}
    for e in dm["episodes"]:
        if e["role"] in ("dev", "commissioning"):
            _, sf = static_flags_from_parquet(dev_root / e["slow_file"], dash)
            b = BL.load_episode(dev_root, e, cls_dev["volume_m3"]); b.static_flags = np.array(sf, dtype=bool); bl[e["name"]] = b
            raw = load_raw(dev_root, e, cls_dev); _, X = build(raw)
            eps[e["name"]] = AG.Ep(e, raw.t, X, np.array(sf, dtype=bool), raw.has_data_fault)
    comm_bl = {b.entry["module_id"]: b for b in bl.values() if b.entry["role"] == "commissioning"}
    healthy = [b for b in bl.values() if b.entry["module_id"] in MODULES and b.entry["fault_id"] == 0 and b.entry["scenario_class"] == "standard" and b.entry["role"] in ("dev", "commissioning") and "dark" not in b.entry["variant_tag"]]
    model_bl = BL.train(healthy, comm_bl, BUDGETS["1/wk"])
    pool = [e for e in eps.values() if e.entry["role"] in ("dev", "commissioning")]
    thr = AG.thresholds(AG.oof_healthy_scores(pool, list(MODULES)), BUDGETS)
    learned = AG.fit(pool)
    flags = {}
    for e in m["episodes"]:
        if e["role"] == ROLE:
            _, sf = static_flags_from_parquet(root / e["slow_file"], dash)
            b = BL.load_episode(root, e, cls["volume_m3"]); b.static_flags = np.array(sf, dtype=bool)
            comm = [c for c in m["episodes"] if c["role"] == "commissioning" and c["module_id"] == e["module_id"]][0]
            for det, f in BL.detect(model_bl, b, BL.load_episode(root, comm, cls["volume_m3"])).items():
                flags.setdefault(("1/wk", det), {})[e["name"]] = f
            raw = load_raw(root, e, cls); _, X = build(raw)
            flags.setdefault(("1/wk", "learned"), {})[e["name"]] = AG.alarm_flags(AG.score(learned, AG.Ep(e, raw.t, X, np.array(sf, dtype=bool), raw.has_data_fault)), thr["1/wk"])
    return flags


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = F.CACHE / "final_drift.pkl"
    if out.exists() and not a.force:
        sys.exit("the drift set was already scored once (use --force only to reproduce, never to re-tune)")
    verify_freeze()
    get_units(DATASET, (ROLE, "commissioning"))                       # fast-layer cache, one pool, here
    res = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for o in ex.map(agent_chunk, [(k, 6) for k in range(6)]):
            res.update(o)
    pickle.dump(res, open(out, "wb"))
    pickle.dump(baselines(), open(F.CACHE / "final_drift_baselines.pkl", "wb"))
    print("drift set scored:", len(res), "episodes")
