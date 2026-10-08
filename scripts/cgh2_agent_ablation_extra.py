"""Extra ablation metrics (new file, frozen files untouched): for each variant, the class decided 30 minutes after the first alert, the median time to the first correct
alert-level diagnosis, and the median kg released before detection for 0.1-1 mm leaks.   python scripts/cgh2_agent_ablation_extra.py full,noT9,..."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ev", ROOT / "scripts" / "cgh2_agent_eval.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
from ml.headline_metrics import summarize

H = 3600.0
if __name__ == "__main__":
    tags = sys.argv[1].split(",")
    rows = ["| variant | class correct 30 min after the first alert | median time to correct diagnosis h (n) | median kg released before detection, 0.1-1 mm leaks (n) | detected within 24 h, 0.1 mm leaks | alert false alarms / week |", "|---|---|---|---|---|---|"]
    for tag in tags:
        D = ev.Data(ev.load_runs(tag))
        S = ev.score_all(D, ["agent_alert"])["agent_alert"]
        ok = tot = 0
        td, kg = [], []
        l01 = [0, 0]
        for n, u in D.units.items():
            e = u.entry
            if e["fault_id"] <= 0 or e["scenario_class"] != "standard":
                continue
            r = D.runs[n]
            d0 = ev.first_alert_decision(r, e)
            if d0 is not None:
                later = [d for d in r["decisions"] if d0["t_s"] <= d["t_s"] <= d0["t_s"] + 30 * 60 + 1 and d["tier"] in ("alert", "critical")]
                tot += 1
                ok += int(later[-1]["cls"] == e["fault_id"])
                t = ev.first_diag(r, e)
                if t is not None:
                    td.append((t - e["onset_s"]) / H)
            if e["fault_id"] == 3 and not e["expected_miss"] and S[n].first_alarm_s is not None:
                kg.append(D.released_between(n, e["onset_s"], S[n].first_alarm_s))
            if e["variant_tag"].endswith("0.1mm") and e["fault_id"] == 3:
                l01[1] += 1
                l01[0] += int(S[n].first_alarm_s is not None and S[n].delay_vs_onset_s <= 24 * H)
        fa = summarize(list(S.values()))["false_alarms"]["per_week"]
        rows.append(f"| {tag} | {ok}/{tot} | {np.median(td):.1f} ({len(td)}) | {np.median(kg):.2f} ({len(kg)}) | {l01[0]}/{l01[1]} | {fa:.2f} |")
    print("\n".join(rows))
