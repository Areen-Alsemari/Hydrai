"""HYDRAI orchestrator (deterministic policy mode).

State machine: MONITOR -> SUSPECT -> INVESTIGATE -> DECIDE -> AWAIT_APPROVAL -> FOLLOW_UP -> CLOSE.

  MONITOR      the always-on cheap tools (T1, the fast layer, T2/T3/T4/T5 monitor series) feed the fusion score s = 1 - P(healthy).
  SUSPECT      s crosses the WATCH level (healthy-calibrated at 1 false event per day) for two consecutive 5-minute evaluations.
  INVESTIGATE  hypothesis-driven calls (budget MAX_CALLS) chosen from the fusion's top classes; every call is logged with its inputs, outputs and runtime.
  DECIDE       tier (watch / alert / critical), class with probability, action, explanation. Class posterior = fusion probabilities x a fixed likelihood
               table over the tools' verdicts (defined a priori, below). Open-set: below OPEN_THRESHOLD the class is reported as "unknown pattern".
  AWAIT_APPROVAL  the simulated (or real) operator approves or rejects the recommended action; the agent never actuates.
  FOLLOW_UP    re-checks every FOLLOW_EVERY minutes (at most MAX_FOLLOW times) and escalates if the picture worsens.
  CLOSE        the score has stayed below the watch level for CLOSE_AFTER minutes.

Tiers (defined before any result was looked at)
  watch     s >= watch threshold.
  alert     s >= alert threshold (healthy-calibrated at 1 false event per week), OR watch plus at least one HARD evidence verdict from an investigation tool
            (twin verifier accepts, a T4 control-logic violation, T3 thermal verdict, T5 sensor verdict).
  critical  alert AND (class in {abnormal pressure, containment} with posterior >= 0.5, OR leak-rate estimate >= 5 kg/h, OR pressure >= PAHH, OR gas detector >= trip).

The benchmarked orchestrator is this deterministic policy; the LLM mode (hydrai_twin/cgh2_agent/llm.py) only talks to the operator and is not used in any benchmark number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from hydrai_twin.cgh2_agent.features import WARMUP
from hydrai_twin.cgh2_agent.tools import CallLog, Ctx, REGISTRY, load_all_tools
from hydrai_twin.cgh2_agent.tools.t13_procedures import CLASS_NAMES, lookup

EVAL_EVERY = 5               # minutes between orchestrator evaluations
SUSPECT_N = 2                # consecutive evaluations above the watch level before investigating
FOLLOW_SCHEDULE = (10, 30)   # minutes after the first decision of an event for the first two follow-ups (a fast trigger is refined within the first half hour)
FOLLOW_EVERY = 60            # minutes between later follow-up investigations
MAX_FOLLOW = 24
CLOSE_AFTER = 120            # minutes below the watch level to close an event
MAX_CALLS = 7
OPEN_THRESHOLD = 0.5
OPERATOR_DELAY_MIN = 5

HARD = {"T9_twin_verifier": {"accept"},
        "T4_pressure_behaviour": {"relief_blocked_suspected", "compressor_overrun", "discharge_valve_stuck_open_suspected", "pressure_collapse", "relief_lifted"},
        "T3_thermal_state": {"external_heating_suspected", "cooling_failure_suspected", "overheating"},
        "T6_structural": {"stiffness_drift"},
        "T12_alarm_context": {"static_alarm_active"},
        "T5_sensor_integrity": {"temperature_probe_suspect", "pressure_transmitter_suspect", "strain_gauge_suspect", "flow_meters_suspect"}}

# likelihood table over tool verdicts: (tool, verdict) -> {class: multiplier}; fixed a priori, not tuned
LR = {("T9_twin_verifier", "accept:leak"): {3: 3.0, 5: 3.0}, ("T9_twin_verifier", "reject:leak"): {3: 0.3, 5: 0.3},
      ("T9_twin_verifier", "accept:leak_fit"): {3: 2.0, 5: 2.0}, ("T9_twin_verifier", "reject:leak_fit"): {3: 0.7, 5: 0.7},
      ("T9_twin_verifier", "accept:heating"): {2: 3.0, 4: 1.5}, ("T9_twin_verifier", "reject:heating"): {2: 0.4},
      ("T2_inventory_leak", "leak_suspected"): {3: 2.0, 5: 2.0}, ("T2_inventory_leak", "no_leak_evidence"): {3: 0.5, 5: 0.5},
      ("T3_thermal_state", "external_heating_suspected"): {2: 2.0, 4: 2.0}, ("T3_thermal_state", "cooling_failure_suspected"): {2: 2.5},
      ("T3_thermal_state", "overheating"): {2: 2.0}, ("T3_thermal_state", "thermal_normal"): {2: 0.5},
      ("T4_pressure_behaviour", "relief_blocked_suspected"): {4: 3.0}, ("T4_pressure_behaviour", "compressor_overrun"): {4: 3.0},
      ("T4_pressure_behaviour", "discharge_valve_stuck_open_suspected"): {4: 3.0}, ("T4_pressure_behaviour", "relief_lifted"): {4: 3.0},
      ("T4_pressure_behaviour", "pressure_high"): {4: 2.0}, ("T4_pressure_behaviour", "pressure_collapse"): {5: 25.0},
      ("T5_sensor_integrity", "temperature_probe_suspect"): {1: 3.0, 3: 0.5}, ("T5_sensor_integrity", "pressure_transmitter_suspect"): {1: 3.0, 3: 0.5},
      ("T6_structural", "stiffness_drift"): {6: 4.0}, ("T6_structural", "structure_normal"): {6: 0.5},
      ("T5_sensor_integrity", "strain_gauge_suspect"): {1: 2.0, 6: 0.7}, ("T5_sensor_integrity", "no_sensor_fault_evidence"): {1: 0.5}}

PLAN = {3: ("T2_inventory_leak", "T9_twin_verifier:leak", "T9_twin_verifier:leak_fit", "T11_hold_test_planner", "T10_forecast_consequence"),
        5: ("T4_pressure_behaviour", "T2_inventory_leak", "T9_twin_verifier:leak", "T9_twin_verifier:leak_fit", "T10_forecast_consequence"),
        2: ("T3_thermal_state", "T9_twin_verifier:heating"), 4: ("T4_pressure_behaviour", "T3_thermal_state", "T10_forecast_consequence"),
        1: ("T5_sensor_integrity",), 6: ("T6_structural", "T5_sensor_integrity")}


@dataclass
class Decision:
    t_s: float
    i: int
    tier: str
    cls: int
    class_probs: dict[int, float]
    open_set: bool
    score: float
    posterior: dict[int, float]
    hard_evidence: list[str]
    approved: bool | None = None
    leak_estimate: dict[str, Any] | None = None
    released_kg: float | None = None
    forecast: dict[str, Any] | None = None
    procedure: dict[str, Any] | None = None
    text_en: str = ""
    text_ar: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    runtime_ms: float = 0.0

    def to_json(self) -> dict[str, Any]:
        return {"t_s": self.t_s, "tick": self.i, "tier": self.tier, "class": self.cls, "class_name_en": CLASS_NAMES.get(self.cls, CLASS_NAMES[-1])[0],
                "class_name_ar": CLASS_NAMES.get(self.cls, CLASS_NAMES[-1])[1], "class_probs": {str(k): round(v, 4) for k, v in self.class_probs.items()},
                "open_set": self.open_set, "score": round(self.score, 4), "posterior": {str(k): round(v, 4) for k, v in self.posterior.items()},
                "hard_evidence": self.hard_evidence, "approved": self.approved, "leak_estimate": self.leak_estimate, "released_kg": self.released_kg, "forecast": self.forecast,
                "procedure": self.procedure, "text_en": self.text_en, "text_ar": self.text_ar, "trace": self.trace, "runtime_ms": round(self.runtime_ms, 2)}


def operator_default(decision: Decision) -> tuple[bool, float]:
    """Simulated operator: approves alerts and criticals after a short delay, ignores watches (no action requested)."""
    return decision.tier in ("alert", "critical"), OPERATOR_DELAY_MIN * 60.0


class Orchestrator:
    def __init__(self, thresholds: dict[str, float], operator: Callable[[Decision], tuple[bool, float]] = operator_default, enabled_tools: set[str] | None = None, use_static: bool = True):
        load_all_tools()
        self.use_static = use_static             # the existing static alarm state is an input (it opens an investigation at once and counts as hard evidence)
        self.thr = thresholds
        self.operator = operator
        self.enabled = enabled_tools            # None = all; used by the ablations
        self.on = lambda name: self.enabled is None or name in self.enabled

    # ------------------------------------------------------------------ investigation
    def investigate(self, ctx: Ctx, i: int, p: np.ndarray, why: str, prev_class: int | None = None) -> tuple[CallLog, dict[str, Any]]:
        log = CallLog()
        res: dict[str, Any] = {}
        run = lambda name, **kw: res.__setitem__(name + (":" + kw["hypothesis"] if "hypothesis" in kw else ""), log.run(REGISTRY[name], ctx, i, why, **kw)) if (self.on(name) and len(log.calls) < MAX_CALLS) else None
        run("T1_data_integrity") if False else None
        # T1 is always on in MONITOR; its verdict is attached to the trace (cheap)
        if self.on("T1_data_integrity") and len(log.calls) < MAX_CALLS:
            res["T1_data_integrity"] = log.run(REGISTRY["T1_data_integrity"], ctx, i, "check data trust before reasoning on it")
        fault_p = p[1:] / max(p[1:].sum(), 1e-9)
        order = [int(k) + 1 for k in np.argsort(-fault_p)]
        groups = [order[0]] + ([order[1]] if fault_p[order[0] - 1] < 0.6 else [])
        if float(ctx.monitor("T4_pressure_behaviour")["collapse_trip"][i]) > 0.5:          # fast-layer trip: the containment question first, nothing else
            groups = [5]
        for g in groups:
            for step in PLAN[g]:
                name, _, hyp = step.partition(":")
                key = name + (":" + hyp if hyp else "")
                if key in res:
                    continue
                if name == "T11_hold_test_planner":
                    t2, t9 = res.get("T2_inventory_leak"), res.get("T9_twin_verifier:leak")
                    if t2 is None or not (t2.verdict != "leak_suspected" or (t9 is not None and t9.verdict == "need_more_data") or abs(float(t2.score or 0)) < 6.0):
                        continue                                              # leak evidence is clear: no hold test needed
                    run(name)
                    continue
                if name == "T9_twin_verifier" and hyp == "leak_fit":
                    t2 = res.get("T2_inventory_leak")
                    if t2 is not None and t2.verdict == "leak_suspected" and float(t2.estimate["leak_rate"]["value"]) < 3.0:
                        continue                                              # a small, well-resolved leak: the filter's estimate is the better one
                    run(name, hypothesis="leak_fit")
                    continue
                if name == "T10_forecast_consequence":
                    fit_r = res.get("T9_twin_verifier:leak_fit")
                    if fit_r is not None and fit_r.verdict == "accept":
                        e = fit_r.estimate["leak_rate"]
                        run(name, rate_kgh=float(e["value"]), rate_sigma_kgh=0.5 * (float(e["hi"]) - float(e["lo"])) / 2.0)
                    else:
                        run(name)
                    continue
                if name == "T9_twin_verifier":
                    t2 = res.get("T2_inventory_leak")
                    if hyp == "leak" and t2 is not None and t2.verdict != "leak_suspected" and g in (3, 5) and fault_p[g - 1] < 0.9:
                        continue                                              # nothing to verify: no leak evidence from the inventory tool
                    run(name, hypothesis=hyp)
                else:
                    run(name)
        if self.on("T12_alarm_context") and len(log.calls) < MAX_CALLS + 1:
            res["T12_alarm_context"] = log.run(REGISTRY["T12_alarm_context"], ctx, i, "what do the existing static alarms say")
        return log, res

    # ------------------------------------------------------------------ decision
    def decide(self, ctx: Ctx, i: int, p: np.ndarray, log: CallLog, res: dict[str, Any]) -> Decision:
        u = ctx.unit
        s = float(1.0 - p[0])
        fault_p = p[1:] / max(p[1:].sum(), 1e-9)
        post = {k + 1: float(fault_p[k]) for k in range(6)}
        hard = []
        for key, r in res.items():
            tool, _, hyp = key.partition(":")
            lr = LR.get((tool, f"{r.verdict}:{hyp}" if hyp else r.verdict))
            if lr:
                for c, mult in lr.items():
                    post[c] *= mult
            if r.verdict in HARD.get(tool, ()):
                hard.append(f"{tool}:{r.verdict}")
        z = sum(post.values())
        post = {c: v / z for c, v in post.items()}
        top = max(post, key=post.get)
        open_set = post[top] < OPEN_THRESHOLD
        cls = -1 if open_set else top
        tier = "watch"
        if s >= self.thr["alert"] or hard:
            tier = "alert"
        t2 = res.get("T2_inventory_leak")
        t9f = res.get("T9_twin_verifier:leak_fit")
        rate = float(t2.estimate["leak_rate"]["value"]) if t2 is not None and t2.verdict == "leak_suspected" else 0.0
        if t9f is not None and t9f.verdict == "accept":
            rate = max(rate, float(t9f.estimate["leak_rate"]["value"]))
        c = ctx.cache["clean"]
        P_bar, H2 = float(c["P"][i]), float(c["H2"][i])
        crit_reason = cls in (4, 5) and post.get(cls, 0) >= 0.5 or rate >= 5.0 or P_bar >= u.cls["pahh_bar"] or H2 >= 50.0
        if tier == "alert" and crit_reason:
            tier = "critical"
        d = Decision(float(u.t[i]), i, tier, cls, {k: float(p[k]) for k in range(7)}, open_set, s, post, hard)
        use_fit = t9f is not None and t9f.verdict == "accept" and (t2 is None or t2.verdict != "leak_suspected" or float(t9f.estimate["leak_rate"]["value"]) > 2.0 * float(t2.estimate["leak_rate"]["value"]))
        if use_fit:
            d.leak_estimate = {k: t9f.estimate[k] for k in ("leak_rate", "orifice_diameter")}
            d.leak_estimate["method"] = "digital-twin fit (rate and start time) to the last 20 min of pressure"
            d.released_kg = float(t9f.estimate["released_so_far"]["value"])
        elif t2 is not None and t2.verdict == "leak_suspected":
            d.leak_estimate = {k: t2.estimate[k] for k in ("leak_rate", "orifice_diameter")}
            d.released_kg = float(t2.estimate["released_so_far"]["value"])
        t10 = res.get("T10_forecast_consequence")
        if t10 is not None and t10.verdict == "consequence_forecast":
            d.forecast = t10.estimate
        pr = REGISTRY["T13_procedures"].call(ctx, i, cls=cls, severity=tier) if self.on("T13_procedures") else None
        if pr is not None:
            d.procedure = pr.fields
        d.text_en, d.text_ar = self.explain(d, res)
        d.trace = log.calls
        d.runtime_ms = log.total_runtime_ms()
        return d

    @staticmethod
    def explain(d: Decision, res: dict[str, Any]) -> tuple[str, str]:
        nm = CLASS_NAMES.get(d.cls, CLASS_NAMES[-1])
        head_en = f"{d.tier.upper()}: {nm[0]} (probability {d.posterior.get(d.cls, 0):.0%})." if not d.open_set else f"{d.tier.upper()}: unusual pattern that matches no known class."
        head_ar = f"{ {'watch': 'مراقبة', 'alert': 'تنبيه', 'critical': 'حرج'}[d.tier] }: {nm[1]} (الاحتمال {d.posterior.get(d.cls, 0):.0%})." if not d.open_set else f"{ {'watch': 'مراقبة', 'alert': 'تنبيه', 'critical': 'حرج'}[d.tier] }: نمط غير معتاد لا يطابق أي فئة معروفة."
        keep = [r for k, r in res.items() if k.split(":")[0] in ("T2_inventory_leak", "T3_thermal_state", "T4_pressure_behaviour", "T5_sensor_integrity", "T9_twin_verifier", "T10_forecast_consequence")
                and r.verdict not in ("thermal_normal", "pressure_normal", "no_sensor_fault_evidence", "no_leak_evidence", "no_adverse_trend", "need_more_data", "reject")]
        en = " ".join([head_en] + [r.text_en for r in keep])
        ar = " ".join([head_ar] + [r.text_ar for r in keep])
        if d.procedure:
            en += f" Recommended: {d.procedure['action_en']} Why: {d.procedure['reason_en']}"
            ar += f" الإجراء المقترح: {d.procedure['action_ar']} السبب: {d.procedure['reason_ar']}"
        return en, ar

    # ------------------------------------------------------------------ run over a unit
    def run(self, ctx: Ctx, P: np.ndarray, record_ticks: bool = False, start: int | None = None, stop: int | None = None, P_fast: np.ndarray | None = None) -> dict[str, Any]:
        """Replays the unit through the state machine. `P` is the (n, 7) smoothed fusion probabilities (causal). Returns the events, decisions and (optionally) per-evaluation ticks."""
        u = ctx.unit
        ctx.monitor("T1_data_integrity")
        n = u.n if stop is None else min(stop, u.n)
        state, consec, below = "MONITOR", 0, 0
        events: list[dict[str, Any]] = []
        decisions: list[Decision] = []
        ticks: list[dict[str, Any]] = []
        ev: dict[str, Any] | None = None
        last_inv, n_follow, tier_now, cls_now = -10 ** 9, 0, "none", 0
        first = WARMUP if start is None else max(start, WARMUP)
        # fast layer: a pressure collapse trips the orchestrator at once (every tick, no smoothing, no 5-minute grid)
        trip = np.flatnonzero(ctx.monitor("T4_pressure_behaviour")["collapse_trip"] > 0.5)
        grid = sorted(set(range(first, n, EVAL_EVERY)) | {int(k) for k in trip if first <= k < n})
        trip_set = {int(k) for k in trip}
        if self.use_static:
            on = np.flatnonzero(np.diff(np.concatenate([[False], u.static]).astype(int)) == 1)
            static_set = {int(k) for k in on if first <= k < n}
            grid = sorted(set(grid) | static_set)
        else:
            static_set = set()
        trip_set = trip_set | static_set
        for i in grid:
            s = float(1.0 - P[i, 0])
            if state in ("MONITOR", "SUSPECT") and i in trip_set:
                state, consec = "INVESTIGATE", SUSPECT_N
            elif state == "MONITOR":
                if s >= self.thr["watch"]:
                    state, consec = "SUSPECT", 1
            elif state == "SUSPECT":
                consec = consec + 1 if s >= self.thr["watch"] else 0
                if consec == 0:
                    state = "MONITOR"
                elif consec >= SUSPECT_N:
                    state = "INVESTIGATE"
            if state == "INVESTIGATE":
                p_now = P_fast[i] if (P_fast is not None and i in trip_set) else P[i]              # fast trigger: instantaneous probabilities, not the 15-minute mean
                log, res = self.investigate(ctx, i, p_now, "score above watch level" if i not in trip_set else "fast trigger (static alarm or pressure collapse)")
                d = self.decide(ctx, i, p_now, log, res)
                state = "DECIDE"
                ev = {"event": len(events) + 1, "t_suspect_s": float(u.t[i]), "decisions": [], "t_watch_s": float(u.t[i]), "t_alert_s": None, "t_critical_s": None, "closed_s": None}
                events.append(ev)
                self._record(ev, d, decisions)
                state = "AWAIT_APPROVAL" if d.tier in ("alert", "critical") else "FOLLOW_UP"
                last_inv, n_follow, below = i, 0, 0
                tier_now, cls_now = d.tier, d.cls
                if state == "AWAIT_APPROVAL":
                    ok, delay = self.operator(d)
                    d.approved = bool(ok)
                    ev["approval_s"] = float(u.t[i]) + delay
                    state = "FOLLOW_UP"
            elif state == "FOLLOW_UP":
                below = below + EVAL_EVERY if s < self.thr["watch"] else 0
                escalate = (tier_now == "watch" and s >= self.thr["alert"]) or (i in trip_set and (cls_now != 5 or tier_now == "watch"))
                gap = FOLLOW_SCHEDULE[n_follow] if n_follow < len(FOLLOW_SCHEDULE) else FOLLOW_EVERY
                due = (i - last_inv) >= gap and n_follow < MAX_FOLLOW
                if below >= CLOSE_AFTER:
                    ev["closed_s"] = float(u.t[i])
                    state, tier_now, cls_now = "MONITOR", "none", 0
                elif escalate or due:
                    log, res = self.investigate(ctx, i, P[i], "follow-up" if not escalate else "escalation: score crossed the alert level")
                    d = self.decide(ctx, i, P[i], log, res)
                    self._record(ev, d, decisions)
                    last_inv, n_follow = i, n_follow + 1
                    if d.tier != tier_now and d.tier in ("alert", "critical"):
                        ok, delay = self.operator(d)
                        d.approved = bool(ok)
                    tier_now, cls_now = d.tier, d.cls
            if record_ticks:
                ticks.append({"tick": i, "t_s": float(u.t[i]), "state": state, "tier": tier_now, "class": cls_now, "score": round(s, 4)})
        return {"events": events, "decisions": decisions, "ticks": ticks}

    @staticmethod
    def _record(ev: dict[str, Any], d: Decision, decisions: list[Decision]) -> None:
        decisions.append(d)
        ev["decisions"].append(len(decisions) - 1)
        if d.tier in ("alert", "critical") and ev["t_alert_s"] is None:
            ev["t_alert_s"] = d.t_s
        if d.tier == "critical" and ev["t_critical_s"] is None:
            ev["t_critical_s"] = d.t_s
