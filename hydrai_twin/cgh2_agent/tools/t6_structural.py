"""T6 structural: strain-per-pressure stiffness drift and excess fatigue damage.

Hoop strain is stiffness-proportional to pressure (strain = k x P + thermal offset). A growing stress concentration raises k. A forgetting-factor regression
of strain on pressure (shell-temperature term removed with the healthy coefficient) tracks k(t); the unit's own k over days 1-2 is its baseline, so a fixed
gauge factor or mounting offset cancels. `fatigue_excess` counts equivalent extra healthy cycles accumulated, with damage per compressor cycle ~ (k/k0)^3.
Compared with a raw strain threshold, which cannot see a stiffness change while the pressure is low.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import ewma, ops_features

TAU_MIN = 720.0                    # 12 h forgetting time
BASE_DAYS = (1.0, 2.0)


def stiffness_series(unit, c_tw: float) -> dict[str, np.ndarray]:
    P, S, Tw = unit.raw.x["P"], unit.raw.x["strain"], unit.raw.x["Tw"]
    y = S - c_tw * Tw
    mP, mY = ewma(P, TAU_MIN), ewma(y, TAU_MIN)
    vPP = ewma(P * P, TAU_MIN) - mP * mP
    cPY = ewma(P * y, TAU_MIN) - mP * mY
    ok = vPP > (0.03 * unit.cls["mop_bar"]) ** 2
    k = np.where(ok, cPY / np.maximum(vPP, 1e-9), np.nan)
    kf = np.array(k)
    last = np.nan
    for i in range(len(kf)):                                   # hold the last valid estimate while the pressure is steady
        if np.isfinite(kf[i]):
            last = kf[i]
        else:
            kf[i] = last
    sel = (unit.t >= BASE_DAYS[0] * 86400) & (unit.t <= BASE_DAYS[1] * 86400) & np.isfinite(kf)
    k0 = float(np.median(kf[sel])) if sel.sum() > 100 else float(np.nanmedian(kf))
    k_rel = np.where(unit.t > BASE_DAYS[1] * 86400, kf / k0 - 1.0, 0.0)
    return {"k": kf, "k_rel": np.nan_to_num(k_rel), "k0": np.full(len(kf), k0)}


@register
class Structural(Tool):
    name = "T6_structural"
    description = "Strain-per-pressure stiffness drift against the unit's own baseline and excess fatigue damage; compare raw strain thresholds."
    version = "1.0"
    cost = "cheap"

    def monitor(self, ctx):
        u, fit = ctx.unit, ctx.fit
        s = stiffness_series(u, float(fit.extra["st_coef"][2]))
        sig = fit.extra["k_rel_sigma"]
        z = s["k_rel"] / sig
        o = ops_features(u)
        run = o["run"] > 0.5
        stops = np.concatenate([[0.0], ((~run[1:]) & run[:-1]).astype(float)])
        dmg = stops * (np.maximum(1.0 + s["k_rel"], 0.0) ** 3 - 1.0)
        return {"k_ue_per_bar": s["k"], "k_rel": s["k_rel"], "k_z": z, "fatigue_excess_cycles": np.cumsum(np.where(u.t > BASE_DAYS[1] * 86400, dmg, 0.0)), "cycles": np.cumsum(stops)}

    def call(self, ctx, i, **kw):
        m = ctx.monitor(self.name)
        sig = ctx.fit.extra["k_rel_sigma"]
        kr, z = float(m["k_rel"][i]), float(m["k_z"][i])
        v = "stiffness_drift" if z >= 4.0 else "structure_normal"
        est = {"strain_per_pressure_change": {"value": round(100 * kr, 2), "lo": round(100 * (kr - 2 * sig), 2), "hi": round(100 * (kr + 2 * sig), 2), "unit": "% vs the unit's own baseline"},
               "excess_fatigue": {"value": round(float(m["fatigue_excess_cycles"][i]), 2), "unit": "equivalent extra healthy cycles"}}
        en = (f"Strain per bar has risen {100 * kr:.1f} % above this vessel's own baseline ({float(m['fatigue_excess_cycles'][i]):.1f} extra healthy-cycle equivalents of fatigue so far): stress concentration growing."
              if v == "stiffness_drift" else "Strain responds to pressure as it did at commissioning.")
        ar = (f"الانفعال لكل بار ارتفع بنسبة {100 * kr:.1f}% فوق خط الأساس لهذا الوعاء (نحو {float(m['fatigue_excess_cycles'][i]):.1f} دورة تعب مكافئة زائدة حتى الآن): تركّز الإجهاد في ازدياد."
              if v == "stiffness_drift" else "استجابة الانفعال للضغط كما كانت عند التشغيل الأولي.")
        return ToolResult(self.name, v, score=z, estimate=est, fields={"k_z": round(z, 2), "cycles_total": int(m["cycles"][i])}, text_en=en, text_ar=ar)
