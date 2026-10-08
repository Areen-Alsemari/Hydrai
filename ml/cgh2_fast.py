"""
CGH2 agent, fast layer (step 2A): severe events on the 1 s layer. Rule-based and physical, so there is nothing to train; the only numbers are
thresholds set from HEALTHY dev 1 s data (the layer is recorded during dispenser fills, compressor transitions and events):

  detector   hydrogen %LFL at/above the alarm (25), or a rise of >= RISE_LFL in 10 s (a leak plume arriving, before the alarm level)
  relief     the PRV state is open (lift)
  collapse   the pressure falls by more than COLLAPSE_MARGIN x the largest healthy 30 s drop (normalised by MOP): a rupture or a large leak
  rupture    collapse AND the detector near saturation: a rupture signature (a dispenser draw never saturates the detector)
  overpressure  pressure at/above PAHH (1.05 x MOP): the one fast event a blocked relief valve produces

Samples whose OPC quality is not Good are ignored (an injected out-of-range spike otherwise looks like a 40 % pressure collapse).

Healthy 1 s data covers fills and bursts only, so false alarms are reported per hour of RECORDED 1 s healthy data, not per week.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np

RISE_LFL = 8.0
RISE_WINDOW_S = 10
COLLAPSE_WINDOW_S = 30
COLLAPSE_MARGIN = 1.5
H2_ALARM_LFL = 25.0
RUPTURE_LFL = 90.0


def read_fast(path: Path) -> dict[str, np.ndarray]:
    t, P, H2, prv = [], [], [], []
    with gzip.open(path, "rt") as f:
        for line in f:
            r = json.loads(line)
            m, q = r["measurements"], r.get("measurement_quality", {})
            t.append(r["system_context"]["t_s"])
            # OPC quality: samples that are not Good (stale, out-of-range, dropout) are ignored, as an operator's alarm logic would
            P.append(m["pressure_bar_a"] if (m["pressure_bar_a"] is not None and q.get("pressure_bar_a", "Good") == "Good") else np.nan)
            H2.append(m["h2_concentration_pct"] if (m["h2_concentration_pct"] is not None and q.get("h2_concentration_pct", "Good") == "Good") else np.nan)
            prv.append(1.0 if m.get("prv_state") == "open" else 0.0)
    return {"t": np.array(t), "P": np.array(P), "H2": np.array(H2), "prv": np.array(prv)}


def drops(d: dict[str, np.ndarray], mop: float, window_s: int = COLLAPSE_WINDOW_S) -> np.ndarray:
    """Pressure fall over the last `window_s` seconds as a fraction of MOP (positive = falling); NaN where there is no contiguous history."""
    t, P = d["t"], d["P"]
    j = np.searchsorted(t, t - window_s, side="left")
    ok = (t - t[j] >= window_s - 1.5) & (t - t[j] <= window_s + 1.5)
    out = np.full(len(t), np.nan)
    out[ok] = (P[j][ok] - P[ok]) / mop
    return out


def rises(d: dict[str, np.ndarray], window_s: int = RISE_WINDOW_S) -> np.ndarray:
    t, H = d["t"], d["H2"]
    j = np.searchsorted(t, t - window_s, side="left")
    ok = (t - t[j] >= window_s - 1.5) & (t - t[j] <= window_s + 1.5)
    out = np.full(len(t), np.nan)
    out[ok] = H[ok] - H[j][ok]
    return out


def healthy_limits(arrays: list[tuple[dict[str, np.ndarray], float]]) -> dict[str, float]:
    """Largest healthy 30 s pressure drop (x MOP) and largest healthy 10 s hydrogen rise over the given healthy 1 s data."""
    md, mr = 0.0, 0.0
    for d, mop in arrays:
        dr, rs = drops(d, mop), rises(d)
        if np.isfinite(dr).any():
            md = max(md, float(np.nanmax(dr)))
        if np.isfinite(rs).any():
            mr = max(mr, float(np.nanmax(rs)))
    return {"max_healthy_drop_frac": md, "max_healthy_h2_rise": mr}


def detect(d: dict[str, np.ndarray], mop: float, lim: dict[str, float], pahh: float | None = None) -> dict[str, np.ndarray]:
    dr, rs = drops(d, mop), rises(d)
    collapse = np.nan_to_num(dr, nan=0.0) > COLLAPSE_MARGIN * lim["max_healthy_drop_frac"]
    return {
        "detector": (d["H2"] >= H2_ALARM_LFL) | (np.nan_to_num(rs, nan=0.0) >= max(RISE_LFL, COLLAPSE_MARGIN * lim["max_healthy_h2_rise"])),
        "relief": d["prv"] > 0.5,
        "collapse": collapse,
        "rupture": collapse & (d["H2"] >= RUPTURE_LFL),
        "overpressure": (np.nan_to_num(d["P"], nan=0.0) >= pahh) if pahh is not None else np.zeros(len(d["t"]), bool),
    }


def first_event(flags: dict[str, np.ndarray], t: np.ndarray, after_s: float) -> tuple[float | None, str | None]:
    best = (None, None)
    for k, f in flags.items():
        idx = np.flatnonzero(f & (t >= after_s))
        if len(idx) and (best[0] is None or t[idx[0]] < best[0]):
            best = (float(t[idx[0]]), k)
    return best
