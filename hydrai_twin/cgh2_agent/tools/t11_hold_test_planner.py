"""T11 hold_test_planner: when the evidence for a small leak is ambiguous, recommend a hold test (compressor off, inlet and discharge closed, no draw) and say how
long it must last for the leak rate to be resolved against the quiet-window noise of this vessel class (healthy spread of the inventory slope by window length)."""

from __future__ import annotations

import numpy as np

from hydrai_twin.cgh2_agent.fit import GLR_WINDOWS
from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register


@register
class HoldTestPlanner(Tool):
    name = "T11_hold_test_planner"
    description = "Recommends a hold test and its duration so that the suspected leak rate is resolved (3 sigma) against the quiet-window slope noise."
    version = "1.0"
    cost = "cheap"

    def call(self, ctx, i, **kw):
        m2 = ctx.monitor("T2_inventory_leak")
        iref = ctx.unit.raw.inv_ref_kg
        L = max(float(m2["L_kgh"][i]), 0.0)
        sL = float(m2["sL_kgh"][i])
        sig = ctx.fit.glr_sigma
        need = None
        for w in GLR_WINDOWS:
            if L >= 3.0 * sig.get(w, 0.01) * iref:
                need = w
                break
        floor_rate = 3.0 * sig.get(GLR_WINDOWS[-1], 0.01) * iref
        if need is None:
            v = "hold_test_cannot_resolve"
            en = f"A leak of {L:.2f} kg/h is below what a 24 h hold test resolves for this vessel ({floor_rate:.2f} kg/h at 3 sigma); keep monitoring or improve the flow-meter zero stability."
            ar = f"تسرب بمعدل {L:.2f} كغ/ساعة أقل مما يمكن حسمه باختبار احتجاز لمدة 24 ساعة لهذا الوعاء ({floor_rate:.2f} كغ/ساعة عند 3 سيجما)؛ واصل المراقبة أو حسّن استقرار صفر عدّاد التدفق."
            est = {"min_resolvable_rate": {"value": round(floor_rate, 2), "unit": "kg/h"}}
        else:
            hrs = need / 60.0
            v = "hold_test_recommended"
            en = f"Run a hold test of at least {hrs:.0f} h (compressor off, inlet and discharge closed, no draw): a leak of {L:.2f} kg/h (0-{L + 2 * sL:.2f}) is then resolved at 3 sigma."
            ar = f"أجرِ اختبار احتجاز لا يقل عن {hrs:.0f} ساعة (الضاغط متوقف، المدخل والمخرج مغلقان، بدون سحب): عندها يمكن حسم تسرب بمعدل {L:.2f} كغ/ساعة (0-{L + 2 * sL:.2f}) عند 3 سيجما."
            est = {"hold_duration": {"value": round(hrs, 1), "unit": "h"}, "min_resolvable_rate": {"value": round(3.0 * sig[need] * iref, 2), "unit": "kg/h"}}
        return ToolResult(self.name, v, score=None, estimate=est, fields={"suspected_leak_kgh": round(L, 3)}, text_en=en, text_ar=ar)
