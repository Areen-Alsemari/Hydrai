"""
Tool parameters learned from HEALTHY dev data (cross-fitted: a module's tools never use parameters fitted on that module). Low-capacity linear models on
purpose, so fitting on training modules only leaves almost no room to overfit.

  E3  bulk gas-temperature corrector: a ridge model of (bulk - probe) from online-available operation features (compressor charging/decay, draws, shell
      minus gas, diurnal phase). Its target is the twin's bulk temperature, which a site would get from a commissioning reference probe: a TRAINING label only.
  noise  inventory-estimate error (kg) after correction, split settled / unsettled, for the Kalman filter's measurement noise
  T3  healthy regression of the gas temperature on shell, ambient, diurnal phase and operation state, and its residual spread
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hydrai_twin.cgh2_agent.tools.common import inventory, ops_features


def design(unit) -> tuple[np.ndarray, list[str]]:
    o = ops_features(unit)
    raw = unit.raw
    hour = (unit.t / 3600.0) % 24.0
    dT = raw.x["T"] - raw.x["Tw"]
    cols = {"one": np.ones(unit.n), "A": o["A"], "B": o["B"], "D": o["D"], "dT_gw": dT, "A_dT": o["A"] * dT, "hour_sin": np.sin(2 * np.pi * hour / 24), "hour_cos": np.cos(2 * np.pi * hour / 24),
            "run": o["run"], "ambient_minus_gas": raw.x["Ta"] - raw.x["T"]}
    return np.column_stack(list(cols.values())), list(cols)


def t3_design(unit, T=None, Tw=None, Ta=None) -> np.ndarray:
    """Regressors of the healthy gas-temperature model (T3): operation state, diurnal phase, shell and ambient temperature."""
    Xu, cols = design(unit)
    keep = [c for c in range(Xu.shape[1]) if cols[c] not in ("dT_gw", "A_dT", "ambient_minus_gas")]
    return np.column_stack([Xu[:, keep], unit.raw.x["Tw"] if Tw is None else Tw, unit.raw.x["Ta"] if Ta is None else Ta])


def ridge(X: np.ndarray, y: np.ndarray, lam: float = 1.0) -> np.ndarray:
    A = X.T @ X + lam * np.eye(X.shape[1])
    A[0, 0] -= lam
    return np.linalg.solve(A, X.T @ y)


GLR_WINDOWS = (60, 120, 240, 480, 1440)           # minutes: 1 h .. 24 h (the 30 min window is dominated by the gradient noise and is left out)


def hold_slopes(x: np.ndarray, w: int) -> np.ndarray:
    """OLS slope per HOUR over the trailing w samples (60 s spacing); NaN while the window is filling."""
    i = np.arange(w) - (w - 1) / 2.0
    k = i / np.sum(i * i)
    return np.concatenate([np.full(w - 1, np.nan), np.convolve(x, k[::-1], mode="valid") * 60.0])


@dataclass
class Fit:
    grad_coef: np.ndarray | None = None
    grad_cols: list[str] = field(default_factory=list)
    sigma_I: dict[str, float] = field(default_factory=lambda: {"settled": 0.9, "unsettled": 3.0})          # kg at the class inventory scale (set in fit_tools)
    sigma_I_uncorrected: dict[str, float] = field(default_factory=dict)
    sigma_I10: dict[str, float] = field(default_factory=lambda: {"settled": 0.003, "unsettled": 0.004})     # error of a 10-minute MEAN of the inventory estimate (fraction of class inventory)
    glr_sigma: dict[int, float] = field(default_factory=dict)                 # spread (fraction of class inventory per hour) of the healthy hold-window slope, by window (minutes)
    t3_coef: np.ndarray | None = None
    t3_cols: list[str] = field(default_factory=list)
    t3_sigma: float = 1.0
    extra: dict = field(default_factory=dict)          # T3/T4/T5 healthy-data parameters (see `fit_extra`)
    notes: dict = field(default_factory=dict)

    def gradient(self, unit) -> np.ndarray:
        """Estimated (bulk - probe) in K, added to the probe before computing inventory."""
        if self.grad_coef is None:
            return np.zeros(unit.n)
        X, cols = design(unit)
        return X @ self.grad_coef


def fit_tools(train_units: list, use_e3: bool = True) -> Fit:
    """`train_units`: healthy dev units (Unit objects; their .truth holds the twin's bulk temperature and mass, used only as TRAINING labels)."""
    fit = Fit()
    X, y, st = [], [], []
    for u in train_units:
        Xu, cols = design(u)
        k = np.arange(u.n) > 360
        X.append(Xu[k]); y.append((u.truth["gas_temp_bulk_c"] - u.raw.x["T"])[k])
    X, y = np.vstack(X), np.concatenate(y)
    fit.grad_cols = cols
    if use_e3:
        fit.grad_coef = ridge(X, y)
    # inventory error after correction, by regime (relative to the class inventory so it transfers)
    err_c, err_u, sett = [], [], []
    for u in train_units:
        k = np.arange(u.n) > 360
        Tcorr = u.raw.x["T"] + fit.gradient(u)
        Ic = inventory(u.raw.x["P"], Tcorr, u.cls["volume_m3"])
        Iu = inventory(u.raw.x["P"], u.raw.x["T"], u.cls["volume_m3"])
        o = ops_features(u)
        err_c.append(((Ic - u.truth["mass_kg"]) / u.raw.inv_ref_kg)[k]); err_u.append(((Iu - u.truth["mass_kg"]) / u.raw.inv_ref_kg)[k]); sett.append((o["settled"] >= 1.0)[k])
    ec, eu, s = np.concatenate(err_c), np.concatenate(err_u), np.concatenate(sett)
    # robust spread (MAD) around the regime median; a constant per-unit offset is removed by the commissioning baseline
    mad = lambda a: 1.4826 * np.median(np.abs(a - np.median(a)))
    fit.sigma_I = {"settled": float(mad(ec[s])), "unsettled": float(mad(ec[~s]))}                       # fractions of the class inventory
    e10, s10 = [], []
    for a, b in zip(err_c, sett):
        m10 = len(a) // 10
        e10.append(a[: m10 * 10].reshape(-1, 10).mean(axis=1)); s10.append(b[: m10 * 10].reshape(-1, 10).mean(axis=1) > 0.5)
    e10, s10 = np.concatenate(e10), np.concatenate(s10)
    fit.sigma_I10 = {"settled": float(mad(e10[s10])), "unsettled": float(mad(e10[~s10]))}
    # healthy hold-window slopes (for the GLR slope test): spread of the OLS slope of the corrected inventory over quiet windows
    from hydrai_twin.cgh2_agent.tools.common import gated_flows, ops_features as _ops
    slopes: dict[int, list] = {w: [] for w in GLR_WINDOWS}
    for u in train_units:
        Ic = inventory(u.raw.x["P"], u.raw.x["T"] + fit.gradient(u), u.cls["volume_m3"]) / u.raw.inv_ref_kg
        gf, gd, _ = gated_flows(u)
        quiet = (~(np.nan_to_num(u.raw.disc_state["comp"], nan=0.0) > 0.5)) & (gd < 0.03) & (gf < 0.03)
        for w in GLR_WINDOWS:
            ok = np.convolve(quiet.astype(int), np.ones(w, int), mode="full")[: u.n] >= w
            sl = hold_slopes(Ic, w)
            slopes[w].append(sl[ok & np.isfinite(sl)])
    fit.glr_sigma = {w: float(1.4826 * np.median(np.abs(np.concatenate(v) - np.median(np.concatenate(v))))) if sum(len(a) for a in v) > 50 else 0.01 for w, v in slopes.items()}
    fit.sigma_I_uncorrected = {"settled": float(mad(eu[s])), "unsettled": float(mad(eu[~s]))}
    # T3: healthy regression of gas temperature
    X3, y3 = [], []
    for u in train_units:
        Xu, cols3 = design(u)
        Xu = Xu[:, [c for c in range(Xu.shape[1]) if cols3[c] not in ("dT_gw", "A_dT", "ambient_minus_gas")]]
        k = np.arange(u.n) > 360
        Xw = np.column_stack([Xu, u.raw.x["Tw"], u.raw.x["Ta"]])
        X3.append(Xw[k]); y3.append(u.raw.x["T"][k])
    X3, y3 = np.vstack(X3), np.concatenate(y3)
    fit.t3_coef = ridge(X3, y3)
    fit.t3_cols = [c for c in cols3 if c not in ("dT_gw", "A_dT", "ambient_minus_gas")] + ["Tw", "Ta"]
    r3 = y3 - X3 @ fit.t3_coef
    fit.t3_sigma = float(1.4826 * np.median(np.abs(r3 - np.median(r3))))
    fit.extra = fit_extra(fit, train_units)
    fit.notes = {"n_train_units": len(train_units), "grad_rows": int(len(y)),
                 "inventory_error_mad_frac": {"corrected": fit.sigma_I, "uncorrected": fit.sigma_I_uncorrected}}
    return fit


def fit_extra(fit: "Fit", train_units: list) -> dict:
    """Healthy-data scales for the model-based tools (T3 smoothed residual, wall-temperature rate, P-strain and P-T redundancy residuals, longest healthy
    continuous discharge, compensated-pressure excess). Robust spreads of residuals on HEALTHY dev units of the training modules only."""
    from hydrai_twin.cgh2_agent.tools.common import dpdt_bar_per_k, ewma, gated_flows, mad_sigma, slope_per_h
    X_st, y_st = [], []
    for u in train_units:
        k = np.arange(u.n) > 1440
        X_st.append(np.column_stack([np.ones(u.n), u.raw.x["P"], u.raw.x["Tw"]])[k]); y_st.append(u.raw.x["strain"][k])
    st_coef = np.linalg.lstsq(np.vstack(X_st), np.concatenate(y_st), rcond=None)[0]
    fit.extra = {"st_coef": st_coef, "st_hoop_ref": float(train_units[0].cls["hoop_strain_ue_per_bar"])}             # available to the tools run below (T1 confirms pressure with strain)
    t3r, twr, str_, ptr, runs, exc = [], [], [], [], [], []
    for u in train_units:
        k = np.arange(u.n) > 1440
        r3 = ewma(u.raw.x["T"] - t3_design(u) @ fit.t3_coef, 20.0)
        t3r.append(r3[k])
        twr.append(slope_per_h(u.raw.x["Tw"], 30)[k])
        rs = u.raw.x["strain"] - np.column_stack([np.ones(u.n), u.raw.x["P"], u.raw.x["Tw"]]) @ st_coef
        str_.append(ewma(rs, 30.0)[k])
        gf, gd, _ = gated_flows(u)
        quiet = (gf < 0.02) & (gd < 0.02)
        w = 30
        okq = np.convolve(quiet.astype(int), np.ones(w + 1, int), mode="full")[: u.n] >= w + 1
        dP = np.concatenate([np.zeros(w), u.raw.x["P"][w:] - u.raw.x["P"][:-w]])
        dT = np.concatenate([np.zeros(w), u.raw.x["T"][w:] - u.raw.x["T"][:-w]])
        pt = dP - dpdt_bar_per_k(u.raw.x["P"]) * dT
        ptr.append(pt[k & okq])
        d = gd > 0.02
        run, best = 0, 0
        for v in d:
            run = run + 1 if v else 0
            best = max(best, run)
        runs.append(best)
        mop = u.cls["mop_bar"]
        Pc = u.raw.x["P"] - dpdt_bar_per_k(u.raw.x["P"]) * (u.raw.x["T"] - u.entry.get("compensation_ref_temp_c", 60.0))
        exc.append(((Pc - mop) / mop)[k])
    from hydrai_twin.cgh2_agent.tools.t6_structural import stiffness_series
    krs = []
    for u in train_units:
        kr = stiffness_series(u, float(st_coef[2]))["k_rel"]
        krs.append(kr[u.t > 2.5 * 86400])
    # fast leak-rate estimator (T2): per window, the factor that puts the healthy 99.5th percentile of |slope / white-noise sigma| at FAST_Z_TAIL
    from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools
    from hydrai_twin.cgh2_agent.tools.t2_inventory_leak import FAST_WINDOWS, FAST_Z_TAIL, fast_slopes, kalman
    load_all_tools()
    zs = {w: [] for w in FAST_WINDOWS}
    for u in train_units:
        ctx = Ctx(u, fit)
        kf = kalman(ctx)
        for w, (Lw, sw) in fast_slopes(ctx, kf).items():
            zs[w].append(np.abs(Lw / np.maximum(sw, 1e-9))[2 * 1440:])
    fast_corr = {w: float(max(np.percentile(np.concatenate(v), 99.5) / FAST_Z_TAIL, 1.0)) for w, v in zs.items()}
    cat = lambda L: np.concatenate(L)
    return {"st_hoop_ref": float(train_units[0].cls["hoop_strain_ue_per_bar"]), "fast_corr": fast_corr, "k_rel_sigma": max(mad_sigma(cat(krs)), 1e-3), "st_coef": st_coef, "t3_sigma_s": mad_sigma(cat(t3r)), "tw_rate_sigma": mad_sigma(cat(twr)), "st_sigma_s": mad_sigma(cat(str_)),
            "pt_sigma_bar": mad_sigma(cat(ptr)), "disc_run_p99_min": float(np.percentile(runs, 99)) if len(runs) else 60.0, "disc_run_max_min": float(max(runs)),
            "pc_excess_p999": float(np.percentile(cat(exc), 99.9))}
