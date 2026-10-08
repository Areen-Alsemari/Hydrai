"""
T2 inventory_leak: the leak tool.

  inventory     temperature-compensated real-gas inventory rho(P, T) x V from the CLEANED tags (T1), with the learned bulk-gas-temperature correction (E3: the probe
                reads a hotter inlet gas after a charge; a ridge model of the gradient from operation features is added to the probe) and the per-unit commissioning
                baseline (E2: each unit's own flow-meter/zero offsets, learned in the commissioning run and refreshed on the first N = 2 days of the same episode)
  GLR           sliding-window slope test on the inventory during QUIET periods (compressor stopped, nothing drawn) for windows 1 h .. 24 h: a constant leak is a RAMP
  Kalman        state [inventory, leak rate] fusing the pressure/temperature inventory with the metered flow mass balance (1 s layer flows where present, 60 s
                snapshots elsewhere); the leak rate is a random walk, so a step leak appears as a rising estimate with its own uncertainty
  outputs       leak rate (kg/h) with interval, equivalent orifice diameter with interval (Cd 0.6 .. 1.0), kg released so far, a z-score for detection

Not used: ground truth, labels, onset times, the paired twin. Parameters (noise levels) come from healthy training modules only.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2_agent.fit import GLR_WINDOWS, hold_slopes
from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import inventory, ops_features

DRAW_ERR_FRAC = 1.0      # inventory-estimate error per kg drawn recently (fitted by eye on the 31 kg bus fill; a dev-data constant, not tuned on test)
DRAW_TAIL_FRAC = 0.1
QL_PER_H = 0.04          # leak-rate random-walk intensity (kg/h)^2 per hour: fixed a priori
UPDATE_EVERY = 10
FIRST_DAYS = 2           # E2: days of the same episode used to refresh the unit offset (declared in advance, no use of onset labels)


def corrected_inventory(ctx) -> np.ndarray:
    if "I_corr" not in ctx.cache:
        ctx.monitor("T1_data_integrity")
        c = ctx.cache["clean"]
        grad = ctx.fit.gradient(ctx.unit) if ctx.opt["e3"] else 0.0
        ctx.cache["I_corr"] = inventory(c["P"], c["T"] + grad, ctx.unit.cls["volume_m3"])
    return ctx.cache["I_corr"]


def kalman(ctx, ql: float = QL_PER_H) -> dict[str, np.ndarray]:
    u, fit = ctx.unit, ctx.fit
    iref = u.raw.inv_ref_kg
    Im = corrected_inventory(ctx)
    ctx.monitor("T1_data_integrity")
    c = ctx.cache["clean"]
    net = c["fill_min"] - c["disc_min"]                                          # kg per tick (gated by valve/compressor state, 1 s layer where present)
    flows = c["fill_min"] + c["disc_min"]
    o = ops_features(u)
    sig10 = np.where(o["settled"] >= 1.0, fit.sigma_I10["settled"], fit.sigma_I10["unsettled"]) * iref
    # after a large draw the archived P/T no longer describe the vessel: the inventory estimate is off by about the drawn mass,
    # decaying with the gas-wall time constant (dev healthy: |err|/recent draw has median ~1.1 for >10 kg draws), plus a slow tail
    tau_min = u.cls["tau_gas_wall_s"] / 60.0
    W, W2 = np.zeros(u.n), np.zeros(u.n)
    a1, a2 = np.exp(-1.0 / tau_min), np.exp(-1.0 / (2.4 * tau_min))
    for i in range(1, u.n):
        W[i] = W[i - 1] * a1 + c["disc_min"][i]
        W2[i] = W2[i - 1] * a2 + c["disc_min"][i]
    sig10 = np.sqrt(sig10 ** 2 + (DRAW_ERR_FRAC * W) ** 2 + (DRAW_TAIL_FRAC * W2) ** 2)
    # recent charging leaves a smaller transient (healthy dev: |err| / recent fill p90 ~0.2 at the gas-wall time constant): used by the fast slope estimator
    Wf = np.zeros(u.n)
    for i in range(1, u.n):
        Wf[i] = Wf[i - 1] * a1 + c["fill_min"][i]
    sig_fast = np.sqrt(sig10 ** 2 + (0.25 * Wf) ** 2)
    n = u.n
    x = np.array([Im[0], 0.0]); P = np.diag([4.0, 1.0])
    L, sL, Ih = np.zeros(n), np.zeros(n), np.zeros(n)
    dt_h = 1.0 / 60.0
    F = np.array([[1.0, -dt_h], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    for i in range(1, n):
        x = F @ x + np.array([net[i], 0.0])
        q_i = (0.005 * flows[i]) ** 2 + (0.002) ** 2
        P = F @ P @ F.T + np.diag([q_i, ql * dt_h])
        if i % UPDATE_EVERY == 0:
            z = Im[i - UPDATE_EVERY + 1:i + 1].mean()
            R = sig10[i] ** 2
            S = P[0, 0] + R
            K = np.array([P[0, 0], P[1, 0]]) / S
            x = x + K * (z - x[0])
            P = (np.eye(2) - np.outer(K, H[0])) @ P
        L[i], sL[i], Ih[i] = x[1], np.sqrt(max(P[1, 1], 1e-12)), x[0]
    return {"L": L, "sL": sL, "I": Ih, "sig": sig10, "sig_fast": sig_fast}


FAST_WINDOWS = (5, 10, 20)           # minutes
FAST_Z_TAIL = 3.0                    # healthy 99.5th percentile of |slope / sigma| is calibrated to this (see fit_extra)


def fast_slopes(ctx, kf: dict, off: np.ndarray | float = 0.0) -> dict:
    """Local OLS slopes (kg/h loss) of R(t) = compensated inventory - cumulative metered net flow over short windows, with the white-noise sigma from the
    per-sample inventory error (inflated after recent draws and fills). For large leaks that start abruptly these respond within minutes, far faster than
    the filter's slowly varying leak state."""
    u = ctx.unit
    Im = corrected_inventory(ctx)
    net = ctx.cache["clean"]["fill_min"] - ctx.cache["clean"]["disc_min"]
    Rr = Im - np.cumsum(net)
    out = {}
    for w in FAST_WINDOWS:
        i_ = np.arange(w) - (w - 1) / 2.0
        kern = i_ / np.sum(i_ * i_)
        slope = np.zeros(u.n)
        slope[w - 1:] = np.convolve(Rr, kern[::-1], mode="valid") * 60.0
        out[w] = (-slope - off, kf["sig_fast"] * np.sqrt(12.0 / (w * (w * w - 1.0))) * 60.0)
    return out


