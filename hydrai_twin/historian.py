"""
Historian realism: what an agent on a PI-style historian side channel sees (reference configuration, not a verified
Saudi system). Default ON in the dataset driver; OFF (`HistorianConfig(enabled=False)`) returns the records untouched,
i.e. the ideal instrument view.

Signal path, per dashboard tag, applied to each data layer (slow 60 s / fast 1 s) as its own time series:

  live DCS value (static alarms act on this)                      -> stored as `measurements_live`
  1. injected data faults (side-channel artifacts, LABELLED):
       dropout       value missing (None), OPC quality Bad
       stale_value   last value repeated, quality Uncertain
       flat_line     sensor output stuck, quality still Good (silent)
       out_of_range  value beyond the instrument range, quality Uncertain
  2. exception filter   pass a value only if it moved more than a deadband (0.1-0.5 % of span, per channel) or 600 s passed
  3. swinging-door compression   archive points only when a straight line can no longer stay within the compression
                                 deviation (= 2 x the exception deadband, placeholder); forced point every 8 h
  4. retrieval          linear interpolation between archived points back onto the sample grid. The archive keeps the last RAW
                        point before the door closes (PI style), so at a corner the reconstruction can overshoot the compression
                        deviation, by up to about twice it; this is how such historians behave, not a bug
  -> `measurements` (what the agent sees) + `measurement_quality` (OPC Good / Uncertain / Bad per tag)

LABELS. `data_faults` = {tag: fault type | "none"} per sample and `labels["has_data_fault"]`. They are evaluation labels,
NEVER physical anomalies: `ai_label` / `ai_label_observable` are untouched, and the headline metrics count an alarm that
starts inside a data fault separately (ml/headline_metrics.py).

Log-scale channels (the vacuum gauge) filter and compress in log10 space with the deadband taken as a percentage of the
span in decades; a linear deadband would erase a 0.3-2 Pa reading.

Every rate and deadband here is a placeholder (placeholders.py: historian_*, question Q10).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hydrai_twin import placeholders as PH
from hydrai_twin.seeding import stable_seed

FAULT_TYPES = ("dropout", "stale_value", "flat_line", "out_of_range")
QUALITY_OF_FAULT = {"dropout": "Bad", "stale_value": "Uncertain", "flat_line": "Good", "out_of_range": "Uncertain"}
NO_FAULT = "none"
MIN_WINDOW_S = 60.0     # the slow layer logs every 60 s: a shorter window would be invisible there and visible in the 1 s layer
DISCRETE_TAGS = ("pcv_state", "prv_state")

# exception deadband, % of span, inside the reference config's 0.1-0.5 %. Chosen per channel; placeholders (Q10).
DEFAULT_DEADBAND_PCT = {
    "pressure_bar_a": 0.1, "liquid_temp_c": 0.1, "inner_wall_temp_c": 0.2, "outer_wall_temp_c": 0.2,
    "h2_concentration_pct": 0.5, "liquid_level_pct": 0.1, "mass_flow_fill_kg_s": 0.2, "mass_flow_discharge_kg_s": 0.2,
    "strain_ue": 0.2, "vacuum_pressure_pa": 0.5, "ambient_temp_c": 0.2,
}


@dataclass(frozen=True)
class TagInfo:
    channel: str
    lo: float
    hi: float
    log: bool = False

    @property
    def span(self) -> float:
        return float(np.log10(self.hi / self.lo)) if self.log else self.hi - self.lo


@dataclass(frozen=True)
class HistorianConfig:
    enabled: bool = True
    deadband_pct_span: dict = field(default_factory=lambda: dict(DEFAULT_DEADBAND_PCT))
    exception_forced_s: float = 600.0
    compression: bool = True
    compdev_mult: float = 2.0
    compression_forced_s: float = 28800.0
    fault_rates: dict = field(default_factory=lambda: {
        "dropout": (0.2, 300.0), "stale_value": (0.1, 900.0), "flat_line": (0.05, 7200.0), "out_of_range": (0.05, 120.0)})   # (events/day/tag, mean seconds)
    inject_faults: bool = True

    @classmethod
    def from_registry(cls, **kw: Any) -> "HistorianConfig":
        """Defaults read from the placeholder registry (marks them used in the manifest)."""
        return cls(exception_forced_s=PH.value("historian_exception_forced_s"), compdev_mult=PH.value("historian_compdev_mult"),
                   compression_forced_s=PH.value("historian_compression_forced_s"),
                   fault_rates={"dropout": (PH.value("historian_fault_dropout_per_day"), 300.0),
                                "stale_value": (PH.value("historian_fault_stale_per_day"), 900.0),
                                "flat_line": (PH.value("historian_fault_flatline_per_day"), 7200.0),
                                "out_of_range": (PH.value("historian_fault_outofrange_per_day"), 120.0)}, **kw)

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "exception_deadband_pct_span": dict(self.deadband_pct_span),
                "exception_forced_point_s": self.exception_forced_s, "compression": "swinging_door" if self.compression else "none",
                "compression_deviation_mult_of_exception_deadband": self.compdev_mult,
                "compression_forced_point_s": self.compression_forced_s, "inject_faults": self.inject_faults,
                "injected_fault_rates_per_day_and_mean_s": {k: list(v) for k, v in self.fault_rates.items()},
                "opc_quality_of_fault": QUALITY_OF_FAULT,
                "level": "reference configuration (STD) for the filters; deadbands per channel, compdev and fault rates are placeholders (Q10)"}


# -- fault schedule -------------------------------------------------------------

def fault_windows(seed: int, tag: str, horizon_s: float, cfg: HistorianConfig) -> list[tuple[float, float, str]]:
    """Seeded (start, end, type) windows for one tag over [0, horizon_s). Independent of the data layer, so the slow and
    fast layers see the same faults."""
    if not cfg.inject_faults or horizon_s <= 0:
        return []
    rng = np.random.default_rng(stable_seed(seed, "historian-faults", tag))
    out: list[tuple[float, float, str]] = []
    for ftype in FAULT_TYPES:
        per_day, mean_s = cfg.fault_rates[ftype]
        n = rng.poisson(per_day * horizon_s / 86400.0)
        for _ in range(n):
            start = float(rng.uniform(0.0, horizon_s))
            dur = float(max(MIN_WINDOW_S, rng.exponential(mean_s)))
            out.append((start, min(start + dur, horizon_s), ftype))
    return sorted(out)


# -- filters --------------------------------------------------------------------

def exception_filter(t: np.ndarray, x: np.ndarray, valid: np.ndarray, deadband: float, forced_s: float) -> np.ndarray:
    """Indices (into t/x) of the values the exception filter passes."""
    idx = np.flatnonzero(valid)
    if len(idx) == 0:
        return idx
    passed = [idx[0]]
    last_v, last_t = x[idx[0]], t[idx[0]]
    for i in idx[1:]:
        if abs(x[i] - last_v) > deadband or t[i] - last_t >= forced_s:
            passed.append(i)
            last_v, last_t = x[i], t[i]
    return np.array(passed, dtype=int)


def swinging_door(t: np.ndarray, x: np.ndarray, dev: float, forced_s: float) -> np.ndarray:
    """Indices of the points a swinging-door archive keeps: a point is archived when no straight line from the last
    archived point can stay within +/-dev of every point since; a point is also archived `forced_s` after the last one."""
    n = len(t)
    if n <= 2:
        return np.arange(n)
    keep = [0]
    a = 0
    lo_b, hi_b = -np.inf, np.inf
    i = 1
    while i < n:
        dt = t[i] - t[a]
        if dt >= forced_s:
            keep.append(i)
            a, lo_b, hi_b = i, -np.inf, np.inf
            i += 1
            continue
        lo = (x[i] - dev - x[a]) / dt
        hi = (x[i] + dev - x[a]) / dt
        lo2, hi2 = max(lo_b, lo), min(hi_b, hi)
        if lo2 > hi2:
            keep.append(i - 1)
            a, lo_b, hi_b = i - 1, -np.inf, np.inf
            continue
        lo_b, hi_b = lo2, hi2
        i += 1
    if keep[-1] != n - 1:
        keep.append(n - 1)
    return np.array(keep, dtype=int)


def _compress_series(t: np.ndarray, x: np.ndarray, valid: np.ndarray, info: TagInfo, deadband_pct: float, cfg: HistorianConfig):
    """Exception filter + swinging door on one tag's series; returns (reconstructed x, n_valid, n_passed, n_archived)."""
    xv = x.copy()
    if info.log:
        xv = np.log10(np.clip(xv, info.lo * 1e-3, None))
    db = deadband_pct / 100.0 * info.span
    passed = exception_filter(t, xv, valid, db, cfg.exception_forced_s)
    if len(passed) == 0:
        return x, int(valid.sum()), 0, 0
    arch = passed[swinging_door(t[passed], xv[passed], cfg.compdev_mult * db, cfg.compression_forced_s)] if cfg.compression else passed
    rec = np.full(len(x), np.nan)
    vidx = np.flatnonzero(valid)
    rec[vidx] = np.interp(t[vidx], t[arch], xv[arch])
    if info.log:
        rec = 10.0 ** rec
    return rec, int(valid.sum()), int(len(passed)), int(len(arch))


