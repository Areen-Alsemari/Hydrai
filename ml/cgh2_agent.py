"""
CGH2 agent, slow layer (steps 1-2B): a learned detector on the compensated features with thresholds set on healthy units only.

Protocol (no peeking)
  * model: HistGradientBoosting on ml.cgh2_features, FIXED hyperparameters chosen a priori (no tuning on any held-out data)
  * training rows: every 5th minute after a 24 h warm-up; label 1 from the first observable deviation onward (the paired-twin time is a TRAINING
    LABEL only, never a feature), 0 before onset and in normal episodes; the window between onset and first-observable is ignored
  * leave-one-module-out: for held-out module h the model trains on the other dev modules; the threshold is fitted on OUT-OF-FOLD scores of the
    healthy episodes of the training modules (each scored by a model that did not see that module), to a false-alarm budget in events per week
  * score = 15-minute mean of the predicted probability; alarm when above the threshold (events merge within 1 h, as for the baselines)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ml.classical_baselines import count_events
from ml.cgh2_baselines import fit_threshold_bounded

WARMUP = 1440            # samples (24 h)
STRIDE = 5
SMOOTH = 15
WEEK_S = 7 * 86400.0
HGB = dict(max_iter=120, learning_rate=0.1, max_depth=5, min_samples_leaf=50, l2_regularization=1.0, random_state=0)


@dataclass
class Ep:
    entry: dict[str, Any]
    t: np.ndarray
    X: np.ndarray
    static: np.ndarray | None = None
    has_df: np.ndarray | None = None


def labels(e: Ep) -> np.ndarray:
    """1 after the first observable deviation, 0 before onset / in normal episodes, -1 (ignored) in between and after an unobservable onset."""
    n = len(e.t)
    ent = e.entry
    y = np.zeros(n, dtype=int)
    if ent["fault_id"] == 0:
        return y
    on, ob = ent["onset_s"], ent["first_observable_s"]
    post = e.t >= on
    y[post] = -1
    if ob is not None:
        y[e.t >= ob] = 1
    return y


def train_rows(eps: list[Ep], stride: int = STRIDE) -> tuple[np.ndarray, np.ndarray]:
    Xs, ys = [], []
    for e in eps:
        y = labels(e)
        idx = np.arange(WARMUP, len(e.t), stride)
        idx = idx[y[idx] >= 0]
        Xs.append(e.X[idx])
        ys.append(y[idx])
    return np.vstack(Xs), np.concatenate(ys)


def fit(eps: list[Ep], cols: np.ndarray | None = None) -> HistGradientBoostingClassifier:
    X, y = train_rows(eps)
    if cols is not None:
        X = X[:, cols]
    pos = max(int(y.sum()), 1)
    w = np.where(y == 1, min((len(y) - pos) / pos, 20.0), 1.0)
    m = HistGradientBoostingClassifier(**HGB)
    m.fit(X, y, sample_weight=w)
    return m


def score(m: HistGradientBoostingClassifier, e: Ep, cols: np.ndarray | None = None) -> np.ndarray:
    X = e.X if cols is None else e.X[:, cols]
    s = np.zeros(len(e.t))
    s[WARMUP:] = m.predict_proba(X[WARMUP:])[:, 1]
    c = np.concatenate([[0.0], np.cumsum(s)])
    sm = np.concatenate([c[1:SMOOTH] / np.arange(1, SMOOTH), (c[SMOOTH:] - c[:-SMOOTH]) / SMOOTH])
    sm[:WARMUP] = 0.0
    return sm


def is_calibration_episode(e: Ep) -> bool:
    ent = e.entry
    return ent["fault_id"] == 0 and ent["scenario_class"] == "standard" and "dark" not in ent["variant_tag"]


def oof_healthy_scores(train_eps: list[Ep], modules: list[str], cols: np.ndarray | None = None) -> list[tuple[np.ndarray, np.ndarray]]:
    """Out-of-fold smoothed scores of the healthy (calibration) episodes of `modules`: each module scored by a model trained on the others."""
    out = []
    for m_out in modules:
        model = fit([e for e in train_eps if e.entry["module_id"] != m_out], cols)
        for e in train_eps:
            if e.entry["module_id"] == m_out and is_calibration_episode(e):
                s = score(model, e, cols)
                out.append((e.t[WARMUP:], s[WARMUP:]))
    return out


def thresholds(oof: list[tuple[np.ndarray, np.ndarray]], budgets: dict[str, float]) -> dict[str, float]:
    weeks = sum(t[-1] - t[0] for t, _ in oof) / WEEK_S
    return {b: fit_threshold_bounded(oof, rate * weeks) for b, rate in budgets.items()}


def alarm_flags(s: np.ndarray, thr: float) -> np.ndarray:
    return s > thr


