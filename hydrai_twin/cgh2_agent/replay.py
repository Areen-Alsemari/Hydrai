"""Replay: stream one episode through the orchestrator as JSON ticks (tags, raw pressure, compensated inventory, agent state, alerts, trace), with accelerated
playback, plus a self-contained HTML viewer (no network, no dependencies) with a simulated operator approve/reject."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

import numpy as np

from hydrai_twin.cgh2_agent.agent import Decision
from hydrai_twin.cgh2_agent.session import AgentSession
from hydrai_twin.cgh2_agent.tools.t13_procedures import CLASS_NAMES

TAGS = {"P": "GH2-PT-101", "T": "GH2-TT-101", "Tw": "GH2-TT-102", "H2": "GH2-AT-101", "fill": "GH2-FT-101", "disc": "GH2-FT-102", "strain": "GH2-SE-101", "Ta": "GH2-TT-901"}


def build(session: AgentSession, stride: int = 5, start_min: int | None = None, stop_min: int | None = None, operator=None) -> dict[str, Any]:
    """Runs the agent over the episode and returns {'meta', 'ticks', 'decisions'}. Ticks are every `stride` minutes from `start_min`."""
    if operator is not None:
        session.orch.operator = operator
    u, ctx = session.unit, session.ctx
    out = session.run(record_ticks=False, start=start_min, stop=stop_min)
    dec: list[Decision] = out["decisions"]
    m2 = ctx.monitor("T2_inventory_leak")
    c = ctx.cache["clean"]
    iref = u.raw.inv_ref_kg
    n = u.n if stop_min is None else min(stop_min, u.n)
    first = 1440 if start_min is None else max(start_min, 1440)
    dec_by_tick = {d.i: k for k, d in enumerate(dec)}
    ev_start = [e["t_watch_s"] for e in out["events"]] + [1e18]
    state_t = _state_timeline(out, u)
    ticks = []
    latest = None
    rel_cum = np.cumsum(np.clip(m2["L_kgh"], 0, None)) / 60.0
    for i in sorted(set(range(first, n, stride)) | set(dec_by_tick)):
        if i in dec_by_tick:
            latest = dec_by_tick[i]
        t = float(u.t[i])
        st = state_t(i)
        d = dec[latest] if latest is not None and st["tier"] != "none" else None
        z = float(m2["L_z"][i])
        leak = None
        if z >= 2.0:
            L, sL = float(m2["L_kgh"][i]), float(m2["sL_kgh"][i])
            leak = {"rate_kgh": round(L, 3), "lo": round(max(L - 2 * sL, 0), 3), "hi": round(L + 2 * sL, 3), "orifice_mm": round(float(m2["d_eq_mm"][i]), 3), "z": round(z, 2)}
            j0 = max((int(e) for e in [dec[0].i] if True), default=i) if dec else i
            leak["released_kg_since_first_watch"] = round(float(rel_cum[i] - rel_cum[max(j0 - 1, 0)]), 2) if i >= j0 else 0.0
        tags = {TAGS[k]: round(float(u.raw.x[k][i]), 4) for k in TAGS}
        ticks.append({"tick": i, "t_s": t, "t_h": round(t / 3600.0, 4), "tags": tags, "raw_pressure_bar": round(float(u.raw.x["P"][i]), 3), "clean_pressure_bar": round(float(c["P"][i]), 3),
                      "compensated_inventory_kg": round(float(m2["In"][i] * iref), 3), "kalman_inventory_kg": round(float(m2["I_hat"][i]), 3),
                      "agent": {"state": st["state"], "tier": st["tier"], "class": (d.cls if d else 0), "class_name_en": CLASS_NAMES.get(d.cls if d else 0, CLASS_NAMES[-1])[0] if d else "healthy",
                                "class_name_ar": CLASS_NAMES.get(d.cls if d else 0, CLASS_NAMES[-1])[1] if d else "سليم", "score": round(float(1 - session.P[i, 0]), 4),
                                "watch_threshold": round(session.orch.thr["watch"], 4), "alert_threshold": round(session.orch.thr["alert"], 4)},
                      "leak": leak, "static_alarm": bool(u.static[i]), "decision_index": latest if (i in dec_by_tick) else None,
                      "text_en": d.text_en if (d and i in dec_by_tick) else "", "text_ar": d.text_ar if (d and i in dec_by_tick) else ""})
    from ml.headline_metrics import alarm_events
    from hydrai_twin.cgh2_agent import operator_proxy as OP
    thr_op = OP.thresholds_cached()
    t_h = lambda ts: [round(float(x) / 3600.0, 3) for x in ts]
    timelines = {"agent_watch_h": t_h([e["t_watch_s"] for e in out["events"]]), "agent_alert_h": t_h([e["t_alert_s"] for e in out["events"] if e["t_alert_s"] is not None]),
                 "static_alarm_h": t_h(alarm_events(u.t, u.static, 3600.0)),
                 "operator_15min_h": t_h(alarm_events(u.t, OP.flags(u, thr_op[15], 15), 3600.0)), "operator_60min_h": t_h(alarm_events(u.t, OP.flags(u, thr_op[60], 60), 3600.0)),
                 "onset_h": None if u.entry["onset_s"] is None else round(u.entry["onset_s"] / 3600.0, 3),
                 "note": "operator = a MODELLED operator who looks at the raw dashboard every 15 / 60 minutes (not a human study); alarm events merged within 1 h"}
    meta = {"episode": u.entry["name"], "timelines": timelines, "family": u.entry["family"], "module": u.entry["module_id"], "onset_s": u.entry["onset_s"], "first_observable_s": u.entry["first_observable_s"],
            "static_alarm_first_s": u.entry["static_alarm_first_s"], "dt_s": 60, "stride_min": stride, "thresholds": session.orch.thr, "events": out["events"], "tags": TAGS,
            "note": "Policy-mode orchestrator; every number in the explanation text comes from a tool output listed in the decision trace."}
    return {"meta": meta, "ticks": ticks, "decisions": [d.to_json() for d in dec]}


def _state_timeline(out: dict[str, Any], u):
    """Maps a tick to the orchestrator state / tier using the recorded events (monitor / suspect / investigate ... / follow-up / closed)."""
    evs = out["events"]
    decs = out["decisions"]

    def at(i: int) -> dict[str, str]:
        t = float(u.t[i])
        for e in evs:
            end = e["closed_s"] if e["closed_s"] is not None else 1e18
            if e["t_watch_s"] <= t <= end:
                tier = "watch"
                last = None
                for k in e["decisions"]:
                    if decs[k].t_s <= t:
                        last = decs[k]
                if last is not None:
                    tier = last.tier
                phase = "AWAIT_APPROVAL" if (e.get("approval_s") and e["t_watch_s"] <= t < e["approval_s"] and tier != "watch") else "INVESTIGATE" if t == e["t_watch_s"] else "FOLLOW_UP"
                return {"state": phase, "tier": tier}
        return {"state": "MONITOR", "tier": "none"}
    return at


def stream_lines(data: dict[str, Any], speed: float = 3600.0, sleep: bool = True) -> Iterator[str]:
    """Yields one JSON line per tick; with sleep=True the playback runs at `speed` x real time (default 3600: one simulated hour per second)."""
    yield json.dumps({"type": "meta", **data["meta"]})
    prev_t = None
    for tk in data["ticks"]:
        if sleep and prev_t is not None:
            time.sleep(max(tk["t_s"] - prev_t, 0) / speed)
        prev_t = tk["t_s"]
        rec = {"type": "tick", **tk}
        if tk["decision_index"] is not None:
            rec["decision"] = data["decisions"][tk["decision_index"]]
        yield json.dumps(rec)


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HYDRAI agent replay</title>
<style>
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#ddd;--ok:#2a7;--watch:#d9a400;--alert:#e07020;--crit:#c0262d;--card:#f6f7f8}
@media(prefers-color-scheme:dark){:root{--bg:#15181b;--fg:#e8e8e8;--mut:#9aa;--line:#333;--card:#1e2226}}
body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:10px 16px;border-bottom:1px solid var(--line);display:flex;gap:12px;flex-wrap:wrap;align-items:center}
h1{font-size:16px;margin:0}main{padding:12px 16px;display:grid;gap:12px;grid-template-columns:2fr 1fr}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}
canvas{width:100%;height:150px;display:block}canvas.tl{height:96px}
.tier{display:inline-block;padding:2px 10px;border-radius:12px;color:#fff;font-weight:600}
.t-none{background:var(--ok)}.t-watch{background:var(--watch)}.t-alert{background:var(--alert)}.t-critical{background:var(--crit)}
button,select{font:inherit;padding:4px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);cursor:pointer}
.trace div{border-top:1px solid var(--line);padding:4px 0;font-size:12px}.mut{color:var(--mut)}
.rtl{direction:rtl;text-align:right}.lg span{display:inline-block;margin-right:12px}.lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}
</style></head><body>
<header><h1>HYDRAI agent replay</h1><span id="ep" class="mut"></span><button id="play">Play</button>
<label>speed <select id="spd"><option value="1800">0.5 h/s</option><option value="3600" selected>1 h/s</option><option value="14400">4 h/s</option><option value="43200">12 h/s</option></select></label>
<button id="lang">العربية</button>
<input id="sl" type="range" min="0" value="0" style="flex:1;min-width:160px"><span id="clock"></span></header>
<main><div>
<div class="card"><b>Pressure (bar)</b> <span class="mut">raw vs cleaned</span><canvas id="c1"></canvas></div>
<div class="card" style="margin-top:12px"><b>Compensated inventory (kg)</b> <span class="mut">temperature-compensated real-gas inventory and Kalman estimate</span><canvas id="c2"></canvas></div>
<div class="card" style="margin-top:12px"><b>Agent score</b> <span class="mut">1 - P(healthy), watch and alert thresholds</span><canvas id="c3"></canvas></div>
<div class="card" style="margin-top:12px"><b>Who warned when</b> <span class="mut">first alert of each event; the dashed line is the true fault onset</span>
<div class="lg mut"><span><i style="background:#27a"></i>agent alert</span><span><i style="background:#c0262d"></i>static alarm</span><span><i style="background:#a72"></i>operator proxy (modelled, looks every 15 min)</span></div><canvas id="c4" class="tl"></canvas></div></div>
<div><div class="card"><div><span id="l_state">State</span> <b id="st"></b> &nbsp; <span id="l_tier">Tier</span> <span id="tier" class="tier t-none">none</span> &nbsp; <span id="l_sa">Static alarm</span> <b id="sa"></b></div>
<div style="margin-top:6px"><span id="l_cls">Class</span> <b id="cls"></b></div><div id="leak" class="mut" style="margin-top:6px"></div>
<p id="txt"></p><div><button id="ok" disabled>Approve action</button> <button id="no" disabled>Reject</button> <span id="op" class="mut"></span></div></div>
<div class="card trace" style="margin-top:12px"><b id="l_trace">Reasoning trace</b> <span class="mut">(ordered tool calls of the latest decision)</span><div id="tr"></div></div></div></main>
<script>
const D=__DATA__;const T=D.ticks;const TL=D.meta.timelines;const sl=document.getElementById('sl');sl.max=T.length-1;document.getElementById('ep').textContent=D.meta.episode+' (medium class)';
let k=0,timer=null,lastDec=null,ops={},lastEn='',lastAr='',lang='en';
const C=(id)=>document.getElementById(id);
const L={en:{State:'State',Tier:'Tier',Static:'Static alarm',Class:'Class',Trace:'Reasoning trace',ok:'Approve action',no:'Reject',active:'ACTIVE',quiet:'quiet',none:'no investigation yet'},
         ar:{State:'الحالة',Tier:'المستوى',Static:'الإنذار الثابت',Class:'الفئة',Trace:'مسار الاستدلال',ok:'الموافقة على الإجراء',no:'رفض',active:'فعّال',quiet:'صامت',none:'لا يوجد فحص بعد'}};
function draw(id,series,cols,ymin,ymax,marks){const cv=C(id),r=devicePixelRatio||1,w=cv.clientWidth*r,h=cv.clientHeight*r;cv.width=w;cv.height=h;const g=cv.getContext('2d');g.clearRect(0,0,w,h);
const x0=T[0].t_h,x1=T[T.length-1].t_h;const X=t=>(t-x0)/(x1-x0)*w,Y=v=>h-(v-ymin)/(ymax-ymin)*h;
const css=getComputedStyle(document.body);
(marks||[]).forEach(m=>{g.strokeStyle=m.c;g.setLineDash([4,3]);g.beginPath();g.moveTo(X(m.t),0);g.lineTo(X(m.t),h);g.stroke();g.setLineDash([])});
series.forEach((s,j)=>{g.strokeStyle=cols[j];g.lineWidth=1.5*r;g.beginPath();let st=false;for(let i=0;i<=k;i++){const v=s(T[i]);if(v==null)continue;const x=X(T[i].t_h),y=Y(v);st?g.lineTo(x,y):g.moveTo(x,y);st=true}g.stroke()});
g.fillStyle=css.color;g.font=(11*r)+'px sans-serif';g.fillText(ymax.toFixed(0),2,12*r);g.fillText(ymin.toFixed(0),2,h-3);}
function timeline(){const cv=C('c4'),r=devicePixelRatio||1,w=cv.clientWidth*r,h=cv.clientHeight*r;cv.width=w;cv.height=h;const g=cv.getContext('2d');g.clearRect(0,0,w,h);
const x0=T[0].t_h,x1=T[T.length-1].t_h,X=t=>(t-x0)/(x1-x0)*w,now=T[k].t_h,css=getComputedStyle(document.body);
const rows=[['agent',TL.agent_alert_h,'#27a'],['static',TL.static_alarm_h,'#c0262d'],['operator',TL.operator_15min_h,'#a72']];
g.font=(11*r)+'px sans-serif';
if(TL.onset_h!=null){g.strokeStyle='#999';g.setLineDash([4,3]);g.beginPath();g.moveTo(X(TL.onset_h),0);g.lineTo(X(TL.onset_h),h);g.stroke();g.setLineDash([])}
rows.forEach((rw,j)=>{const y=(j+0.5)*h/3;g.strokeStyle='rgba(128,128,128,.35)';g.beginPath();g.moveTo(0,y);g.lineTo(w,y);g.stroke();g.fillStyle=css.color;g.fillText(rw[0],4,y-5*r);
rw[1].forEach(t=>{if(t<=now){g.fillStyle=rw[2];g.beginPath();g.arc(X(t),y,5*r,0,6.3);g.fill()}})});
g.strokeStyle=css.color;g.beginPath();g.moveTo(X(now),0);g.lineTo(X(now),h);g.stroke();}
const ext=(f)=>{let a=1e9,b=-1e9;T.forEach(t=>{const v=f(t);if(v!=null){a=Math.min(a,v);b=Math.max(b,v)}});return [a-(b-a)*0.05,b+(b-a)*0.05]};
const eP=ext(t=>t.raw_pressure_bar),eI=ext(t=>t.compensated_inventory_kg);
const marks=[];if(D.meta.onset_s)marks.push({t:D.meta.onset_s/3600,c:'#999'});
function setLang(l){lang=l;const s=L[l];document.documentElement.lang=l;C('l_state').textContent=s.State;C('l_tier').textContent=s.Tier;C('l_sa').textContent=s.Static;C('l_cls').textContent=s.Class;C('l_trace').textContent=s.Trace;C('ok').textContent=s.ok;C('no').textContent=s.no;C('lang').textContent=l==='en'?'العربية':'English';C('txt').className=l==='ar'?'rtl':'';render()}
function render(){const t=T[k],s=L[lang];C('clock').textContent='t = '+t.t_h.toFixed(1)+' h';sl.value=k;
draw('c1',[x=>x.raw_pressure_bar,x=>x.clean_pressure_bar],['#c0262d','#2a7'],eP[0],eP[1],marks);
draw('c2',[x=>x.compensated_inventory_kg,x=>x.kalman_inventory_kg],['#27a','#a72'],eI[0],eI[1],marks);
draw('c3',[x=>x.agent.score,x=>x.agent.watch_threshold,x=>x.agent.alert_threshold],['#27a','#d9a400','#e07020'],0,1,marks);timeline();
const a=t.agent;C('st').textContent=a.state;C('tier').textContent=a.tier;C('tier').className='tier t-'+a.tier;C('sa').textContent=t.static_alarm?s.active:s.quiet;
C('cls').textContent=lang==='en'?a.class_name_en:a.class_name_ar;
C('leak').textContent=t.leak?(lang==='en'?('leak '+t.leak.rate_kgh+' kg/h ('+t.leak.lo+'-'+t.leak.hi+'), orifice ~'+t.leak.orifice_mm+' mm, released since first watch '+t.leak.released_kg_since_first_watch+' kg'):('تسرب '+t.leak.rate_kgh+' كغ/ساعة ('+t.leak.lo+'-'+t.leak.hi+')، قطر الفتحة ~'+t.leak.orifice_mm+' مم، المتسرب منذ أول مراقبة '+t.leak.released_kg_since_first_watch+' كغ')):'';
lastDec=null;lastEn='';lastAr='';if(a.tier!=='none'){for(let i=k;i>=0;i--){if(T[i].decision_index!=null){lastDec=T[i].decision_index;lastEn=T[i].text_en;lastAr=T[i].text_ar;break}}}   // the latest decision at or before this tick (also after a slider jump)
C('txt').textContent=lang==='en'?lastEn:lastAr;
const d=lastDec!=null?D.decisions[lastDec]:null;const pend=d&&(d.tier==='alert'||d.tier==='critical')&&ops[lastDec]==null;
C('ok').disabled=C('no').disabled=!pend;C('op').textContent=d&&ops[lastDec]!=null?('operator: '+ops[lastDec]):(d&&d.approved!==null?'simulated operator: '+(d.approved?'approved':'rejected'):'');
C('tr').innerHTML=d?d.trace.map(c=>'<div><b>'+c.order+'. '+c.tool+'</b> <span class="mut">('+c.runtime_ms+' ms) '+c.why+'</span><br>'+(c.result.verdict)+' &mdash; '+(lang==='en'?c.result.text_en:c.result.text_ar)+'</div>').join(''):'<div class="mut">'+s.none+'</div>';}
function step(){if(k<T.length-1){k++;render();const dt=(T[k].t_s-T[k-1].t_s)/Number(C('spd').value)*1000;timer=setTimeout(step,Math.max(dt,15))}else{C('play').textContent='Play';timer=null}}
C('play').onclick=()=>{if(timer){clearTimeout(timer);timer=null;C('play').textContent='Play'}else{C('play').textContent='Pause';if(k>=T.length-1)k=0;step()}};
sl.oninput=()=>{k=Number(sl.value);render()};C('ok').onclick=()=>{ops[lastDec]='approved';render()};C('no').onclick=()=>{ops[lastDec]='rejected';render()};C('lang').onclick=()=>setLang(lang==='en'?'ar':'en');
render();window.onresize=render;
</script></body></html>"""


def write_html(data: dict[str, Any], path: str) -> None:
    slim = {"meta": data["meta"], "ticks": data["ticks"], "decisions": data["decisions"]}
    with open(path, "w") as f:
        f.write(HTML.replace("__DATA__", json.dumps(slim)))
