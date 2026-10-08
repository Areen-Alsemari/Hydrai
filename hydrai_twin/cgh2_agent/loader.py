"""Load the dataset into Units (dev + commissioning by default; unseen only when asked, for the one-shot evaluation)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hydrai_twin.cgh2.dashboard import CGH2Dashboard
from hydrai_twin.cgh2_agent import stream
from hydrai_twin.physical_dataset import static_flags_from_parquet

ROOT = Path(__file__).resolve().parents[2]


def load_all(dataset: str = "output/cgh2/medium", roles: tuple[str, ...] = ("dev", "commissioning"), valve_states: bool = True):
    root = ROOT / dataset
    m = json.loads((root / "manifest.json").read_text())
    cls = m["class_parameters"]
    dash = CGH2Dashboard.from_dict(m["dashboard"])
    ents = [e for e in m["episodes"] if e["role"] in roles]
    fc = stream.build_fast_cache(root, ents, cls["mop_bar"])             # cached per episode: cheap after the first run
    units = {}
    for e in ents:
        _, sf = static_flags_from_parquet(root / e["slow_file"], dash)
        units[e["name"]] = stream.load_unit(root, e, cls, fc, np.array(sf, dtype=bool), valve_states)
    return m, units
