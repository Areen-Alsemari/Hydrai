"""T5 sensor_integrity: analytic redundancy between gauges.

  * pressure vs strain: the hoop strain follows pressure (and shell temperature); a persistent disagreement says one of the two is off
  * pressure vs temperature: with no gas moving the density is constant, so a pressure change must match dP/dT x the temperature change; a temperature
    probe that moves without the pressure following (or the reverse) is lying
  * T1 evidence: held-out spikes on the temperature probe, stale values, gated flow meters
The suspect gauge and the pressure it implies elsewhere (strain-equivalent) are reported; when only one pair disagrees the tool says which pairs and
names the likely culprit but marks it ambiguous. Subtle slow drift (0.5-2 % FS over days) is NOT evaluated: the dataset contains no such episodes.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import dpdt_bar_per_k, ewma, strain_model


@register
class SensorIntegrity(Tool):
    name = "T5_sensor_integrity"
    description = "Analytic redundancy (pressure vs strain vs temperature vs flow balance); which gauge is lying and the probable true value."
    version = "1.0"
    cost = "cheap"

    def monitor(self, ctx):
        u, fit = ctx.unit, ctx.fit
        t1 = ctx.monitor("T1_data_integrity")
        c = ctx.cache["clean"]
        a_, k_, c_ = strain_model(fit, u)
        st_hat = a_ + k_ * c["P"] + c_ * c["Tw"]
        rs = c["strain"] - st_hat
        ps_off = ewma(rs, 30.0)
        # per-unit strain offset: the first 2 days define the unit's own zero (commissioning-style baseline), so a constant sensor offset is not mistaken for a fault
        k = (u.t > 0.5 * 86400) & (u.t <= 2.0 * 86400)
        base = float(np.median(rs[k])) if k.sum() > 100 else 0.0
        z_ps = (ps_off - base) / fit.extra["st_sigma_s"]
        z_ps[: 2 * 1440] = 0.0
        w = 30
        P, T = c["P"], c["T"]
        dP = np.concatenate([np.zeros(w), P[w:] - P[:-w]])
        dT = np.concatenate([np.zeros(w), T[w:] - T[:-w]])
        quiet = (c["fill_min"] < 0.02) & (c["disc_min"] < 0.02)
        okq = np.convolve(quiet.astype(int), np.ones(w + 1, int), mode="full")[: u.n] >= w + 1
        pt = np.where(okq, dP - dpdt_bar_per_k(P) * dT, 0.0)
        z_pt = ewma(pt, 15.0) / (fit.extra["pt_sigma_bar"] * u.cls["mop_bar"] / 300.0)
        z_pt[: 1440] = 0.0
        strain_equiv_bar = (c["strain"] - base - a_ - c_ * c["Tw"]) / k_
        return {"z_ps": z_ps, "z_pt": z_pt, "strain_equiv_P_bar": strain_equiv_bar, "spike_T_1h": t1["spike_T_1h"], "spike_P_1h": t1["spike_P_1h"], "stale_T": t1["stale_T"],
                "stale_P": t1["stale_P"], "flows_gated_1h": t1["flows_gated_1h"], "bad_frac_P_10m": t1["bad_frac_P_10m"], "bad_frac_T_10m": t1["bad_frac_T_10m"]}

    def call(self, ctx, i, **kw):
        m = ctx.monitor(self.name)
        g = lambda k: float(m[k][i])
        sus = {"temperature_probe": g("spike_T_1h") / 3.0 + (1.0 if g("stale_T") > 240 else 0.0) + max(abs(g("z_pt")) - 3.0, 0.0) / 3.0,
               "pressure_transmitter": g("spike_P_1h") + (1.0 if g("stale_P") > 240 else 0.0) + max(abs(g("z_ps")) - 3.0, 0.0) / 3.0 * (1.0 if abs(g("z_pt")) > 3 else 0.5),
               "strain_gauge": max(abs(g("z_ps")) - 3.0, 0.0) / 3.0 * (0.5 if abs(g("z_pt")) > 3 else 1.0),
               "flow_meters": g("flows_gated_1h") / 10.0}
        who = max(sus, key=sus.get)
        v = "no_sensor_fault_evidence" if sus[who] < 1.0 else f"{who}_suspect"
        ambiguous = sorted(sus.values())[-1] - sorted(sus.values())[-2] < 0.5 and sus[who] >= 1.0
        P = float(ctx.cache["clean"]["P"][i])
        est = {"suspicion": {k: round(val, 2) for k, val in sus.items()}, "probable_true_pressure": {"value": round(float(m["strain_equiv_P_bar"][i]), 1), "unit": "bar (strain-equivalent)"} if v.startswith("pressure") else {"value": round(P, 1), "unit": "bar (as read)"}}
        en = ("Gauges agree with each other." if v == "no_sensor_fault_evidence" else f"{who.replace('_', ' ')} looks unreliable" + (" (ambiguous: another pair also disagrees)" if ambiguous else "") + f"; pressure-strain z {g('z_ps'):.1f}, pressure-temperature z {g('z_pt'):.1f}, {g('spike_T_1h'):.0f} implausible temperature values in the last hour.")
        ar = ("المقاييس متوافقة فيما بينها." if v == "no_sensor_fault_evidence" else f"المستشعر المشتبه به: {who} " + ("(غير محسوم: زوج آخر من المقاييس يختلف أيضاً)" if ambiguous else "") + f"؛ فرق الضغط-الانفعال {g('z_ps'):.1f}، فرق الضغط-الحرارة {g('z_pt'):.1f}، {g('spike_T_1h'):.0f} قراءات حرارة غير منطقية في الساعة الأخيرة.")
        return ToolResult(self.name, v, score=max(sus.values()), estimate=est, fields={"z_pressure_strain": round(g("z_ps"), 2), "z_pressure_temperature": round(g("z_pt"), 2), "ambiguous": bool(ambiguous)}, text_en=en, text_ar=ar)
