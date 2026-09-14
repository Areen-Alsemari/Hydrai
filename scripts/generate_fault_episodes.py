"""Generate one episode per Sec.10 fault scenario (1-6, -1) and check each
against the workbook's own qualitative signature table: does pressure/
temperature/boil-off/H2/strain move the direction Sec.10 says it should,
comparing the pre-onset (label 0) window against the fully-ramped
post-onset window."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import constants as C
from hydrai_twin.fault_episode import FaultEpisodeConfig, FaultEpisodeGenerator

OUT_DIR = Path(__file__).resolve().parent.parent / "output"


def phase_slices(records):
    pre = [r for r in records if r["labels"]["fault_id"] == 0 and r["system_context"]["phase"] == "idle"]
    post = [r for r in records if r["labels"]["fault_id"] != 0 and r["system_context"]["fault_severity"] >= 0.99]
    return pre, post


def stat(records, path_fn):
    vals = [path_fn(r) for r in records]
    return (min(vals), sum(vals) / len(vals), max(vals)) if vals else (float("nan"),) * 3


def summarize(fault_id, records):
    name = C.FAULT_LABELS[fault_id]
    pre, post = phase_slices(records)
    print(f"=== fault_id={fault_id} ({name}) -- {len(records)} records, "
          f"{sum(1 for r in records if r['labels']['fault_id']==fault_id)} labeled post-onset ===")
    if records[0]["system_context"].get("unknown_sub_faults") is not None:
        print(f"  composed of sub-faults: {records[0]['system_context']['unknown_sub_faults']}")

    fields = [
        ("pressure_bar_a", "bar(a)"),
        ("liquid_temp_c", "C"),
        ("h2_concentration_pct", "%vol"),
        ("strain_ue", "ue"),
        ("vacuum_pressure_pa", "Pa"),
        ("apparent_boiloff_rate_pct_day", "%/day"),
    ]
    for field, unit in fields:
        pre_lo, pre_mean, pre_hi = stat(pre, lambda r: r["simulation_ground_truth"][field])
        post_lo, post_mean, post_hi = stat(post, lambda r: r["simulation_ground_truth"][field])
        print(f"  {field:32s} pre[{pre_lo:9.3f},{pre_hi:9.3f}] mean={pre_mean:9.3f}  ->  "
              f"post[{post_lo:9.3f},{post_hi:9.3f}] mean={post_mean:9.3f}  ({unit})")
    print()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    scenarios = [1, 2, 3, 4, 5, 6, -1]
    for fault_id in scenarios:
        cfg = FaultEpisodeConfig(
            fault_id=fault_id,
            module_id="M01",
            boiloff_mode="baseline",
            seed=100 + fault_id if fault_id >= 0 else 999,
            idle_duration_s=900.0,
            ramp_duration_s=300.0,
        )
        records = FaultEpisodeGenerator(cfg).generate()
        fname = OUT_DIR / f"fault_episode_{fault_id if fault_id >= 0 else 'unknown'}.json"
        fname.write_text(json.dumps(records, indent=2))
        summarize(fault_id, records)


if __name__ == "__main__":
    main()
