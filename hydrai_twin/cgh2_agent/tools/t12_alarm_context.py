"""T12 alarm_context: what the existing static alarms say now, what they would say, and how many alarms the operator is already carrying."""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register


@register
class AlarmContext(Tool):
    name = "T12_alarm_context"
    description = "Existing static alarm state now, which limits are close, time since the first static alarm and the recent alarm load."
    version = "1.0"
    cost = "cheap"

    def call(self, ctx, i, **kw):
        u = ctx.unit
        if "clean" not in ctx.cache:
            ctx.monitor("T1_data_integrity")
        c = ctx.cache["clean"]
        cl = u.cls
        h2 = float(c["H2"][i])
        near = {"PAH": float(c["P"][i]) / cl["pah_bar"], "PAHH": float(c["P"][i]) / cl["pahh_bar"], "TAH": float(c["T"][i]) / 85.0, "TAHH": float(c["T"][i]) / 100.0,
                "H2_alarm": h2 / 25.0, "H2_trip": h2 / 50.0}
        active = bool(u.static[i])
        last_h = int(np.sum(np.diff(u.static[max(0, i - 60):i + 1].astype(int)) == 1))
        first = np.flatnonzero(u.static[: i + 1])
        t_first = None if len(first) == 0 else float((i - first[0]) / 60.0)
        closest = max(near, key=near.get)
        v = "static_alarm_active" if active else ("static_alarm_near" if near[closest] >= 0.9 else "static_alarms_quiet")
        tx_en = {"static_alarm_active": f"A static alarm is active (first one {t_first:.1f} h ago)." if t_first is not None else "A static alarm is active.",
                 "static_alarm_near": f"No static alarm yet; closest limit is {closest} at {100 * near[closest]:.0f} % of its set point.",
                 "static_alarms_quiet": "No static alarm is active and none is close to its limit: the existing alarm system is silent."}[v]
        tx_ar = {"static_alarm_active": f"يوجد إنذار ثابت فعّال (أول إنذار منذ {t_first:.1f} ساعة)." if t_first is not None else "يوجد إنذار ثابت فعّال.",
                 "static_alarm_near": f"لا يوجد إنذار ثابت بعد؛ أقرب حد هو {closest} عند {100 * near[closest]:.0f}% من نقطة الضبط.",
                 "static_alarms_quiet": "لا يوجد إنذار ثابت فعّال ولا حد قريب: نظام الإنذار الحالي صامت."}[v]
        return ToolResult(self.name, v, score=near[closest], estimate={"closest_limit": {"value": closest, "fraction_of_setpoint": round(near[closest], 3)}},
                          fields={"static_active": active, "alarm_onsets_last_hour": last_h, "hours_since_first_static_alarm": t_first}, text_en=tx_en, text_ar=tx_ar)
