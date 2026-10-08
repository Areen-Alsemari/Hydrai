"""T3 thermal_state: model-based observer of the gas and shell temperature.

Expected gas temperature comes from a low-capacity healthy regression on ambient, shell temperature, diurnal phase and the operation state (charging
rise, post-charge decay, draw cooling). The residual (smoothed, in units of its healthy spread) flags overheating; WHERE it appears separates the
likely causes: during/after charging (cooling failure), with the shell heating up fast (external or fire heating), or neither (probe or ambient).
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.fit import t3_design
from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import ewma, ops_features, slope_per_h

TAH_C, TAHH_C = 85.0, 100.0                 # dashboard static limits (registry TAH / TAHH)


@register
class ThermalState(Tool):
    name = "T3_thermal_state"
    description = "Expected gas and shell temperature from ambient, diurnal phase, fills and draws; residual for overheating, cooling failure and fire heating."
    version = "1.0"
    cost = "cheap"

    def monitor(self, ctx):
        u, fit = ctx.unit, ctx.fit
        ctx.monitor("T1_data_integrity")
        c = ctx.cache["clean"]
        o = ops_features(u)
        X = t3_design(u, T=c["T"], Tw=c["Tw"], Ta=c["Ta"])
        r = c["T"] - X @ fit.t3_coef
        rs = ewma(r, 20.0)
        sig = fit.extra["t3_sigma_s"]
        tw_rate = slope_per_h(c["Tw"], 30)
        tg_rate = slope_per_h(c["T"], 60)
        z = rs / sig
        z[: 1440] = 0.0
        # residual separately for charging periods and for the rest: the cause shows in where it appears
        run = o["run"] > 0.5
        r_run, r_idle = ewma(np.where(run, r, np.nan), 90.0), ewma(np.where(~run, r, np.nan), 90.0)
        return {"t3_resid_K": rs, "t3_z": z, "t3_resid_run_K": r_run, "t3_resid_idle_K": r_idle, "tw_rate_Kh": tw_rate, "tw_rate_z": tw_rate / fit.extra["tw_rate_sigma"],
                "tg_rate_Kh": tg_rate, "T_gas_C": c["T"], "T_wall_C": c["Tw"]}

    def call(self, ctx, i, **kw):
        m = ctx.monitor(self.name)
        z, rK = float(m["t3_z"][i]), float(m["t3_resid_K"][i])
        tw_z, tg_rate = float(m["tw_rate_z"][i]), float(m["tg_rate_Kh"][i])
        Tg = float(m["T_gas_C"][i])
        run_K, idle_K = float(m["t3_resid_run_K"][i]), float(m["t3_resid_idle_K"][i])
        s = ctx.fit.extra["t3_sigma_s"]
        if z >= 4.0 and tw_z >= 4.0:
            v = "external_heating_suspected"
        elif z >= 4.0 and run_K > 2.0 * max(idle_K, 0.5):
            v = "cooling_failure_suspected"
        elif z >= 4.0:
            v = "overheating"
        else:
            v = "thermal_normal"

        def ttl(limit):
            if tg_rate <= 0.2:
                return None
            return max(limit - Tg, 0.0) / tg_rate
        est = {"excess_temperature": {"value": round(rK, 2), "lo": round(rK - 2 * s, 2), "hi": round(rK + 2 * s, 2), "unit": "K"},
               "gas_temperature_rate": {"value": round(tg_rate, 2), "unit": "K/h"}}
        for nm, lim in (("time_to_TAH", TAH_C), ("time_to_TAHH", TAHH_C)):
            t = ttl(lim)
            est[nm] = {"value": None if t is None else round(t, 2), "unit": "h"}
        text = {"external_heating_suspected": (f"Gas is {rK:.1f} K hotter than the model expects and the shell is heating at {float(m['tw_rate_Kh'][i]):.1f} K/h: external heat source or fire exposure suspected.",
                                               f"الغاز أسخن بمقدار {rK:.1f} كلفن مما يتوقعه النموذج وجدار الوعاء يسخن بمعدل {float(m['tw_rate_Kh'][i]):.1f} كلفن/ساعة: يُشتبه بمصدر حرارة خارجي أو تعرّض لحريق."),
                "cooling_failure_suspected": (f"Gas is {rK:.1f} K above expectation, mostly while charging: the compressor intercooler may have failed.",
                                              f"الغاز أعلى من المتوقع بمقدار {rK:.1f} كلفن وخاصة أثناء التعبئة: قد يكون مبرّد الضاغط متعطلاً."),
                "overheating": (f"Gas is {rK:.1f} K above the model expectation without a matching shell rise.", f"الغاز أعلى من المتوقع بمقدار {rK:.1f} كلفن دون ارتفاع مماثل في جدار الوعاء."),
                "thermal_normal": ("Gas and shell temperatures agree with the model.", "درجات حرارة الغاز والوعاء متوافقة مع النموذج.")}[v]
        return ToolResult(self.name, v, score=z, estimate=est, series={"gas_residual_K_last6h_every15min": [round(float(a), 2) for a in m["t3_resid_K"][max(0, i - 360):i + 1:15]]},
                          fields={"residual_z": round(z, 2), "shell_rate_z": round(tw_z, 2), "residual_running_K": round(run_K, 2), "residual_idle_K": round(idle_K, 2)},
                          text_en=text[0], text_ar=text[1])
