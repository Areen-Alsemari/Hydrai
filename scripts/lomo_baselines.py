"""Leave-one-module-out evaluation of Model A / Model B across feature sets
(absolute vs. module-relative vs. module-relative + multi-horizon), over the
6 development modules. Writes output/ml/lomo_metrics.json.

Usage:
    python scripts/lomo_baselines.py
    python scripts/lomo_baselines.py --data output/dataset --sets absolute relative_multi
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.features import STRIDE_S, build_feature_set
from ml.lomo import run_lomo
from ml.relative import FEATURE_SETS, ModuleBaselines


def fmt(d):
    return f"{d['mean']:.3f}±{d['std']:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/dataset")
    ap.add_argument("--out", default="output/ml")
    ap.add_argument("--sets", nargs="*", default=list(FEATURE_SETS), choices=FEATURE_SETS)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    data, out = root / args.data, root / args.out
    out.mkdir(parents=True, exist_ok=True)

    t = time.time()
    feats = build_feature_set(data / "dataset.jsonl", out / "features_all.npz")
    comm = build_feature_set(data / "commissioning.jsonl", out / "features_commissioning.npz")
    baselines = ModuleBaselines().fit(comm["X"], comm["module"], comm["phase"])
    print(f"features: {feats['X'].shape}  modules: {sorted(set(feats['module']))}  ({time.time()-t:.0f}s)")

    results = {}
    for fs in args.sets:
        t = time.time()
        r = run_lomo(feats, baselines, fs, stride_s=STRIDE_S, seed=args.seed)
        results[fs] = r
        a, b = r["aggregate"]["model_a"], r["aggregate"]["model_b"]
        print(f"\n=== feature set: {fs}  ({r['n_features']} features, {time.time()-t:.0f}s) ===")
        print(f"Model B  accuracy(settled) {fmt(b['accuracy_settled'])}  macro-F1 {fmt(b['macro_f1_settled'])}  normal recall {fmt(b['normal_recall'])}")
        print("   per-class recall:    " + "  ".join(f"{l}:{b['per_class_recall'][l]['mean']:.2f}" for l in b["per_class_recall"]))
        print("   per-class precision: " + "  ".join(f"{l}:{b['per_class_precision'][l]['mean']:.2f}" for l in b["per_class_precision"]))
        for name, m in a.items():
            print(f"Model A [{name:7s}] AUROC(settled) {fmt(m['auroc_settled'])}  recall@thr {fmt(m['recall_settled'])}  false-alarm {fmt(m['false_alarm_window_rate'])}")
        worst = min(r["folds"], key=lambda k: r["folds"][k]["model_b"]["accuracy_settled"])
        print(f"   per-module Model B accuracy: " + "  ".join(f"{m}:{f['model_b']['accuracy_settled']:.3f}" for m, f in r["folds"].items()) + f"   (worst: {worst})")

    (out / "lomo_metrics.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {out / 'lomo_metrics.json'}")


if __name__ == "__main__":
    main()