# -- public ---------------------------------------------------------------------

def apply_historian(
    records: list[dict[str, Any]],
    cfg: HistorianConfig,
    seed: int,
    tags: dict[str, TagInfo],
    horizon_s: float,
    layer_dt_s: float = 60.0,
    discrete_tags: tuple[str, ...] = DISCRETE_TAGS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (records as the historian serves them, stats). `tags` = the dashboard's measured tags with their instrument
    range; other channels in `measurements` pass through unchanged. `layer_dt_s` is the layer's nominal row spacing (60 or 1 s), used
    to count fault RUN STARTS and the exposure they were counted over. Identity (same list, empty stats) when disabled."""
    if not cfg.enabled or not records:
        return records, {}
    n = len(records)
    t = np.array([float(r["system_context"]["t_s"]) for r in records])
    out = [copy.copy(r) for r in records]
    for r in out:
        r["measurements"] = dict(r["measurements"])
        r["measurements_live"] = {k: r["measurements"][k] for k in tags if k in r["measurements"]}
        r["measurement_quality"] = {}
        r["data_faults"] = {}
        r["labels"] = dict(r["labels"])
    any_fault = np.zeros(n, dtype=bool)
    stats: dict[str, Any] = {}

    for tag, info in tags.items():
        if tag not in records[0]["measurements"]:
            continue
        x = np.array([np.nan if r["measurements"][tag] is None else float(r["measurements"][tag]) for r in records])
        valid = ~np.isnan(x)
        qual = np.full(n, "Good", dtype=object)
        ftype = np.full(n, NO_FAULT, dtype=object)
        for t0, t1, ft in fault_windows(seed, tag, horizon_s, cfg):
            m = (t >= t0) & (t < t1)
            if not m.any():
                continue
            if ft == "dropout":
                x[m] = np.nan
            elif ft in ("stale_value", "flat_line"):
                before = np.flatnonzero((t < t0) & ~np.isnan(x))
                x[m] = x[before[-1]] if len(before) else x[np.flatnonzero(m)[0]]
            else:       # out_of_range: beyond the instrument range
                x[m] = info.hi * 3.0 if info.log else info.hi + 0.05 * info.span
            qual[m] = QUALITY_OF_FAULT[ft]
            ftype[m] = ft
        valid = ~np.isnan(x)
        any_fault |= ftype != NO_FAULT
        rec, n_valid, n_pass, n_arch = _compress_series(t, x, valid, info, cfg.deadband_pct_span.get(tag, 0.2), cfg)
        for i, r in enumerate(out):
            r["measurements"][tag] = None if np.isnan(rec[i]) else float(rec[i])
            r["measurement_quality"][tag] = str(qual[i])
            r["data_faults"][tag] = str(ftype[i])
        # run starts: a fault run whose first row has a contiguous predecessor (so it truly begins inside this layer's
        # data, not at a burst boundary); exposure = rows that have a contiguous predecessor x the layer period
        cont = np.concatenate([[False], np.diff(t) <= 1.5 * layer_dt_s])
        prev_type = np.concatenate([np.array([NO_FAULT], dtype=object), ftype[:-1]])
        starts = cont & (ftype != NO_FAULT) & (ftype != prev_type)
        stats[tag] = {"n_samples": n, "n_valid": n_valid, "n_exception_passed": n_pass, "n_archived": n_arch,
                      "compression_ratio": (n_valid / n_arch) if n_arch else None,
                      "fault_samples": {ft: int((ftype == ft).sum()) for ft in FAULT_TYPES},
                      "fault_run_starts": {ft: int((starts & (ftype == ft)).sum()) for ft in FAULT_TYPES},
                      "exposure_channel_days": float(cont.sum()) * layer_dt_s / 86400.0}

    for tag in discrete_tags:       # discrete inputs (valve states, compressor status): only dropouts (-> "unknown", Bad)
        if tag not in records[0]["measurements"]:
            continue
        mask = np.zeros(n, dtype=bool)
        for t0, t1, ft in fault_windows(seed, tag, horizon_s, cfg):
            if ft == "dropout":
                mask |= (t >= t0) & (t < t1)
        any_fault |= mask
        for i, r in enumerate(out):
            r["measurements_live"][tag] = r["measurements"][tag]
            r["measurements"][tag] = "unknown" if mask[i] else r["measurements"][tag]
            r["measurement_quality"][tag] = "Bad" if mask[i] else "Good"
            r["data_faults"][tag] = "dropout" if mask[i] else NO_FAULT
    for i, r in enumerate(out):
        r["labels"]["has_data_fault"] = bool(any_fault[i])
    return out, stats
