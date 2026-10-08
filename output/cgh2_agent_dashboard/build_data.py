"""Collect the numbers the dashboard shows from REAL replay JSON (read-only) into data.json. Nothing is computed beyond slicing, differences of times, and the kg-released integral of the
twin's own leak mass flow (evaluation ground truth, labelled as such on screen). Sources are listed in SOURCES.md.

    python build_data.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent.session import get_units

DEMO = ROOT / "output" / "cgh2_agent_demo"
NEW = HERE / "replays"
SRC = {"leak05": DEMO / "M01__leak-0.5mm.ticks.jsonl", "leak025": DEMO / "M01__leak-0.25mm.ticks.jsonl", "leak01": DEMO / "M01__leak-0.1mm.ticks.jsonl",
       "interc": DEMO / "M01__thermal-intercooler-r6h.ticks.jsonl", "cont": NEW / "M01__containment-leak-3.5mm.ticks.jsonl",
       "M02": NEW / "M02__normal-refuelling0.ticks.jsonl", "M03": NEW / "M03__normal-refuelling0.ticks.jsonl", "M04": NEW / "M04__normal-refuelling0.ticks.jsonl",
       "M05": NEW / "M05__normal-refuelling0.ticks.jsonl", "M06": NEW / "M06__normal-refuelling0.ticks.jsonl"}
NOW_H = {"s12": 81.0, "fleet": 100.0}                           # chosen instants (episode time, h)
TAG = {"P": "GH2-PT-101", "T": "GH2-TT-101", "Tw": "GH2-TT-102", "H2": "GH2-AT-101"}
r = lambda x, n=2: None if x is None else round(float(x), n)


def load(p):
    L = [json.loads(l) for l in open(p)]
    return L[0], L[1:]


def ep_name(key):
    return json.loads(open(SRC[key]).readline())["episode"]


if __name__ == "__main__":
    _, units = get_units()
    man = json.load(open(ROOT / "output/cgh2/medium/manifest.json"))
    cls = man["class_parameters"]
    out = {"class": {k: cls[k] for k in ("mop_bar", "pah_bar", "pahh_bar", "comp_start_bar", "comp_stop_bar")}, "ep": {}, "decisions": {}}
    ticks = {}
    for key, p in SRC.items():
        meta, tk = load(p)
        ticks[key] = (meta, tk)
        u = units[meta["episode"]]
        cum = np.concatenate([[0.0], np.cumsum((np.nan_to_num(u.truth["mdot_leak"]) + np.nan_to_num(u.truth["mdot_prv"])) * 60.0)])
        ds = u.raw.disc_state
        keep = key in ("leak05", "leak025", "leak01", "interc", "cont")
        # which ticks to embed: a window per episode (the screens' windows) or only a thin set for the fleet / overview modules
        onset = meta["timelines"]["onset_h"]
        if key == "leak05":
            lo, hi = 45.0, 100.0
        elif key == "interc":
            a0 = next(a for a in meta["timelines"]["agent_alert_h"] if a >= onset)
            lo, hi = a0 - 30.0, a0 + 10.0
        elif keep:
            lo, hi = (onset - 28.0 if onset else 40), (onset + 40.0 if onset else 200)
        else:
            lo, hi = 70.0, 110.0
        sel = [x for x in tk if lo <= x["t_h"] <= hi]
        rows = {"t": [], "P": [], "T": [], "Tw": [], "H2": [], "Pc": [], "inv": [], "kal": [], "score": [], "tier": [], "state": [], "cls": [], "static": [], "comp": [], "inlet": [], "dvalve": [], "prv": [],
                "Lr": [], "Llo": [], "Lhi": [], "orif": []}
        for x in sel:
            i = x["tick"]
            rows["t"].append(r(x["t_h"], 4)); rows["P"].append(r(x["raw_pressure_bar"], 2)); rows["Pc"].append(r(x["clean_pressure_bar"], 2))
            rows["T"].append(r(x["tags"][TAG["T"]], 2)); rows["Tw"].append(r(x["tags"][TAG["Tw"]], 2)); rows["H2"].append(r(x["tags"][TAG["H2"]], 2))
            rows["inv"].append(r(x["compensated_inventory_kg"], 2)); rows["kal"].append(r(x["kalman_inventory_kg"], 2)); rows["score"].append(r(x["agent"]["score"], 4))
            rows["tier"].append(x["agent"]["tier"]); rows["state"].append(x["agent"]["state"]); rows["cls"].append(x["agent"]["class_name_en"]); rows["static"].append(int(x["static_alarm"]))
            for k, nm in (("comp", "comp"), ("inlet", "inlet"), ("dvalve", "dvalve"), ("prv", "prv")):
                v = ds[nm][i]
                rows[k].append(None if not np.isfinite(v) else int(v > 0.5))
            lk = x["leak"]
            rows["Lr"].append(r(lk["rate_kgh"], 3) if lk else None); rows["Llo"].append(r(lk["lo"], 3) if lk else None); rows["Lhi"].append(r(lk["hi"], 3) if lk else None)
            rows["orif"].append(r(lk["orifice_mm"], 3) if lk else None)
        tl = meta["timelines"]
        on_s = meta["onset_s"]
        def kg_at(t_h):
            if on_s is None or t_h is None:
                return None
            c = lambda t: cum[min(int(np.searchsorted(u.t, t * 3600.0)), len(cum) - 1)]
            return r(c(t_h) - c(on_s / 3600.0), 2)
        post = lambda arr: [a for a in arr if onset is not None and a >= onset]
        first_alert = next((a for a in post(tl["agent_alert_h"])), None)
        first_op15 = next((a for a in post(tl["operator_15min_h"])), None)
        first_static = next((a for a in post(tl["static_alarm_h"])), None)
        out["ep"][key] = {"episode": meta["episode"], "module": meta["module"], "onset_h": onset, "thresholds": meta["thresholds"], "rows": rows,
                          "first_alert_h": first_alert, "first_operator15_h": first_op15, "first_static_h": first_static,
                          "kg_at_alert": kg_at(first_alert), "kg_at_operator15": kg_at(first_op15), "kg_at_static": kg_at(first_static),
                          "events": [{k: e.get(k) for k in ("t_suspect_s", "t_watch_s", "t_alert_s", "approval_s", "closed_s")} for e in meta["events"][:1]],
                          "timelines": tl}
        dec = [x["decision"] for x in tk if x.get("decision")]
        out["decisions"][key] = dec[:12]
    # fleet / overview snapshot values at the chosen instants (nearest tick at or before)
    def snap(key, t_h):
        meta, tk = ticks[key]
        x = [y for y in tk if y["t_h"] <= t_h][-1]
        u = units[meta["episode"]]
        ds = u.raw.disc_state
        i = x["tick"]
        return {"module": meta["module"], "episode": meta["episode"], "t_h": x["t_h"], "P": r(x["raw_pressure_bar"]), "T": r(x["tags"][TAG["T"]]), "H2": r(x["tags"][TAG["H2"]]), "inv": r(x["compensated_inventory_kg"]),
                "comp": int(ds["comp"][i] > 0.5), "static": int(x["static_alarm"]), "tier": x["agent"]["tier"], "state": x["agent"]["state"], "score": r(x["agent"]["score"], 3), "cls": x["agent"]["class_name_en"],
                "cls_ar": x["agent"]["class_name_ar"], "tags": x["tags"], "watch": x["agent"]["watch_threshold"], "alert": x["agent"]["alert_threshold"]}
    out["overview"] = [snap("leak05", NOW_H["s12"])] + [snap(m, NOW_H["s12"]) for m in ("M02", "M03", "M04", "M05", "M06")]
    out["fleet"] = [snap("leak025", NOW_H["fleet"])] + [snap(m, NOW_H["fleet"]) for m in ("M02", "M03", "M04", "M05", "M06")]
    out["now"] = NOW_H
    thr = json.load(open(ROOT / "output/cgh2_cache/agent/operator_thresholds.json"))["15"]          # set once on healthy dev data
    out["op"] = {"pressure_bar": thr["pressure"] * cls["mop_bar"], "temp_k": thr["temperature"], "comp_start_bar": cls["comp_start_bar"]}
    (HERE / "data.json").write_text(json.dumps(out, separators=(",", ":")))
    print("data.json", round((HERE / "data.json").stat().st_size / 1024), "KB")
    for k, v in out["ep"].items():
        print(k, v["episode"], "onset", v["onset_h"], "alert", v["first_alert_h"], "op15", v["first_operator15_h"], "static", v["first_static_h"], "kg alert/op", v["kg_at_alert"], v["kg_at_operator15"])
    print([ (o["module"], o["tier"]) for o in out["overview"]], [(o["module"], o["tier"], o["state"]) for o in out["fleet"]])
