"""Helpers shared by the tools (operations features, inventory, noise models). Causal: everything looks backwards only."""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R

TAU_RISE_S = 600.0


def inventory(P_bar: np.ndarray, T_c: np.ndarray, volume_m3: float) -> np.ndarray:
    return np.asarray(G.rho_PT(np.clip(P_bar, 1.0, None), T_c + 273.15)) * volume_m3


def time_since(event: np.ndarray, dt_s: float = 60.0, cap_s: float = 48 * 3600.0) -> np.ndarray:
    idx = np.where(event, np.arange(len(event)), -1)
    last = np.maximum.accumulate(idx)
    return np.where(last >= 0, (np.arange(len(event)) - last) * dt_s, cap_s).clip(max=cap_s)


def run_age(run: np.ndarray, dt_s: float = 60.0) -> np.ndarray:
    """Seconds the compressor has been running (0 when stopped)."""
    age = np.zeros(len(run))
    for i in range(1, len(run)):
        age[i] = age[i - 1] + dt_s if run[i] else 0.0
    return age


def ops_features(unit) -> dict[str, np.ndarray]:
    """Operation-state features for the gradient model and the thermal observer, from the compressor state and the flows."""
    raw = unit.raw
    run = (np.nan_to_num(raw.disc_state["comp"], nan=0.0) > 0.5)
    if not np.isfinite(raw.disc_state["comp"]).any() or not (raw.disc_state["comp"] > -1).any():          # valve-state ablation: infer from the fill flow
        run = unit.fill_min > 0.05
    disc = unit.disc_min > 0.05
    tau = unit.cls["tau_gas_wall_s"]
    age = run_age(run)
    since_stop = time_since(~run & np.concatenate([[False], run[:-1]]))                      # time since the last compressor STOP
    runlen_before = np.zeros(len(run))
    cur = 0.0
    for i in range(len(run)):                                                               # length of the last completed run (s)
        if run[i]:
            cur = age[i]
        runlen_before[i] = cur
    since_disc = time_since(disc)
    A = run * (1.0 - np.exp(-age / TAU_RISE_S))                                              # gradient building while charging
    B = (~run) * np.exp(-since_stop / tau) * np.minimum(runlen_before / 1800.0, 1.0)         # decaying after a charge
    D = np.exp(-since_disc / tau) * disc.astype(float)                                       # expansion cooling during/after a draw
    last_op = np.minimum(np.minimum(since_stop, since_disc), np.where(run, 0.0, 48 * 3600.0))
    return {"run": run.astype(float), "A": A, "B": B, "D": D, "since_stop_s": since_stop, "since_disc_s": since_disc,
            "settled": np.minimum(last_op / (4.0 * tau), 3.0)}


def gated_flows(unit) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(fill kg/min, discharge kg/min, number of gated ticks) with physical gating: where the 1 s layer has no rows for that minute, a discharge flow is
    forced to zero while the discharge valve reports closed, and a compressor feed is forced to zero while the compressor reports stopped and the inlet
    valve closed. This removes a silent flat-line fault on a flow meter (Good quality, value stuck) from the mass balance. It needs the compressor/valve
    states (the valve-state switch); without them the flows are used as metered."""
    raw = unit.raw
    fill, disc = unit.fill_min.copy(), unit.disc_min.copy()
    uncovered = unit.fast["nrows"] < 1
    dv, comp, inlet = raw.disc_state["dvalve"], raw.disc_state["comp"], raw.disc_state["inlet"]
    gated = np.zeros(unit.n)
    if np.isfinite(dv).any():
        g = uncovered & (dv < 0.5)
        disc[g] = 0.0
        gated += g
    if np.isfinite(comp).any() and np.isfinite(inlet).any():
        g = uncovered & (comp < 0.5) & (inlet < 0.5)
        fill[g] = 0.0
        gated += g
    return fill, disc, gated


def ewma(x: np.ndarray, tau_min: float) -> np.ndarray:
    """Causal exponential smoother with time constant tau_min samples (60 s spacing); starts at x[0]; NaN-safe (holds the last value)."""
    from scipy.signal import lfilter
    x = np.asarray(x, dtype=float)
    ok = np.isfinite(x)
    if not ok.any():
        return np.zeros_like(x)
    idx = np.where(ok, np.arange(len(x)), 0)
    xf = x[np.maximum.accumulate(idx)]
    xf[: int(np.argmax(ok))] = x[np.argmax(ok)]
    a = 1.0 - np.exp(-1.0 / max(tau_min, 1e-6))
    y, _ = lfilter([a], [1.0, -(1.0 - a)], xf, zi=[(1.0 - a) * xf[0]])
    return y


def slope_per_h(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing OLS slope per hour over w samples (60 s spacing); 0 while the window fills."""
    i = np.arange(w) - (w - 1) / 2.0
    k = i / np.sum(i * i)
    out = np.zeros(len(x))
    if len(x) >= w:
        out[w - 1:] = np.convolve(np.nan_to_num(x), k[::-1], mode="valid") * 60.0
    return out


def dpdt_bar_per_k(P_bar: np.ndarray) -> np.ndarray:
    """(dP/dT) at constant density of CoolProp hydrogen near 300 K, approx linear in P (1.037 bar/K at 300 bar; checked to ~3 % over 50-350 bar)."""
    return 0.003458 * np.asarray(P_bar, dtype=float)


def mad_sigma(a: np.ndarray) -> float:
    a = a[np.isfinite(a)]
    if len(a) < 20:
        return 1.0
    return float(1.4826 * np.median(np.abs(a - np.median(a))) + 1e-12)


def strain_model(fit, unit) -> tuple[float, float, float]:
    """(intercept ue, ue per bar, ue per K of shell temperature) of strain = a + k P + c Tw. The slope is the fitted medium-class value rescaled by this vessel's
    nameplate hoop strain per bar, so the other pressure classes read on the same footing."""
    a, k, c = (float(v) for v in fit.extra["st_coef"])
    ref = float(fit.extra.get("st_hoop_ref", unit.cls["hoop_strain_ue_per_bar"]))
    return a, k * float(unit.cls["hoop_strain_ue_per_bar"]) / ref, c
