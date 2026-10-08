"""T1 data_integrity: quality flags, causal despiking, stale / constant-value detection and historian-view cleanup.

The historian can hand over implausible values with Good quality (a ramp towards an injected out-of-range sample was observed: 343 bar read while the live
value was 189). T1 holds a sample that jumps further than physics allows from the trailing median for up to 3 ticks (then accepts it if it persists: a
real step such as a rupture is not hidden for more than 3 minutes), and reports what it held out. A held-out temperature value is EVIDENCE of probe
trouble, not just noise: T5 reads the count. Cleaned series are what every other tool reads.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import gated_flows, strain_model

HOLD = 3
STALE_T_TICKS = 60
WIN = 9


def despike(x: np.ndarray, thr: float, hold: int = HOLD, win: int = WIN, confirmed: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Hold a sample that jumps further than physics allows from the trailing median for up to `hold` ticks. `confirmed[i]` = an independent gauge agrees with the new
    value, so the change is real (a rupture or a fast leak) and is accepted at once instead of being held against a stale median."""
    out = x.copy()
    flag = np.zeros(len(x), dtype=bool)
    run = 0
    buf: list[float] = []
    for i, v in enumerate(x):
        m = np.median(buf) if len(buf) >= 3 else v
        if confirmed is not None and confirmed[i]:
            run = 0
            buf = buf[-2:] if abs(v - m) > thr else buf                      # a confirmed step: restart the reference near the new level
        elif abs(v - m) > thr and run < hold:
            out[i], flag[i] = m, True
            run += 1
        else:
            run = 0
        buf.append(out[i])
        if len(buf) > win:
            buf.pop(0)
    return out, flag


def roll_count(flag: np.ndarray, w: int) -> np.ndarray:
    c = np.concatenate([[0.0], np.cumsum(flag.astype(float))])
    out = c[w:] - c[:-w]
    return np.concatenate([c[1:w], out]) if w > 1 else c[1:]


def run_length_unchanged(r: np.ndarray, cap: int = 2000) -> np.ndarray:
    ch = np.concatenate([[True], np.abs(np.diff(np.nan_to_num(r, nan=-9e9))) > 1e-12])
    idx = np.where(ch, np.arange(len(r)), 0)
    return np.minimum(np.arange(len(r)) - np.maximum.accumulate(idx), cap).astype(float)


@register
class DataIntegrity(Tool):
    name = "T1_data_integrity"
    description = "OPC quality, causal despiking, stale/constant-value runs and historian-view cleanup; supplies the cleaned series every other tool reads."
    version = "1.0"
    cost = "cheap"

    def monitor(self, ctx):
        u, raw = ctx.unit, ctx.unit.raw
        mop = u.cls["mop_bar"]
        out: dict[str, np.ndarray] = {}
        clean = {}
        for k, thr in (("strain", 600.0), ("Tw", 10.0), ("Ta", 10.0), ("T", 12.0), ("P", 0.06 * mop)):                      # strain and shell first: they confirm the pressure
            conf = None
            if k == "P" and ctx.fit is not None and "st_coef" in ctx.fit.extra:
                a_, k_, c_ = strain_model(ctx.fit, u)
                P_strain = (clean["strain"] - a_ - c_ * clean["Tw"]) / k_
                conf = np.abs(P_strain - raw.x["P"]) < max(0.1 * mop, 100.0 / k_)                 # 5 sigma of a 1 % FS strain gauge
            clean[k], fl = despike(raw.x[k], thr, confirmed=conf)
            out[f"spike_{k}"] = fl.astype(float)
            out[f"spike_{k}_1h"] = roll_count(fl, 60)
        for k in ("H2", "fill", "disc"):
            clean[k] = raw.x[k]
        if ctx.opt.get("gate_flows", True):
            clean["fill_min"], clean["disc_min"], gated = gated_flows(u)
            out["flows_gated_1h"] = roll_count(gated > 0, 60)
        else:
            clean["fill_min"], clean["disc_min"] = u.fill_min, u.disc_min
            out["flows_gated_1h"] = np.zeros(u.n)
        for k in ("P", "T", "fill", "disc"):
            bad = (~raw.good[k]).astype(float)
            out[f"bad_frac_{k}_10m"] = roll_count(bad, 10) / 10.0
            out[f"stale_{k}"] = run_length_unchanged(raw.raw[k])
        # a gas-temperature probe flat for >= 1 h while below the high-temperature alarm is treated as stuck: the model-expected temperature replaces it
        # (the compensated stop, the inventory and the thermal observer would otherwise run on a frozen value). A stuck value above 80 C is left alone.
        stuck = (out["stale_T"] >= STALE_T_TICKS) & (clean["T"] < 80.0)
        if stuck.any() and ctx.fit is not None and ctx.fit.t3_coef is not None:
            from hydrai_twin.cgh2_agent.fit import t3_design
            T_exp = t3_design(u, Tw=clean["Tw"], Ta=clean["Ta"]) @ ctx.fit.t3_coef
            clean["T"] = np.where(stuck, T_exp, clean["T"])
        out["T_untrusted"] = stuck.astype(float)
        ctx.cache["clean"] = clean
        out["trust"] = ((out["bad_frac_P_10m"] < 0.5) & (out["bad_frac_T_10m"] < 0.5)).astype(float)
        return out

    def call(self, ctx, i, **kw):
        m = ctx.monitor(self.name)
        w = slice(max(0, i - 59), i + 1)
        sp_t, sp_p = int(m["spike_T_1h"][i]), int(m["spike_P_1h"][i])
        bad = {k: float(m[f"bad_frac_{k}_10m"][i]) for k in ("P", "T", "fill", "disc")}
        v = "temperature_probe_erratic" if sp_t >= 3 else "pressure_value_implausible_held" if sp_p >= 1 else "data_ok" if m["trust"][i] > 0 else "data_quality_poor"
        return ToolResult(self.name, v, score=float(sp_t), fields={"temperature_spikes_1h": sp_t, "pressure_spikes_held_1h": sp_p, "bad_fraction_10min": bad},
                          text_en={"temperature_probe_erratic": f"{sp_t} implausible gas-temperature readings in the last hour: the probe looks erratic.",
                                   "pressure_value_implausible_held": "A pressure value outside physical limits was held out (historian artifact); not treated as a pressure event.",
                                   "data_ok": "Data quality is normal.", "data_quality_poor": "More than half of the recent pressure or temperature samples are not Good quality."}[v],
                          text_ar={"temperature_probe_erratic": f"{sp_t} قراءات غير منطقية لحرارة الغاز خلال الساعة الأخيرة: مسبار الحرارة يبدو غير مستقر.",
                                   "pressure_value_implausible_held": "تم استبعاد قيمة ضغط خارج الحدود الفيزيائية (خلل في سجل البيانات) ولم تُعامل كحدث ضغط.",
                                   "data_ok": "جودة البيانات طبيعية.", "data_quality_poor": "أكثر من نصف عينات الضغط أو الحرارة الأخيرة ليست بجودة جيدة."}[v])
