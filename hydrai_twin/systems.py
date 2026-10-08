"""
System switch: the LH2 twin (default, unchanged: the BACKUP system) or the compressed gaseous hydrogen twin.

    from hydrai_twin.systems import generate_dataset
    generate_dataset(system="lh2", ...)      # the LH2 physical dataset driver, exactly as before
    generate_dataset(system="cgh2", ...)     # the CGH2 dataset driver (hydrai_twin/cgh2/)

Nothing here changes LH2 behaviour; the default is "lh2".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SYSTEMS = ("lh2", "cgh2")
DEFAULT_SYSTEM = "lh2"


def check(system: str) -> str:
    if system not in SYSTEMS:
        raise ValueError(f"system must be one of {SYSTEMS}, got {system!r}")
    return system


def generate_episode(system: str = DEFAULT_SYSTEM, **kwargs: Any):
    """One episode of the chosen system (keyword arguments are that system's episode config)."""
    if check(system) == "lh2":
        from hydrai_twin.physical_episode import generate_physical_episode
        return generate_physical_episode(**kwargs)
    from hydrai_twin.cgh2.episode import generate_cgh2_episode
    return generate_cgh2_episode(**kwargs)


def generate_dataset(system: str = DEFAULT_SYSTEM, out_dir: Path | str = "", workers: int = 1, **config: Any):
    """A dataset of the chosen system (`config` = that system's dataset config fields)."""
    out = Path(out_dir)
    if check(system) == "lh2":
        from hydrai_twin.physical_dataset import PhysicalDatasetConfig, generate_physical_dataset
        return generate_physical_dataset(PhysicalDatasetConfig(**config), out, workers=workers)
    from hydrai_twin.cgh2.dataset import CGH2DatasetConfig, generate_cgh2_dataset
    return generate_cgh2_dataset(CGH2DatasetConfig(**config), out, workers=workers)
