"""T10 forecast_consequence: what happens if nothing is done.

Leak: inventory decays as dI/dt = -L0 * (I/I0) (rate proportional to pressure, isothermal): kg released within 1 / 6 / 24 h, time until the inventory falls to
the proposed low-pressure alarm level (70 % MOP, a register OPEN decision, so it is labelled as proposed), and the inventory at risk.
Pressure rise: time to PAH / PAHH / relief set point from the T4 slope. Intervals use the leak-rate interval of T2 (+/- 2 sigma) and, for the pressure
rise, the 10-minute vs 30-minute slope. A compressor that restarts at 85 % MOP would partly refill a leaking vessel: the forecast is the unrefilled bound.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register

PAL_FRAC = 0.70               # PROPOSED low-pressure alarm (register open decision), fraction of MOP


def leak_forecast(L0: float, I0: float, I_pal: float) -> dict:
    I0 = max(float(I0), 1e-3)                                      # numerical guard: after a vessel has emptied the inventory estimate can be <= 0 (it gave inf / nan forecasts in 0.6 % of late follow-ups)
    tau = I0 / max(L0, 1e-9)                                       # h
    rel = lambda h: I0 * (1.0 - np.exp(-h / tau))
    t_pal = None if I_pal >= I0 else float(tau * np.log(I0 / I_pal))
    return {"released_1h": float(rel(1)), "released_6h": float(rel(6)), "released_24h": float(rel(24)), "t_pal_h": t_pal, "tau_h": float(tau)}


@register
class ForecastConsequence(Tool):
    name = "T10_forecast_consequence"
    description = "Time to limit (low pressure, PAH, PAHH, relief), kg released if unchecked and inventory at risk, with intervals."
    version = "1.0"
    cost = "cheap"

    def call(self, ctx, i, rate_kgh: float | None = None, rate_sigma_kgh: float | None = None, **kw):
        u = ctx.unit
        m2, m4 = ctx.monitor("T2_inventory_leak"), ctx.monitor("T4_pressure_behaviour")
        c = ctx.cache["clean"]
        L, sL = float(m2["L_kgh"][i]), float(m2["sL_kgh"][i])
        I0 = float(m2["I_hat"][i])
        P, T = float(c["P"][i]), float(c["T"][i]) + 273.15
        mop = u.cls["mop_bar"]
        I_pal = float(G.inventory_kg(PAL_FRAC * mop, T, u.cls["volume_m3"]))
        est, fields = {}, {}
        forced = rate_kgh is not None                                               # a leak rate supplied by the orchestrator (twin fit): use it instead of the filter's
        if forced:
            L, sL = float(rate_kgh), float(rate_sigma_kgh if rate_sigma_kgh is not None else 0.25 * rate_kgh)
        if (float(m2["L_z"][i]) >= 2.0 or forced) and L > 0.02:
            lo_rate, mid_rate, hi_rate = max(L - 2 * sL, 1e-3), L, L + 2 * sL
            lo, mid, hi = (leak_forecast(x, I0, I_pal) for x in (lo_rate, mid_rate, hi_rate))
            # primary scenario: the compressor keeps topping the vessel up (restarts at 85 % MOP, stops at MOP): pressure stays in the 85-100 % MOP band, so the
            # leak runs at about its current rate x (92.5 % MOP / current pressure). The no-refill bound (isothermal decay) is reported next to it.
            f_p = float(np.clip(0.925 * mop / max(P, 1.0), 0.5, 1.2))
            for h, nm in ((1, "released_in_1h"), (6, "released_in_6h"), (24, "released_in_24h")):
                est[nm] = {"value": round(mid_rate * h * f_p, 1), "lo": round(lo_rate * h * f_p, 1), "hi": round(hi_rate * h * f_p, 1), "unit": "kg (if unchecked, compressor topping up)"}
                est[nm + "_no_refill"] = {"value": round(mid["released_%dh" % h], 1), "lo": round(lo["released_%dh" % h], 1), "hi": round(hi["released_%dh" % h], 1), "unit": "kg (if unchecked, no refill: lower bound)"}
            est["time_to_proposed_low_pressure"] = {"value": None if mid["t_pal_h"] is None else round(mid["t_pal_h"], 1),
                                                    "lo": None if hi["t_pal_h"] is None else round(hi["t_pal_h"], 1),
                                                    "hi": None if lo["t_pal_h"] is None else round(lo["t_pal_h"], 1), "unit": "h (level = 70 % MOP, proposed)"}
            est["inventory_at_risk"] = {"value": round(I0, 1), "unit": "kg"}
            fields["scenario"] = "leak"
        ttl = {}
        lims = {"time_to_PAH": ("ttl_pah_h", u.cls["pah_bar"]), "time_to_PAHH": ("ttl_pahh_h", u.cls["pahh_bar"]), "time_to_relief_set": ("ttl_prv_h", u.cls["mawp_bar"])}
        for nm, (k, lim) in lims.items():
            v = float(m4[k][i]) if float(m4["collapse_trip"][i]) < 0.5 else 99.0
            if v < 99:
                cand = [max(lim - P, 0) / s for s in (float(m4["dpdt30_bar_h"][i]), float(m4["dpdt_bar_h"][i])) if s > 0.3]
                ttl[nm] = {"value": round(v, 2), "lo": round(min(cand + [v]), 2), "hi": round(max(cand + [v]), 2), "unit": "h"}
        est.update(ttl)
        if ttl:
            fields["scenario"] = (fields.get("scenario", "") + "+pressure_rise").lstrip("+")
        v = "consequence_forecast" if est else "no_adverse_trend"
        tx_en, tx_ar = ("", "") if est else ("No adverse trend to forecast.", "لا يوجد اتجاه سلبي للتنبؤ به.")
        if "released_in_24h" in est:
            r = est["released_in_24h"]
            tx_en = f"If the leak is not stopped (compressor topping up), about {est['released_in_6h']['value']:.0f} kg is lost in 6 h and {r['value']:.0f} kg ({r['lo']:.0f}-{r['hi']:.0f}) in 24 h; {I0:.0f} kg is in the vessel."
            tx_ar = f"إذا لم يُوقف التسرب (مع استمرار الضاغط في إعادة التعبئة)، تُفقد نحو {est['released_in_6h']['value']:.0f} كغ خلال 6 ساعات و{r['value']:.0f} كغ ({r['lo']:.0f}-{r['hi']:.0f}) خلال 24 ساعة؛ في الوعاء {I0:.0f} كغ."
        if "time_to_PAH" in ttl:
            tt = ttl["time_to_PAH"]
            tx_en += f"{' ' if tx_en else ''}Pressure reaches the high-pressure alarm in about {tt['value']:.1f} h."
            tx_ar += f"{' ' if tx_ar else ''}يصل الضغط إلى إنذار الضغط العالي خلال نحو {tt['value']:.1f} ساعة."
        return ToolResult(self.name, v, score=None, estimate=est, fields=fields, text_en=tx_en, text_ar=tx_ar)
