"""Leave-one-module-out training of the fusion meta-model on the tools' feature matrices.

For each held-out dev module h: the model trains on the other dev modules; watch / alert thresholds are fitted on OUT-OF-FOLD healthy scores of the training
modules (each scored by a model that did not see that module). Per-unit smoothed class probabilities of module h are cached for the orchestrator.
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.features import FEATURES

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")


def entries(dataset: str = "output/cgh2/medium", roles=("dev",)):
    m = json.loads((ROOT / dataset / "manifest.json").read_text())
    return [e for e in m["episodes"] if e["role"] in roles]


def run_fold(args):
    h, tag, drop, stride = args
    t0 = time.time()
    units = [F.load_funit(e) for e in entries()]
    if drop:
        cols = [j for j, k in enumerate(FEATURES) if any(k.startswith(p) for p in drop)]
        for u in units:
            u.X[:, cols] = 0.0                       # the tool is absent: its features carry no information
    train = [u for u in units if u.entry["module_id"] != h]
    model = F.train_meta(train, stride)
    oof = F.oof_healthy(train, [m for m in MODULES if m != h], stride)
    thr = F.thresholds_from(oof)
    pre = f"{tag}_" if tag else ""
    for u in units:
        if u.entry["module_id"] == h:
            np.save(F.CACHE / f"probs_{pre}{u.entry['name']}.npy", F.probs(model, u))
    with open(F.CACHE / f"meta_{pre}{h}.pkl", "wb") as f:
        pickle.dump({"model": model, "thr": thr, "oof_weeks": sum(t[-1] - t[0] for t, _ in oof) / F.WEEK_S}, f)
    return h, thr, time.time() - t0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--drop", default="", help="comma-separated feature prefixes to remove, e.g. T3_,T6_")
    ap.add_argument("--stride", type=int, default=F.STRIDE)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    drop = [x for x in a.drop.split(",") if x]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for h, thr, dt in ex.map(run_fold, [(m, a.tag, drop, a.stride) for m in MODULES]):
            print(h, {k: round(v, 4) for k, v in thr.items()}, f"{dt:.0f} s", flush=True)
