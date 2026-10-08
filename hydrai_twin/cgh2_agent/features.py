"""Tool outputs -> one causal feature row per tick (the input of the fusion meta-model). Everything comes from the tools' monitor() series, i.e. from
dashboard-visible tags, OPC quality, compressor/valve states, the clock and the fast layer. The existing static alarm state is NOT a feature (T12 reports it
as context only), so the agent's detection is measured independently of the static alarms."""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools
from hydrai_twin.cgh2_agent.tools.common import ewma, ops_features

FEATURES = [
    # T1 data integrity
    "T1_spike_T_1h", "T1_spike_P_1h", "T1_bad_P_10m", "T1_bad_T_10m", "T1_flows_gated_1h", "T1_T_untrusted",
    # T2 inventory / leak (the fast 20-minute slope is NOT a fusion feature: it spikes in healthy refuelling and forced the healthy-calibrated thresholds up; it only sizes large leaks in T2.call)
    "T2_L_frac_h", "T2_L_z", "T2_glr_z", "T2_d_eq_mm", "T2_sL_frac_h",
    # T3 thermal
    "T3_z", "T3_resid_K", "T3_resid_run_K", "T3_resid_idle_K", "T3_tw_rate_z", "T3_tg_rate_Kh",
    # T4 pressure behaviour
    "T4_pc_excess", "T4_overrun_min", "T4_run_past_stop_min", "T4_p_over_pah", "T4_pfast_over_pahh", "T4_relief_open", "T4_relief_not_lifting_min", "T4_dpdt_bar_h",
    "T4_dpdt30_bar_h", "T4_disc_run_excess", "T4_pressure_collapse", "T4_p_over_mawp",
    # T5 sensor integrity
    "T5_z_ps", "T5_z_pt",
    # T6 structural
    "T6_k_rel", "T6_z",
    # fast layer (1 s) and gas detector
    "F_h2max", "F_h2rise10", "H2_slow",
    # operation context
    "O_run", "O_A", "O_B", "O_D", "O_settled", "O_hour_sin", "O_hour_cos",
]
WARMUP = 1440


def feature_matrix(ctx: Ctx) -> np.ndarray:
    """(n_ticks, n_features) float32. Rows before the 24 h warm-up are zeros."""
    load_all_tools()
    u = ctx.unit
    m1, m2, m3, m4, m5, m6 = (ctx.monitor(k) for k in ("T1_data_integrity", "T2_inventory_leak", "T3_thermal_state", "T4_pressure_behaviour", "T5_sensor_integrity", "T6_structural"))
    c = ctx.cache["clean"]
    iref = u.raw.inv_ref_kg
    mop = u.cls["mop_bar"]                                # pressure-denominated features are normalised to the 300 bar class so the other classes read on the same scale
    o = ops_features(u)
    hour = (u.t / 3600.0) % 24.0
    cols = {
        "T1_spike_T_1h": m1["spike_T_1h"], "T1_spike_P_1h": m1["spike_P_1h"], "T1_bad_P_10m": m1["bad_frac_P_10m"], "T1_bad_T_10m": m1["bad_frac_T_10m"],
        "T1_flows_gated_1h": m1["flows_gated_1h"], "T1_T_untrusted": m1["T_untrusted"],
        "T2_L_frac_h": m2["L_kgh"] / iref * 100.0, "T2_L_z": m2["L_z"], "T2_glr_z": m2["glr_z"], "T2_d_eq_mm": m2["d_eq_mm"], "T2_sL_frac_h": m2["sL_kgh"] / iref * 100.0,
        "T3_z": m3["t3_z"], "T3_resid_K": m3["t3_resid_K"], "T3_resid_run_K": m3["t3_resid_run_K"], "T3_resid_idle_K": m3["t3_resid_idle_K"],
        "T3_tw_rate_z": m3["tw_rate_z"], "T3_tg_rate_Kh": m3["tg_rate_Kh"],
        "T4_pc_excess": m4["pc_excess"], "T4_overrun_min": np.minimum(m4["overrun_min"], 600.0), "T4_run_past_stop_min": np.minimum(m4["run_past_stop_min"], 600.0),
        "T4_p_over_pah": m4["p_over_pah"], "T4_pfast_over_pahh": m4["pfast_over_pahh"], "T4_relief_open": m4["relief_open"],
        "T4_relief_not_lifting_min": np.minimum(m4["relief_not_lifting_min"], 600.0), "T4_dpdt_bar_h": m4["dpdt_bar_h"] * 300.0 / mop, "T4_dpdt30_bar_h": m4["dpdt30_bar_h"] * 300.0 / mop,
        "T4_disc_run_excess": np.minimum(m4["disc_run_excess"], 50.0), "T4_pressure_collapse": m4["pressure_collapse"], "T4_p_over_mawp": m4["p_over_mawp"],
        "T5_z_ps": m5["z_ps"], "T5_z_pt": m5["z_pt"],
        "T6_k_rel": m6["k_rel"], "T6_z": m6["k_z"],      # the cumulative fatigue count is reported by T6.call but is not a fusion feature: it drifts in healthy runs and works as an episode-age clock
        "F_h2max": u.fast["h2max"], "F_h2rise10": u.fast["rise10"], "H2_slow": c["H2"],
        "O_run": o["run"], "O_A": o["A"], "O_B": o["B"], "O_D": o["D"], "O_settled": o["settled"], "O_hour_sin": np.sin(2 * np.pi * hour / 24), "O_hour_cos": np.cos(2 * np.pi * hour / 24),
    }
    X = np.column_stack([np.nan_to_num(np.asarray(cols[k], dtype=float), nan=0.0, posinf=0.0, neginf=0.0) for k in FEATURES]).astype(np.float32)
    X[:WARMUP] = 0.0
    return X
