"""
Model A -- anomaly detection ("is current behavior inconsistent with
expected operation?"), per Predictive_Hydrogen_Storage_Safety_Project_Handoff
Sec.14. Two baselines, both trained on NORMAL windows only (label 0 -- this
includes the clean pre-onset segments of fault episodes, which are normal
operation by construction):

  - zscore:  statistical/residual baseline. Standardize each feature against
             normal-operation mean/std; score = max |z| over features.
  - iforest: Isolation Forest on the standardized features.

Higher score = more anomalous. Output shape per window mirrors the handoff's
example: {"anomaly_score": float}.

Threshold calibration: the alarm threshold is the 99th percentile of normal
scores, but computed out-of-fold by LEAVE-ONE-MODULE-OUT (fit on 4 training
modules, score the 5th's normal windows, pool) rather than on the data the
model was fit on -- in-sample scores are optimistically low and would
under-set the threshold, inflating the false-alarm rate on unseen data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score


NORMAL_QUANTILE = 0.99


@dataclass
class ZScoreModel:
    mean_: np.ndarray | None = None
    std_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "ZScoreModel":
        self.mean_ = X.mean(axis=0)
        self.std_ = X.std(axis=0) + 1e-6
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return np.abs((X - self.mean_) / self.std_).max(axis=1)


@dataclass
class IForestModel:
    seed: int = 0
    n_estimators: int = 200
    scaler_mean_: np.ndarray | None = None
    scaler_std_: np.ndarray | None = None
    forest_: IsolationForest | None = None

    def fit(self, X: np.ndarray) -> "IForestModel":
        self.scaler_mean_ = X.mean(axis=0)
        self.scaler_std_ = X.std(axis=0) + 1e-6
        self.forest_ = IsolationForest(
            n_estimators=self.n_estimators, random_state=self.seed, n_jobs=-1
        ).fit((X - self.scaler_mean_) / self.scaler_std_)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        # sklearn: higher score_samples = more normal, so negate.
        return -self.forest_.score_samples((X - self.scaler_mean_) / self.scaler_std_)


MODEL_FACTORIES = {"zscore": ZScoreModel, "iforest": IForestModel}


def calibrate_threshold(factory, X_normal: np.ndarray, modules_normal: np.ndarray) -> float:
    """Out-of-fold (leave-one-module-out) normal-score quantile."""
    oof = []
    for m in np.unique(modules_normal):
        held = modules_normal == m
        oof.append(factory().fit(X_normal[~held]).score(X_normal[held]))
    return float(np.quantile(np.concatenate(oof), NORMAL_QUANTILE))


def _recall(alarm: np.ndarray, mask: np.ndarray) -> dict:
    n = int(mask.sum())
    return {"n": n, "recall": float(alarm[mask].mean()) if n else None}


def evaluate(scores: np.ndarray, threshold: float, test: dict, stride_s: float) -> dict:
    y_true = (test["y"] != 0).astype(int)
    alarm = scores > threshold
    normal = y_true == 0
    settled = (test["sev_frac"] >= 0.95) & (y_true == 1)

    tp = int((alarm & (y_true == 1)).sum())
    fp = int((alarm & normal).sum())
    fn = int((~alarm & (y_true == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    normal_hours = normal.sum() * stride_s / 3600.0

    # Settled-slice metrics: positives that have actually ramped to their
    # episode's full severity, vs. all normal windows.
    keep = normal | settled
    out = {
        "threshold": threshold,
        "n_test_windows": int(len(y_true)),
        "n_positive_windows": int(y_true.sum()),
        "auroc_all": float(roc_auc_score(y_true, scores)),
        "auprc_all": float(average_precision_score(y_true, scores)),
        "auroc_settled": float(roc_auc_score(y_true[keep], scores[keep])),
        "auprc_settled": float(average_precision_score(y_true[keep], scores[keep])),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_alarm_window_rate": float(alarm[normal].mean()),
        "false_alarm_windows_per_normal_hour": float(fp / normal_hours) if normal_hours else None,
        "recall_settled": float(alarm[settled].mean()) if settled.any() else None,
        "recall_by_scenario": {},
        "recall_settled_by_scenario_variant": {},
    }
    for scen in sorted(set(test["scenario"]) - {"normal"}):
        s_mask = (test["scenario"] == scen) & (y_true == 1)
        out["recall_by_scenario"][scen] = _recall(alarm, s_mask)
        for var in sorted(set(test["variant"][s_mask])):
            v_mask = s_mask & (test["variant"] == var) & (test["sev_frac"] >= 0.95)
            out["recall_settled_by_scenario_variant"][f"{scen}:{var}"] = _recall(alarm, v_mask)
    return out


def run_model_a(train: dict, test: dict, stride_s: float, seed: int = 0) -> dict:
    normal = train["y"] == 0
    X_n, mod_n = train["X"][normal], train["module"][normal]
    results = {"n_train_normal_windows": int(normal.sum()), "models": {}}
    for name, cls in MODEL_FACTORIES.items():
        factory = (lambda cls=cls: cls(seed=seed)) if name == "iforest" else cls
        threshold = calibrate_threshold(factory, X_n, mod_n)
        model = factory().fit(X_n)
        scores = model.score(test["X"])
        results["models"][name] = evaluate(scores, threshold, test, stride_s)
        results["models"][name]["_scores"] = scores           # non-JSON arrays, stripped before dumping
    return results
