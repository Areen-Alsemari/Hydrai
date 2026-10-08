"""
Data access for the agent: one `Unit` per episode with the dashboard-visible series, the DCS alarm state, per-minute flow integrals that use the 1 s
layer where it exists (fills are short pulses; 60 s snapshots integrate them badly), and fast-layer signals. Evaluation-only arrays (ground truth,
data-fault flags) live in `Unit.truth` and are never read by a tool.
"""

from __future__ import annotations

import gzip
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from hydrai_twin.cgh2 import gas as G
from ml.cgh2_features import Raw, load_raw

CACHE = Path(__file__).resolve().parents[2] / "output" / "cgh2_cache"


def _fast_signals(args):
    """Per-minute signals from the 1 s layer of one episode: row count, mean flows, max 30 s pressure drop (x MOP), max 10 s H2 rise, max H2, any relief."""
    root, entry, mop = args
    out_path = CACHE / f"fast_{entry['name']}.npz"
    if out_path.exists():
        return entry["name"], dict(np.load(out_path))
    t, P, H2, prv, fill, disc = [], [], [], [], [], []
    with gzip.open(root / entry["fast_file"], "rt") as f:
        for line in f:
            r = json.loads(line)
            m, q = r["measurements"], r.get("measurement_quality", {})
            t.append(r["system_context"]["t_s"])
            ok = lambda k: m[k] is not None and q.get(k, "Good") == "Good"
            P.append(m["pressure_bar_a"] if ok("pressure_bar_a") else np.nan)
            H2.append(m["h2_concentration_pct"] if ok("h2_concentration_pct") else np.nan)
            fill.append(m["mass_flow_fill_kg_s"] if ok("mass_flow_fill_kg_s") else np.nan)
            disc.append(m["mass_flow_discharge_kg_s"] if ok("mass_flow_discharge_kg_s") else np.nan)
            prv.append(1.0 if m.get("prv_state") == "open" else 0.0)
    t, P, H2, prv, fill, disc = (np.array(a) for a in (t, P, H2, prv, fill, disc))
    nmin = int(max(entry["duration_s"], t.max() if len(t) else 0) // 60) + 3
    sig = {k: np.full(nmin, np.nan) for k in ("n", "fill", "disc", "drop30", "rise10", "h2max", "prv", "pmax")}
    sig["n"] = np.zeros(nmin)
    sig["sum_fill"], sig["sum_disc"] = np.zeros(nmin), np.zeros(nmin)          # kg in the covered seconds of the minute (1 s rows)
    if len(t):
        j30 = np.searchsorted(t, t - 30, side="left")
        ok30 = (t - t[j30] >= 28.5) & (t - t[j30] <= 31.5)
        drop = np.where(ok30, (P[j30] - P) / mop, np.nan)
        j10 = np.searchsorted(t, t - 10, side="left")
        ok10 = (t - t[j10] >= 8.5) & (t - t[j10] <= 11.5)
        rise = np.where(ok10, H2 - H2[j10], np.nan)
        b = (t // 60).astype(int)
        for k in np.unique(b):
            s = b == k
            sig["n"][k] = s.sum()
            sig["sum_fill"][k], sig["sum_disc"][k] = np.nansum(fill[s]), np.nansum(disc[s])
            sig["fill"][k], sig["disc"][k] = np.nanmean(fill[s]) if np.isfinite(fill[s]).any() else np.nan, np.nanmean(disc[s]) if np.isfinite(disc[s]).any() else np.nan
            sig["drop30"][k] = np.nanmax(drop[s]) if np.isfinite(drop[s]).any() else np.nan
            sig["rise10"][k] = np.nanmax(rise[s]) if np.isfinite(rise[s]).any() else np.nan
            sig["h2max"][k] = np.nanmax(H2[s]) if np.isfinite(H2[s]).any() else np.nan
            sig["prv"][k], sig["pmax"][k] = prv[s].max(), np.nanmax(P[s]) if np.isfinite(P[s]).any() else np.nan
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez(out_path, **sig)
    return entry["name"], sig


def build_fast_cache(root: Path, entries: list[dict], mop: float, workers: int = 6) -> dict[str, dict[str, np.ndarray]]:
    if all((CACHE / f"fast_{e['name']}.npz").exists() for e in entries):             # everything cached: no process pool needed
        return {e["name"]: dict(np.load(CACHE / f"fast_{e['name']}.npz")) for e in entries}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(_fast_signals, [(root, e, mop) for e in entries]))


@dataclass
class Unit:
    entry: dict[str, Any]
    t: np.ndarray
    cls: dict[str, Any]
    raw: Raw
    fill_min: np.ndarray                     # kg per tick (best available integral: 1 s layer where present, snapshots elsewhere)
    disc_min: np.ndarray
    fast: dict[str, np.ndarray]              # per-tick fast-layer signals (aligned to slow ticks)
    static: np.ndarray                       # DCS alarm state (existing static alarms) per tick
    truth: dict[str, np.ndarray] = field(default_factory=dict)      # EVALUATION ONLY (ground truth, data-fault flags): never read by a tool

    @property
    def n(self) -> int:
        return len(self.t)


def load_unit(root: Path, entry: dict, cls: dict, fast_cache: dict[str, dict[str, np.ndarray]], static_flags: np.ndarray, valve_states: bool = True) -> Unit:
    raw = load_raw(root, entry, cls, valve_states)
    idx = np.round(raw.t / 60.0).astype(int)
    fc = fast_cache[entry["name"]]
    take = lambda a: a[np.clip(idx, 0, len(a) - 1)]
    nrows = take(fc["n"])
    cover = nrows >= 1
    fill_snap = raw.x["fill"] * 60.0
    disc_snap = raw.x["disc"] * 60.0
    # kg in this minute: the 1 s rows are summed exactly (a dispenser draw can fill only part of a minute); the compressor feed, which is steady, is
    # extended over the uncovered seconds at the covered mean; minutes with no 1 s rows use the 60 s snapshot
    fill_min = np.where(cover, take(fc["sum_fill"]) * 60.0 / np.maximum(nrows, 1), fill_snap)
    disc_min = np.where(cover, take(fc["sum_disc"]), disc_snap)
    fast = {k: np.where(np.isfinite(take(v)), take(v), 0.0) for k, v in fc.items()}
    fast["cover"] = (nrows >= 20).astype(float)
    fast["nrows"] = nrows
    tb = pq.read_table(root / entry["slow_file"], columns=["gt__gas_temp_c", "gt__mass_kg", "gt__mdot_leak_kg_s", "gt__mdot_prv_kg_s", "gt__pressure_bar_a"]).to_pydict()
    truth = {"gas_temp_bulk_c": np.array(tb["gt__gas_temp_c"], dtype=float), "mass_kg": np.array(tb["gt__mass_kg"], dtype=float),
             "mdot_leak": np.array(tb["gt__mdot_leak_kg_s"], dtype=float), "mdot_prv": np.array(tb["gt__mdot_prv_kg_s"], dtype=float),
             "pressure": np.array(tb["gt__pressure_bar_a"], dtype=float), "has_data_fault": raw.has_data_fault}
    return Unit(entry, raw.t, cls, raw, fill_min, disc_min, fast, np.asarray(static_flags, dtype=bool), truth)


def slice_unit(u: Unit, n: int) -> Unit:
    """The same unit truncated to its first n ticks (used to test that every tool is causal: values at tick n-1 must not depend on later data)."""
    from dataclasses import replace
    cut = lambda a: a[:n]
    raw = replace(u.raw, t=cut(u.raw.t), x={k: cut(v) for k, v in u.raw.x.items()}, raw={k: cut(v) for k, v in u.raw.raw.items()}, good={k: cut(v) for k, v in u.raw.good.items()},
                  disc_state={k: cut(v) for k, v in u.raw.disc_state.items()}, has_data_fault=cut(u.raw.has_data_fault))
    return Unit(u.entry, cut(u.t), u.cls, raw, cut(u.fill_min), cut(u.disc_min), {k: cut(v) for k, v in u.fast.items()}, cut(u.static), {k: cut(v) for k, v in u.truth.items()})
