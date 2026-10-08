"""
Headline metrics for the agent, defined against the EXISTING static alarms.

Two numbers lead the report:

  1. LEAD TIME vs the static alarms: for each fault episode, (first static alarm
     at/after onset) - (first agent alarm at/after onset). Positive = the agent
     warned earlier. Reported with the outcome mix, so a missed fault or a
     fault the static alarms never caught is not hidden inside a mean:
        agent_first | static_first | agent_only | static_only | both_missed
  2. FALSE ALARMS PER WEEK over HEALTHY exposure: every normal episode in full
     plus the pre-onset part of each fault episode. Alarm samples within
     `merge_gap_s` of each other count as ONE alarm event.

Detection delay is also reported against both reference times (true onset, and
the first observable deviation, an ideal-observer bound; see observability.py).
An alarm BEFORE onset is a false alarm, never a detection.

The static-alarm baseline goes through exactly the same scoring, so the agent is
compared against what operators already have, not against zero. Which limits
count as "the existing static alarms" comes from the dashboard config
(channels.py); until the real one is supplied it is the placeholder default.

No thresholds are tuned here. A detector hands in a boolean flag per 60 s slow
sample; the operating point of the detector must be fixed on training/LOMO-train
data before it is scored (see ml/ for the no-cheating rules).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

WEEK_S = 7 * 86400.0
HOUR_S = 3600.0
DEFAULT_MERGE_GAP_S = 3600.0

# Alarm-load norms (reference configuration, source STD): EEMUA 191 / ISA-18.2.
EEMUA_MANAGEABLE_PER_H = 6.0     # about 6 alarms per hour on average is manageable
EEMUA_BUSY_CEILING_PER_H = 12.0  # 12 per hour is the busy ceiling
AGENT_TARGET_PER_H = 1.0         # agent target: no more than about 1 alert per hour of healthy operation


def alarm_events(t_s: Sequence[float], flags: Sequence[bool], merge_gap_s: float = DEFAULT_MERGE_GAP_S) -> list[float]:
    """Start times of alarm events: flagged samples closer than `merge_gap_s` form one event."""
    events: list[float] = []
    last_flag_t: float | None = None
    for t, f in zip(t_s, flags):
        if not f:
            continue
        if last_flag_t is None or t - last_flag_t > merge_gap_s:
            events.append(float(t))
        last_flag_t = float(t)
    return events


@dataclass
class EpisodeScore:
    episode_id: str
    fault_id: int
    scenario_class: str
    onset_s: float | None
    first_observable_s: float | None
    end_s: float
    healthy_exposure_s: float
    detector: str
    n_false_alarms: int                   # alarm events before onset (whole episode if no fault), NOT starting inside a data fault
    n_data_fault_alarms: int              # alarm events that START inside an injected data fault (stale / flat-line / out-of-range / dropout)
    first_alarm_s: float | None           # first alarm event at/after onset (fault episodes only)
    static_first_alarm_s: float | None    # same, for the static baseline
    delay_vs_onset_s: float | None
    delay_vs_observable_s: float | None
    lead_vs_static_s: float | None
    outcome: str                          # normal | agent_first | static_first | tie | agent_only | static_only | both_missed


def score_episode(
    meta: dict[str, Any],
    t_s: Sequence[float],
    detector_flags: Sequence[bool],
    static_flags: Sequence[bool],
    detector: str = "agent",
    merge_gap_s: float = DEFAULT_MERGE_GAP_S,
    data_fault_flags: Sequence[bool] | None = None,
) -> EpisodeScore:
    """Score one episode. `meta` is the generator's meta (onset_s, first_observable_s, ...). `data_fault_flags` (per sample, the
    `label__has_data_fault` column) marks injected historian faults: an alarm event that starts inside one is counted in
    `n_data_fault_alarms`, not as a false alarm and never as a detection. Data faults are not physical anomalies. This is
    conservative: a genuine detection whose first alarm happens to fall inside a data fault is not credited (faults are rare)."""
    df = np.asarray(data_fault_flags, dtype=bool) if data_fault_flags is not None else None
    t_arr = np.asarray(t_s, dtype=float)

    def in_fault(e: float) -> bool:
        return bool(df is not None and df[int(np.searchsorted(t_arr, e))])

    onset = meta.get("onset_s")
    end = float(meta["duration_s"])
    d_ev_all = alarm_events(t_s, detector_flags, merge_gap_s)
    s_ev = alarm_events(t_s, static_flags, merge_gap_s)
    d_ev_fault = [e for e in d_ev_all if in_fault(e)]
    d_ev = [e for e in d_ev_all if not in_fault(e)]
    if onset is None:
        return EpisodeScore(meta["episode_id"], 0, meta.get("scenario_class", "standard"), None, None, end, end, detector,
                            len(d_ev), len(d_ev_fault), None, None, None, None, None, "normal")
    # An event that STARTED before onset and is still flagged after onset also counts as a false alarm at its
    # start; the fault is only credited with an event that starts at/after onset.
    n_false = sum(1 for e in d_ev if e < onset)
    d_first = next((e for e in d_ev if e >= onset), None)
    s_first = next((e for e in s_ev if e >= onset), None)
    obs = meta.get("first_observable_s")
    lead = (s_first - d_first) if (d_first is not None and s_first is not None) else None
    if d_first is None and s_first is None:
        outcome = "both_missed"
    elif d_first is None:
        outcome = "static_only"
    elif s_first is None:
        outcome = "agent_only"
    elif lead > 0:
        outcome = "agent_first"
    elif lead < 0:
        outcome = "static_first"
    else:
        outcome = "tie"
    return EpisodeScore(
        meta["episode_id"], int(meta["fault_id"]), meta.get("scenario_class", "standard"), float(onset),
        obs, end, float(meta.get("healthy_exposure_s", onset)), detector, n_false,
        sum(1 for e in d_ev_fault if e < onset), d_first, s_first,
        (d_first - onset) if d_first is not None else None,
        (d_first - obs) if (d_first is not None and obs is not None) else None,
        lead, outcome)


def _poisson_ci(k: int, exposure_weeks: float, conf: float = 0.95) -> tuple[float, float]:
    """Exact (Garwood) interval for a rate k / exposure."""
    if exposure_weeks <= 0:
        return (float("nan"), float("nan"))
    from scipy.stats import chi2
    a = 1.0 - conf
    lo = 0.0 if k == 0 else 0.5 * chi2.ppf(a / 2, 2 * k)
    hi = 0.5 * chi2.ppf(1 - a / 2, 2 * (k + 1))
    return (lo / exposure_weeks, hi / exposure_weeks)


def _q(x: list[float], q: float) -> float | None:
    return float(np.quantile(x, q)) if x else None


def summarize(scores: Sequence[EpisodeScore]) -> dict[str, Any]:
    """Headline numbers for one detector over a set of episodes (e.g. the held-out module's)."""
    faults = [s for s in scores if s.fault_id != 0]
    exposure_s = float(sum(s.healthy_exposure_s for s in scores))
    weeks = exposure_s / WEEK_S
    n_false = int(sum(s.n_false_alarms for s in scores))
    n_df = int(sum(s.n_data_fault_alarms for s in scores))
    lo, hi = _poisson_ci(n_false, weeks)
    detected = [s for s in faults if s.first_alarm_s is not None]
    leads = [s.lead_vs_static_s for s in faults if s.lead_vs_static_s is not None]
    outcomes: dict[str, int] = {}
    for s in faults:
        outcomes[s.outcome] = outcomes.get(s.outcome, 0) + 1
    return {
        "n_episodes": len(scores), "n_fault_episodes": len(faults),
        "false_alarms": {"events": n_false, "healthy_exposure_weeks": weeks,
                         "per_week": (n_false / weeks) if weeks > 0 else None, "per_week_ci95": [lo, hi],
                         "data_fault_alarm_events": n_df,
                         "data_fault_alarms_per_week": (n_df / weeks) if weeks > 0 else None},
        "alerts_per_hour_healthy": (n_false + n_df) / (exposure_s / HOUR_S) if exposure_s > 0 else None,
        "detection": {
            "detected": len(detected), "fraction": (len(detected) / len(faults)) if faults else None,
            "delay_vs_onset_h": {"median": _h(_q([s.delay_vs_onset_s for s in detected], 0.5)),
                                 "p25": _h(_q([s.delay_vs_onset_s for s in detected], 0.25)),
                                 "p75": _h(_q([s.delay_vs_onset_s for s in detected], 0.75))},
            "delay_vs_first_observable_h": {"median": _h(_q([s.delay_vs_observable_s for s in detected if s.delay_vs_observable_s is not None], 0.5))},
        },
        "lead_vs_static": {
            "outcomes": outcomes,
            "n_both_fired": len(leads),
            "lead_h": {"median": _h(_q(leads, 0.5)), "p25": _h(_q(leads, 0.25)), "p75": _h(_q(leads, 0.75))},
            "fraction_agent_first_of_all_faults": (outcomes.get("agent_first", 0) / len(faults)) if faults else None,
            "note": "positive lead = agent alarmed before the static alarm; agent_only = static never fired; "
                    "static_only/both_missed are failures and are counted, not dropped",
        },
    }


def _h(x: float | None) -> float | None:
    return None if x is None else x / 3600.0


def summarize_by_fault(scores: Sequence[EpisodeScore]) -> dict[int, dict[str, Any]]:
    """Per fault type (healthy exposure stays pooled, so the false-alarm rate is only in `summarize`)."""
    out: dict[int, dict[str, Any]] = {}
    for fid in sorted({s.fault_id for s in scores if s.fault_id != 0}):
        sub = [s for s in scores if s.fault_id == fid]
        d = summarize(sub)
        out[fid] = {"n": len(sub), "detection": d["detection"], "lead_vs_static": d["lead_vs_static"]}
    return out


def alerts_per_hour(n_events: int, exposure_s: float) -> float | None:
    return n_events / (exposure_s / HOUR_S) if exposure_s > 0 else None


def alarm_load_verdict(per_hour: float | None, kind: str) -> str:
    """kind = 'operator' (EEMUA 191: <= 6/h manageable, 12/h busy ceiling) or 'agent' (target about 1/h)."""
    if per_hour is None:
        return "n/a"
    if kind == "agent":
        return "within target" if per_hour <= AGENT_TARGET_PER_H else f"ABOVE the ~{AGENT_TARGET_PER_H:g}/h target"
    if per_hour <= EEMUA_MANAGEABLE_PER_H:
        return "manageable"
    return "busy (above manageable)" if per_hour <= EEMUA_BUSY_CEILING_PER_H else "ABOVE the busy ceiling"
