"""T9 twin_verifier: simulate a hypothesis with the digital twin and compare with what the dashboard shows.

The recent window is replayed through the two-node real-gas vessel model, started from the observed inventory and temperatures, driven by the metered
fill and discharge flows, with the shell temperature held at its measured value. The healthy hypothesis and the proposed one (leak at the estimated rate,
or extra heat input) are scored on how well they reproduce the observed pressure (and temperature). The verdict is accept / reject / need-more-data.
This tool is the one that uses the simulator; it never reads ground truth.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2.vessel import PRV, Vessel
from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register
from hydrai_twin.cgh2_agent.tools.common import inventory

P_NOISE_BAR = 0.35                 # pressure noise floor of the comparison (transmitter accuracy and the anchor error), bar at the medium class
LEAK_GRID_KGH = tuple(np.geomspace(1.0, 800.0, 16))
Q_GRID_W = (0.5e3, 1e3, 2e3, 5e3, 10e3, 20e3, 50e3)


def simulate(ctx, i: int, window: int, leak_kgh: float = 0.0, q_ext_w: float = 0.0, leak_start: int | None = None):
    u, fit = ctx.unit, ctx.fit
    c = ctx.cache["clean"]
    j = max(i - window, 0)
    grad = fit.gradient(u)
    cls = SimpleNamespace(**u.cls)
    k0 = slice(j, min(j + 6, i))
    P0, T0 = float(np.mean(c["P"][k0])), float(np.mean(c["T"][k0] + grad[k0]))
    m0 = float(inventory(np.array([P0]), np.array([T0]), cls.volume_m3)[0])
    veh = Vessel(cls, PRV(1e9, 0.05, 1.1, 10.0, 0.9), m0, T0 + 273.15, float(c["Tw"][j]) + 273.15)
    area = 0.0
    if leak_kgh > 0:
        area = (leak_kgh / 3600.0) / max(G.choked_mass_flux_fast(P0 * 1e5, T0 + 273.15), 1e-9)
    leak_k0 = j if leak_start is None else leak_start                  # tick at which the leak begins (default: the start of the window)
    P_sim, T_sim = np.zeros(i - j + 1), np.zeros(i - j + 1)
    P_sim[0], T_sim[0] = veh.P_bar, veh.Tg - 273.15
    for n, k in enumerate(range(j + 1, i + 1), start=1):
        veh.Tw = float(c["Tw"][k]) + 273.15
        r = veh.step(60.0, float(c["Tw"][k]) + 273.15, mdot_in=float(c["fill_min"][k]) / 60.0, T_in_k=310.0, mdot_disp=float(c["disc_min"][k]) / 60.0, leak_area_m2=(area if k >= leak_k0 else 0.0), q_ext_w=q_ext_w)
        P_sim[n], T_sim[n] = r["P_bar"], r["Tg_k"] - 273.15
    return j, P_sim, T_sim


@register
class TwinVerifier(Tool):
    name = "T9_twin_verifier"
    description = "Replays the recent window through the digital twin under a hypothesis (leak at the estimated rate, extra heat) and compares with the observations: accept / reject / ask for more data."
    version = "1.0"
    cost = "expensive"

    def _leak_fit(self, ctx, i: int, span: int, noise: float) -> ToolResult:
        """Search leak rate and start time (grid) for the best match to the last `span` minutes of pressure: the sizing mode for leaks that are too young or too
        fast for the inventory-balance estimators (a vessel emptying in minutes cools adiabatically, which the twin includes)."""
        c = ctx.cache["clean"]
        j = max(i - span, 0)
        starts = sorted({j, i - span // 2, i - 5, i - 3})
        score_from = max(i - 10, j)
        P_obs = c["P"][score_from:i + 1]
        err = lambda Ps: float(np.sqrt(np.mean((P_obs - Ps[score_from - j:]) ** 2)))
        _, P0s, _ = simulate(ctx, i, span)
        e0 = err(P0s)
        grid = []
        for k0 in starts:
            for L in LEAK_GRID_KGH:
                _, Ps, _ = simulate(ctx, i, span, leak_kgh=float(L), leak_start=k0)
                grid.append((err(Ps), float(L), k0))
        e1, L1, k1 = min(grid)
        ok = [g for g in grid if g[0] <= 1.3 * e1 + 0.5 * noise]
        lo, hi = min(g[1] for g in ok), max(g[1] for g in ok)
        gain = e0 - e1
        verdict = "accept" if (e1 <= 0.6 * e0 and gain >= noise) else "reject" if e1 >= 0.9 * e0 else "need_more_data"
        P_bar, T_k = float(c["P"][i]), float(c["T"][i]) + 273.15
        from hydrai_twin.cgh2_agent.tools.t2_inventory_leak import orifice_mm
        d, d_lo, d_hi = orifice_mm(L1, P_bar, T_k, 0.8), orifice_mm(lo, P_bar, T_k, 1.0), orifice_mm(hi, P_bar, T_k, 0.6)
        started = i - k1
        released = L1 * started / 60.0
        en = (f"Twin fit of the last {span} min: a leak of about {L1:.1f} kg/h ({lo:.1f}-{hi:.1f}) equivalent to a {d:.2f} mm orifice ({d_lo:.2f}-{d_hi:.2f} mm) that began about {started} min ago explains the pressure far better than a healthy vessel (error {e1:.2f} vs {e0:.2f} bar)."
              if verdict == "accept" else f"The twin does not find a leak that explains the last {span} min better than a healthy vessel (error {e1:.2f} vs {e0:.2f} bar).")
        ar = (f"مطابقة التوأم الرقمي لآخر {span} دقيقة: تسرب بنحو {L1:.1f} كغ/ساعة ({lo:.1f}-{hi:.1f}) يكافئ فتحة {d:.2f} مم ({d_lo:.2f}-{d_hi:.2f} مم) بدأ منذ نحو {started} دقيقة يفسّر الضغط أفضل بكثير من وعاء سليم (خطأ {e1:.2f} مقابل {e0:.2f} بار)."
              if verdict == "accept" else f"لا يجد التوأم الرقمي تسرباً يفسّر آخر {span} دقيقة بشكل أفضل من وعاء سليم (خطأ {e1:.2f} مقابل {e0:.2f} بار).")
        return ToolResult(self.name, verdict, score=gain / max(noise, 1e-6),
                          estimate={"leak_rate": {"value": round(L1, 2), "lo": round(lo, 2), "hi": round(hi, 2), "unit": "kg/h"}, "orifice_diameter": {"value": round(d, 3), "lo": round(d_lo, 3), "hi": round(d_hi, 3), "unit": "mm"},
                                    "released_so_far": {"value": round(released, 2), "unit": "kg"}, "rms_error_healthy": {"value": round(e0, 3), "unit": "bar"}, "rms_error_hypothesis": {"value": round(e1, 3), "unit": "bar"}},
                          fields={"hypothesis": "leak_fit", "window_min": span, "leak_started_min_ago": int(started)}, text_en=en, text_ar=ar)

    def call(self, ctx, i, hypothesis: str = "leak", window_min: int = 180, rate_kgh: float | None = None, **kw):
        u = ctx.unit
        if "clean" not in ctx.cache:
            ctx.monitor("T1_data_integrity")
        c = ctx.cache["clean"]
        window = int(min(window_min, i))
        mop = u.cls["mop_bar"]
        noise = P_NOISE_BAR * mop / 300.0
        if hypothesis == "leak_fit":
            return self._leak_fit(ctx, i, min(window, 20), noise)
        j, P0s, T0s = simulate(ctx, i, window)
        P_obs, T_obs = c["P"][j:i + 1], c["T"][j:i + 1]
        q4 = len(P_obs) // 4
        err = lambda Ps: float(np.sqrt(np.mean((P_obs[q4:] - Ps[q4:]) ** 2)))
        e0 = err(P0s)
        best, e1, label = {}, e0, "none"
        unit_lbl = "bar"
        if hypothesis == "leak":
            L = rate_kgh
            if L is None:
                L = float(ctx.monitor("T2_inventory_leak")["L_kgh"][i])
            if L > 1e-3:
                _, P1s, T1s = simulate(ctx, i, window, leak_kgh=L)
                e1, label = err(P1s), f"leak {L:.2f} kg/h"
                best = {"leak_rate_kgh": round(L, 3), "final_pressure_residual_bar_healthy": round(float(P_obs[-1] - P0s[-1]), 2),
                        "final_pressure_residual_bar_hypothesis": round(float(P_obs[-1] - P1s[-1]), 2)}
        elif hypothesis == "heating":
            unit_lbl = "K"
            errs = []
            for q in Q_GRID_W:
                _, Ps, Ts = simulate(ctx, i, window, q_ext_w=q)
                errs.append((float(np.sqrt(np.mean((T_obs[q4:] - Ts[q4:]) ** 2))), q))
            e0 = float(np.sqrt(np.mean((T_obs[q4:] - T0s[q4:]) ** 2)))
            e1, q = min(errs)
            label = f"extra heat input {q / 1e3:.1f} kW"
            noise = 0.5
            best = {"heat_input_kw": round(q / 1e3, 1)}
        gain = e0 - e1
        if label == "none":
            verdict = "need_more_data"
        elif e0 <= 1.5 * noise and gain < noise:
            verdict = "reject"                                           # the healthy twin already explains the window
        elif e1 <= 0.6 * e0 and gain >= noise:
            verdict = "accept"
        elif e1 >= 0.9 * e0:
            verdict = "reject"
        else:
            verdict = "need_more_data"
        en = {"accept": f"The twin reproduces the last {window} min much better with {label} (RMS error {e1:.2f} vs {e0:.2f} {unit_lbl} for a healthy vessel).",
              "reject": f"Adding {label} does not improve the match (RMS error {e1:.2f} vs {e0:.2f} {unit_lbl} for a healthy vessel)." if label != "none" else "No hypothesis to test.",
              "need_more_data": f"The twin cannot decide between healthy and {label}: errors {e0:.2f} vs {e1:.2f} {unit_lbl}. A hold test or a longer window is needed."}[verdict]
        ar = {"accept": f"التوأم الرقمي يعيد إنتاج آخر {window} دقيقة بدقة أفضل بكثير مع الفرضية ({label}): خطأ {e1:.2f} مقابل {e0:.2f} لوعاء سليم.",
              "reject": f"إضافة الفرضية ({label}) لا تحسّن المطابقة: خطأ {e1:.2f} مقابل {e0:.2f} لوعاء سليم.",
              "need_more_data": f"لا يستطيع التوأم الرقمي الحسم بين الوعاء السليم والفرضية ({label}): الأخطاء {e0:.2f} مقابل {e1:.2f}. يلزم اختبار احتجاز أو نافذة أطول."}[verdict]
        return ToolResult(self.name, verdict, score=gain / max(noise, 1e-6),
                          estimate={"rms_error_healthy": {"value": round(e0, 3), "unit": unit_lbl}, "rms_error_hypothesis": {"value": round(e1, 3), "unit": unit_lbl}},
                          fields={"hypothesis": hypothesis, "label": label, "window_min": window, **best}, text_en=en, text_ar=ar)
