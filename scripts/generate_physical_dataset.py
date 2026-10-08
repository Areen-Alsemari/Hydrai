"""Generate the physical-model dataset: dev modules x variants (+ commissioning runs, + fresh unseen units), seen through the
reference dashboard (reference configuration, not a verified Saudi system).

    python scripts/generate_physical_dataset.py                    # full -> output/physical_dataset/ (not in git)
    python scripts/generate_physical_dataset.py --fast             # smoke test (5-day episodes, one variant per family)
    python scripts/generate_physical_dataset.py --stratified       # robustness variant -> output/physical_dataset_stratified/
    python scripts/generate_physical_dataset.py --dashboard my_tags.json     # the plant's real tag list / rates / alarm limits
    python scripts/generate_physical_dataset.py --no-historian               # ideal instrument data (no filters, quality codes or faults)
    python scripts/generate_physical_dataset.py --h2-mode spec --vacuum-mode spec --level-mode ideal   # workbook Sec. 9 instruments
    python scripts/generate_physical_dataset.py --boiloff target             # 0.10 %/day (the spec value) instead of the 0.30 %/day default
    python scripts/generate_physical_dataset.py --valve-states               # expose valve states as discrete inputs

Generated data stays out of git.
"""

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin.channels import DashboardConfig
from hydrai_twin.historian import HistorianConfig
from hydrai_twin.physical_dataset import PhysicalDatasetConfig, generate_physical_dataset

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", choices=["lh2", "cgh2"], default="lh2", help="lh2 (default, unchanged) or cgh2 (compressed gaseous hydrogen; see scripts/cgh2_generate.py)")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--stratified", action="store_true", help="empirical stratification; robustness checks only")
    ap.add_argument("--dashboard", default=None, help="JSON with tags / sample periods / alarm limits (default: dashboard_tags.json, the reference config)")
    ap.add_argument("--no-historian", action="store_true")
    ap.add_argument("--no-channel-sampling", action="store_true", help="previous per-record instrument view (no periods / aggregation)")
    ap.add_argument("--h2-mode", choices=["lfl", "spec"], default="lfl")
    ap.add_argument("--vacuum-mode", choices=["log_gauge", "spec"], default="log_gauge")
    ap.add_argument("--level-mode", choices=["dp", "ideal"], default="dp")
    ap.add_argument("--boiloff", choices=["target", "baseline"], default=None, help="default: PHYSICAL_DEFAULT_BOILOFF_MODE (baseline = 0.30 %%/day; target = 0.10 %%/day, the spec value)")
    ap.add_argument("--valve-states", action="store_true")
    ap.add_argument("--modules", nargs="*", default=None)
    ap.add_argument("--no-unseen", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--out", default=None)
    args, rest = ap.parse_known_args()
    if args.system == "cgh2":                      # delegate; the LH2 path below is untouched
        import runpy
        sys.argv = ([str(ROOT / "scripts" / "cgh2_generate.py"), "--workers", str(args.workers)] + (["--fast"] if args.fast else [])
                    + (["--out", args.out] if args.out else []) + rest)
        runpy.run_path(sys.argv[0], run_name="__main__")
        return
    if rest:
        ap.error("unrecognized arguments: " + " ".join(rest))

    cfg = PhysicalDatasetConfig(
        fast=args.fast, stratification="empirical" if args.stratified else "off", include_unseen=not args.no_unseen,
        dashboard=DashboardConfig.from_json(args.dashboard) if args.dashboard else DashboardConfig.reference(),
        h2_mode=args.h2_mode, vacuum_mode=args.vacuum_mode, level_mode=args.level_mode, valve_states=args.valve_states,
        channel_sampling=not args.no_channel_sampling,
        historian=replace(HistorianConfig.from_registry(), enabled=not args.no_historian),
    )
    if args.boiloff:
        cfg.boiloff_mode = args.boiloff
    if args.modules:
        cfg.dev_modules = tuple(args.modules)
    default = "output/physical_dataset_stratified" if args.stratified else ("output/physical_dataset_fast" if args.fast else "output/physical_dataset")
    out = ROOT / (args.out or default)
    print(f"writing {out}  (workers={args.workers}, fast={args.fast}, dashboard={cfg.dashboard.status!r}, historian={'on' if cfg.historian.enabled else 'off'}, "
          f"boiloff={cfg.boiloff_mode}, h2={cfg.h2_mode}, vacuum={cfg.vacuum_mode}, level={cfg.level_mode})")
    m = generate_physical_dataset(cfg, out, workers=args.workers)
    by_role = {}
    for e in m["episodes"]:
        by_role[e["role"]] = by_role.get(e["role"], 0) + 1
    print(f"{m['n_episodes']} episodes {by_role} in {m['wall_seconds']}s -> {out / 'manifest.json'}")


if __name__ == "__main__":
    main()
