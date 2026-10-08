"""
Model B -- fault diagnosis ("if abnormal, what is most likely happening?"),
Predictive_Hydrogen_Storage_Safety_Project_Handoff Sec.14. Multi-class
gradient-boosted trees over the same window features as Model A, predicting
the HYDRAI Sec.10 AI labels: 0 normal, 1 sensor fault, 2 insulation
degradation, 3 vacuum degradation, 4 abnormal pressure rise, 5 containment
anomaly, 6 structural concern, -1 unknown.

Two evaluation slices are reported because the generators flip the label at
onset while physical severity is still ~0: "all" windows, and "settled"
(fault windows at >=95% of their episode's own max severity, plus all
normal windows).

Ablation: the insulation-vs-vacuum pair (2 vs 3) has an identical P/T/
boil-off signature in Sec.10; only the vacuum-jacket sensor separates them.
`run_model_b` re-trains without the vacuum_pressure_pa features and reports
the 2-vs-3 confusion, to show whether the model actually depends on it.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

from ml.features import FEATURE_NAMES, LABEL_ORDER


def _fit(X: np.ndarray, y: np.ndarray, seed: int) -> HistGradientBoostingClassifier:
    # early_stopping=False: sklearn's internal validation split is a random
    # window split, which would leak neighbouring windows of the same episode.
    return HistGradientBoostingClassifier(
        max_iter=150, learning_rate=0.1, class_weight="balanced",
        early_stopping=False, random_state=seed,
    ).fit(X, y)


def proba_in_label_order(clf: HistGradientBoostingClassifier, X: np.ndarray) -> np.ndarray:
    """predict_proba columns re-ordered to LABEL_ORDER (classes absent from
    training get probability 0)."""
    raw = clf.predict_proba(X)
    out = np.zeros((len(X), len(LABEL_ORDER)))
    for j, c in enumerate(clf.classes_):
        out[:, LABEL_ORDER.index(int(c))] = raw[:, j]
    return out


def _report(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    p, r, f, support = precision_recall_fscore_support(y_true, y_pred, labels=LABEL_ORDER, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABEL_ORDER, average="macro", zero_division=0)),
        "per_class": {
            str(lab): {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(support[i])}
            for i, lab in enumerate(LABEL_ORDER)
        },
        "confusion_matrix": {"labels": LABEL_ORDER, "rows_true_cols_pred": cm.tolist()},
    }


def _slices(test: dict) -> dict[str, np.ndarray]:
    settled_or_normal = (test["y"] == 0) | (test["sev_frac"] >= 0.95)
    return {"all": np.ones(len(test["y"]), dtype=bool), "settled": settled_or_normal}


def _pair_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """How often true-2 is predicted 3 and vice versa (settled windows)."""
    out = {}
    for a, b in ((2, 3), (3, 2)):
        m = y_true == a
        out[f"true_{a}_predicted_{b}"] = float((y_pred[m] == b).mean()) if m.any() else None
        out[f"true_{a}_recall"] = float((y_pred[m] == a).mean()) if m.any() else None
    return out


def run_model_b(
    train: dict, test: dict, seed: int = 0, feature_names: list[str] | None = None, run_ablation: bool = True
) -> dict:
    names = feature_names if feature_names is not None else FEATURE_NAMES
    results: dict = {"n_features": len(names), "n_train_windows": int(len(train["y"]))}
    clf = _fit(train["X"], train["y"], seed)
    pred = clf.predict(test["X"])
    results["_pred"] = pred                                  # non-JSON arrays, stripped before dumping
    results["_proba"] = proba_in_label_order(clf, test["X"])
    for name, mask in _slices(test).items():
        results[name] = _report(test["y"][mask], pred[mask])
    results["pair_2v3_settled"] = _pair_confusion(test["y"][_slices(test)["settled"]], pred[_slices(test)["settled"]])

    if not run_ablation:
        return results

    keep = [i for i, n in enumerate(names) if not n.startswith("vacuum_pressure_pa__")]
    clf_nv = _fit(train["X"][:, keep], train["y"], seed)
    pred_nv = clf_nv.predict(test["X"][:, keep])
    s = _slices(test)["settled"]
    results["ablation_no_vacuum_sensor"] = {
        "settled": _report(test["y"][s], pred_nv[s]),
        "pair_2v3_settled": _pair_confusion(test["y"][s], pred_nv[s]),
    }
    return results
