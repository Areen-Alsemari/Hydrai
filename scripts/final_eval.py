"""ONE-SHOT evaluation of the frozen pipeline on never-before-seen units.

Pipeline (frozen BEFORE this was run, from the LOMO results on M01-M06):
  features  : relative_multi (module-relative, multi-horizon)
  Model A   : z-score + Isolation Forest on healthy windows, threshold = 99th
              percentile of nested-leave-one-module-out normal scores
  Model B   : HistGradientBoosting, fixed hyperparameters, raw (no smoothing --
              persistence showed no benefit in LOMO)
Trained on all six development modules (M01-M06); evaluated on X01-X03, which
were generated with different seeds and different module profiles and were
never used for any decision. Each unit is normalized against ITS OWN
commissioning run.

Because a repeated "final" evaluation is just tuning, this script refuses to
run again once output/ml/final_eval.json exists (delete it deliberately if you
really mean to start over, and treat any later numbers as development numbers).
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.features import LABEL_ORDER, STRIDE_S, build_feature_set
from ml.lomo import _b_metrics
from ml.model_a import run_model_a
from ml.model_b import run_model_b
from ml.postprocess import detection_delays
from ml.relative import ModuleBaselines, prepare
from ml.util import strip_private

FEATURE_SET = "relative_multi"


def main():
    root = Path(__file__).resolve().parent.parent
    out = root / "output/ml"
    result_path = out / "final_eval.json"
    if result_path.exists():
        sys.exit(f"{result_path} already exists: the one-shot final evaluation has been run. "
                 "Re-running it would turn it into a tuning loop. Delete the file only if you intend to restart.")

    dev = build_feature_set(root / "output/dataset/dataset.jsonl", out / "features_all.npz")
    dev_c = build_feature_set(root / "output/dataset/commissioning.jsonl", out / "features_commissioning.npz")
    fin = build_feature_set(root / "output/dataset_final/dataset.jsonl", out / "features_final.npz")
    fin_c = build_feature_set(root / "output/dataset_final/commissioning.jsonl", out / "features_final_commissioning.npz")
    assert set(dev["module"]).isdisjoint(set(fin["module"])), "final units must not overlap development modules"

    Xd, names = prepare(dev, ModuleBaselines().fit(dev_c["X"], dev_c["module"], dev_c["phase"]), FEATURE_SET)
    Xf, _ = prepare(fin, ModuleBaselines().fit(fin_c["X"], fin_c["module"], fin_c["phase"]), FEATURE_SET)
    train = {**{k: v for k, v in dev.items() if k != "X"}, "X": Xd}
    test = {**{k: v for k, v in fin.items() if k != "X"}, "X": Xf}
    print(f"train: {sorted(set(train['module']))} ({len(train['y'])} windows)   test: {sorted(set(test['module']))} ({len(test['y'])} windows)")

    a = run_model_a(train, test, stride_s=STRIDE_S, seed=0)
    b = run_model_b(train, test, seed=0, feature_names=names, run_ablation=True)

    y, ep, pred = test["y"], test["episode_id"], b["_pred"]
    settled = (y == 0) | (test["sev_frac"] >= 0.95)
    res = {"feature_set": FEATURE_SET, "train_modules": sorted(set(train["module"])), "test_units": sorted(set(test["module"])),
           "model_b": {"pooled_settled": _b_metrics(y, pred, settled), "pooled_all": _b_metrics(y, pred, np.ones(len(y), bool)), "per_unit_settled": {}},
           "model_a": {}, "model_b_ablation_no_vacuum": b["ablation_no_vacuum_sensor"]}
    for u in sorted(set(test["module"])):
        m = test["module"] == u
        res["model_b"]["per_unit_settled"][u] = _b_metrics(y, pred, settled & m)
    for name, d in a["models"].items():
        alarm = d["_scores"] > d["threshold"]
        res["model_a"][name] = {
            "auroc_settled": d["auroc_settled"], "auprc_settled": d["auprc_settled"],
            "recall_settled": d["recall_settled"], "false_alarm_window_rate": d["false_alarm_window_rate"],
            "recall_settled_by_scenario_variant": d["recall_settled_by_scenario_variant"],
            "detection": detection_delays(ep, y, alarm, STRIDE_S),
        }
    result_path.write_text(json.dumps(strip_private(res), indent=2))

    bs = res["model_b"]["pooled_settled"]
    print(f"\nMODEL B (unseen units, settled): accuracy {bs['accuracy']:.3f}  macro-F1 {bs['macro_f1']:.3f}  grouped(2|4) accuracy {bs['accuracy_grouped_2_4']:.3f}  (n={bs['n']})")
    print("  all windows: accuracy %.3f" % res["model_b"]["pooled_all"]["accuracy"])
    print("  per-class recall:", {k: round(v, 2) for k, v in bs["per_class_recall"].items()})
    print("  per-unit accuracy:", {u: round(v["accuracy"], 3) for u, v in res["model_b"]["per_unit_settled"].items()})
    print("  2-vs-3 with vacuum sensor:", b["pair_2v3_settled"])
    print("  2-vs-3 WITHOUT vacuum sensor:", b["ablation_no_vacuum_sensor"]["pair_2v3_settled"])
    for name, d in res["model_a"].items():
        det = d["detection"]
        print(f"MODEL A [{name}]: AUROC(settled) {d['auroc_settled']:.3f}  recall(settled) {d['recall_settled']:.3f}  false-alarm {d['false_alarm_window_rate']:.3f}  "
              f"detected {det['detected_fraction']:.2f}  median delay {det['median_delay_s']}s")
    print(f"\nwrote {result_path}")


if __name__ == "__main__":
    main()
