"""Write the two single-file dashboards (English, Arabic RTL) from template.html + data.json.   python build_html.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = {
 "plant": ["Compressed-hydrogen storage (CGH2)", "تخزين الهيدروجين المضغوط (CGH2)"],
 "plant_sub": ["existing plant dashboard + HYDRAI read-only add-on", "لوحة المصنع الحالية + إضافة HYDRAI للقراءة فقط"],
 "replay_time": ["Replay time", "زمن إعادة التشغيل"],
 "disclaimer": ["Simulated reference configuration, not a verified Saudi system", "تكوين مرجعي محاكى، وليس نظاماً سعودياً تم التحقق منه"],
 "src_ep_note": ["replay of the digital twin", "إعادة تشغيل للتوأم الرقمي"],
 "tier_none": ["normal", "طبيعي"], "tier_normal": ["normal", "طبيعي"], "tier_watch": ["watch", "مراقبة"], "tier_alert": ["alert", "تنبيه"], "tier_critical": ["critical", "حرج"], "tier": ["Tier", "المستوى"],
 "run": ["RUN", "يعمل"], "stop": ["STOP", "متوقف"], "module": ["Module", "الوحدة"], "gas_p": ["Gas pressure", "ضغط الغاز"], "gas_t": ["Gas temp.", "حرارة الغاز"],
 "compressor": ["Compressor", "الضاغط"], "static_alarms": ["Static alarms", "الإنذارات الثابتة"], "active": ["ACTIVE", "فعّال"], "quiet": ["quiet", "صامت"],
 "no_static_title": ["No static alarm is active", "لا يوجد إنذار ثابت فعّال"], "limits": ["Alarm limits", "حدود الإنذار"],
 "overview_note": ["M01 replays the 0.5 mm leak episode; M02–M06 replay their own normal episodes at the same replay time.", "تعرض M01 حلقة التسرب 0.5 مم؛ وتعرض M02–M06 حلقاتها الطبيعية عند زمن الإعادة نفسه."],
 "pressure": ["Pressure", "الضغط"], "p_short": ["P, bar(a)", "الضغط، بار"], "t_short": ["T, °C", "الحرارة، °م"], "tags_now": ["tags at this instant", "المتغيرات في هذه اللحظة"], "wall_temp": ["Outer wall temp.", "حرارة الجدار الخارجي"], "fill_flow": ["Fill flow", "تدفق التعبئة"], "disc_flow": ["Discharge flow", "تدفق التفريغ"], "strain": ["Strain", "الانفعال"], "ambient": ["Ambient temperature", "حرارة المحيط"], "gas_temp": ["Gas temperature", "حرارة الغاز"], "gas_det": ["Gas detector", "كاشف الغاز"],
 "compressor_s": ["Compressor", "الضاغط"], "inlet_v": ["Inlet valve", "صمام المدخل"], "disc_v": ["Discharge valve", "صمام التفريغ"], "prv": ["Relief valve", "صمام التنفيس"], "static_alarm_s": ["Static alarm", "الإنذار الثابت"],
 "x_replay_h": ["Replay time, h", "زمن إعادة التشغيل، ساعة"],
 "p_modules": ["Plant dashboard · modules", "لوحة المصنع · الوحدات"], "read_only": ["read-only", "للقراءة فقط"], "p_trends": ["Plant dashboard · tag trends", "لوحة المصنع · اتجاهات المتغيرات"],
 "p_plant": ["Plant dashboard (existing)", "لوحة المصنع (الحالية)"], "p_hydrai": ["HYDRAI (add-on)", "HYDRAI (إضافة)"], "addon": ["read-only side channel", "قناة جانبية للقراءة فقط"],
 "comp_inv": ["Temperature-compensated inventory", "المخزون المصحَّح حرارياً"], "leak_rate_est": ["Leak-rate estimate, 95 % band", "تقدير معدل التسرب (نطاق 95٪)"],
 "detector": ["Detector", "الجهة"], "first_alarm": ["First alarm", "أول إنذار"], "after_onset": ["After onset", "بعد بدء العطل"], "replay_h": ["replay h", "ساعة الإعادة"],
 "none_episode": ["none in the whole episode", "لا إنذار طوال الحلقة"], "op_proxy": ["Modelled operator", "مشغّل نموذجي"], "op_note_short": ["not a human study", "وليس دراسة على بشر"],
 "gap_line": ["HYDRAI warned {g} h before the modelled operator would have acted", "حذّر HYDRAI قبل المشغّل النموذجي بمقدار {g} ساعة"],
 "class": ["Class", "الفئة"], "probability": ["probability", "الاحتمال"], "action": ["Recommended action", "الإجراء الموصى به"], "why": ["Physical reason", "السبب الفيزيائي"],
 "approve": ["Approve action", "الموافقة على الإجراء"], "reject": ["Reject", "رفض"],
 "leak_rate": ["Leak rate", "معدل التسرب"], "interval95": ["95 % interval", "مجال ثقة 95٪"], "orifice": ["Equivalent orifice", "قطر الفتحة المكافئ"],
 "released": ["Released so far (estimate)", "المتسرّب حتى الآن (تقدير)"], "released_note": ["inventory tool", "أداة المخزون"],
 "warned_at": ["HYDRAI alert", "تنبيه HYDRAI"], "after_onset_l": ["after onset (twin ground truth)", "بعد بدء العطل (حقيقة التوأم)"],
 "static_now": ["Static alarms", "الإنذارات الثابتة"], "no_static_short": ["none close to a limit", "لا حد قريب"], "alert_by": ["raised at replay time", "صدر عند زمن الإعادة"],
 "sim_op": ["Simulated operator step: in the replay the simulated operator approved after {m} min. Buttons are shown static.", "خطوة المشغّل المحاكى: وافق المشغّل المحاكى في إعادة التشغيل بعد {m} دقائق. الأزرار معروضة بشكل ثابت."],
 "hist_title": ["Decisions after the alert (replay)", "القرارات بعد التنبيه (إعادة التشغيل)"], "min_after": ["min after onset", "دقيقة بعد بدء العطل"], "sim_op_gen": ["Simulated operator step: the buttons are shown static.", "خطوة المشغّل المحاكى: الأزرار معروضة بشكل ثابت."], "evidence": ["Evidence (tool outputs)", "الأدلة (مخرجات الأدوات)"], "released_short": ["released", "المتسرّب"],
 "p_alert": ["HYDRAI alert detail", "تفاصيل تنبيه HYDRAI"], "p_follow": ["How the estimate develops", "تطور التقدير"],
 "t9_fit": ["Twin fit of the last {w} min: pressure error {a} bar against {b} bar for a healthy vessel", "مطابقة التوأم لآخر {w} دقيقة: خطأ الضغط {a} بار مقابل {b} بار لوعاء سليم"],
 "t9_replay": ["Twin replay of the last {w} min: pressure error {a} bar against {b} bar for a healthy vessel", "إعادة تشغيل التوأم لآخر {w} دقيقة: خطأ الضغط {a} بار مقابل {b} بار لوعاء سليم"],
 "t11": ["Hold test of at least {h} h recommended", "يوصى باختبار احتجاز لا يقل عن {h} ساعات"],
 "t10": ["Consequence forecast computed (estimate only, not shown here)", "حُسب تنبؤ العواقب (تقدير فقط، غير معروض هنا)"],
 "st_monitor": ["score below watch level", "الدرجة دون مستوى المراقبة"], "st_suspect": ["score above watch level", "الدرجة فوق مستوى المراقبة"], "st_invest": ["tool calls", "استدعاء الأدوات"],
 "st_decide": ["tier, class, action", "المستوى والفئة والإجراء"], "st_await": ["simulated operator", "المشغّل المحاكى"], "st_follow": ["re-checks +10, +30 min, then hourly", "إعادة فحص بعد 10 و30 دقيقة ثم كل ساعة"],
 "st_close": ["score below watch for 2 h", "الدرجة دون المراقبة لساعتين"],
 "inv_calls": ["Tool calls in INVESTIGATE", "استدعاءات الأدوات في مرحلة INVESTIGATE"], "inv_at": ["at replay time", "عند زمن الإعادة"], "calls": ["calls", "استدعاءات"],
 "tool": ["Tool", "الأداة"], "verdict": ["Verdict", "النتيجة"], "result": ["Result", "الخلاصة"],
 "decide_line": ["Decision: {tier} · {cls} · {p} %", "القرار: {tier} · {cls} · {p}٪"], "p_trace": ["Reasoning trace of one decision", "مسار الاستدلال لقرار واحد"],
 "x_after_onset": ["Hours after fault onset (twin ground truth)", "الساعات بعد بدء العطل (حقيقة التوأم)"],
 "hy_sub": ["fusion of tool outputs", "دمج مخرجات الأدوات"], "static_sub": ["PAH, PAHH, TAH, TAHH, H₂", "PAH, PAHH, TAH, TAHH, H₂"], "op_sub": ["looks every 15 min", "ينظر كل 15 دقيقة"],
 "onset_gt": ["fault onset (twin ground truth)", "بدء العطل (حقيقة التوأم)"], "static_none": ["no alarm in the whole 14-day episode", "لا إنذار طوال الحلقة (14 يوماً)"], "gap_short": ["{g} h earlier", "أبكر بمقدار {g} ساعة"],
 "kg_before": ["Released before the alarm, kg (twin ground truth)", "المتسرّب قبل الإنذار، كغ (حقيقة التوأم)"],
 "kg_note": ["kg = hydrogen leaked between fault onset and the first alarm, from the twin's own leak mass flow.", "كغ = الهيدروجين المتسرّب بين بدء العطل وأول إنذار، من تدفق التسرب في التوأم نفسه."],
 "op_def": ["Modelled operator, not a human study: looks at the raw dashboard every 15 min; acts when the raw pressure is {x} bar below the compressor working band or the gas is {y} K above ambient (thresholds set once on healthy data, 1 false alarm per week per rule).",
            "مشغّل نموذجي وليس دراسة على بشر: ينظر إلى اللوحة الخام كل 15 دقيقة؛ ويتحرك عندما ينخفض الضغط الخام بمقدار {x} بار عن نطاق عمل الضاغط أو ترتفع حرارة الغاز {y} كلفن فوق المحيط (حدود ثُبّتت مرة واحدة على بيانات سليمة، إنذار كاذب واحد أسبوعياً لكل قاعدة)."],
 "p_who": ["Who warned when · 0.5 mm leak", "من حذّر ومتى · تسرب 0.5 مم"],
 "fleet_src": ["fleet, replay state of six modules", "الأسطول، حالة إعادة التشغيل لست وحدات"], "comp_inv_s": ["Comp. inventory", "المخزون المصحَّح"], "hy_score": ["HYDRAI score", "درجة HYDRAI"],
 "watch_l": ["watch", "مراقبة"], "alert_l": ["alert", "تنبيه"], "hy_state": ["HYDRAI state", "حالة HYDRAI"],
 "excess_t": ["Gas above expectation", "الغاز فوق المتوقع"], "diagnosis": ["Diagnosis", "التشخيص"], "t3_resid": ["Gas temperature above expectation (tool T3)", "حرارة الغاز فوق المتوقع (الأداة T3)"],
 "p_thermal_ev": ["Evidence · intercooler failure", "الأدلة · عطل المبرّد الوسيط"],
}
if __name__ == "__main__":
    data = (HERE / "data.json").read_text()
    tpl = (HERE / "template.html").read_text()
    for lang, d in (("en", "ltr"), ("ar", "rtl")):
        html = tpl.replace("__LANG__", lang).replace("__DIR__", d).replace("/*DATA*/", data).replace("/*I18N*/", json.dumps(I, ensure_ascii=False))
        (HERE / f"hydrai_dashboard_{lang}.html").write_text(html)
        print(lang, round(len(html) / 1024), "KB")
