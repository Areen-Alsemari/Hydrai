"""Per-episode table for the slow-drift episodes (task 1): detected or not, lead time, whether the agent named a sensor fault and which sensor. Reads the caches written once by cgh2_drift_run.py."""

import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent import operator_proxy as OP
from hydrai_twin.cgh2_agent.session import get_units
from ml.headline_metrics import alarm_events, score_episode

H = 3600.0
PAL = 0.70

if __name__ == "__main__":
    _, units = get_units("output/cgh2_drift/medium", ("drift", "commissioning"))
    D = {k: u for k, u in units.items() if u.entry["role"] == "drift"}
    runs = pickle.load(open(F.CACHE / "final_drift.pkl", "rb"))
    base = pickle.load(open(F.CACHE / "final_drift_baselines.pkl", "rb"))
    thr = OP.thresholds_cached()

    def flags(det, n, u):
        if det == "static_A":
            return u.static
        if det == "static_B":
            return u.static | ((u.raw.x["P"] < PAL * u.cls["mop_bar"]) & (u.t > 86400.0))
        if det in ("learned", "roc", "ewma", "cusum", "inv"):
            return base[("1/wk", det)][n]
        if det == "agent":
            f = np.zeros(u.n, dtype=bool)
            for ev in runs[n]["events"]:
                if ev["t_alert_s"] is not None:
                    f[min(int(np.searchsorted(u.t, ev["t_alert_s"])), u.n - 1)] = True
            return f
        if det.startswith("op"):
            per = int(det[2:4]) if det[2:4].isdigit() else 15
            return OP.flags(u, thr[per], per, expert=det.endswith("x"))
        raise KeyError(det)

    dets = ["static_A", "static_B", "learned", "agent", "op15", "op60", "op15x"]
    rows = ["| episode | sensor, drift | floor (ideal observer) | " + " | ".join(f"{d}: first alarm after onset" for d in dets) + " | agent: class at first alert / any decision in the event | agent: which sensor (T5 verdict) |", "|---|---|---|" + "---|" * (len(dets) + 2)]
    summary = {d: 0 for d in dets}
    summary_post = {d: 0 for d in dets}
    named = named_right = 0
    leads_static, leads_op = [], []
    detail = []
    for n, u in D.items():
        e = u.entry
        sc = {d: score_episode(e, u.t, flags(d, n, u), u.static, d, data_fault_flags=u.truth["has_data_fault"]) for d in dets}
        cells = []
        for d in dets:
            s = sc[d]
            early = e["first_observable_s"] is None or (s.first_alarm_s is not None and s.first_alarm_s < e["first_observable_s"])      # cannot have been caused by the drift: it is not yet observable (or never is)
            cells.append("-" if s.first_alarm_s is None else f"{s.delay_vs_onset_s / H:.1f} h" + ("†" if early else "") + (f" (+{s.n_false_alarms} pre-onset)" if s.n_false_alarms else ""))
            summary[d] += int(s.first_alarm_s is not None)
            summary_post[d] += int(s.first_alarm_s is not None and not early)
        r = runs[n]
        d0 = next((d for d in r["decisions"] if d["t_s"] >= e["onset_s"] and d["tier"] in ("alert", "critical")), None)
        ev_dec = [d for d in r["decisions"] if d["t_s"] >= e["onset_s"]]
        any_sensor = any(d["cls"] == 1 for d in ev_dec)
        t5 = [c["verdict"] for d in ev_dec for c in d["calls"] if c["tool"].startswith("T5") and c["verdict"].endswith("_suspect")]
        want = {"pressure_bar_a": "pressure_transmitter_suspect", "gas_temp_c": "temperature_probe_suspect"}[e["drift_tag"]]
        sens = ("/".join(sorted(set(t5))) if t5 else "-") + (" (right)" if want in t5 else " (wrong)" if t5 else "")
        named += int(d0 is not None and d0["cls"] == 1)
        named_right += int(want in t5 and d0 is not None)
        fl = "-" if e["first_observable_s"] is None else f"{(e['first_observable_s'] - e['onset_s']) / H:.0f} h"
        rows.append(f"| {n} | {e['drift_tag'].replace('_bar_a', '').replace('_c', '')} {e['drift_sign'] * e['drift_pct_fs']:+.1f} % FS | {fl} | " + " | ".join(cells) +
                    f" | {('class ' + str(d0['cls'])) if d0 else 'no alert'} / {'sensor named' if any_sensor else 'sensor not named'} | {sens} |")
        for other, bucket in (("static_A", leads_static), ("op15", leads_op)):
            if sc["agent"].first_alarm_s is not None and sc[other].first_alarm_s is not None:
                bucket.append((sc[other].first_alarm_s - sc["agent"].first_alarm_s) / H)
        detail.append((n, sc))
    n_ep = len(D)
    # chance reference: the same detectors on HEALTHY dev episodes (standard, incl. dark-vessel), with a pseudo-onset at each drift episode's onset time: how often does an unrelated
    # alarm event land in the window after it (any time to the end of the episode, within 72 h)?
    _, dev = get_units()
    healthy = {k: u for k, u in dev.items() if u.entry["role"] == "dev" and u.entry["fault_id"] == 0 and u.entry["scenario_class"] == "standard"}
    runs_dev = pickle.load(open(F.CACHE / "runs_full.pkl", "rb"))
    ck = pickle.load(open(ROOT / "output" / "cgh2_cache" / "checkpoint1_scores.pkl", "rb"))["flags"]
    onsets = [u.entry["onset_s"] for u in D.values()]

    def dev_flags(det, n, u):
        if det == "static_A":
            return u.static
        if det == "static_B":
            return u.static | ((u.raw.x["P"] < PAL * u.cls["mop_bar"]) & (u.t > 86400.0))
        if det == "learned":
            return ck[("1/wk", "learned")][n]
        if det == "agent":
            f = np.zeros(u.n, dtype=bool)
            for ev in runs_dev[n]["events"]:
                if ev["t_alert_s"] is not None:
                    f[min(int(np.searchsorted(u.t, ev["t_alert_s"])), u.n - 1)] = True
            return f
        per = int(det[2:4])
        return OP.flags(u, thr[per], per, expert=det.endswith("x"))
    null_any = {d: [] for d in dets}
    null_72 = {d: [] for d in dets}
    for d in dets:
        for n, u in healthy.items():
            ev = np.array(alarm_events(u.t, dev_flags(d, n, u), 3600.0))
            for o in onsets:
                nxt = ev[ev >= o]
                null_any[d].append(len(nxt) > 0)
                null_72[d].append(bool(len(nxt) and nxt[0] - o <= 72 * H))
    out = ["# Slow sensor-drift episodes: frozen agent against the static alarms, the learned model and the modelled operator", "",
           "Reference configuration, not a verified Saudi system. 12 NEW episodes (6 slow pressure-transmitter drifts, 6 slow gas-temperature-probe drifts, 0.5-2 % of full scale reached after 5 days, medium class, modules M01-M06, new seeds) in `output/cgh2_drift/medium/`, "
           "never used for tuning; scored ONCE with the frozen configuration (tool fit and fusion model fitted on all dev, nothing fitted here). The vessel is healthy: only the dashboard reading is wrong. "
           "'First alarm after onset' is the first alarm event at or after the drift onset (a pre-onset alarm is a false alarm and is shown separately; it is never credited). "
           "The ideal-observer floor is the time the noise-free drift first exceeds 3 sigma of the channel (sigma = accuracy / 2; for the gas-temperature probe this includes the 1 K bulk gradient); '-' = it never does, "
           "so no per-channel observer could see that drift at all. The operator proxy is a MODELLED operator (see `operator_proxy.py`), not a human study.", "",
           "## Per episode", ""] + rows + ["", "## Summary", "",
           "| detector | alarm after onset, any time (of 12) | CHANCE: the same detector on healthy dev episodes with the same pseudo-onsets | alarm after onset AND after the ideal-observer floor (the drift could have caused it) | CHANCE within 72 h of onset |", "|---|---|---|---|---|"] + [f"| {d} | {summary[d]} | {100 * np.mean(null_any[d]):.0f} % (expect {12 * np.mean(null_any[d]):.1f} of 12) | {summary_post[d]} | {100 * np.mean(null_72[d]):.0f} % |" for d in dets] + [""]
    out += ["† = the alarm came before the drift was observable at all (before the ideal-observer floor, or the floor does not exist): it cannot have been caused by the drift. A detector that fires at its false-alarm rate, whatever happens, looks like a detector in this table; the chance column says how much of that is expected from false alarms alone.", ""]
    out += [f"Agent named a sensor fault at the first alert in {named}/{n_ep} episodes and the RIGHT sensor in {named_right}/{n_ep}. "]
    if leads_static:
        out.append(f"Where both fired, the agent's median lead over static A: {np.median(leads_static):+.1f} h (n = {len(leads_static)}); over the 15-minute operator proxy: {np.median(leads_op):+.1f} h (n = {len(leads_op)}).")
    else:
        out.append("Static A never fired on a drift episode after onset in a case where the agent also fired (no paired lead).")
    out += ["", "Reading guide: the static alarms (PAH / PAHH / TAH / TAHH / H2) watch limits, and a drift of 0.5-2 % of full scale leaves the reading far inside them; they can only fire if something else happens in the same episode. "
            "The agent's chance on a pressure drift comes from the pressure-strain redundancy (T5) and from the inventory balance (T2), which a biased pressure reading breaks; a gas-temperature drift shifts the compensated inventory and "
            "the thermal residual (T3, T5) but at 0.5-2 % of a 190 K span (1-4 K) it is at or below the probe's own error plus the 1 K bulk gradient, which is why most of those have no ideal-observer floor."]
    p = ROOT / "output" / "reports" / "cgh2_agent_drift.md"
    p.write_text("\n".join(out) + "\n")
    print("\n".join(out[len(out) - 40:]) if False else p)
