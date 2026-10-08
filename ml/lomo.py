"""
Leave-one-module-out (LOMO) evaluation: the headline generalization number.

For each module m: fit Model A/B on the OTHER modules only (each normalized
against its own commissioning baseline), evaluate on m (normalized against
m's own commissioning baseline). Reported as mean +/- std across modules.
A single held-out module can be an unrepresentative draw (the first split on
M06 was the hardest of six), so the across-module mean is the number to
quote, and the spread is part of the result.

Hyperparameters are fixed a priori (see model_a.py / model_b.py) and are NOT
tuned on LOMO folds. Model A's alarm threshold is calibrated inside each
fold from the training modules only (nested leave-one-module-out).
"""

from __future__ import annotations

import numpy as np

from ml.model_a import run_model_a
from ml.model_b import run_model_b
from ml.relative import ModuleBaselines, prepare

A_MODELS = ("zscore", "iforest")


def _subset(feats: dict, mask: np.ndarray, X: np.ndarray) -> dict:
    out = {k: v[mask] for k, v in feats.items() if k != "X"}
    out["X"] = X[mask]
    return out


def _fold_summary(a: dict, b: dict) -> dict:
    s = b["settled"]
    return {
        "model_a": {
            name: {
                "auroc_settled": a["models"][name]["auroc_settled"],
                "auprc_settled": a["models"][name]["auprc_settled"],
                "recall_settled": a["models"][name]["recall_settled"],
                "false_alarm_window_rate": a["models"][name]["false_alarm_window_rate"],
                "recall_by_scenario": {k: v["recall"] for k, v in a["models"][name]["recall_by_scenario"].items()},
            }
            for name in A_MODELS
        },
        "model_b": {
            "accuracy_settled": s["accuracy"],
            "macro_f1_settled": s["macro_f1"],
            "normal_recall": s["per_class"]["0"]["recall"],
            "per_class_recall": {k: v["recall"] for k, v in s["per_class"].items()},
            "per_class_precision": {k: v["precision"] for k, v in s["per_class"].items()},
        },
    }


def _mean_std(vals: list[float]) -> dict:
    v = np.array([x for x in vals if x is not None], dtype=float)
    return {"mean": float(v.mean()), "std": float(v.std()), "min": float(v.min()), "max": float(v.max())}


def aggregate(folds: dict[str, dict]) -> dict:
    mods = list(folds)
    agg: dict = {"model_a": {}, "model_b": {}}
    for name in A_MODELS:
        agg["model_a"][name] = {
            k: _mean_std([folds[m]["model_a"][name][k] for m in mods])
            for k in ("auroc_settled", "auprc_settled", "recall_settled", "false_alarm_window_rate")
        }
    for k in ("accuracy_settled", "macro_f1_settled", "normal_recall"):
        agg["model_b"][k] = _mean_std([folds[m]["model_b"][k] for m in mods])
    labels = folds[mods[0]]["model_b"]["per_class_recall"].keys()
    agg["model_b"]["per_class_recall"] = {l: _mean_std([folds[m]["model_b"]["per_class_recall"][l] for m in mods]) for l in labels}
    agg["model_b"]["per_class_precision"] = {l: _mean_std([folds[m]["model_b"]["per_class_precision"][l] for m in mods]) for l in labels}
    return agg


def run_lomo(feats: dict, baselines: ModuleBaselines | None, feature_set: str, stride_s: float, seed: int = 0) -> dict:
    X, names = prepare(feats, baselines, feature_set)
    modules = sorted(set(feats["module"]))
    folds: dict[str, dict] = {}
    oof: dict[str, list] = {k: [] for k in ("y", "pred", "proba", "episode_id", "module", "scenario", "variant", "sev_frac", "phase")}
    oof.update({f"score_{n}": [] for n in A_MODELS})
    oof.update({f"thr_{n}": [] for n in A_MODELS})
    for m in modules:
        held = feats["module"] == m
        train, test = _subset(feats, ~held, X), _subset(feats, held, X)
        assert m not in set(train["module"]) and set(test["module"]) == {m}
        a = run_model_a(train, test, stride_s=stride_s, seed=seed)
        b = run_model_b(train, test, seed=seed, feature_names=names, run_ablation=False)
        folds[m] = _fold_summary(a, b)
        for k in ("y", "episode_id", "module", "scenario", "variant", "sev_frac", "phase"):
            oof[k].append(test[k])
        oof["pred"].append(b["_pred"])
        oof["proba"].append(b["_proba"])
        for n in A_MODELS:
            oof[f"score_{n}"].append(a["models"][n]["_scores"])
            oof[f"thr_{n}"].append(np.full(len(test["y"]), a["models"][n]["threshold"]))
    oof = {k: np.concatenate(v) for k, v in oof.items()}
    return {"feature_set": feature_set, "n_features": len(names), "folds": folds,
            "aggregate": aggregate(folds), "oof": oof}


