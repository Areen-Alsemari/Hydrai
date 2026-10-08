"""T13 procedures: rule table (class x severity) of recommended actions in English and Arabic, each with the physical reason. Advisory only: the operator approves."""

from __future__ import annotations

from hydrai_twin.cgh2_agent.tools import Tool, ToolResult, register

CLASS_NAMES = {0: ("healthy", "سليم"), 1: ("sensor fault", "عطل مستشعر"), 2: ("thermal anomaly", "شذوذ حراري"), 3: ("small slow leak", "تسرب صغير بطيء"),
               4: ("abnormal pressure behaviour", "سلوك ضغط غير طبيعي"), 5: ("containment anomaly", "شذوذ في الاحتواء"), 6: ("structural concern", "مخاوف إنشائية"), -1: ("unknown pattern", "نمط غير معروف")}

# (action_en, action_ar, reason_en, reason_ar) by (class, severity)
RULES = {
    (3, "watch"): ("Plan a hold test (compressor off, no draw) at the next quiet period and keep monitoring.", "خطّط لاختبار احتجاز (الضاغط متوقف وبدون سحب) في أقرب فترة هادئة وواصل المراقبة.",
                   "A small leak shows as a steady inventory loss only when no gas moves.", "التسرب الصغير يظهر كفقدان ثابت للمخزون عندما لا يتحرك الغاز فقط."),
    (3, "alert"): ("Inspect fittings and flanges with a portable H2 detector; limit refuelling; prepare to isolate if the loss rate rises.", "افحص الوصلات والفلنجات بكاشف هيدروجين محمول؛ قلّل التعبئة؛ استعد للعزل إذا زاد معدل الفقد.",
                   "Hydrogen is flammable from 4 % in air; a leak in a confined space can accumulate.", "الهيدروجين قابل للاشتعال من 4% في الهواء؛ والتسرب في مكان مغلق قد يتراكم."),
    (3, "critical"): ("Isolate the vessel, stop refuelling, ventilate, remove ignition sources and call the site safety officer.", "اعزل الوعاء، أوقف التعبئة، هوِّ المكان، أزل مصادر الاشتعال واتصل بمسؤول السلامة.",
                      "The release rate is large enough to form a flammable cloud.", "معدل التسرب كبير بما يكفي لتكوّن سحابة قابلة للاشتعال."),
    (5, "watch"): ("Check the leak estimate and the gas detector; prepare isolation.", "تحقق من تقدير التسرب وكاشف الغاز؛ جهّز العزل.", "A leak of this size drains the vessel in hours.", "تسرب بهذا الحجم يفرغ الوعاء خلال ساعات."),
    (5, "alert"): ("Isolate the vessel (close the discharge and inlet valves), stop the compressor, keep people away and ventilate.", "اعزل الوعاء (أغلق صمامي التفريغ والمدخل)، أوقف الضاغط، أبعد الأفراد وهوِّ المكان.",
                   "Stopping the supply and isolating limits the released mass and the cloud size.", "إيقاف الإمداد والعزل يحدّان من الكتلة المتسربة وحجم السحابة."),
    (5, "critical"): ("Emergency shutdown: isolate and depressurise to the safe vent, evacuate the area, no ignition sources, call emergency services.", "إيقاف طارئ: اعزل وخفّف الضغط إلى المنفّس الآمن، أخلِ المنطقة، لا مصادر اشتعال، اتصل بالطوارئ.",
                      "A large or sudden release can ignite or form a pressure wave.", "التسرب الكبير أو المفاجئ قد يشتعل أو يولد موجة ضغط."),
    (4, "watch"): ("Confirm compressor stop logic and valve positions on site.", "تأكد من منطق إيقاف الضاغط ومواضع الصمامات في الموقع.", "Pressure is not following the control logic.", "الضغط لا يتبع منطق التحكم."),
    (4, "alert"): ("Stop the compressor manually, close the inlet valve, check the relief path and vent if pressure keeps rising.", "أوقف الضاغط يدوياً، أغلق صمام المدخل، افحص مسار التنفيس وخفّف الضغط إذا استمر الارتفاع.",
                   "Pressure above the rating can rupture the vessel; the relief valve is the last barrier.", "الضغط فوق التصنيف قد يمزق الوعاء؛ وصمام التنفيس هو الحاجز الأخير."),
    (4, "critical"): ("Emergency stop of all inflow, open the manual vent, clear the area: pressure is near or above the relief set point.", "إيقاف طارئ لكل التدفق الداخل، افتح المنفّس اليدوي، أخلِ المنطقة: الضغط قريب من نقطة التنفيس أو أعلى.",
                      "Relief lift releases hydrogen at the vent and a blocked relief risks vessel failure.", "فتح التنفيس يطلق الهيدروجين، وانسداده يعرّض الوعاء للفشل."),
    (2, "watch"): ("Check ambient conditions, cooling and the intercooler status.", "افحص الظروف المحيطة والتبريد وحالة المبرّد الوسيط.", "Gas temperature is above what the operating state explains.", "حرارة الغاز أعلى مما تفسره حالة التشغيل."),
    (2, "alert"): ("Reduce charging, check the intercooler and look for an external heat source; prepare to stop the compressor.", "قلّل التعبئة، افحص المبرّد الوسيط وابحث عن مصدر حرارة خارجي؛ استعد لإيقاف الضاغط.",
                   "Hot gas raises pressure (about 1 bar per K at 300 bar) and weakens the vessel wall.", "الغاز الساخن يرفع الضغط (نحو 1 بار لكل كلفن عند 300 بار) ويُضعف جدار الوعاء."),
    (2, "critical"): ("Stop charging, isolate heat sources, apply cooling and prepare emergency depressurisation (possible fire exposure).", "أوقف التعبئة، اعزل مصادر الحرارة، طبّق التبريد وجهّز تخفيف الضغط الطارئ (احتمال التعرض لحريق).",
                      "Fire heating can push the vessel beyond its rating within minutes.", "التسخين بالحريق قد يدفع الوعاء لتجاوز تصنيفه خلال دقائق."),
    (1, "watch"): ("Cross-check the suspect gauge against the others and schedule calibration.", "قارن المقياس المشتبه به مع المقاييس الأخرى وجدول المعايرة.", "The gauges disagree; only one can be right.", "المقاييس غير متفقة؛ واحد منها فقط صحيح."),
    (1, "alert"): ("Treat the suspect reading as unreliable; use the redundant gauge and send an instrument technician.", "اعتبر القراءة المشتبه بها غير موثوقة؛ استخدم المقياس البديل وأرسل فني أجهزة.", "Decisions on a lying gauge can be wrong in either direction.", "القرارات المبنية على مقياس خاطئ قد تخطئ في أي اتجاه."),
    (1, "critical"): ("Treat the suspect reading as unreliable and operate on the redundant gauges until it is replaced.", "اعتبر القراءة غير موثوقة وشغّل بالاعتماد على المقاييس البديلة حتى الاستبدال.", "No safety function should rely on a failed instrument.", "يجب ألا تعتمد أي وظيفة أمان على جهاز معطل."),
    (6, "watch"): ("Schedule an inspection of the vessel; log the strain-per-pressure trend.", "جدول فحصاً للوعاء؛ سجّل اتجاه الانفعال لكل ضغط.", "The vessel responds more to pressure than before.", "الوعاء يستجيب للضغط أكثر من السابق."),
    (6, "alert"): ("Reduce the maximum operating pressure and schedule a non-destructive inspection soon.", "قلّل أقصى ضغط تشغيل وجدول فحصاً غير إتلافي قريباً.", "Stiffness loss is consistent with crack growth or wall thinning.", "فقدان الصلابة يتسق مع نمو الشقوق أو ترقق الجدار."),
    (6, "critical"): ("Depressurise to a safe level and take the vessel out of service pending inspection.", "خفّف الضغط إلى مستوى آمن وأخرج الوعاء من الخدمة لحين الفحص.", "Continuing at full pressure risks fatigue failure.", "الاستمرار بالضغط الكامل يعرّض لفشل الكلال."),
    (-1, "watch"): ("Unusual pattern that matches no known class: review the trends and gather more data.", "نمط غير معتاد لا يطابق أي فئة معروفة: راجع الاتجاهات وجمّع بيانات أكثر.", "The behaviour is outside what the tools were fitted on.", "السلوك خارج نطاق ما تم بناء الأدوات عليه."),
    (-1, "alert"): ("Unusual pattern that matches no known class: have an operator inspect the unit and treat it cautiously.", "نمط غير معتاد لا يطابق أي فئة معروفة: اطلب من المشغل فحص الوحدة وتعامل بحذر.", "An unrecognised pattern should not be ignored or auto-diagnosed.", "لا ينبغي تجاهل نمط غير معروف أو تشخيصه آلياً."),
    (-1, "critical"): ("Unusual pattern with a safety-relevant signal: treat as an emergency until understood.", "نمط غير معتاد مع إشارة مرتبطة بالسلامة: تعامل معه كحالة طارئة حتى يُفهم.", "Unknown plus a hazard indicator is the conservative case.", "المجهول مع مؤشر خطر هو الحالة التي تتطلب الحذر."),
}


def lookup(cls: int, severity: str) -> dict:
    a = RULES.get((cls, severity)) or RULES.get((-1, severity)) or RULES[(-1, "watch")]
    nm = CLASS_NAMES.get(cls, CLASS_NAMES[-1])
    return {"class": cls, "class_en": nm[0], "class_ar": nm[1], "severity": severity, "action_en": a[0], "action_ar": a[1], "reason_en": a[2], "reason_ar": a[3]}


@register
class Procedures(Tool):
    name = "T13_procedures"
    description = "Rule table of recommended actions per class and severity (English and Arabic) with the physical reason. Advisory: the operator approves."
    version = "1.0"
    cost = "cheap"

    def call(self, ctx, i, cls: int = -1, severity: str = "watch", **kw):
        r = lookup(int(cls), severity)
        return ToolResult(self.name, "procedure", estimate={}, fields=r, text_en=f"{r['action_en']} Why: {r['reason_en']}", text_ar=f"{r['action_ar']} السبب: {r['reason_ar']}")
