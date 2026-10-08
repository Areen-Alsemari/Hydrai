"""Pooled out-of-fold analysis of the selected pipeline (LOMO over the 6
development modules): confusion matrix, ambiguity-aware grouped metric,
effect of causal persistence, and detection delay. Writes
output/ml/lomo_pooled.json.

Usage: python scripts/analyze_lomo.py [--set relative_multi]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.features import LABEL_ORDER, STRIDE_S, build_feature_set
from ml.lomo import pooled_report, run_lomo
from ml.relative import FEATURE_SETS, ModuleBaselines
from ml.util import strip_private


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/dataset")
    ap.add_argument("--out", default="output/ml")
    ap.add_argument("--set", default="relative_multi", choices=FEATURE_SETS)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    data, out = root / args.data, root / args.out

    feats = build_feature_set(data / "dataset.jsonl", out / "features_all.npz")
    comm = build_feature_set(data / "commissioning.jsonl", out / "features_commissioning.npz")
    baselines = ModuleBaselines().fit(comm["X"], comm["module"], comm["phase"])

    r = run_lomo(feats, baselines, args.set, stride_s=STRIDE_S)
    rep = pooled_report(r["oof"], STRIDE_S)
    (out / "lomo_pooled.json").write_text(json.dumps(strip_private({"feature_set": args.set, **rep}), indent=2))

    print(f"feature set: {args.set}   settings: {rep['settings']}")
    for tag in ("raw", "smoothed"):
        for sl in ("settled", "all"):
            m = rep["model_b"][tag][sl]
            print(f"Model B [{tag:8s}|{sl:7s}] acc {m['accuracy']:.3f}  macro-F1 {m['macro_f1']:.3f}  grouped(2|4) acc {m['accuracy_grouped_2_4']:.3f}  (n={m['n']})")
    cm = np.array(rep["model_b"]["smoothed"]["settled"]["confusion_matrix"]["rows_true_cols_pred"])
    print("\nconfusion (smoothed, settled) rows=true cols=pred, order", LABEL_ORDER)
    print(cm)
    print()
    for n, d in rep["model_a"].items():
        for tag in ("raw", "persistent"):
            m = d[tag]
            det = m["detection"]
            print(f"Model A [{n:7s}|{tag:10s}] false-alarm {m['false_alarm_window_rate']:.3f}  recall settled {m['recall_settled']:.3f} all {m['recall_all']:.3f}  "
                  f"detected {det['detected_fraction']:.2f} of {det['n_fault_episodes']} episodes, median delay {det['median_delay_s']}s p90 {det['p90_delay_s']}s")
    print("\nModel A zscore persistent, settled recall by scenario:")
    for s, v in rep["model_a"]["zscore"]["persistent"]["recall_settled_by_scenario"].items():
        print(f"   {s:26s} {v:.3f}")


if __name__ == "__main__":
    main()
