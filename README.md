# HYDRAI Digital Twin

Simulation code and dataset generator for the HYDRAI liquid-hydrogen storage
digital twin. See `HYDRAI_Consolidated_Parameter_Workbook.md` and
`Predictive_Hydrogen_Storage_Safety_Project_Handoff.md` for the source
specs this implements against (every hardcoded constant in `hydrai_twin/`
cites which section it came from).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Regenerating the dataset

`output/dataset/*.jsonl` is generated, not checked in (300-800MB per file,
and fully reproducible from a fixed seed -- see `.gitignore`). To rebuild:

```bash
# Full dataset: 6 modules x ~35 scenario/severity/onset variants each,
# ~432K records, train/test split by held-out module (M06). Takes ~4 min.
python scripts/generate_dataset.py

# Quick smoke-test version (shorter episodes, fewer modules): ~6s.
python scripts/generate_dataset.py --modules M01 M02 --fast

# Also write the separate Sec.7 "target"-tier (0.05-0.10%/day) file,
# never merged into the baseline train/test set:
python scripts/generate_dataset.py --include-target-tier
```

Output: `dataset.jsonl` (everything), `train.jsonl` / `test.jsonl` (split
by held-out module, see `hydrai_twin/dataset.py:split_train_test`), and
`manifest.json` (per-episode metadata + label/variant counts -- this one
IS checked in, since it's small and lets you inspect what a run produced
without regenerating).

## Tests

```bash
python -m pytest tests/ -q
```
