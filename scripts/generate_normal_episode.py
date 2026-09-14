"""Generate one normal-operation episode (filling -> idle -> discharge) and
write it to output/normal_episode_sample.json, plus print a phase-by-phase
sanity summary against the workbook's own normal-operation bands."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import constants as C
from hydrai_twin.episode import NormalEpisodeConfig, NormalEpisodeGenerator


def summarize(records):
    by_phase = {}
    for r in records:
        by_phase.setdefault(r["system_context"]["phase"], []).append(r)

    print(f"episode_id: {records[0]['episode_id']}")
    print(f"total records: {len(records)}")
    print(f"boiloff_mode: {records[0]['system_context']['boiloff_mode']}")
    print()

    for phase, rows in by_phase.items():
        gt0, gt1 = rows[0]["simulation_ground_truth"], rows[-1]["simulation_ground_truth"]
        m0 = rows[0]["measurements"]
        p_vals = [r["simulation_ground_truth"]["pressure_bar_a"] for r in rows]
        lt_vals = [r["simulation_ground_truth"]["liquid_temp_c"] for r in rows]
        strain_vals = [r["simulation_ground_truth"]["strain_ue"] for r in rows]
        print(f"--- phase: {phase} ({len(rows)} ticks) ---")
        print(f"  mass_kg: {gt0['mass_kg']:.2f} -> {gt1['mass_kg']:.2f}")
        print(f"  fill_pct: {gt0['liquid_level_pct']:.2f} -> {gt1['liquid_level_pct']:.2f}")
        print(f"  pressure_bar_a range: [{min(p_vals):.3f}, {max(p_vals):.3f}]  "
              f"(Sec.5 normal band {C.PRESSURE_NORMAL_RANGE_BAR})")
        print(f"  liquid_temp_c range: [{min(lt_vals):.2f}, {max(lt_vals):.2f}]  "
              f"(Sec.6 normal band {C.TEMP_LH2_NORMAL_C})")
        print(f"  strain_ue range: [{min(strain_vals):.1f}, {max(strain_vals):.1f}]  "
              f"(Sec.9 sensor range {C.SENSOR_SPECS['strain_ue'][0:2]})")
        print(f"  example noisy measurement frame: {json.dumps(m0, indent=None)}")
        print()


def main():
    cfg = NormalEpisodeConfig(module_id="M01", boiloff_mode="baseline", seed=42, idle_duration_s=300.0)
    records = NormalEpisodeGenerator(cfg).generate()

    out_path = Path(__file__).resolve().parent.parent / "output" / "normal_episode_sample.json"
    out_path.write_text(json.dumps(records, indent=2))
    print(f"wrote {len(records)} records to {out_path}\n")

    summarize(records)


if __name__ == "__main__":
    main()