# --- pooled out-of-fold report -------------------------------------------------

from sklearn.metrics import confusion_matrix, f1_score  # noqa: E402

from ml.features import LABEL_ORDER  # noqa: E402
from ml.postprocess import detection_delays, labels_from_proba, persistent_alarm, smooth_proba  # noqa: E402

# A-priori persistence settings (NOT tuned on LOMO results): 6 windows = 60 s
# at the 10 s stride for Model B; 3-of-5 windows for Model A alarms.
B_SMOOTH_K = 6
A_PERSIST_K, A_PERSIST_M = 5, 3

# Insulation degradation (2) and abnormal pressure rise (4) share the same
# observable signature in this sensor suite: both are a slow pressure/
# temperature creep, and the only thing that differs is boil-off magnitude
# (~5e-5 kg/s), far below what the level sensor resolves. Reported as an
# EXTRA grouped metric next to the strict one -- never instead of it.
AMBIGUOUS_GROUP = {2, 4}


def _grouped(arr: np.ndarray) -> np.ndarray:
    return np.where(np.isin(arr, list(AMBIGUOUS_GROUP)), 2, arr)


def _b_metrics(y, pred, mask):
    cm = confusion_matrix(y[mask], pred[mask], labels=LABEL_ORDER)
    return {
        "n": int(mask.sum()),
        "accuracy": float((y[mask] == pred[mask]).mean()),
        "macro_f1": float(f1_score(y[mask], pred[mask], labels=LABEL_ORDER, average="macro", zero_division=0)),
        "accuracy_grouped_2_4": float((_grouped(y[mask]) == _grouped(pred[mask])).mean()),
        "per_class_recall": {str(l): float((pred[mask][y[mask] == l] == l).mean()) if (y[mask] == l).any() else None for l in LABEL_ORDER},
        "confusion_matrix": {"labels": LABEL_ORDER, "rows_true_cols_pred": cm.tolist()},
    }


def pooled_report(oof: dict, stride_s: float) -> dict:
    y, ep = oof["y"], oof["episode_id"]
    settled = (y == 0) | (oof["sev_frac"] >= 0.95)
    allm = np.ones(len(y), dtype=bool)
    smoothed = labels_from_proba(smooth_proba(oof["proba"], ep, B_SMOOTH_K))

    out: dict = {"settings": {"b_smooth_k": B_SMOOTH_K, "a_persist": f"{A_PERSIST_M}-of-{A_PERSIST_K}"}, "model_b": {}, "model_a": {}}
    for tag, pred in (("raw", oof["pred"]), ("smoothed", smoothed)):
        out["model_b"][tag] = {"settled": _b_metrics(y, pred, settled), "all": _b_metrics(y, pred, allm)}

    pos = y != 0
    normal = ~pos
    for n in A_MODELS:
        raw_alarm = oof[f"score_{n}"] > oof[f"thr_{n}"]
        pers = persistent_alarm(raw_alarm, ep, A_PERSIST_K, A_PERSIST_M)
        out["model_a"][n] = {}
        for tag, al in (("raw", raw_alarm), ("persistent", pers)):
            sett_pos = pos & (oof["sev_frac"] >= 0.95)
            out["model_a"][n][tag] = {
                "false_alarm_window_rate": float(al[normal].mean()),
                "recall_settled": float(al[sett_pos].mean()),
                "recall_all": float(al[pos].mean()),
                "detection": detection_delays(ep, y, al, stride_s),
                "recall_settled_by_scenario": {
                    s: float(al[sett_pos & (oof["scenario"] == s)].mean())
                    for s in sorted(set(oof["scenario"][pos]))
                },
            }
    return out
