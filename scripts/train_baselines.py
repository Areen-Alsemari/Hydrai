"""Train and evaluate the Model A (anomaly detection) and Model B (fault
diagnosis) baselines on output/dataset/{train,test}.jsonl, using the
held-out-module split. Writes output/ml/metrics.json and prints a summary.

Usage:
    python scripts/train_baselines.py
    python scripts/train_baselines.py --data output/dataset --seed 1
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.features import STRIDE_S, WINDOW_S, build_feature_set
from ml.model_a import run_model_a
from ml.model_b import run_model_b
from ml.util import strip_private


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/dataset")
    ap.add_argument("--out", default="output/ml")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    data, out = root / args.data, root / args.out
    out.mkdir(parents=True, exist_ok=True)

    t = time.time()
    train = build_feature_set(data / "train.jsonl", out / "features_train.npz")
    test = build_feature_set(data / "test.jsonl", out / "features_test.npz")
    print(f"features: train {train['X'].shape}, test {test['X'].shape}  ({time.time()-t:.0f}s)")
    print(f"train modules: {sorted(set(train['module']))}  test modules: {sorted(set(test['module']))}")

    a = run_model_a(train, test, stride_s=STRIDE_S, seed=args.seed)
    b = run_model_b(train, test, seed=args.seed)

    (out / "metrics.json").write_text(json.dumps(
        strip_private({"window_s": WINDOW_S, "stride_s": STRIDE_S, "seed": args.seed, "model_a": a, "model_b": b}), indent=2))

    print(f"\n=== Model A (anomaly detection; trained on {a['n_train_normal_windows']} normal windows) ===")
    for name, m in a["models"].items():
        print(f"[{name}] AUROC all/settled: {m['auroc_all']:.3f}/{m['auroc_settled']:.3f}  "
              f"AUPRC all/settled: {m['auprc_all']:.3f}/{m['auprc_settled']:.3f}")
        print(f"   @thr(99% oof normal): precision {m['precision']:.3f}  recall {m['recall']:.3f}  "
              f"settled-recall {m['recall_settled']:.3f}  false-alarm rate {m['false_alarm_window_rate']:.3f}  "
              f"({m['false_alarm_windows_per_normal_hour']:.1f} alarm-windows/normal-hr)")
        for scen, r in m["recall_by_scenario"].items():
            print(f"     {scen:26s} recall {r['recall']:.3f}  (n={r['n']})")

    print("\n=== Model B (fault diagnosis) ===")
    for sl in ("all", "settled"):
        r = b[sl]
        print(f"[{sl}] n={r['n']}  accuracy {r['accuracy']:.3f}  macro-F1 {r['macro_f1']:.3f}")
        for lab, c in r["per_class"].items():
            print(f"     label {lab:>2s}: P {c['precision']:.3f}  R {c['recall']:.3f}  F1 {c['f1']:.3f}  (n={c['support']})")
    print(f"2-vs-3 (settled), with vacuum sensor:    {b['pair_2v3_settled']}")
    print(f"2-vs-3 (settled), WITHOUT vacuum sensor: {b['ablation_no_vacuum_sensor']['pair_2v3_settled']}")
    print(f"\nwrote {out / 'metrics.json'}")


if __name__ == "__main__":
    main()
