"""
Causal post-processing: persistence over consecutive windows.

A deployed monitor sees windows one at a time and need not act on a single
one. Two standard, strictly causal devices (each output at window t uses only
windows <= t of the SAME episode -- never future windows, never other
episodes):

  smooth_proba : mean of the last k class-probability vectors, then argmax
                 (Model B).
  persistent_alarm : alarm only if >= m of the last k raw alarms fired
                 (Model A).

Parameters are fixed a priori (k=6 -> 60 s at the 10 s stride for Model B;
3-of-5 for Model A), NOT tuned on LOMO folds. The cost is added latency, so
detection delay is reported alongside (`detection_delays`), and the
"all windows" slice (which includes the ramp-up right after onset) is
reported next to the "settled" one so the lag isn't hidden.

Windows must be ordered by time within each episode (they are: features are
emitted sequentially per episode).
"""

from __future__ import annotations

import numpy as np

LABEL_ORDER = [0, 1, 2, 3, 4, 5, 6, -1]


def _episode_slices(episode_id: np.ndarray):
    """Yield (start, stop) for each contiguous episode run."""
    n = len(episode_id)
    start = 0
    for i in range(1, n + 1):
        if i == n or episode_id[i] != episode_id[start]:
            yield start, i
            start = i


def smooth_proba(proba: np.ndarray, episode_id: np.ndarray, k: int) -> np.ndarray:
    out = np.empty_like(proba)
    for a, b in _episode_slices(episode_id):
        c = np.cumsum(np.vstack([np.zeros((1, proba.shape[1])), proba[a:b]]), axis=0)
        for t in range(b - a):
            lo = max(0, t - k + 1)
            out[a + t] = (c[t + 1] - c[lo]) / (t + 1 - lo)
    return out


def labels_from_proba(proba: np.ndarray) -> np.ndarray:
    return np.array(LABEL_ORDER)[proba.argmax(axis=1)]


def persistent_alarm(alarm: np.ndarray, episode_id: np.ndarray, k: int, m: int) -> np.ndarray:
    out = np.zeros(len(alarm), dtype=bool)
    a_int = alarm.astype(int)
    for a, b in _episode_slices(episode_id):
        c = np.concatenate([[0], np.cumsum(a_int[a:b])])
        for t in range(b - a):
            lo = max(0, t - k + 1)
            out[a + t] = (c[t + 1] - c[lo]) >= m
    return out


def detection_delays(episode_id: np.ndarray, y: np.ndarray, alarm: np.ndarray, stride_s: float) -> dict:
    """Per fault episode: seconds from the first positive-labeled window
    (onset) to the first alarm at or after it. None = never detected."""
    delays, missed = [], 0
    for a, b in _episode_slices(episode_id):
        pos = np.flatnonzero(y[a:b] != 0)
        if len(pos) == 0:
            continue
        onset = pos[0]
        hit = np.flatnonzero(alarm[a:b][onset:])
        if len(hit) == 0:
            missed += 1
        else:
            delays.append(float(hit[0] * stride_s))
    n = len(delays) + missed
    return {
        "n_fault_episodes": n,
        "detected_fraction": len(delays) / n if n else None,
        "median_delay_s": float(np.median(delays)) if delays else None,
        "p90_delay_s": float(np.percentile(delays, 90)) if delays else None,
    }
