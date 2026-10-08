"""
Classical baselines to put next to the static alarms (PROVISIONAL: the static alarm limits are the workbook's 'simulation
threshold' values on a reference dashboard, not a verified Saudi system).

  ROC    rate-of-rise alarm on pressure and liquid temperature: OLS slope over a fixed window (2 h, an a-priori choice, not
         tuned), alarm when the slope exceeds a threshold. Rise only: a healthy PCV opening drops pressure by tens of mbar in
         minutes, so a two-sided rate threshold set on healthy data would be blind. Falling pressure (a leak) is NOT seen.
  EWMA   exponentially weighted moving average (lambda = 0.02, a-priori) of a healthy-trained residual; alarm on |z| > threshold
  CUSUM  two-sided CUSUM of the same residual (reference k = 0.5 sigma of the healthy residual); alarm on max(S+, S-) > threshold

Residuals (all healthy-trained, module-relative where a unit baseline is needed; they see the HISTORIAN view, quality Good only):
  pressure     p - median of the unit's own healthy commissioning run (storage phase)
  temperature  T_liq - f(p), f a quadratic fitted on the TRAINING units' healthy storage data (saturation: T follows p), minus the
               unit's commissioning median of that residual
  vacuum       log10(vacuum reading) - the unit's commissioning median (log gauge)

THRESHOLDS ARE SET ON HEALTHY UNITS ONLY, to a fixed false-alarm budget (alarm events per week of healthy exposure, split equally
over the channels a detector uses; events within one hour merge). Healthy units = the training modules' normal episodes and
commissioning runs. Detectors run in the storage phase only (operations are operator-driven transients); samples whose OPC quality
is not Good are replaced by the last good value. Nothing is tuned on fault episodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from scipy.signal import lfilter

from ml.headline_metrics import alarm_events

WEEK_S = 7 * 86400.0
MERGE_GAP_S = 3600.0
ROC_WINDOW = 120            # samples of 60 s = 2 h
EWMA_LAMBDA = 0.02
CUSUM_K_SIGMA = 0.5
CHANNELS = {"pressure": "pressure_bar_a", "temp": "liquid_temp_c", "vac": "vacuum_pressure_pa"}
DETECTORS = {"roc": ("pressure", "temp"), "ewma": ("pressure", "temp", "vac"), "cusum": ("pressure", "temp", "vac")}


@dataclass
class Episode:
    entry: dict[str, Any]
    t: np.ndarray                 # storage-phase times (s)
    full_t: np.ndarray
    storage: np.ndarray           # boolean mask over the full series
    x: dict[str, np.ndarray]      # historian view, good samples forward-filled, storage phase
    has_data_fault: np.ndarray    # full series
    static_flags: np.ndarray | None = None


def _good_ffill(x: np.ndarray, good: np.ndarray) -> np.ndarray:
    if not good.any():
        return np.zeros_like(x)
    idx = np.where(good, np.arange(len(x)), 0)
    first = int(np.flatnonzero(good)[0])
    idx[:first] = first
    return x[np.maximum.accumulate(idx)]


def load_episode(root: Path, entry: dict[str, Any]) -> Episode:
    cols = ["ctx__t_s", "ctx__phase", "label__has_data_fault"]
    names = set(pq.ParquetFile(root / entry["slow_file"]).schema.names)
    for ch in CHANNELS.values():
        cols += [f"meas__{ch}"] + ([f"q__{ch}"] if f"q__{ch}" in names else [])
    if "label__has_data_fault" not in names:
        cols.remove("label__has_data_fault")
    tb = pq.read_table(root / entry["slow_file"], columns=cols).to_pydict()
    t = np.array(tb["ctx__t_s"], dtype=float)
    storage = np.array([p == "storage" for p in tb["ctx__phase"]])
    x = {}
    for k, ch in CHANNELS.items():
        raw = np.array([np.nan if v is None else v for v in tb[f"meas__{ch}"]], dtype=float)
        q = tb.get(f"q__{ch}")
        good = ~np.isnan(raw) & (np.array([v == "Good" for v in q]) if q is not None else True)
        xf = _good_ffill(np.nan_to_num(raw), good)
        x[k] = xf[storage]
    df = np.array(tb["label__has_data_fault"], dtype=bool) if "label__has_data_fault" in tb else np.zeros(len(t), bool)
    return Episode(entry, t[storage], t, storage, x, df)


# -- statistics -----------------------------------------------------------------

def roc_rise(x: np.ndarray, window: int = ROC_WINDOW) -> np.ndarray:
    """OLS slope over the trailing window, per HOUR (samples are 60 s); 0 before the window fills."""
    i = np.arange(window) - (window - 1) / 2.0
    k = i / np.sum(i * i)
    s = np.convolve(x, k[::-1], mode="valid") * 60.0
    return np.concatenate([np.zeros(window - 1), s])


def ewma_abs(r: np.ndarray, lam: float = EWMA_LAMBDA) -> np.ndarray:
    return np.abs(lfilter([lam], [1.0, -(1.0 - lam)], r))


def cusum(r: np.ndarray, k: float) -> np.ndarray:
    sp = sn = 0.0
    out = np.empty(len(r))
    for i, v in enumerate(r):
        sp = max(0.0, sp + v - k)
        sn = max(0.0, sn - v - k)
        out[i] = sp if sp > sn else sn
    return out


# -- residuals ------------------------------------------------------------------

@dataclass
class Residualizer:
    temp_fit: np.ndarray                          # quadratic coefficients T = f(p), fitted on training healthy data

    @classmethod
    def fit(cls, healthy: list[Episode]) -> "Residualizer":
        p = np.concatenate([e.x["pressure"] for e in healthy])
        T = np.concatenate([e.x["temp"] for e in healthy])
        return cls(np.polyfit(p, T, 2))

    def baseline(self, comm: Episode) -> dict[str, float]:
        return {"pressure": float(np.median(comm.x["pressure"])),
                "temp": float(np.median(comm.x["temp"] - np.polyval(self.temp_fit, comm.x["pressure"]))),
                "vac": float(np.median(np.log10(np.clip(comm.x["vac"], 1e-3, None))))}

    def residuals(self, e: Episode, base: dict[str, float]) -> dict[str, np.ndarray]:
        return {"pressure": e.x["pressure"] - base["pressure"],
                "temp": e.x["temp"] - np.polyval(self.temp_fit, e.x["pressure"]) - base["temp"],
                "vac": np.log10(np.clip(e.x["vac"], 1e-3, None)) - base["vac"]}


# -- threshold fitting ------------------------------------------------------------

def count_events(t: np.ndarray, flag: np.ndarray, gap: float = MERGE_GAP_S) -> int:
    """Alarm events (flagged samples closer than `gap` merge) -- vectorized equivalent of headline_metrics.alarm_events."""
    if not flag.any():
        return 0
    last = np.maximum.accumulate(np.where(flag, t, -np.inf))
    prev = np.concatenate([[-np.inf], last[:-1]])
    return int(np.sum(flag & (t - prev > gap)))


def fit_threshold(stats: list[tuple[np.ndarray, np.ndarray]], budget_events: float) -> float:
    """Smallest threshold with at most `budget_events` events summed over the healthy training series [(t, stat), ...]."""
    hi = max(float(s.max()) for _, s in stats) if stats else 0.0
    lo = 0.0
    if sum(count_events(t, s > lo) for t, s in stats) <= budget_events:
        return lo
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if sum(count_events(t, s > mid) for t, s in stats) <= budget_events:
            hi = mid
        else:
            lo = mid
    return hi


def detector_stats(name: str, e: Episode, res: dict[str, np.ndarray], sigma: dict[str, float]) -> dict[str, np.ndarray]:
    """Per-channel statistic for one detector (ROC reads the signal itself; EWMA / CUSUM read the healthy-trained residual)."""
    out = {}
    for ch in DETECTORS[name]:
        if name == "roc":
            out[ch] = roc_rise(e.x[ch])
        elif name == "ewma":
            out[ch] = ewma_abs(res[ch])
        else:
            out[ch] = cusum(res[ch], CUSUM_K_SIGMA * sigma[ch])
    return out


def train(healthy: list[Episode], comm_of: dict[str, Episode], budget_per_week: float) -> dict[str, Any]:
    """Fit residual model, healthy residual sigmas, and the per-channel thresholds of every detector to a fixed false-alarm budget."""
    rz = Residualizer.fit(healthy)
    bases = {m: rz.baseline(c) for m, c in comm_of.items()}
    res = [(e, rz.residuals(e, bases[e.entry["module_id"]])) for e in healthy]
    sigma = {ch: float(np.std(np.concatenate([r[ch] for _, r in res]))) for ch in CHANNELS}
    weeks = sum(e.t[-1] - e.t[0] for e, _ in res) / WEEK_S
    thr: dict[str, dict[str, float]] = {}
    for name, chans in DETECTORS.items():
        per_ch = budget_per_week * weeks / len(chans)
        stats = [(e.t, detector_stats(name, e, r, sigma)) for e, r in res]
        thr[name] = {ch: fit_threshold([(t, s[ch]) for t, s in stats], per_ch) for ch in chans}
    return {"residualizer": rz, "bases": bases, "sigma": sigma, "thr": thr, "train_weeks": weeks}


def detect(model: dict[str, Any], e: Episode, comm: Episode) -> dict[str, np.ndarray]:
    """Per-detector alarm flags over the FULL series (False outside the storage phase)."""
    rz: Residualizer = model["residualizer"]
    base = model["bases"].get(e.entry["module_id"]) or rz.baseline(comm)
    r = rz.residuals(e, base)
    flags = {}
    for name, chans in DETECTORS.items():
        st = detector_stats(name, e, r, model["sigma"])
        f = np.zeros(len(e.t), dtype=bool)
        for ch in chans:
            f |= st[ch] > model["thr"][name][ch]
        full = np.zeros(len(e.full_t), dtype=bool)
        full[e.storage] = f
        flags[name] = full
    return flags