def settled_before(u, w: int) -> np.ndarray:
    """True where the gas had already settled (>= 2 gas-wall time constants since the last operation) at the START of the trailing w-sample window."""
    o = ops_features(u)
    s = np.minimum(o["since_stop_s"], o["since_disc_s"])
    ok = s >= 2.0 * u.cls["tau_gas_wall_s"] + w * 60.0                     # still quiet for the whole window and 2 tau before it
    return ok


def glr(ctx) -> dict[str, np.ndarray]:
    """Sliding-window slope z-scores on quiet windows (leak = negative slope), maximum over windows; NaN->0 when no window is quiet."""
    u, fit = ctx.unit, ctx.fit
    iref = u.raw.inv_ref_kg
    In = corrected_inventory(ctx) / iref
    c = ctx.cache["clean"]
    quiet = (~(np.nan_to_num(u.raw.disc_state["comp"], nan=0.0) > 0.5)) & (c["disc_min"] < 0.03) & (c["fill_min"] < 0.03)
    zs = np.zeros((len(GLR_WINDOWS), u.n))
    sl_all = np.zeros((len(GLR_WINDOWS), u.n))
    for k, w in enumerate(GLR_WINDOWS):
        ok = np.convolve(quiet.astype(int), np.ones(w, int), mode="full")[: u.n] >= w
        ok &= settled_before(u, w)
        sl = hold_slopes(In, w)
        sl_all[k] = np.where(ok & np.isfinite(sl), sl, 0.0)
        zs[k] = np.where(ok & np.isfinite(sl), -(sl - ctx.baseline.get("glr_off", {}).get(w, 0.0)) / max(fit.glr_sigma.get(w, 0.01), 1e-6), 0.0)
    kbest = np.argmax(zs, axis=0)
    return {"glr_z": zs.max(axis=0), "glr_window_min": np.array(GLR_WINDOWS)[kbest].astype(float), "glr_slope_kgh": -sl_all[kbest, np.arange(u.n)] * iref}


