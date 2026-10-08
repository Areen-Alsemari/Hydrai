"""
Window-level feature extraction for the Model A / Model B baselines.

Leakage rule: features are computed ONLY from `measurements` (the noisy
sensor readings a deployed monitor would see) plus the operating phase
(filling/idle/discharge -- valve/mode state a real system knows). Nothing
from `simulation_ground_truth`, `labels`, `fault_severity`, `variant_tag`,
or timestamps-since-onset is ever used as a feature; those are kept only as
evaluation metadata. tests/test_ml.py enforces this.

Windows: trailing window of WINDOW_S seconds, emitted every STRIDE_S
seconds. A second, longer trailing window (LONG_WINDOW_S, truncated at the
start of an episode -- strictly causal, never looks ahead) adds slow-trend
context, and `recent_delta` = short-window mean minus long-window mean is a
self-referential "what changed recently" feature that needs no external
baseline. The label of a window is the ai_label at its LAST tick (what the
system would be asked "is something wrong right now?"). Because the
generators flip the label at onset while severity is still ~0, windows
ending shortly after onset are labeled positive but nearly
indistinguishable from normal -- evaluation therefore also reports a
"settled" slice (severity >= 95% of the episode's own max).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from hydrai_twin import constants as C

WINDOW_S = 120.0
LONG_WINDOW_S = 600.0
STRIDE_S = 10.0
CHANNELS = list(C.SENSOR_SPECS.keys())
PHASES = ("filling", "idle", "discharge")
LABEL_ORDER = [0, 1, 2, 3, 4, 5, 6, -1]

# kg of LH2 per 1% of liquid level, from Sec.2 volume and Sec.3 density at
# NBP; used only for the inventory-residual feature below.
KG_PER_LEVEL_PCT = C.TANK_INTERNAL_VOLUME_M3 * 70.97 / 100.0

_SHORT_STATS = ("mean", "std", "slope", "last")
_LONG_STATS = ("mean", "std", "slope")
FEATURE_NAMES = (
    [f"{ch}__{s}" for s in _SHORT_STATS for ch in CHANNELS]
    + ["inventory_residual_kg_s"]
    + [f"{ch}__long_{s}" for s in _LONG_STATS for ch in CHANNELS]
    + ["inventory_residual_long_kg_s"]
    + [f"{ch}__recent_delta" for ch in CHANNELS]
    + [f"phase__{p}" for p in PHASES]
)
N_SHORT = len(_SHORT_STATS) * len(CHANNELS) + 1  # short-window block incl. inventory residual


def _mean_std_slope(win: np.ndarray, dt_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = win.shape[0]
    t = (np.arange(n) - (n - 1) / 2.0) * dt_s
    mean = win.mean(axis=0)
    std = win.std(axis=0)
    denom = (t**2).sum()
    slope = (t[:, None] * (win - mean)).sum(axis=0) / denom if denom > 0 else np.zeros_like(mean)
    return mean, std, slope


def _inventory_residual(mean: np.ndarray, slope: np.ndarray) -> float:
    i_level = CHANNELS.index("liquid_level_pct")
    i_fill = CHANNELS.index("mass_flow_fill_kg_s")
    i_dis = CHANNELS.index("mass_flow_discharge_kg_s")
    # Measured inventory change vs. measured net flow (Sec.7 mass balance:
    # dM/dt = mdot_in - mdot_out - mdot_BOG). A persistent nonzero residual
    # is the classic leak signature; per-tick sensor noise makes it small
    # relative to noise for small leaks, which is realistic.
    return slope[i_level] * KG_PER_LEVEL_PCT - (mean[i_fill] - mean[i_dis])


def window_features(win: np.ndarray, dt_s: float, phase_onehot: np.ndarray, long_win: np.ndarray | None = None) -> np.ndarray:
    """win: (n_ticks, n_channels) short trailing window of measurements;
    long_win: longer trailing window ending at the same tick (defaults to
    `win`). Returns one feature row ordered as FEATURE_NAMES."""
    long_win = win if long_win is None else long_win
    mean, std, slope = _mean_std_slope(win, dt_s)
    lmean, lstd, lslope = _mean_std_slope(long_win, dt_s)
    return np.concatenate([
        mean, std, slope, win[-1], [_inventory_residual(mean, slope)],
        lmean, lstd, lslope, [_inventory_residual(lmean, lslope)],
        mean - lmean,
        phase_onehot,
    ]).astype(np.float32)


def _iter_episodes(path: Path) -> Iterator[list[dict]]:
    current_id, buf = None, []
    with path.open() as f:
        for line in f:
            r = json.loads(line)
            if r["episode_id"] != current_id and buf:
                yield buf
                buf = []
            current_id = r["episode_id"]
            buf.append(r)
    if buf:
        yield buf


def episode_windows(
    records: list[dict], window_s: float = WINDOW_S, stride_s: float = STRIDE_S, long_window_s: float = LONG_WINDOW_S
) -> dict:
    """Turn one episode (list of records) into stacked window features + metadata."""
    t0 = datetime.fromisoformat(records[0]["timestamp"])
    t1 = datetime.fromisoformat(records[1]["timestamp"])
    dt = (t1 - t0).total_seconds()
    n_win = max(2, int(round(window_s / dt)))
    n_long = max(n_win, int(round(long_window_s / dt)))
    stride = max(1, int(round(stride_s / dt)))

    x = np.array([[r["measurements"][ch] for ch in CHANNELS] for r in records], dtype=np.float64)
    phase_idx = np.array([PHASES.index(r["system_context"]["phase"]) for r in records])
    labels = np.array([r["labels"]["ai_label"] for r in records])
    sev = np.array([r["system_context"].get("fault_severity", 0.0) for r in records])
    ep_max = sev.max() if sev.max() > 0 else 1.0

    if len(records) < n_win:
        return {}
    wins = sliding_window_view(x, n_win, axis=0)  # (T-n+1, n_ch, n_win)
    ends = np.arange(n_win - 1, len(records), stride)

    feats = []
    for end in ends:
        w = wins[end - n_win + 1].T  # (n_win, n_ch)
        lw = x[max(0, end - n_long + 1): end + 1]  # causal, truncated at episode start
        feats.append(window_features(w, dt, np.eye(len(PHASES))[phase_idx[end]], lw))

    ctx = records[0]["system_context"]
    k = len(ends)
    return {
        "X": np.stack(feats),
        "y": labels[ends],
        "severity": sev[ends],
        "sev_frac": sev[ends] / ep_max,
        "phase": np.array([PHASES[i] for i in phase_idx[ends]]),
        "episode_id": np.array([records[0]["episode_id"]] * k),
        "module": np.array([ctx["module_id"]] * k),
        "scenario": np.array([ctx["scenario"]] * k),
        "variant": np.array([ctx.get("variant_tag", "default")] * k),
    }


def build_feature_set(jsonl_path: Path, cache_path: Path | None = None) -> dict:
    """Stream a dataset JSONL into window features. Cached to .npz since
    re-parsing hundreds of MB of JSON dominates runtime."""
    if cache_path is not None and cache_path.exists() and cache_path.stat().st_mtime >= jsonl_path.stat().st_mtime:
        with np.load(cache_path, allow_pickle=False) as z:
            cached = {k: z[k] for k in z.files}
        # reject caches written under an older feature schema (different columns)
        if cached["X"].shape[1] == len(FEATURE_NAMES):
            return cached

    parts = [p for p in (episode_windows(ep) for ep in _iter_episodes(jsonl_path)) if p]
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path, **out)
    return out
