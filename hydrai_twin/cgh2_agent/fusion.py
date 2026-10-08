"""Fusion of tool outputs: a small multiclass meta-model on the tools' monitor features (trained on dev tool outputs only), 15-minute smoothing, and
alert tiers whose thresholds come from HEALTHY out-of-fold scores at fixed false-alarm budgets.

Labels (training only): healthy = 0 before onset and in normal episodes; the fault class from the first OBSERVABLE deviation on (the paired-twin time is a
training label, never a feature); the gap between onset and first observable and any unobservable stretch is ignored; composite (unknown) episodes are
not trained on so they can test open-set rejection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from hydrai_twin.cgh2_agent.features import FEATURES, WARMUP
from ml.cgh2_baselines import fit_threshold_bounded

CLASSES = np.arange(7)
STRIDE = 5
SMOOTH = 15
HGB = dict(max_iter=120, learning_rate=0.1, max_depth=5, min_samples_leaf=50, l2_regularization=1.0, random_state=0)
WEEK_S = 7 * 86400.0
BUDGETS = {"watch": 7.0, "alert": 1.0, "alert_4wk": 0.25}          # healthy false events per week: watch 1/day, alert 1/week (and 1 per 4 weeks, reported)
CACHE = Path(__file__).resolve().parents[2] / "output" / "cgh2_cache" / "agent"


@dataclass
class FUnit:
    entry: dict[str, Any]
    t: np.ndarray
    X: np.ndarray


def load_funit(entry: dict[str, Any]) -> FUnit:
    z = np.load(CACHE / f"feat_{entry['name']}.npz")
    return FUnit(entry, z["t"], z["X"])


def row_labels(e: FUnit) -> np.ndarray:
    """0 healthy, 1..6 fault class from the first observable deviation, -1 ignored, -2 excluded episode (composite)."""
    ent = e.entry
    y = np.zeros(len(e.t), dtype=int)
    fid = ent["fault_id"]
    if fid == 0:
        return y
    if fid < 0:
        return np.full(len(e.t), -2)
    y[e.t >= ent["onset_s"]] = -1
    if ent["first_observable_s"] is not None:
        y[e.t >= ent["first_observable_s"]] = fid
    return y


def is_calibration(e: FUnit) -> bool:
    ent = e.entry
    return ent["fault_id"] == 0 and ent["scenario_class"] == "standard" and "dark" not in ent["variant_tag"] and ent["role"] == "dev"


def train_meta(units: list[FUnit], stride: int = STRIDE) -> HistGradientBoostingClassifier:
    Xs, ys = [], []
    for e in units:
        y = row_labels(e)
        idx = np.arange(WARMUP, len(e.t), stride)
        idx = idx[y[idx] >= 0]
        Xs.append(e.X[idx]); ys.append(y[idx])
    X, y = np.vstack(Xs), np.concatenate(ys)
    cnt = np.bincount(y, minlength=7).astype(float)
    # class weights: healthy keeps weight 1; each fault class is up-weighted towards (but not past) the healthy count / 20
    w_cls = np.where(cnt > 0, np.minimum(cnt[0] / np.maximum(cnt, 1.0), 20.0), 1.0)
    w_cls[0] = 1.0
    m = HistGradientBoostingClassifier(**HGB)
    m.fit(X, y, sample_weight=w_cls[y])
    return m


def smooth(a: np.ndarray, w: int = SMOOTH) -> np.ndarray:
    c = np.concatenate([np.zeros((1,) + a.shape[1:]), np.cumsum(a, axis=0)])
    out = np.empty_like(a, dtype=float)
    n = len(a)
    k = np.arange(n)
    lo = np.maximum(k - w + 1, 0)
    out = (c[k + 1] - c[lo]) / (k + 1 - lo).reshape((-1,) + (1,) * (a.ndim - 1))
    return out


def probs(model: HistGradientBoostingClassifier, e: FUnit) -> np.ndarray:
    """(n, 7) class probabilities, 15-minute causal mean; healthy=1 during the warm-up."""
    n = len(e.t)
    P = np.zeros((n, 7))
    P[:, 0] = 1.0
    raw = model.predict_proba(e.X[WARMUP:])
    full = np.zeros((n - WARMUP, 7))
    full[:, model.classes_] = raw
    P[WARMUP:] = full
    S = smooth(P)
    S[:WARMUP] = 0.0
    S[:WARMUP, 0] = 1.0
    return S


def score_from_probs(P: np.ndarray) -> np.ndarray:
    return 1.0 - P[:, 0]


def oof_healthy(units: list[FUnit], modules: list[str], stride: int = STRIDE) -> list[tuple[np.ndarray, np.ndarray]]:
    """Out-of-fold anomaly scores of the healthy calibration episodes of `modules`: each module scored by a model trained on the others."""
    out = []
    for m_out in modules:
        model = train_meta([e for e in units if e.entry["module_id"] != m_out and e.entry["role"] == "dev"], stride)
        for e in units:
            if e.entry["module_id"] == m_out and is_calibration(e):
                out.append((e.t[WARMUP:], score_from_probs(probs(model, e))[WARMUP:]))
    return out


def thresholds_from(oof: list[tuple[np.ndarray, np.ndarray]]) -> dict[str, float]:
    weeks = sum(t[-1] - t[0] for t, _ in oof) / WEEK_S
    return {k: fit_threshold_bounded(oof, rate * weeks) for k, rate in BUDGETS.items()}


def raw_probs(model: HistGradientBoostingClassifier, e: FUnit, k: int = 3) -> np.ndarray:
    """(n, 7) class probabilities with only a k-sample (k-minute) causal mean: the instantaneous picture used at fast triggers (static alarm, pressure collapse),
    where the 15-minute smoothing would still be dominated by the quiet period before the event."""
    n = len(e.t)
    P = np.zeros((n, 7))
    P[:, 0] = 1.0
    raw = model.predict_proba(e.X[WARMUP:])
    full = np.zeros((n - WARMUP, 7))
    full[:, model.classes_] = raw
    P[WARMUP:] = full
    S = smooth(P, k)
    S[:WARMUP] = 0.0
    S[:WARMUP, 0] = 1.0
    return S
