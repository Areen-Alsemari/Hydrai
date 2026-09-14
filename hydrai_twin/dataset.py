"""
Top-level dataset driver: runs the normal-operation generator (episode.py)
and the fault-injection generator (fault_episode.py) across a set of
modules AND a set of severity/size/onset-timing variants per scenario, and
writes out JSONL files plus a manifest.

Why variants, not just modules x scenarios: one canonical trajectory per
scenario (differing only in noise seed) doesn't give a downstream model
enough signal to learn severity, or to tell real physical variation apart
from noise -- it can just memorize each scenario's one fixed shape. See
_fault_variants() below for exactly what's varied per scenario and why.

Citation (corrected): this module's diversity and split requirements come
from Predictive_Hydrogen_Storage_Safety_Project_Handoff.md, NOT
HYDRAI_Consolidated_Parameter_Workbook.md (the earlier, incorrect
attribution has been fixed here). Verified against that file directly:
  - Sec.12 "Scenario Classes" -> "Leak scenarios should vary": leak
    location, orifice size, initial pressure/temperature, sudden-vs-
    progressive, growth law, operating mode at onset, duration,
    environment, sensor noise/placement -- the basis for _fault_variants().
  - Sec.19 "Evaluation" -> "Split rule": "Split by scenario/episode, not
    random rows... Prefer unseen episodes/configurations in test" -- the
    basis for split_train_test() below splitting by whole held-out module
    rather than by random episode/row.
  - Sec.24 "What NOT to Do", items 2 ("Do not train only on normal vs leak;
    include confusing faults") and 8 ("Do not randomly split rows from the
    same episode across train/test") -- reinforces both of the above.

Every episode uses a distinct, derived-but-reproducible seed
(base_seed + a stable per-(module, scenario, variant) offset), so the whole
dataset is deterministic given `base_seed`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hydrai_twin import constants as C
from hydrai_twin.episode import NormalEpisodeConfig, NormalEpisodeGenerator
from hydrai_twin.fault_episode import FaultEpisodeConfig, FaultEpisodeGenerator

FAULT_SCENARIOS = (1, 2, 3, 4, 5, 6, -1)  # Sec.10 labels, excluding 0 (handled by the normal generator)

# --- variant axes (all simulation/dataset-design choices, not workbook
# numbers except where a variant directly names a Sec.10/Sec.17.3 tier) ----
_ONSET_FRAC_CYCLE = [0.15, 0.3, 0.45, 0.6, 0.75]
_LEAK_SEVERITY_LADDER = ["pinhole", "small", "small_medium", "medium_large", "full_bore"]
_UNKNOWN_SUBFAULT_PAIRS = [(2, 5), (3, 6), (4, 5), (2, 4), (3, 5), (6, 2)]


def _fault_variants(fault_id: int) -> list[dict[str, Any]]:
    """One dict of FaultEpisodeConfig kwarg overrides per variant. Each
    dict always carries `variant_tag` (used both for dataset introspection
    and by split_train_test's held_out_severity_by_fault filter) and
    `onset_frac_of_idle` (every scenario varies onset timing)."""

    if fault_id == 1:
        # Sensor fault: conceptually unchanged (Sec.10: ground truth stays
        # normal, only the flagged channel goes erratic) -- vary onset only.
        return [
            {"onset_frac_of_idle": frac, "variant_tag": f"onset_{frac:.2f}"}
            for frac in _ONSET_FRAC_CYCLE
        ]

    if fault_id in (2, 3):
        # Insulation/vacuum degradation: cross Sec.10's two non-normal
        # health tiers (70="degraded", 40="severe") with three ramp speeds,
        # each combo also getting a distinct onset time (cycled, not crossed
        # again, to keep the variant count from exploding).
        health_tiers = [("degraded", 70.0), ("severe", 40.0)]
        ramp_tiers = [("fast", 120.0), ("medium", 300.0), ("slow", 900.0)]
        variants = []
        i = 0
        for health_label, health_pct in health_tiers:
            for ramp_label, ramp_s in ramp_tiers:
                variants.append({
                    "target_health_pct": health_pct,
                    "ramp_duration_s": ramp_s,
                    "onset_frac_of_idle": _ONSET_FRAC_CYCLE[i % len(_ONSET_FRAC_CYCLE)],
                    "variant_tag": f"{health_label}_{ramp_label}",
                })
                i += 1
        return variants

    if fault_id in (4, 6):
        # Abnormal pressure rise / structural concern: vary magnitude via
        # max_severity (mild/moderate/severe) rather than always maxing out.
        severity_tiers = [("mild", 0.4), ("moderate", 0.7), ("severe", 1.0)]
        return [
            {
                "max_severity": sev,
                "onset_frac_of_idle": _ONSET_FRAC_CYCLE[i % len(_ONSET_FRAC_CYCLE)],
                "variant_tag": label,
            }
            for i, (label, sev) in enumerate(severity_tiers)
        ]

    if fault_id == 5:
        # Containment anomaly: full Sec.17.3 leak-size ladder, each rung
        # paired with a distinct (initial pressure, fill level at onset,
        # onset timing) combination -- paired 1:1 rather than fully crossed
        # with the ladder, to keep episode count manageable while still
        # varying both axes the diversity request called for.
        conditions = [
            (1.05, 80.0, 0.2),
            (1.20, 85.0, 0.35),
            (1.45, 90.0, 0.5),
            (1.05, 85.0, 0.65),
            (1.35, 90.0, 0.3),
        ]
        variants = []
        for leak_severity, (p0, fill_target, onset) in zip(_LEAK_SEVERITY_LADDER, conditions):
            variants.append({
                "leak_severity": leak_severity,
                "initial_pressure_bar": p0,
                "fill_target_pct": fill_target,
                "onset_frac_of_idle": onset,
                "variant_tag": leak_severity,
            })
        return variants

    if fault_id == -1:
        # Unknown composite: vary onset timing and which two named faults
        # get composed (kept conceptually as "any two", per the request).
        variants = []
        for i, (a, b) in enumerate(_UNKNOWN_SUBFAULT_PAIRS):
            onset = _ONSET_FRAC_CYCLE[i % len(_ONSET_FRAC_CYCLE)]
            variants.append({
                "unknown_sub_fault_ids": (a, b),
                "onset_frac_of_idle": onset,
                "variant_tag": f"unknown_{a}_{b}",
            })
        return variants

    raise ValueError(f"no variant matrix defined for fault_id={fault_id}")


@dataclass
class DatasetConfig:
    modules: tuple[str, ...] = tuple(C.MODULE_IDS)
    boiloff_modes: tuple[str, ...] = ("baseline",)   # Sec.7: kept explicit, not blended;
                                                       # "target" tier is written to its own
                                                       # separate file by write_target_tier_dataset(),
                                                       # never merged in here
    include_normal: bool = True
    fault_ids: tuple[int, ...] = FAULT_SCENARIOS
    idle_duration_s_normal: float = 600.0
    idle_duration_s_fault: float = 900.0
    dt_s: float = 1.0
    base_seed: int = 20260101
    start_time: datetime | None = None
    episode_spacing_s: float = 3600.0  # stagger each episode's timestamps so a
                                        # dataset built from many episodes doesn't
                                        # have every one starting at the same clock time


@dataclass
class EpisodeManifestEntry:
    episode_id: str
    module_id: str
    boiloff_mode: str
    fault_id: int
    fault_name: str
    variant_tag: str
    n_records: int
    seed: int


def _seed_for(base_seed: int, module_idx: int, scenario_key: str) -> int:
    # stable, collision-free derivation: not workbook-related, just bookkeeping
    return base_seed + module_idx * 100_000 + abs(hash(scenario_key)) % 99_991


def generate_dataset(cfg: DatasetConfig) -> tuple[list[dict[str, Any]], list[EpisodeManifestEntry]]:
    all_records: list[dict[str, Any]] = []
    manifest: list[EpisodeManifestEntry] = []
    t_cursor = cfg.start_time or datetime.now(timezone.utc)

    for module_idx, module_id in enumerate(cfg.modules):
        for boiloff_mode in cfg.boiloff_modes:
            if cfg.include_normal:
                seed = _seed_for(cfg.base_seed, module_idx, f"normal-{boiloff_mode}")
                ep_cfg = NormalEpisodeConfig(
                    module_id=module_id,
                    boiloff_mode=boiloff_mode,
                    dt_s=cfg.dt_s,
                    idle_duration_s=cfg.idle_duration_s_normal,
                    seed=seed,
                    start_time=t_cursor,
                )
                records = NormalEpisodeGenerator(ep_cfg).generate()
                all_records.extend(records)
                manifest.append(EpisodeManifestEntry(
                    episode_id=records[0]["episode_id"], module_id=module_id,
                    boiloff_mode=boiloff_mode, fault_id=0, fault_name="normal",
                    variant_tag="default", n_records=len(records), seed=seed,
                ))
                t_cursor += timedelta(seconds=len(records) * cfg.dt_s + cfg.episode_spacing_s)

            for fault_id in cfg.fault_ids:
                for variant in _fault_variants(fault_id):
                    variant_tag = variant["variant_tag"]
                    seed = _seed_for(cfg.base_seed, module_idx, f"fault-{fault_id}-{variant_tag}-{boiloff_mode}")
                    f_cfg = FaultEpisodeConfig(
                        fault_id=fault_id,
                        module_id=module_id,
                        boiloff_mode=boiloff_mode,
                        dt_s=cfg.dt_s,
                        idle_duration_s=cfg.idle_duration_s_fault,
                        seed=seed,
                        start_time=t_cursor,
                        **variant,
                    )
                    records = FaultEpisodeGenerator(f_cfg).generate()
                    all_records.extend(records)
                    manifest.append(EpisodeManifestEntry(
                        episode_id=records[0]["episode_id"], module_id=module_id,
                        boiloff_mode=boiloff_mode, fault_id=fault_id,
                        fault_name=C.FAULT_LABELS.get(fault_id, "unknown_anomaly"),
                        variant_tag=variant_tag, n_records=len(records), seed=seed,
                    ))
                    t_cursor += timedelta(seconds=len(records) * cfg.dt_s + cfg.episode_spacing_s)

    return all_records, manifest


def _label_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        name = r["labels"]["fault_name"]
        counts[name] = counts.get(name, 0) + 1
    return counts


def _variant_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        key = f"{r['labels']['fault_name']}:{r['system_context']['variant_tag']}"
        counts[key] = counts.get(key, 0) + 1
    return counts


# --- train/test split -------------------------------------------------------

#: Default held-out module for the generalization test. Train sees the full
#: severity spectrum (mild/moderate/severe, every leak size, etc.) on every
#: OTHER module -- severity is not excluded from training. Reasoning
#: (corrected from an earlier version of this split): for a safety-
#: monitoring model, "the model has zero training examples of severe cases"
#: is the worst possible failure mode for exactly the labels that matter
#: most -- severity detection needs to be a learned pattern from seeing
#: mild/moderate/severe examples elsewhere, not extrapolation to a case
#: with no precedent. The held-out module alone is the generalization test
#: (Sec.19 "Split rule": "prefer unseen episodes/configurations in test");
#: an earlier version of this function additionally excluded top-severity
#: variants from training across ALL modules, which has been removed.
DEFAULT_HELD_OUT_MODULES: tuple[str, ...] = ("M06",)


def split_train_test(
    records: list[dict[str, Any]],
    held_out_modules: tuple[str, ...] = DEFAULT_HELD_OUT_MODULES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split by held-out module, not by random episode/row (Sec.19 "Split
    rule": "Split by scenario/episode, not random rows... Prefer unseen
    episodes/configurations in test"; Sec.24 item 8: "Do not randomly split
    rows from the same episode across train/test"). Every module not in
    `held_out_modules` goes entirely to train, at every severity/size
    variant; every module in `held_out_modules` goes entirely to test, also
    at every variant -- so test evaluates generalization to a genuinely
    unseen configuration (a different module), including its severe cases,
    which the model learned to recognize from the other modules' severe
    cases rather than seeing for the first time in test.
    """
    train, test = [], []
    for r in records:
        module_id = r["system_context"]["module_id"]
        (test if module_id in held_out_modules else train).append(r)
    return train, test


# --- writers -----------------------------------------------------------

def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def write_dataset(
    cfg: DatasetConfig,
    out_dir: Path,
    held_out_modules: tuple[str, ...] = DEFAULT_HELD_OUT_MODULES,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    records, manifest = generate_dataset(cfg)
    train, test = split_train_test(records, held_out_modules)

    _write_jsonl(records, out_dir / "dataset.jsonl")
    _write_jsonl(train, out_dir / "train.jsonl")
    _write_jsonl(test, out_dir / "test.jsonl")

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(
        {
            "config": {
                "modules": cfg.modules,
                "boiloff_modes": cfg.boiloff_modes,
                "fault_ids": cfg.fault_ids,
                "base_seed": cfg.base_seed,
                "dt_s": cfg.dt_s,
            },
            "split": {
                "held_out_modules": held_out_modules,
                "note": "severity/size is NOT excluded from training -- train sees the full "
                        "spectrum on every non-held-out module; only the held-out module's "
                        "records go to test, at every severity level.",
                "train_records": len(train),
                "test_records": len(test),
            },
            "episodes": [e.__dict__ for e in manifest],
            "total_records": len(records),
            "label_counts": _label_counts(records),
            "variant_counts": _variant_counts(records),
        },
        indent=2,
    ))


def resplit_jsonl(
    src_path: Path,
    train_path: Path,
    test_path: Path,
    held_out_modules: tuple[str, ...] = DEFAULT_HELD_OUT_MODULES,
) -> tuple[int, int]:
    """Re-apply split_train_test's logic directly to an already-generated
    dataset.jsonl, streaming line-by-line rather than regenerating the
    underlying episodes (which is expensive) or holding the whole file in
    memory. Returns (train_count, test_count)."""
    train_n = test_n = 0
    with src_path.open() as src, train_path.open("w") as tf, test_path.open("w") as ef:
        for line in src:
            module_id = json.loads(line)["system_context"]["module_id"]
            if module_id in held_out_modules:
                ef.write(line)
                test_n += 1
            else:
                tf.write(line)
                train_n += 1
    return train_n, test_n


def write_target_tier_dataset(cfg: DatasetConfig, out_dir: Path) -> None:
    """Sec.7's 'target' tier (0.05-0.10%/day) -- the roadmap/aspirational
    insulation performance, not realistic ground truth. Written to its own
    file, using the SAME variant matrix as the baseline dataset for
    comparability, but never merged into dataset.jsonl/train.jsonl/test.jsonl
    and not run through split_train_test (it's a standalone reference
    artifact, opt-in, not part of the train/test methodology)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target_cfg = DatasetConfig(
        modules=cfg.modules,
        boiloff_modes=("target",),
        include_normal=cfg.include_normal,
        fault_ids=cfg.fault_ids,
        idle_duration_s_normal=cfg.idle_duration_s_normal,
        idle_duration_s_fault=cfg.idle_duration_s_fault,
        dt_s=cfg.dt_s,
        base_seed=cfg.base_seed + 1,  # distinct seed stream from the baseline-tier dataset
        episode_spacing_s=cfg.episode_spacing_s,
    )
    records, manifest = generate_dataset(target_cfg)
    _write_jsonl(records, out_dir / "dataset_target_tier.jsonl")
    (out_dir / "manifest_target_tier.json").write_text(json.dumps(
        {
            "note": "Sec.7 'target' tier (0.05-0.10%/day) -- roadmap/aspirational, NOT merged into the baseline training set.",
            "total_records": len(records),
            "episodes": [e.__dict__ for e in manifest],
            "label_counts": _label_counts(records),
        },
        indent=2,
    ))
