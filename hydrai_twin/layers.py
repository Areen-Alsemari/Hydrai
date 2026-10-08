"""
Writers for the two data layers of a physical episode.

  slow layer : 60 s snapshots of the whole timeline -> Parquet (flat columns,
               prefixes ctx__ / meas__ / gt__ / label__)
  fast layer : 1 s rows during operations and event bursts -> JSONL (same
               nested schema as the legacy dataset)

Parquet needs `pyarrow` (requirements.txt).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

_PREFIXES = (("ctx", "system_context"), ("meas", "measurements"), ("q", "measurement_quality"),
             ("gt", "simulation_ground_truth"), ("label", "labels"),
             ("live", "measurements_live"), ("dfault", "data_faults"))   # q / live / dfault: only when the historian layer is on


def flatten_record(rec: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {"episode_id": rec["episode_id"], "timestamp": rec["timestamp"]}
    for prefix, key in _PREFIXES:
        for k, v in rec.get(key, {}).items():
            flat[f"{prefix}__{k}"] = json.dumps(list(v)) if isinstance(v, (list, tuple)) else v
    return flat


def write_slow_parquet(records: list[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [flatten_record(r) for r in records]
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:                       # union of columns; some keys exist only in some episode types
        for k in row:
            if k not in seen:
                seen.add(k)
                columns.append(k)
    table = pa.Table.from_pylist([{c: row.get(c) for c in columns} for row in rows])
    pq.write_table(table, path, compression="zstd")
    return len(rows)


def write_fast_jsonl(records: list[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open     # .jsonl.gz is still JSONL, just compressed
    with opener(path, "wt") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return len(records)


def write_episode_layers(result, out_dir: Path, name: str, gzip_fast: bool = False) -> dict[str, Any]:
    """Write one EpisodeResult as <name>.slow.parquet + <name>.fast.jsonl +
    <name>.meta.json; returns the paths and row counts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    slow = out_dir / f"{name}.slow.parquet"
    fast = out_dir / (f"{name}.fast.jsonl.gz" if gzip_fast else f"{name}.fast.jsonl")
    meta = out_dir / f"{name}.meta.json"
    n_slow = write_slow_parquet(result.slow, slow)
    n_fast = write_fast_jsonl(result.fast, fast)
    meta.write_text(json.dumps(result.meta, indent=2, default=str))
    return {"slow": slow, "fast": fast, "meta": meta, "n_slow": n_slow, "n_fast": n_fast}
