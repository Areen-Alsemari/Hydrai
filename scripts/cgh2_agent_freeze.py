"""Freeze the agent configuration BEFORE the one-shot unseen / OOD evaluation: hashes of the agent code, the dev-trained fusion models and the thresholds are
written to output/reports/cgh2_agent_freeze.json. cgh2_agent_final.py refuses to run if anything changed after this point.

    python scripts/cgh2_agent_freeze.py            # write the freeze manifest
    python scripts/cgh2_agent_freeze.py --verify   # check it (exit code 1 on mismatch)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "reports" / "cgh2_agent_freeze.json"
GLOBS = ["hydrai_twin/cgh2_agent/**/*.py", "hydrai_twin/cgh2/*.py", "ml/cgh2_*.py", "ml/classical_baselines.py", "ml/headline_metrics.py", "scripts/cgh2_agent_features.py", "scripts/cgh2_agent_meta.py",
         "scripts/cgh2_agent_run_dev.py", "scripts/cgh2_agent_final.py", "scripts/cgh2_agent_eval.py"]
CACHE = ROOT / "output" / "cgh2_cache" / "agent"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot() -> dict:
    files = {str(p.relative_to(ROOT)): sha(p) for g in GLOBS for p in sorted(ROOT.glob(g)) if "__pycache__" not in str(p)}
    models = {f"meta_{h}.pkl": sha(CACHE / f"meta_{h}.pkl") for h in ("M01", "M02", "M03", "M04", "M05", "M06")}
    thr = {h: pickle.load(open(CACHE / f"meta_{h}.pkl", "rb"))["thr"] for h in ("M01", "M02", "M03", "M04", "M05", "M06")}
    return {"files": files, "dev_models": models, "dev_thresholds": thr}


def verify() -> list[str]:
    if not OUT.exists():
        return ["no freeze manifest: run scripts/cgh2_agent_freeze.py first"]
    old, new = json.loads(OUT.read_text()), snapshot()
    bad = [f"{k} changed" for k in old["files"] if old["files"][k] != new["files"].get(k)] + [f"{k} added" for k in new["files"] if k not in old["files"]]
    bad += [f"{k} changed" for k in old["dev_models"] if old["dev_models"][k] != new["dev_models"].get(k)]
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        bad = verify()
        print("freeze OK" if not bad else "FREEZE VIOLATED:\n  " + "\n  ".join(bad))
        sys.exit(1 if bad else 0)
    snap = snapshot()
    snap["frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    snap["note"] = "Dev-only configuration frozen before the unseen / OOD one-shot evaluation. Unseen and OOD data had not been scored by the agent at this point."
    OUT.write_text(json.dumps(snap, indent=1))
    print("frozen", len(snap["files"]), "files,", len(snap["dev_models"]), "models ->", OUT)
