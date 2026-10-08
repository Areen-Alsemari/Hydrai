"""Build the per-minute 1 s-layer cache the agent uses for exact flow integrals and fast-layer signals (dev + commissioning by default; --all adds unseen).

    python scripts/cgh2_agent_cache.py [output/cgh2/medium] [--all]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.cgh2_agent import stream

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", default="output/cgh2/medium")
    ap.add_argument("--all", action="store_true", help="include unseen units (do this only for the one-shot evaluation)")
    a = ap.parse_args()
    root = ROOT / a.dataset
    m = json.loads((root / "manifest.json").read_text())
    ents = [e for e in m["episodes"] if a.all or e["role"] != "unseen"]
    t = time.time()
    fc = stream.build_fast_cache(root, ents, m["class_parameters"]["mop_bar"])
    print(f"{len(fc)} episodes cached in {time.time() - t:.0f} s -> {stream.CACHE}")
