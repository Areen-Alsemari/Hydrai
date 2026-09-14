"""Build the full HYDRAI digital-twin dataset: every module x every Sec.10
scenario x several severity/size/onset-timing variants per scenario,
written as output/dataset/{dataset,train,test}.jsonl + manifest.json.
Optionally also writes the separate, never-merged Sec.7 'target'-tier file.

Usage:
    python scripts/generate_dataset.py                          # full build
    python scripts/generate_dataset.py --modules M01 M02 --fast # quick smoke run
    python scripts/generate_dataset.py --include-target-tier    # + dataset_target_tier.jsonl
    python scripts/generate_dataset.py --held-out-modules M05 M06
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import constants as C
from hydrai_twin.dataset import DatasetConfig, write_dataset, write_target_tier_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", nargs="*", default=list(C.MODULE_IDS))
    ap.add_argument("--held-out-modules", nargs="*", default=["M06"])
    ap.add_argument("--out", default="output/dataset")
    ap.add_argument("--fast", action="store_true", help="shorter episodes, for a quick smoke test")
    ap.add_argument("--seed", type=int, default=20260101)
    ap.add_argument("--include-target-tier", action="store_true",
                     help="also write dataset_target_tier.jsonl (Sec.7 'target' tier, never merged into train/test)")
    args = ap.parse_args()

    cfg = DatasetConfig(
        modules=tuple(args.modules),
        base_seed=args.seed,
        idle_duration_s_normal=120.0 if args.fast else 600.0,
        idle_duration_s_fault=180.0 if args.fast else 900.0,
        dt_s=2.0 if args.fast else 1.0,
    )

    out_dir = Path(__file__).resolve().parent.parent / args.out
    write_dataset(cfg, out_dir, held_out_modules=tuple(args.held_out_modules))

    manifest = json.loads((out_dir / "manifest.json").read_text())
    print(f"wrote {manifest['total_records']} records across {len(manifest['episodes'])} episodes to {out_dir}")
    print(f"  train: {manifest['split']['train_records']}  test: {manifest['split']['test_records']}")
    print(f"  held-out modules: {manifest['split']['held_out_modules']}")
    print("label counts (full dataset):")
    for name, count in sorted(manifest["label_counts"].items()):
        print(f"  {name:28s} {count}")

    if args.include_target_tier:
        write_target_tier_dataset(cfg, out_dir)
        tmanifest = json.loads((out_dir / "manifest_target_tier.json").read_text())
        print(f"\nwrote {tmanifest['total_records']} target-tier records to "
              f"{out_dir / 'dataset_target_tier.jsonl'} (separate file, not merged)")


if __name__ == "__main__":
    main()
