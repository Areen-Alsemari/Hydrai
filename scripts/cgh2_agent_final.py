"""ONE-SHOT final evaluation inputs: unseen modules (medium class) and the OOD classes (low, high). Run only after the dev configuration is frozen.

  stage models     fit the tools on ALL dev healthy units, train the fusion model on all dev rows (cross-fitted features), thresholds from out-of-fold healthy scores
  stage agent      per unit: features (tool fit + the unit's module commissioning baseline), fusion probabilities, orchestrator run  -> output/cgh2_cache/agent/final_<set>.pkl
  stage baselines  classical baselines and the single learned model (checkpoint 1), trained on all dev, applied to the same units -> final_<set>_baselines.pkl

Nothing here reads labels, onset times or healthy-twin data as features. The result files are scored by cgh2_agent_eval.py --final <set>.
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
from hydrai_twin.cgh2_agent.features import feature_matrix
from hydrai_twin.cgh2_agent.fit import fit_tools
from hydrai_twin.cgh2_agent.session import get_units, slim_decision
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")
SETS = {"unseen": ("output/cgh2/medium", "unseen"), "low": ("output/cgh2/low", "ood"), "high": ("output/cgh2/high", "ood")}


def stage_models():
    _, units = get_units("output/cgh2/medium", ("dev", "commissioning"))
    train = [u for u in units.values() if u.entry["role"] == "dev" and u.entry["fault_id"] == 0 and u.entry["scenario_class"] == "standard" and "dark" not in u.entry["variant_tag"]]
    fit = fit_tools(train)
    manifest = json.loads((ROOT / "output/cgh2/medium/manifest.json").read_text())
    funits = [F.load_funit(e) for e in manifest["episodes"] if e["role"] == "dev"]
    t0 = time.time()
    model = F.train_meta(funits)
    oof = F.oof_healthy(funits, list(MODULES))
    thr = F.thresholds_from(oof)
    with open(F.CACHE / "fit_final.pkl", "wb") as f:
        pickle.dump({"fit": fit}, f)
    with open(F.CACHE / "meta_final.pkl", "wb") as f:
        pickle.dump({"model": model, "thr": thr}, f)
    print("final thresholds", {k: round(v, 4) for k, v in thr.items()}, f"{time.time() - t0:.0f} s")


def agent_chunk(args):
    key, k, n = args
    dataset, role = SETS[key]
    load_all_tools()
    _, units = get_units(dataset, (role, "commissioning"))
    fit = pickle.load(open(F.CACHE / "fit_final.pkl", "rb"))["fit"]
    meta = pickle.load(open(F.CACHE / "meta_final.pkl", "rb"))
    comm = {u.entry["module_id"]: u for u in units.values() if u.entry["role"] == "commissioning"}
    base = {}
    for mod, cu in comm.items():
        base[mod] = {"L_off": float(np.median(Ctx(cu, fit).monitor("T2_inventory_leak")["L_kgh"][1440:]))}
    out = {}
    names = [nm for nm, u in units.items() if u.entry["role"] == role]
    (F.CACHE / "final").mkdir(exist_ok=True)
    for nm in names[k::n]:
        u = units[nm]
        ctx = Ctx(u, fit, base[u.entry["module_id"]])
        fu = F.FUnit(u.entry, u.t, feature_matrix(ctx))
        P = F.probs(meta["model"], fu)
        np.save(F.CACHE / "final" / f"probs_{nm}.npy", P)
        r = Orchestrator(meta["thr"]).run(ctx, P, P_fast=F.raw_probs(meta["model"], fu))
        res = {"events": r["events"], "decisions": [slim_decision(d) for d in r["decisions"]], "first_traces": {ev["event"]: r["decisions"][ev["decisions"][0]].to_json() for ev in r["events"][:2]}}
        out[nm] = res
    return out


def stage_agent(key: str):
    t0 = time.time()
    dataset, role = SETS[key]
    get_units(dataset, (role, "commissioning"))                 # builds the fast-layer cache here (one pool), so the workers below only read it
    allres = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for out in ex.map(agent_chunk, [(key, k, 6) for k in range(6)]):
            allres.update(out)
    with open(F.CACHE / f"final_{key}.pkl", "wb") as f:
        pickle.dump(allres, f)
    print(key, len(allres), "units", f"{time.time() - t0:.0f} s")


def stage_baselines(key: str):
    from hydrai_twin.cgh2.dashboard import CGH2Dashboard
    from hydrai_twin.physical_dataset import static_flags_from_parquet
    from ml import cgh2_agent as AG
    from ml import cgh2_baselines as BL
    from ml.cgh2_features import build, load_raw
    BUDGETS = {"1/wk": 1.0}
    dataset, role = SETS[key]
    root = ROOT / dataset
    m = json.loads((root / "manifest.json").read_text())
    dev_root = ROOT / "output/cgh2/medium"
    dm = json.loads((dev_root / "manifest.json").read_text())
    dash = CGH2Dashboard.from_dict(dm["dashboard"])
    cls_dev, cls = dm["class_parameters"], m["class_parameters"]
    bl, eps = {}, {}
    for e in dm["episodes"]:
        if e["role"] in ("dev", "commissioning"):
            _, sf = static_flags_from_parquet(dev_root / e["slow_file"], dash)
            b = BL.load_episode(dev_root, e, cls_dev["volume_m3"]); b.static_flags = np.array(sf, dtype=bool); bl[e["name"]] = b
            raw = load_raw(dev_root, e, cls_dev); names, X = build(raw)
            eps[e["name"]] = AG.Ep(e, raw.t, X, np.array(sf, dtype=bool), raw.has_data_fault)
    mods = list(MODULES)
    comm_bl = {b.entry["module_id"]: b for b in bl.values() if b.entry["role"] == "commissioning"}
    healthy = [b for b in bl.values() if b.entry["module_id"] in mods and b.entry["fault_id"] == 0 and b.entry["scenario_class"] == "standard" and b.entry["role"] in ("dev", "commissioning") and "dark" not in b.entry["variant_tag"]]
    model_bl = BL.train(healthy, comm_bl, BUDGETS["1/wk"])
    pool = [e for e in eps.values() if e.entry["role"] in ("dev", "commissioning")]
    thr = AG.thresholds(AG.oof_healthy_scores(pool, mods), BUDGETS)
    learned = AG.fit(pool)
    flags = {}
    for e in m["episodes"]:
        if e["role"] == role:
            _, sf = static_flags_from_parquet(root / e["slow_file"], dash)
            b = BL.load_episode(root, e, cls["volume_m3"]); b.static_flags = np.array(sf, dtype=bool)
            comm = [c for c in m["episodes"] if c["role"] == "commissioning" and c["module_id"] == e["module_id"]]
            cb = BL.load_episode(root, comm[0], cls["volume_m3"])
            for det, f in BL.detect(model_bl, b, cb).items():
                flags[("1/wk", det)] = flags.get(("1/wk", det), {}); flags[("1/wk", det)][e["name"]] = f
            raw = load_raw(root, e, cls); _, X = build(raw)
            ep = AG.Ep(e, raw.t, X, np.array(sf, dtype=bool), raw.has_data_fault)
            flags.setdefault(("1/wk", "learned"), {})[e["name"]] = AG.alarm_flags(AG.score(learned, ep), thr["1/wk"])
    with open(F.CACHE / f"final_{key}_baselines.pkl", "wb") as f:
        pickle.dump(flags, f)
    print("baselines", key, len(flags[("1/wk", "learned")]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["models", "agent", "baselines"])
    ap.add_argument("--set", choices=list(SETS), default="unseen")
    a = ap.parse_args()
    import importlib.util
    spec = importlib.util.spec_from_file_location("freeze", ROOT / "scripts" / "cgh2_agent_freeze.py")
    fz = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fz)
    violated = fz.verify()
    if violated:
        sys.exit("refusing to touch unseen / OOD data: the frozen configuration changed or was never frozen:\n  " + "\n  ".join(violated))
    {"models": stage_models, "agent": lambda: stage_agent(a.set), "baselines": lambda: stage_baselines(a.set)}[a.stage]()
