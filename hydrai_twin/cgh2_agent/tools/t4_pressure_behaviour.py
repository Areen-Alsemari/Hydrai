"""T4 pressure_behaviour: pressure against the control logic.

The compressor starts at 85 % MOP and stops when the pressure, compensated to a design gas temperature, reaches MOP. T4 compares the observed pressure
and valve/compressor states with that logic: compensated-pressure overrun, compressor running past its stop, relief lift (state or pressure above the
set point), pressure above MAWP while no relief opens (blocked relief), a discharge valve open far longer than any healthy draw (stuck open), and the
pressure slope with its time to PAH / PAHH / relief set point.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import dpdt_bar_per_k, ewma, slope_per_h


# fast-layer trips: twice the largest drop seen in HEALTHY dev data (30 s window: 0.014 x MOP; 1-minute slow-layer step: 0.0275 x MOP), set a priori from healthy behaviour
COLLAPSE_30S = 0.03
COLLAPSE_1MIN = 0.055


def run_len(flag: np.ndarray) -> np.ndarray:
    out = np.zeros(len(flag))
    for i in range(1, len(flag)):
        out[i] = out[i - 1] + 1.0 if flag[i] else 0.0
    return out


@register
class PressureBehaviour(Tool):
    name = "T4_pressure_behaviour"
    description = "Compares pressure and valve/compressor states with the control logic: overrun, stuck valve, blocked relief, relief lift; time to PAH/PAHH/PRV."
    version = "1.0"
    cost = "cheap"

    def monitor(self, ctx):
        u, fit = ctx.unit, ctx.fit
        ctx.monitor("T1_data_integrity")
        c = ctx.cache["clean"]
        mop, cls = u.cls["mop_bar"], u.cls
        P, T = c["P"], c["T"]
        ref = u.entry.get("compensation_ref_temp_c") or 60.0                      # controller configuration (design gas temperature of the compensated stop)
        Pc = P - dpdt_bar_per_k(P) * (T - ref) if u.entry.get("stop_mode") == "compensated" else P.copy()
        excess = (Pc - mop) / mop
        thr = max(fit.extra["pc_excess_p999"], 0.004) + 0.005
        over = excess > thr
        comp = u.raw.disc_state["comp"]
        run = (np.nan_to_num(comp, nan=0.0) > 0.5) if np.isfinite(comp).any() else (c["fill_min"] > 0.05)
        prv_state = u.raw.disc_state["prv"]
        relief_open = (np.nan_to_num(prv_state, nan=0.0) > 0.5) | (u.fast["prv"] > 0.5)
        dv = u.raw.disc_state["dvalve"]
        dv_open = (np.nan_to_num(dv, nan=0.0) > 0.5) if np.isfinite(dv).any() else (c["disc_min"] > 0.02)
        disc_run = run_len((c["disc_min"] > 0.02) | (dv_open & (c["disc_min"] > 0.005)))
        dpdt10 = slope_per_h(P, 10)
        dpdt30 = slope_per_h(P, 30)
        slope = np.where(dpdt10 > 0, np.minimum(dpdt10, np.maximum(dpdt30, 0.0) * 3.0 + 1.0), dpdt10)
        pah, pahh, mawp, setp = cls["pah_bar"], cls["pahh_bar"], cls["mawp_bar"], cls["mawp_bar"]
        run_past = run_len(run & (excess > -0.003))
        abnormal_rise = (excess > 0.0) | (run_past >= 5) | ((~run) & (dpdt10 > 0.3))              # a normal charge toward MOP is not an adverse trend
        ttl = lambda lim: np.where((slope > 0.3) & abnormal_rise, np.clip((lim - P) / np.maximum(slope, 0.3), 0.0, 99.0), 99.0)
        not_lifting = run_len((P > 1.04 * mawp) & ~relief_open)
        p_fast = np.maximum(P, u.fast["pmax"])
        Pr, good = u.raw.x["P"], u.raw.good["P"]
        drop1 = np.zeros(u.n)
        drop1[1:] = np.where(good[1:] & good[:-1], (Pr[:-1] - Pr[1:]) / mop, 0.0)
        trip = (u.fast["drop30"] >= COLLAPSE_30S) | (drop1 >= COLLAPSE_1MIN)
        return {"pc_excess": excess, "overrun_min": run_len(over), "run_past_stop_min": run_past,
                "p_over_pah": P / pah, "p_over_pahh": P / pahh, "p_over_mawp": P / mawp, "pfast_over_pahh": p_fast / pahh, "relief_open": relief_open.astype(float),
                "relief_not_lifting_min": not_lifting, "dpdt_bar_h": dpdt10, "dpdt30_bar_h": dpdt30,
                "disc_run_min": disc_run, "disc_run_excess": disc_run / max(fit.extra["disc_run_p99_min"], 1.0), "ttl_pah_h": ttl(pah), "ttl_pahh_h": ttl(pahh), "ttl_prv_h": ttl(setp),
                "comp_run": run.astype(float), "pressure_collapse": u.fast["drop30"], "drop_1min": drop1, "collapse_trip": trip.astype(float)}

    def call(self, ctx, i, **kw):
        m = ctx.monitor(self.name)
        g = lambda k: float(m[k][i])
        mop = ctx.unit.cls["mop_bar"]
        if g("collapse_trip") > 0.5:
            v = "pressure_collapse"
        elif g("relief_not_lifting_min") >= 3:
            v = "relief_blocked_suspected"
        elif g("relief_open") > 0.5:
            v = "relief_lifted"
        elif g("run_past_stop_min") >= 10 and g("overrun_min") >= 5:
            v = "compressor_overrun"
        elif g("disc_run_excess") > 1.5:
            v = "discharge_valve_stuck_open_suspected"
        elif g("p_over_pah") > 1.0:
            v = "pressure_high"
        else:
            v = "pressure_normal"
        est = {"overrun": {"value": round(g("pc_excess") * mop, 2), "unit": "bar over compensated stop"},
               "pressure_slope": {"value": round(g("dpdt_bar_h"), 2), "unit": "bar/h"}}
        for nm, k in (("time_to_PAH", "ttl_pah_h"), ("time_to_PAHH", "ttl_pahh_h"), ("time_to_relief_set", "ttl_prv_h")):
            est[nm] = {"value": None if g(k) >= 99 else round(g(k), 2), "unit": "h"}
        tx = {"relief_blocked_suspected": ("Pressure is above the vessel rating and no relief valve is lifting: the relief path may be blocked.", "الضغط أعلى من تصنيف الوعاء ولا يوجد فتح لصمام التنفيس: قد يكون مسار التنفيس مسدوداً."),
              "relief_lifted": ("The relief valve is lifting.", "صمام التنفيس يعمل (مفتوح)."),
              "compressor_overrun": (f"The compressor keeps running {g('overrun_min'):.0f} min past its stop pressure ({g('pc_excess') * mop:.1f} bar over): stop logic failure suspected.", f"الضاغط يواصل العمل منذ {g('overrun_min'):.0f} دقيقة بعد ضغط الإيقاف (بزيادة {g('pc_excess') * mop:.1f} بار): يُشتبه بعطل منطق الإيقاف."),
              "discharge_valve_stuck_open_suspected": (f"Discharge has been open {g('disc_run_min'):.0f} min, far longer than any normal draw: valve may be stuck open.", f"التفريغ مفتوح منذ {g('disc_run_min'):.0f} دقيقة، أطول بكثير من أي سحب طبيعي: قد يكون الصمام عالقاً مفتوحاً."),
              "pressure_collapse": (f"Pressure fell {100 * max(g('pressure_collapse'), g('drop_1min')):.0f} % of the rated pressure within a minute: rupture or major release suspected.", f"انخفض الضغط بنسبة {100 * max(g('pressure_collapse'), g('drop_1min')):.0f}% من الضغط المقنن خلال دقيقة: يُشتبه بتمزق أو تسرب كبير."),
              "pressure_high": ("Pressure is above the high-pressure alarm level.", "الضغط أعلى من مستوى إنذار الضغط العالي."),
              "pressure_normal": ("Pressure behaviour agrees with the control logic.", "سلوك الضغط متوافق مع منطق التحكم.")}[v]
        return ToolResult(self.name, v, score=g("p_over_pah"), estimate=est, series={"pressure_over_PAH_last3h_every10min": [round(float(a), 4) for a in m["p_over_pah"][max(0, i - 180):i + 1:10]]},
                          fields={k: round(g(k), 3) for k in ("overrun_min", "run_past_stop_min", "relief_not_lifting_min", "disc_run_min", "p_over_mawp", "pressure_collapse", "drop_1min")}, text_en=tx[0], text_ar=tx[1])
