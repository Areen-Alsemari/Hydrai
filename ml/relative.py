"""
Module-relative features.

Problem this solves: absolute sensor levels differ between physical units
(calibration bias, PCV setpoint, insulation quality, site, ...), so a model
trained on absolute levels from some units misreads a new unit's healthy
baseline as a fault (observed: a held-out module's normal strain level sat
outside the training modules' range and was classified "structural concern").

What a real deployment can do about it: every unit has a healthy
commissioning run. We summarize that run's window features per operating
phase and express later windows relative to it:

    mean / last / slope / inventory features :  x - baseline[unit, phase]
    std features                             :  log((x + eps) / (baseline + eps))
    recent_delta, phase one-hots             :  unchanged (already relative / categorical)

No-cheating constraints (enforced by tests/test_relative.py):
  * the baseline for a unit comes ONLY from that unit's commissioning run
    (a separate, known-healthy episode that is never part of train/test);
  * no labels are ever passed in or used -- "healthy" is a property of the
    commissioning run, not something inferred from evaluation labels;
  * nothing about a unit's evaluation windows (their mean, scale, etc.) is
    used to normalize them -- that would be transductive leakage;
  * transforms are per-unit, so fitting one unit's baseline cannot leak
    information from another (train vs. held-out) unit.

Assumption this makes explicit: a healthy commissioning run exists for each
unit. Results are conditional on that; a unit that was already degraded at
commissioning would be baselined against its degraded state.
"""

from __future__ import annotations

import numpy as np

from ml.features import FEATURE_NAMES, N_SHORT, PHASES

LOG_EPS = 1e-4

FEATURE_SETS = ("absolute", "relative", "relative_multi")


def _kind(name: str) -> str:
    if name.startswith("phase__") or name.endswith("__recent_delta"):
        return "pass"
    if name.endswith("__std") or name.endswith("__long_std"):
        return "logratio"
    return "diff"


KINDS = np.array([_kind(n) for n in FEATURE_NAMES])
DIFF = KINDS == "diff"
LOGRATIO = KINDS == "logratio"

_PHASE_COLS = [FEATURE_NAMES.index(f"phase__{p}") for p in PHASES]
_SHORT_COLS = list(range(N_SHORT)) + _PHASE_COLS   # the original 48-feature set


def columns_for(feature_set: str) -> list[int]:
    if feature_set in ("absolute", "relative"):
        return _SHORT_COLS
    if feature_set == "relative_multi":
        return list(range(len(FEATURE_NAMES)))
    raise ValueError(f"unknown feature set {feature_set!r}; expected one of {FEATURE_SETS}")


def names_for(feature_set: str) -> list[str]:
    return [FEATURE_NAMES[i] for i in columns_for(feature_set)]


class ModuleBaselines:
    """Per-unit, per-phase mean of window features over that unit's healthy
    commissioning run."""

    def __init__(self) -> None:
        self.base_: dict[str, dict[str, np.ndarray]] = {}

    def fit(self, X: np.ndarray, module: np.ndarray, phase: np.ndarray) -> "ModuleBaselines":
        for m in np.unique(module):
            sel = module == m
            overall = X[sel].mean(axis=0)
            self.base_[str(m)] = {"*": overall}
            for p in PHASES:
                ps = sel & (phase == p)
                self.base_[str(m)][p] = X[ps].mean(axis=0) if ps.any() else overall
        return self

    def transform(self, X: np.ndarray, module: np.ndarray, phase: np.ndarray) -> np.ndarray:
        out = np.array(X, dtype=np.float64, copy=True)
        for m in np.unique(module):
            if str(m) not in self.base_:
                raise KeyError(f"no commissioning baseline for module {m!r}")
            for p in np.unique(phase[module == m]):
                sel = (module == m) & (phase == p)
                b = self.base_[str(m)].get(str(p), self.base_[str(m)]["*"])
                out[np.ix_(sel, DIFF)] = X[np.ix_(sel, DIFF)] - b[DIFF]
                out[np.ix_(sel, LOGRATIO)] = np.log((X[np.ix_(sel, LOGRATIO)] + LOG_EPS) / (b[LOGRATIO] + LOG_EPS))
        return out.astype(np.float32)


def prepare(feats: dict, baselines: ModuleBaselines | None, feature_set: str) -> tuple[np.ndarray, list[str]]:
    """Return (X, feature_names) for `feats` under `feature_set`."""
    cols = columns_for(feature_set)
    X = feats["X"]
    if feature_set != "absolute":
        if baselines is None:
            raise ValueError("relative feature sets need ModuleBaselines")
        X = baselines.transform(X, feats["module"], feats["phase"])
    return X[:, cols], [FEATURE_NAMES[i] for i in cols]
