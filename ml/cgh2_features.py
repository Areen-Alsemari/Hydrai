"""
Agent features for the CGH2 twin (step 1). Built ONLY from what a real dashboard shows: the tags (historian view), their OPC quality codes,
the compressor / valve states (switch), and the clock. NOT used: fault labels, onset times, injected-fault flags, the paired healthy twin,
live (pre-historian) values, ground truth. Pressure and inventory are normalised by the class (MOP; inventory at MOP and 300 K) so a model
trained on the medium class transfers to low and high.

Feature groups
  state        P/MOP, temperature-compensated pressure (at 50 C)/MOP, real-gas inventory/I_ref (rho(P, T) x V from the MEASURED P and T)
  thermal      gas, shell, ambient temperature, gas-shell and gas-ambient differences, diurnal phase
  windows      OLS slopes (per hour) of P, compensated P, inventory, gas temperature and rolling spreads over 10 min, 1 h, 6 h, 24 h
  mass balance inventory change minus the metered net flow (fill - discharge) over 10 min / 1 h / 6 h / 24 h, in kg/I_ref and as a z-score against
               the datasheet meter-error model (0.5 % of reading + 0.009 kg/min zero stability, A/2 convention) and the inventory estimate error
  hold slope   inventory slope over the trailing 2 h and 6 h where the compressor was stopped and no gas drawn (a leak-rate estimate), 0 elsewhere
  operations   time since the last compressor change and the last discharge, and a 'settled' ratio = that time / (4 gas-wall time constants)
  detector     hydrogen %LFL, its 10 min slope and 10 min maximum
  context      compressor / valve states (switchable), flows
  quality      share of non-Good samples in the last 10 min and run length of an unchanged value (staleness) for P, T and the two flows
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R

T_REF_C = 50.0
WINDOWS = {"10m": 10, "1h": 60, "6h": 360, "24h": 1440}
HOLD_WINDOWS = {"2h": 120, "6h": 360}
CH = {"P": "pressure_bar_a", "T": "gas_temp_c", "Tw": "outer_wall_temp_c", "Ta": "ambient_temp_c", "H2": "h2_concentration_pct",
      "fill": "mass_flow_fill_kg_s", "disc": "mass_flow_discharge_kg_s", "strain": "strain_ue"}
DISCRETE = {"comp": "compressor_status", "inlet": "inlet_valve", "dvalve": "discharge_valve", "prv": "prv_state"}
CTX_FEATURES = ("comp", "inlet", "dvalve", "prv")           # dropped in the valve-state ablation
FLOW_QUIET = 0.0005                                          # kg/s: above the meters' noise floor (1.5e-4), below any real draw


@dataclass
class Raw:
    entry: dict[str, Any]
    t: np.ndarray
    x: dict[str, np.ndarray]                  # Good samples, forward-filled
    raw: dict[str, np.ndarray]                # historian values before filling (NaN where missing)
    good: dict[str, np.ndarray]
    disc_state: dict[str, np.ndarray]         # 1.0 run/open, 0.0 stop/closed (NaN when unknown / switch off)
    has_data_fault: np.ndarray                # EVALUATION ONLY: never a feature
    volume_m3: float
    mop_bar: float
    tau_gw_s: float
    inv_ref_kg: float


def _ffill(x: np.ndarray, good: np.ndarray) -> np.ndarray:
    if not good.any():
        return np.zeros_like(x)
    idx = np.where(good, np.arange(len(x)), 0)
    first = int(np.flatnonzero(good)[0])
    idx[:first] = first
    return x[np.maximum.accumulate(idx)]


def load_raw(root: Path, entry: dict[str, Any], cls: dict[str, Any], valve_states: bool = True) -> Raw:
    names = set(pq.ParquetFile(root / entry["slow_file"]).schema.names)
    cols = ["ctx__t_s", "label__has_data_fault"] + [f"meas__{c}" for c in CH.values()] + [f"q__{c}" for c in CH.values() if f"q__{c}" in names]
    cols += [f"meas__{c}" for c in DISCRETE.values() if f"meas__{c}" in names]
    tb = pq.read_table(root / entry["slow_file"], columns=cols).to_pydict()
    t = np.array(tb["ctx__t_s"], dtype=float)
    x, rawv, good = {}, {}, {}
    for k, ch in CH.items():
        r = np.array([np.nan if v is None else v for v in tb[f"meas__{ch}"]], dtype=float)
        q = tb.get(f"q__{ch}")
        g = ~np.isnan(r) & (np.array([v == "Good" for v in q]) if q is not None else True)
        x[k], rawv[k], good[k] = _ffill(np.nan_to_num(r), g), r, g
    ds = {}
    for k, ch in DISCRETE.items():
        col = tb.get(f"meas__{ch}")
        if col is None or not valve_states:
            ds[k] = np.full(len(t), np.nan)
        else:
            on = {"run", "open"}
            ds[k] = np.array([np.nan if v == "unknown" else (1.0 if v in on else 0.0) for v in col])
    return Raw(entry, t, x, rawv, good, ds, np.array(tb["label__has_data_fault"], dtype=bool), cls["volume_m3"], cls["mop_bar"],
               cls["tau_gas_wall_s"], float(G.inventory_kg(cls["mop_bar"], 300.0, cls["volume_m3"])))


# -- rolling helpers ----------------------------------------------------------------------------------------------------------

def roll_sum(x: np.ndarray, w: int) -> np.ndarray:
    c = np.concatenate([[0.0], np.cumsum(x)])
    out = c[w:] - c[:-w]
    return np.concatenate([np.full(w - 1, np.nan), out])


def roll_slope(x: np.ndarray, w: int) -> np.ndarray:
    """OLS slope per HOUR over the trailing w samples (60 s spacing); NaN while the window is filling."""
    i = np.arange(w) - (w - 1) / 2.0
    k = i / np.sum(i * i)
    s = np.convolve(x, k[::-1], mode="valid") * 60.0
    return np.concatenate([np.full(w - 1, np.nan), s])


def roll_std(x: np.ndarray, w: int) -> np.ndarray:
    m1, m2 = roll_sum(x, w) / w, roll_sum(x * x, w) / w
    return np.sqrt(np.maximum(m2 - m1 * m1, 0.0))


def run_length_unchanged(r: np.ndarray, cap: int = 600) -> np.ndarray:
    """Samples since the (raw, unfilled) value last changed; NaN counts as unchanged."""
    ch = np.concatenate([[True], ~np.isclose(np.nan_to_num(r[1:], nan=-9e9), np.nan_to_num(r[:-1], nan=-9e9), rtol=0, atol=1e-12)])
    idx = np.where(ch, np.arange(len(r)), 0)
    return np.minimum(np.arange(len(r)) - np.maximum.accumulate(idx), cap).astype(float)


def time_since(event: np.ndarray, t: np.ndarray, cap_s: float) -> np.ndarray:
    idx = np.where(event, np.arange(len(t)), -1)
    last = np.maximum.accumulate(idx)
    out = np.where(last >= 0, t - t[np.clip(last, 0, None)], cap_s)
    return np.minimum(out, cap_s)


def inventory(raw: Raw) -> np.ndarray:
    return np.asarray(G.rho_PT(np.clip(raw.x["P"], 1.0, None), raw.x["T"] + 273.15)) * raw.volume_m3


def compensated_pressure(raw: Raw, inv: np.ndarray) -> np.ndarray:
    return np.asarray(G.pressure_bar(inv / raw.volume_m3, T_REF_C + 273.15))


def hold_mask(raw: Raw, w: int) -> np.ndarray:
    run = np.nan_to_num(raw.disc_state["comp"], nan=0.0) > 0.5
    quiet = (~run) & (raw.x["disc"] < FLOW_QUIET) & (raw.x["fill"] < FLOW_QUIET)
    return np.convolve(quiet.astype(int), np.ones(w, int), mode="full")[: len(quiet)] >= w


def mass_balance(raw: Raw, inv: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
    """(r_mb in kg, sigma_mb in kg): inventory change over w samples minus the metered net flow over the same w samples, and its expected error
    under the datasheet meter model (A/2 convention: zero stability on both meters, 0.5 % of the integrated flow) plus the inventory-estimate error."""
    net = (raw.x["fill"] - raw.x["disc"]) * 60.0
    flow = roll_sum(net, w)                                                        # kg over the trailing w samples (NaN while filling)
    flow_abs = roll_sum(raw.x["fill"] + raw.x["disc"], w) * 60.0
    r = np.concatenate([np.full(w, np.nan), (inv[w:] - inv[:-w]) - flow[w:]])
    zero_kg_min = R.value("flow_datasheet_zero_kg_min")
    s_inv = 0.78 * raw.inv_ref_kg / 204.26                                         # inventory estimate error scales with the store (0.78 kg at 300 bar)
    sig = np.sqrt((s_inv * np.sqrt(2.0)) ** 2 + (0.5 * np.sqrt(2.0) * zero_kg_min * w) ** 2 + (0.5 * R.value("flow_datasheet_pct_reading") / 100.0 * flow_abs) ** 2)
    return r, sig


def build(raw: Raw, valve_states: bool = True, compensated: bool = True) -> tuple[list[str], np.ndarray]:
    """Feature matrix (n x F, float32) and names. Rows with insufficient history carry 0 and a small `history_h` value."""
    n, t = len(raw.t), raw.t
    mop, iref = raw.mop_bar, raw.inv_ref_kg
    inv = inventory(raw)
    pc = compensated_pressure(raw, inv)
    F: dict[str, np.ndarray] = {}
    hour = (t / 3600.0) % 24.0
    P, T = raw.x["P"], raw.x["T"]
    F["Pn"], F["Pcn"], F["In"] = P / mop, pc / mop, inv / iref
    if not compensated:                       # ablation: no real-gas compensation; the inventory-derived features are replaced by raw-pressure copies
        F["Pcn"], F["In"] = P / mop, P / mop
    F["T_gas"], F["T_wall"], F["T_amb"] = T, raw.x["Tw"], raw.x["Ta"]
    F["dT_gw"], F["dT_ga"] = T - raw.x["Tw"], T - raw.x["Ta"]
    F["hour_sin"], F["hour_cos"] = np.sin(2 * np.pi * hour / 24.0), np.cos(2 * np.pi * hour / 24.0)
    F["history_h"] = np.minimum(t / 3600.0, 24.0)
    F["strain_n"] = raw.x["strain"] / 1000.0
    F["h2_lfl"] = raw.x["H2"]
    F["h2_slope_10m"] = roll_slope(raw.x["H2"], 10)
    F["h2_max_10m"] = np.array([np.nan] * 9 + list(np.max(np.lib.stride_tricks.sliding_window_view(raw.x["H2"], 10), axis=1))) if n >= 10 else np.zeros(n)
    F["fill_kgmin"], F["disc_kgmin"] = raw.x["fill"] * 60.0, raw.x["disc"] * 60.0
    base_series = {"Pn": F["Pn"], "Pcn": F["Pcn"], "In": F["In"], "Tg": T}
    for wn, w in WINDOWS.items():
        for sn, s in base_series.items():
            F[f"slope_{sn}_{wn}"] = roll_slope(s, w)
        if w >= 60:
            F[f"std_In_{wn}"] = roll_std(F["In"], w)
            F[f"std_dTgw_{wn}"] = roll_std(F["dT_gw"], w)
        r, sg = mass_balance(raw, inv, w)
        F[f"mb_{wn}"] = r / iref
        F[f"mb_z_{wn}"] = r / sg
    for wn, w in HOLD_WINDOWS.items():
        ok = hold_mask(raw, w)
        F[f"hold_slope_{wn}"] = np.where(ok, roll_slope(inv, w) / iref, 0.0)
        F[f"hold_ok_{wn}"] = ok.astype(float)
    run = np.nan_to_num(raw.disc_state["comp"], nan=0.0) > 0.5
    changed = np.concatenate([[False], run[1:] != run[:-1]])
    F["since_comp_h"] = time_since(changed, t, 48 * 3600.0) / 3600.0
    F["since_disc_h"] = time_since(raw.x["disc"] > FLOW_QUIET, t, 48 * 3600.0) / 3600.0
    last_op = np.minimum(time_since(changed | (raw.x["disc"] > FLOW_QUIET) | run, t, 48 * 3600.0), 48 * 3600.0)
    F["settled"] = np.minimum(last_op / (4.0 * raw.tau_gw_s), 3.0)
    if valve_states:
        for k in CTX_FEATURES:
            F[f"ctx_{k}"] = np.nan_to_num(raw.disc_state[k], nan=0.5)
    for k in ("P", "T", "fill", "disc"):
        bad = (~raw.good[k]).astype(float)
        F[f"badfrac_{k}_10m"] = roll_sum(bad, 10) / 10.0
        F[f"stale_{k}"] = run_length_unchanged(raw.raw[k])
    names = list(F)
    X = np.column_stack([F[k] for k in names]).astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return names, X
