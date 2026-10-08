"""Generate physical-model episodes into the two layers (slow Parquet + fast
JSONL) with a manifest. Generated data stays OUT of git; only the small
sample under samples/physical/ is committed.

    python scripts/generate_physical_sample.py                # 6 scenarios, 14 d each -> output/physical/
    python scripts/generate_physical_sample.py --sample       # 3 short episodes -> samples/physical/ (committed)
    python scripts/generate_physical_sample.py --stratified   # same scenarios with stratification="empirical"
                                                              #   -> output/physical_stratified/ (robustness checks only)

The main dataset keeps stratification OFF. 85-90% fill appears only in the
labeled overfill/hydraulic-lock episode (manifest field scenario_class).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import placeholders as PH
from hydrai_twin.channels import PROVISIONAL_NOTE, REFERENCE_LABEL, DashboardConfig
from hydrai_twin.historian import HistorianConfig, apply_historian
from hydrai_twin.layers import write_episode_layers
from hydrai_twin.physical_dataset import PhysicalDatasetConfig, _tag_infos
from hydrai_twin.physical_episode import PhysicalEpisodeConfig, PhysicalEpisodeGenerator
from hydrai_twin.seeding import stable_seed

ROOT = Path(__file__).resolve().parent.parent

FULL = [
    ("normal", dict(fault_id=0)),
    ("insulation_severe", dict(fault_id=2)),
    ("vacuum_soft", dict(fault_id=3)),
    ("pcv_stuck_closed", dict(fault_id=4)),
    ("leak_small_medium", dict(fault_id=5)),
    ("hydraulic_lock_overfill", dict(fault_id=-1, unknown_sub_fault_ids=(3, 4), fill_target_frac=PH.value("overfill_fill_fraction"), allow_overfill=True)),
]
SAMPLE = [FULL[0], FULL[3], FULL[5]]
SAMPLE_OVERRIDES = dict(storage_days=6.0, onset_day_range=(1.5, 2.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="small committed sample (3 short episodes) -> samples/physical/")
    ap.add_argument("--stratified", action="store_true", help="robustness variant with empirical stratification (separate folder)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=20260201)
    args = ap.parse_args()

    scenarios = SAMPLE if args.sample else FULL
    overrides = dict(SAMPLE_OVERRIDES) if args.sample else {}
    strat = "empirical" if args.stratified else "off"
    default_out = "samples/physical" if args.sample else ("output/physical_stratified" if args.stratified else "output/physical")
    out = ROOT / (args.out or default_out)

    episodes, placeholders = [], {}
    dcfg = PhysicalDatasetConfig(stratification=strat)
    dash, view, hist = dcfg.dashboard_for_view(), dcfg.sensor_view(), dcfg.historian        # reference dashboard, historian ON
    for i, (name, kw) in enumerate(scenarios):
        cfg = PhysicalEpisodeConfig(seed=args.seed + i, stratification=strat, variant_tag=name, sensor_view=view, **overrides, **kw)
        res = PhysicalEpisodeGenerator(cfg).generate()
        hseed = stable_seed(cfg.seed, "hist-slow")
        res.slow, _ = apply_historian(res.slow, hist, hseed, _tag_infos(dash, view), res.meta["duration_s"], 60.0)
        res.fast, _ = apply_historian(res.fast, hist, hseed, _tag_infos(dash, view), res.meta["duration_s"], 1.0)
        paths = write_episode_layers(res, out, name, gzip_fast=args.sample)   # the committed sample gzips the fast layer
        res.meta["files"] = {"slow": paths["slow"].name, "fast": paths["fast"].name}
        for p in res.meta.pop("placeholders_used"):
            placeholders[p["name"]] = p
        episodes.append(res.meta)
        print(f"{name:26s} slow {paths['n_slow']:6d} rows  fast {paths['n_fast']:6d} rows  "
              f"class={res.meta['scenario_class']:24s} fill={res.meta['fill_target_pct']:.0f}%  "
              f"{'ended: dry' if res.meta['ended_reason'] else ''}")

    (out / "manifest.json").write_text(json.dumps({
        "note": "Physical-model dataset. Valve/regulator/vent/instrument/historian values are PLACEHOLDERS pending engineering answers "
                "(ENGINEER_QUESTIONS_VALVE_VENT.md). Main dataset: stratification off, spec fill (85% nominal, 90% max) except labeled "
                "overfill episodes (above 90%); healthy boil-off 0.30 %/day (PHYSICAL_DEFAULT_BOILOFF_MODE; 'target' = 0.10 %/day spec).",
        "dashboard_label": REFERENCE_LABEL, "static_alarm_status": PROVISIONAL_NOTE, "historian": hist.to_dict(),
        "sensor_view": view.to_dict(), "dashboard_tag_names": dash.tag_names(),
        "stratification": strat, "seed": args.seed, "episodes": episodes,
        "placeholders_used": list(placeholders.values()),
    }, indent=2, default=str))
    size_mb = sum(f.stat().st_size for f in out.iterdir()) / 1e6
    print(f"\nwrote {len(episodes)} episodes to {out}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