def orifice_mm(rate_kg_h: float, P_bar: float, T_k: float, cd: float) -> float:
    if rate_kg_h <= 0:
        return 0.0
    flux = G.choked_mass_flux_fast(P_bar * 1e5, T_k)
    area = (rate_kg_h / 3600.0) / (cd * flux)
    return float(1e3 * np.sqrt(4.0 * area / np.pi))


@register
class InventoryLeak(Tool):
    name = "T2_inventory_leak"
    description = "Temperature-compensated real-gas inventory, per-unit baseline, learned bulk-gas-temperature correction, slope test and a Kalman estimator [inventory, leak rate]."
    version = "1.0"
    cost = "medium"

    def monitor(self, ctx):
        u = ctx.unit
        kf = kalman(ctx)
        g = glr(ctx)
        # E2: per-unit offset of the leak-rate estimate (flow-meter zero offsets): commissioning run median, optionally refreshed on the first N days of this episode
        off = np.zeros(u.n)
        mode = ctx.opt["e2"]
        if mode in ("comm", "comm+first2d"):
            off += float(ctx.baseline.get("L_off", 0.0))
        if mode == "comm+first2d":
            # refresh with this unit's own first 2 days, available only from day 2 on (causal): before that the commissioning offset alone applies
            k = (u.t > 0.5 * 86400) & (u.t <= FIRST_DAYS * 86400)
            if k.sum() > 100:
                late = u.t > FIRST_DAYS * 86400
                off[late] = 0.5 * (off[late] + float(np.median(kf["L"][k])))
        ctx.cache["L_off_used"] = float(off[-1])
        Lc = kf["L"] - off
        z = Lc / np.maximum(kf["sL"], 1e-6)
        z[: 24 * 60] = 0.0                                                        # filter warm-up
        P_ = ctx.cache["clean"]["P"]
        T_k = ctx.cache["clean"]["T"] + 273.15
        flux = np.array([G.choked_mass_flux_fast(max(p, 1.0) * 1e5, t) for p, t in zip(P_[::10], T_k[::10])])
        flux = np.repeat(flux, 10)[: u.n]
        d_eq = 1e3 * np.sqrt(4.0 * np.clip(Lc, 0, None) / 3600.0 / (0.8 * flux) / np.pi)
        iref = u.raw.inv_ref_kg
        # fast leak-rate estimate for large leaks: the best (largest z) of the 5 / 10 / 20 minute slopes, each with its tail-calibrated sigma
        corr = ctx.fit.extra.get("fast_corr", {})
        fs = fast_slopes(ctx, kf, off)
        best_z = np.full(u.n, -1e9)
        Lfast, sLfast = np.zeros(u.n), np.ones(u.n)
        for w, (Lw, sw) in fs.items():
            sw = sw * corr.get(w, 2.0)
            zw = Lw / np.maximum(sw, 1e-9)
            better = zw > best_z
            best_z = np.where(better, zw, best_z)
            Lfast, sLfast = np.where(better, Lw, Lfast), np.where(better, sw, sLfast)
        Lfast[:24 * 60] = 0.0
        return {"Lfast_kgh": Lfast, "sLfast_kgh": sLfast, "Lfast_z": Lfast / np.maximum(sLfast, 1e-6), "L_kgh": Lc, "sL_kgh": kf["sL"], "L_z": z, "I_hat": kf["I"], "glr_z": g["glr_z"], "glr_window_min": g["glr_window_min"], "glr_slope_kgh": g["glr_slope_kgh"],
                "d_eq_mm": d_eq, "In": corrected_inventory(ctx) / iref}

    def call(self, ctx, i, **kw):
        m = ctx.monitor(self.name)
        u = ctx.unit
        L, sL, z = float(m["L_kgh"][i]), float(m["sL_kgh"][i]), float(m["L_z"][i])
        P_bar, T_k = float(ctx.cache["clean"]["P"][i]), float(ctx.cache["clean"]["T"][i] + 273.15)
        method = "Kalman estimator over [inventory, leak rate]"
        Lf, sLf = float(m["Lfast_kgh"][i]), float(m["sLfast_kgh"][i])
        persist = float(np.min(m["Lfast_z"][max(i - 2, 0):i + 1])) >= FAST_Z_TAIL                # a transient after a large operation does not last 3 minutes above the healthy tail
        if persist and Lf - 2.0 * sLf > L + 2.0 * sL and Lf > 1.0:                                  # a large leak that started recently: the 20-minute slope is faster than the filter
            L, sL, z, method = Lf, sLf, Lf / max(sLf, 1e-6), "20-minute slope of the metered inventory balance (fast, large leak)"
        lo_rate, hi_rate = max(L - 2.0 * sL, 0.0), max(L + 2.0 * sL, 0.0)
        d = orifice_mm(L, P_bar, T_k, 0.8)
        d_lo, d_hi = orifice_mm(lo_rate, P_bar, T_k, 1.0), orifice_mm(hi_rate, P_bar, T_k, 0.6)
        # kg released so far: integrate the estimate back to the last time it was consistent with zero (z < 0.5)
        j = i
        while j > 24 * 60 and (m["L_z"][j] >= 0.5 or m["Lfast_z"][j] >= 2.0):
            j -= 1
        Lb = np.where(m["Lfast_z"][j:i + 1] >= 3.0, np.maximum(m["L_kgh"][j:i + 1], m["Lfast_kgh"][j:i + 1]), m["L_kgh"][j:i + 1])
        released = float(np.clip(Lb, 0, None).sum() / 60.0)
        sup = list(np.round(m["In"][max(0, i - 360):i + 1:15], 4))
        v = "leak_suspected" if z >= 3.0 or float(m["glr_z"][i]) >= 4.0 else "no_leak_evidence"
        return ToolResult(self.name, v, score=z,
                          estimate={"leak_rate": {"value": round(L, 3), "lo": round(lo_rate, 3), "hi": round(hi_rate, 3), "unit": "kg/h"},
                                    "orifice_diameter": {"value": round(d, 3), "lo": round(d_lo, 3), "hi": round(d_hi, 3), "unit": "mm"},
                                    "released_so_far": {"value": round(released, 2), "unit": "kg"}},
                          series={"inventory_over_inventory_at_MOP_last6h_every15min": [float(a) for a in sup]},
                          fields={"method": method, "kalman_z": round(z, 2), "slope_test_z": round(float(m["glr_z"][i]), 2), "slope_test_window_min": int(m["glr_window_min"][i]),
                                  "unit_offset_kgh": round(float(ctx.cache.get("L_off_used", 0.0)), 3)},
                          text_en=f"Inventory is falling at {L:.2f} kg/h (95 % interval {lo_rate:.2f}-{hi_rate:.2f}); equivalent leak orifice about {d:.2f} mm ({d_lo:.2f}-{d_hi:.2f} mm); about {released:.1f} kg released so far."
                          if v == "leak_suspected" else "No sustained inventory loss beyond the metered flows.",
                          text_ar=f"المخزون ينخفض بمعدل {L:.2f} كغ/ساعة (مجال الثقة {lo_rate:.2f}-{hi_rate:.2f})؛ قطر فتحة التسرب المكافئة نحو {d:.2f} مم ({d_lo:.2f}-{d_hi:.2f} مم)؛ نحو {released:.1f} كغ تسرّبت حتى الآن."
                          if v == "leak_suspected" else "لا يوجد فقدان مستمر في المخزون يتجاوز التدفقات المقاسة.")
