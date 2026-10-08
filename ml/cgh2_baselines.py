"""
Classical baselines for the CGH2 twin, next to the static alarms (PROVISIONAL: PAH 1.02 / PAHH 1.05 x MOP, gas temperature 85/100 C and
hydrogen 25/50 %LFL are reference-configuration limits). Same protocol as ml/classical_baselines.py: thresholds on HEALTHY units only to
a fixed false-alarm budget (alarm events per week, merged within 1 h), leave-one-module-out on the dev modules, one shot on the unseen
units, historian view, OPC Good samples only, nothing tuned on fault episodes.

Detectors (all read only dashboard tags):
  ROC     |2 h rate of change| of pressure and of gas temperature (two-sided: a healthy compressor charge or dispenser draw is a large
          rate of either sign, so the threshold sits above them)
  EWMA    exponentially weighted average (lambda 0.02) of healthy-trained residuals, alarm on |z|
  CUSUM   two-sided CUSUM (k = 0.5 sigma of the healthy residual) of the same residuals
            r_Pc  temperature-compensated pressure (the pressure the same gas would have at 50 C) minus the unit's commissioning median
            r_T   gas temperature minus a healthy-trained regression on shell temperature, ambient temperature and compressor status,
                  minus the unit's commissioning median of that residual
  Thresholds: the smallest value with (a) at most budget/channels false-alarm EVENTS per week of healthy exposure and (b) the alarm on for at most
  2 % of the healthy time, searched for (a) above the floor from (b) (an always-on alarm is one merged event and would otherwise pass (a)).
  INV     temperature-compensated inventory residual: during HOLD (compressor stopped, no gas drawn, for the last 2 h) the slope of the
          real-gas inventory rho(P, T) x V is a leak-rate estimate (kg/h); CUSUM of it after removing the unit's commissioning median
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from hydrai_twin.cgh2 import gas as G
from ml.classical_baselines import (CUSUM_K_SIGMA, EWMA_LAMBDA, MERGE_GAP_S, WEEK_S, cusum, count_events, ewma_abs, roc_rise, _good_ffill)

T_REF_C = 50.0
MAX_ON_FRACTION = 0.02                 # a healthy-trained alarm may be ON at most 2 % of the healthy time (JUDGE): see fit below
HOLD_WINDOW = 120                      # samples (2 h) the inventory slope is computed over
FLOW_ZERO = 0.004                      # kg/s... overwritten below from the meters' noise floor
DETECTORS = {"roc": ("P", "T"), "ewma": ("Pc", "T_res"), "cusum": ("Pc", "T_res"), "inv": ("inv",)}
CH = {"P": "pressure_bar_a", "T": "gas_temp_c", "Tw": "outer_wall_temp_c", "Ta": "ambient_temp_c", "fill": "mass_flow_fill_kg_s", "disc": "mass_flow_discharge_kg_s"}


@dataclass
class Episode:
    entry: dict[str, Any]
    t: np.ndarray
    x: dict[str, np.ndarray]            # historian view (Good samples, forward-filled)
    status_run: np.ndarray
    has_data_fault: np.ndarray
    volume_m3: float
    static_flags: np.ndarray | None = None
    inv: np.ndarray | None = None       # real-gas inventory from the MEASURED P and T (kg)
    pc: np.ndarray | None = None        # temperature-compensated pressure (bar)


def load_episode(root: Path, entry: dict[str, Any], volume_m3: float = 10.0) -> Episode:
    names = set(pq.ParquetFile(root / entry["slow_file"]).schema.names)
    cols = ["ctx__t_s", "label__has_data_fault"] + [f"meas__{c}" for c in CH.values()] + [f"q__{c}" for c in CH.values() if f"q__{c}" in names]
    status = "meas__compressor_status"
    if status in names:
        cols.append(status)
    tb = pq.read_table(root / entry["slow_file"], columns=cols).to_pydict()
    t = np.array(tb["ctx__t_s"], dtype=float)
    x = {}
    for k, ch in CH.items():
        raw = np.array([np.nan if v is None else v for v in tb[f"meas__{ch}"]], dtype=float)
        q = tb.get(f"q__{ch}")
        good = ~np.isnan(raw) & (np.array([v == "Good" for v in q]) if q is not None else True)
        x[k] = _good_ffill(np.nan_to_num(raw), good)
    run = np.array([v == "run" for v in tb[status]]) if status in tb else np.zeros(len(t), bool)
    ep = Episode(entry, t, x, run, np.array(tb["label__has_data_fault"], dtype=bool), volume_m3)
    rho = G.rho_PT(np.clip(x["P"], 1.0, None), x["T"] + 273.15)
    ep.inv = rho * volume_m3
    ep.pc = np.asarray(G.pressure_bar(rho, T_REF_C + 273.15))
    return ep


def hold_slope(e: Episode) -> np.ndarray:
    """Inventory slope (kg/h) over the trailing 2 h where the compressor was stopped and no gas drawn the whole time; 0 elsewhere."""
    n = len(e.t)
    quiet = (~e.status_run) & (e.x["disc"] < 0.0005) & (e.x["fill"] < 0.0005)          # kg/s: the meters' noise floor is ~1.5e-4 kg/s
    ok = np.convolve(quiet.astype(int), np.ones(HOLD_WINDOW, int), mode="full")[:n] >= HOLD_WINDOW
    s = roc_rise(e.inv, HOLD_WINDOW)                                                     # per hour
    return np.where(ok, s, 0.0)


def fit_threshold_bounded(series: list[tuple[np.ndarray, np.ndarray]], budget_events: float, max_on_fraction: float = MAX_ON_FRACTION) -> float:
    """Smallest threshold with (a) at most `budget_events` alarm events over the healthy series and (b) the alarm on for at most `max_on_fraction`
    of the time. Searching (a) ABOVE the floor from (b) matters: an event count alone is degenerate, because a statistic that is always above its
    threshold merges into one event per episode and passes any budget (the shared fit returned 0.0 for ROC-pressure and EWMA)."""
    floor = float(np.quantile(np.concatenate([s for _, s in series]), 1.0 - max_on_fraction))
    hi = max(float(s.max()) for _, s in series)
    if sum(count_events(t, s > floor) for t, s in series) <= budget_events:
        return floor
    lo = floor
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if sum(count_events(t, s > mid) for t, s in series) <= budget_events:
            hi = mid
        else:
            lo = mid
    return hi


@dataclass
class Model:
    temp_coef: np.ndarray
    bases: dict[str, dict[str, float]]
    sigma: dict[str, float]
    thr: dict[str, dict[str, float]]
    train_weeks: float


def _design(e: Episode) -> np.ndarray:
    return np.column_stack([np.ones(len(e.t)), e.x["Tw"], e.x["Ta"], e.status_run.astype(float)])


def residuals(e: Episode, coef: np.ndarray, base: dict[str, float]) -> dict[str, np.ndarray]:
    return {"Pc": e.pc - base["Pc"], "T_res": e.x["T"] - _design(e) @ coef - base["T_res"], "inv": hold_slope(e) - base["inv"]}


def base_of(e: Episode, coef: np.ndarray) -> dict[str, float]:
    hs = hold_slope(e)
    valid = hs != 0.0
    return {"Pc": float(np.median(e.pc)), "T_res": float(np.median(e.x["T"] - _design(e) @ coef)), "inv": float(np.median(hs[valid])) if valid.any() else 0.0}


def stats(name: str, e: Episode, res: dict[str, np.ndarray], sigma: dict[str, float]) -> dict[str, np.ndarray]:
    out = {}
    for ch in DETECTORS[name]:
        if name == "roc":
            out[ch] = np.abs(roc_rise(e.x[ch]))
        elif name == "ewma":
            out[ch] = ewma_abs(res[ch])
        else:
            out[ch] = cusum(res[ch], CUSUM_K_SIGMA * sigma[ch])
    return out


def train(healthy: list[Episode], comm_of: dict[str, Episode], budget_per_week: float) -> Model:
    X = np.vstack([_design(e) for e in healthy])
    y = np.concatenate([e.x["T"] for e in healthy])
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    bases = {m: base_of(c, coef) for m, c in comm_of.items()}
    res = [(e, residuals(e, coef, bases[e.entry["module_id"]])) for e in healthy]
    sigma = {ch: float(np.std(np.concatenate([r[ch] for _, r in res]))) or 1.0 for ch in ("Pc", "T_res", "inv")}
    weeks = sum(e.t[-1] - e.t[0] for e, _ in res) / WEEK_S
    thr: dict[str, dict[str, float]] = {}
    for name, chans in DETECTORS.items():
        per = budget_per_week * weeks / len(chans)
        st = [(e.t, stats(name, e, r, sigma)) for e, r in res]
        thr[name] = {}
        for ch in chans:
            series = [(t, s[ch]) for t, s in st]
            thr[name][ch] = fit_threshold_bounded(series, per)
    return Model(coef, bases, sigma, thr, weeks)


def detect(model: Model, e: Episode, comm: Episode) -> dict[str, np.ndarray]:
    base = model.bases.get(e.entry["module_id"]) or base_of(comm, model.temp_coef)
    r = residuals(e, model.temp_coef, base)
    out = {}
    for name, chans in DETECTORS.items():
        st = stats(name, e, r, model.sigma)
        f = np.zeros(len(e.t), dtype=bool)
        for ch in chans:
            f |= st[ch] > model.thr[name][ch]
        out[name] = f
    return out
