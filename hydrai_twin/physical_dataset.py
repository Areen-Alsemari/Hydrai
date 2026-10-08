"""
Multi-episode driver for the physical model: modules x variants, leave-one-module-out
folds, fresh unseen units, commissioning runs, optional data-quality effects.

Roles
  dev            modules M01..M06: training/validation, scored by leave-one-module-out
  commissioning  one healthy run per unit (module-relative features, never train/test)
  unseen         fresh units U01..U03 with their OWN profile seed and episode seeds. ONE-SHOT:
                 score them once, after every choice is frozen (README, evaluation rules)

Everything in an episode comes from `PhysicalEpisodeGenerator`; the driver only enumerates
variants, runs them (in parallel), writes the two layers, and records a manifest that carries
BOTH reference times for each fault:
    onset_s                   true physical onset
    first_observable*_s       first ideal-observer deviation (k=3 sensitive, k=10 clear),
                              all channels and under the dashboard channel mask
and the static-alarm times on the dashboard's tags, so detection delay and lead time can
be scored against either.

Every unconfirmed value stays a flagged placeholder: the manifest embeds
`placeholders_used`, the dashboard config level, and the data-quality config.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrai_twin import constants as C
from hydrai_twin import placeholders as PH
from hydrai_twin.channels import PROVISIONAL_NOTE, REFERENCE_LABEL, DashboardConfig, first_static_alarm_s
from hydrai_twin.historian import HistorianConfig, TagInfo, apply_historian
from hydrai_twin.layers import write_fast_jsonl, write_slow_parquet
from hydrai_twin.sensor_view import SensorViewConfig
from hydrai_twin.module_profile import ModuleProfile, make_profile
from hydrai_twin.observability import observable_time
from hydrai_twin.physical_episode import (DAY, PHYSICAL_DEFAULT_BOILOFF_MODE, SPEC_MAX_FILL, SPEC_NOMINAL_FILL,
                                          PhysicalEpisodeConfig, PhysicalEpisodeGenerator)
from hydrai_twin.seeding import stable_seed

DEV_MODULES = tuple(C.MODULE_IDS)                 # M01..M06
UNSEEN_MODULES = ("U01", "U02", "U03")
DEV_BASE_SEED = 20260301
UNSEEN_BASE_SEED = 20270301                        # different episode seeds AND profile seed from the dev modules

_LEAK_LADDER = ("pinhole", "small", "small_medium", "medium_large", "full_bore")
_COMPOSITE_PAIRS = ((2, 5), (3, 6), (4, 5), (2, 4))
# Overfill = ABOVE the spec maximum fill (90 %, Sec. 2/8); the fraction is the registered placeholder overfill_fill_fraction.


@dataclass(frozen=True)
class Variant:
    key: str
    kwargs: dict[str, Any] = field(default_factory=dict)       # PhysicalEpisodeConfig overrides
    family: str = ""


def variant_matrix(fast: bool = False) -> list[Variant]:
    """Variants run on EVERY module. `fast` = one or two per family, 5-day episodes (smoke tests)."""
    v: list[Variant] = []

    def add(family: str, key: str, **kw: Any) -> None:
        v.append(Variant(f"{family}-{key}", kw, family))

    for i in range(1 if fast else 4):
        add("normal", f"fill{i}", fault_id=0)
    for i in range(1 if fast else 2):
        add("sensor", f"spike{i}", fault_id=1)
    for tgt in ((2.5,) if fast else (1.5, 2.5)):
        for ramp in ((2.0,) if fast else (1.0, 3.0)):
            add("insulation", f"x{tgt}-r{ramp:g}d", fault_id=2, insulation_mult_target=tgt, ramp_duration_s=ramp * DAY)
    for dp in ((13.33,) if fast else (2.0, 13.33)):
        for ramp in ((2.0,) if fast else (0.5, 2.0)):
            add("vacuum", f"dp{dp:g}-r{ramp:g}d", fault_id=3, vacuum_target_dp_pa=dp, ramp_duration_s=ramp * DAY)
    add("pcv", "stuck_closed0", fault_id=4, pcv_fault="stuck_closed")
    if not fast:
        add("pcv", "stuck_closed1", fault_id=4, pcv_fault="stuck_closed")
    add("pcv", "blocked", fault_id=4, pcv_fault="blocked")
    for rung in (("small_medium",) if fast else _LEAK_LADDER):
        add("leak", rung, fault_id=5, leak_severity=rung)
    for sev in ((1.0,) if fast else (0.5, 1.0)):
        add("structural", f"sev{sev:g}", fault_id=6, max_severity=sev)
    for pair in _COMPOSITE_PAIRS[: (1 if fast else 4)]:
        add("composite", "+".join(map(str, pair)), fault_id=-1, unknown_sub_fault_ids=pair)
    # explicit, labeled overfill scenarios (scenario_class = overfill_hydraulic_lock)
    over = PH.value("overfill_fill_fraction")
    add("overfill", "normal", fault_id=0, fill_target_frac=over, allow_overfill=True)
    add("overfill", "hydraulic_lock", fault_id=-1, unknown_sub_fault_ids=(3, 4), fill_target_frac=over, allow_overfill=True)
    return v


@dataclass
class PhysicalDatasetConfig:
    dev_modules: tuple[str, ...] = DEV_MODULES
    unseen_modules: tuple[str, ...] = UNSEEN_MODULES
    include_unseen: bool = True
    include_commissioning: bool = True
    dev_base_seed: int = DEV_BASE_SEED
    unseen_base_seed: int = UNSEEN_BASE_SEED
    variation_scale: float = 1.0
    fast: bool = False
    stratification: str = "off"                       # "empirical" only for the separate robustness variant
    boiloff_mode: str = PHYSICAL_DEFAULT_BOILOFF_MODE  # "baseline" 0.30 %/day (default) | "target" 0.10 %/day (spec)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig.reference)
    h2_mode: str = "lfl"                              # "lfl" realistic detector | "spec" workbook Sec. 9
    vacuum_mode: str = "log_gauge"                    # "log_gauge" | "spec"
    level_mode: str = "dp"                            # "dp" | "ideal"
    valve_states: bool = False                        # optional discrete inputs; default OFF in the model-visible set
    channel_sampling: bool = True                     # per-channel periods + aggregation; False = previous per-record view
    historian: HistorianConfig = field(default_factory=HistorianConfig.from_registry)   # default ON; enabled=False = ideal data
    gzip_fast: bool = True
    start_time: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def sensor_view(self) -> SensorViewConfig:
        from hydrai_twin.sensor_view import DEFAULT_PERIODS_S
        periods = {**DEFAULT_PERIODS_S, **self.dashboard.periods_s()}
        return SensorViewConfig(enabled=self.channel_sampling, periods_s=periods, h2_mode=self.h2_mode,
                                vacuum_mode=self.vacuum_mode, level_mode=self.level_mode, valve_states=self.valve_states)

    def dashboard_for_view(self) -> DashboardConfig:
        d = self.dashboard.with_h2_mode(self.h2_mode if self.channel_sampling else "spec")
        d.valve_states_available = self.valve_states
        return d

    def episode_overrides(self) -> dict[str, Any]:
        ov: dict[str, Any] = {"stratification": self.stratification, "boiloff_mode": self.boiloff_mode}
        if self.fast:
            ov.update(storage_days=5.0, onset_day_range=(1.5, 2.5))
        return ov


@dataclass
class Job:
    name: str
    role: str
    module_id: str
    variant: Variant
    seed: int
    profile: ModuleProfile
    overrides: dict[str, Any]
    dashboard: dict[str, Any]
    view: SensorViewConfig
    historian: HistorianConfig
    out_dir: str
    gzip_fast: bool
    start_time: datetime


def build_jobs(cfg: PhysicalDatasetConfig, out_dir: Path) -> list[Job]:
    jobs: list[Job] = []
    groups = [("dev", cfg.dev_modules, cfg.dev_base_seed)]
    if cfg.include_unseen:
        groups.append(("unseen", cfg.unseen_modules, cfg.unseen_base_seed))
    ov = cfg.episode_overrides()
    for role, modules, base_seed in groups:
        for m in modules:
            profile = make_profile(m, base_seed, cfg.variation_scale)
            variants = list(variant_matrix(cfg.fast))
            if cfg.include_commissioning:
                variants.append(Variant("commissioning", dict(fault_id=0), "commissioning"))
            for var in variants:
                r = "commissioning" if var.family == "commissioning" else role
                seed = stable_seed(base_seed, m, var.key)
                jobs.append(Job(f"{m}__{var.key}", r, m, var, seed, profile, ov, cfg.dashboard_for_view().to_dict(),
                                cfg.sensor_view(), cfg.historian, str(out_dir / r / m), cfg.gzip_fast, cfg.start_time))
    return jobs


def _tag_infos(dash: DashboardConfig, view: SensorViewConfig) -> dict[str, TagInfo]:
    ranges = view.measurement_ranges()
    logs = view.log_scale_channels()
    return {t.channel: TagInfo(t.channel, ranges[t.channel][0], ranges[t.channel][1], t.channel in logs)
            for t in dash.tags if t.channel in ranges}


def _merge_stats(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = {k: dict(v) for k, v in a.items()}
    for tag, v in b.items():
        if tag not in out:
            out[tag] = dict(v)
            continue
        o = out[tag]
        for k in ("n_samples", "n_valid", "n_exception_passed", "n_archived"):
            o[k] += v[k]
        o["fault_samples"] = {ft: o["fault_samples"][ft] + v["fault_samples"][ft] for ft in o["fault_samples"]}
        o.pop("fault_run_starts", None)          # per-layer only (the layers have different exposure)
        o.pop("exposure_channel_days", None)
        o["compression_ratio"] = (o["n_valid"] / o["n_archived"]) if o["n_archived"] else None
    return out


def run_job(job: Job) -> dict[str, Any]:
    """Generate and write one episode; returns its manifest entry. Top-level so it can run in a worker process."""
    dash = DashboardConfig.from_dict(job.dashboard)
    ecfg = PhysicalEpisodeConfig(module_id=job.module_id, seed=job.seed, start_time=job.start_time, profile=job.profile,
                                 variant_tag=job.variant.key, sensor_view=job.view, **{**job.variant.kwargs, **job.overrides})
    res = PhysicalEpisodeGenerator(ecfg).generate()
    meta = res.meta

    # static alarms act on the LIVE DCS value (before the historian side channel), on the dashboard's tags only
    static = {lvl: first_static_alarm_s(res.slow, dash, lvl) for lvl in (None, "warning", "critical")}
    mask = dash.mask()
    per_ch = meta["per_channel_deviation_s"]
    obs_masked = {k: (observable_time(per_ch, mask.enabled, k) if per_ch else None) for k in ("k3", "k10")}

    infos = _tag_infos(dash, job.view)
    slow, st_slow = apply_historian(res.slow, job.historian, stable_seed(job.seed, "hist-slow"), infos, meta["duration_s"], 60.0)
    fast, st_fast = apply_historian(res.fast, job.historian, stable_seed(job.seed, "hist-slow"), infos, meta["duration_s"], 1.0)
    hist_stats = _merge_stats(st_slow, st_fast)
    out = Path(job.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slow_p = out / f"{job.name}.slow.parquet"
    fast_p = out / (f"{job.name}.fast.jsonl.gz" if job.gzip_fast else f"{job.name}.fast.jsonl")
    write_slow_parquet(slow, slow_p)
    write_fast_jsonl(fast, fast_p)
    fault_counts = {ft: sum(v["fault_samples"][ft] for v in hist_stats.values()) for ft in ("dropout", "stale_value", "flat_line", "out_of_range")} if hist_stats else {}

    entry = {
        "name": job.name, "role": job.role, "module_id": job.module_id, "family": job.variant.family,
        "variant_tag": job.variant.key, "episode_id": meta["episode_id"], "seed": job.seed,
        "fault_id": meta["fault_id"], "scenario": meta["scenario"], "scenario_class": meta["scenario_class"],
        "fill_target_pct": meta["fill_target_pct"], "stratification": meta["stratification"],
        "boiloff_mode": meta["boiloff_mode"], "boiloff_normal_pct_per_day": meta["boiloff_normal_pct_per_day"],
        "onset_s": meta["onset_s"],
        "first_observable_s": meta["first_observable_s"], "first_observable_clear_s": meta["first_observable_clear_s"],
        "first_observable_dashboard_s": obs_masked["k3"], "first_observable_clear_dashboard_s": obs_masked["k10"],
        "onset_to_first_observable_s": meta["onset_to_first_observable_s"],
        "per_channel_deviation_s": per_ch,
        "static_alarm_first_s": {k or "any": v["any"] for k, v in static.items()},
        "static_alarm_first_by_channel_s": static[None]["by_channel"],
        "static_alarm_status": "PROVISIONAL (simulation-threshold limits)",
        "healthy_exposure_s": meta["healthy_exposure_s"], "time_onset_to_end_s": meta["time_onset_to_end_s"],
        "duration_s": meta["duration_s"], "ended_reason": meta["ended_reason"],
        "n_slow": meta["n_slow"], "n_fast": meta["n_fast"],
        "pcv_open_events": meta["pcv_open_events"], "prv_lift_events": meta["prv_lift_events"],
        "liquid_full_events": meta["liquid_full_events"], "liquid_vented_kg": meta["liquid_vented_kg"],
        "mass_residual_kg": meta["mass_residual_kg"],
        "unknown_sub_faults": meta["unknown_sub_faults"],
        "historian": {"tags": hist_stats, "injected_fault_samples": fault_counts,
                      "layers": {"slow": {t: {"fault_run_starts": v["fault_run_starts"], "exposure_channel_days": v["exposure_channel_days"],
                                              "fault_samples": v["fault_samples"], "n_samples": v["n_samples"]} for t, v in st_slow.items()},
                                 "fast": {t: {"fault_run_starts": v["fault_run_starts"], "exposure_channel_days": v["exposure_channel_days"],
                                              "fault_samples": v["fault_samples"], "n_samples": v["n_samples"]} for t, v in st_fast.items()}}},
        "slow_file": str(slow_p.relative_to(out.parent.parent)), "fast_file": str(fast_p.relative_to(out.parent.parent)),
        "_placeholders_full": meta["placeholders_used"],
    }
    return entry


def lomo_folds(dev_modules: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{"test_module": m, "train_modules": [x for x in dev_modules if x != m]} for m in dev_modules]


def generate_physical_dataset(cfg: PhysicalDatasetConfig, out_dir: Path, workers: int = 1, progress: bool = True) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = build_jobs(cfg, out_dir)
    t0 = time.time()
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            entries = []
            for i, e in enumerate(ex.map(run_job, jobs, chunksize=2), 1):
                entries.append(e)
                if progress and i % 20 == 0:
                    print(f"  {i}/{len(jobs)} episodes ({time.time() - t0:.0f}s)", flush=True)
    else:
        entries = [run_job(j) for j in jobs]

    placeholders: dict[str, dict[str, Any]] = {}
    for name in ("h2_alarm_h_lfl", "h2_alarm_hh_lfl", "h2_lfl_vol_pct"):      # the dashboard file carries these; keep the registry in step
        PH.value(name)
    for p in PH.used_placeholders():                                         # values read in this process (historian config, alarms)
        placeholders[p["name"]] = p
    for e in entries:
        for p in e.pop("_placeholders_full"):
            placeholders[p["name"]] = p
    view = cfg.sensor_view()
    dash = cfg.dashboard_for_view()
    comp = {}
    for e in entries:
        for tag, v in e["historian"]["tags"].items():
            c = comp.setdefault(tag, [0, 0])
            c[0] += v["n_valid"]
            c[1] += v["n_archived"]
    manifest = {
        "schema": "hydrai-physical-dataset/2",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "episodes": sorted(entries, key=lambda e: (e["role"], e["module_id"], e["name"])),
        "n_episodes": len(entries),
        "dashboard_label": REFERENCE_LABEL,
        "config": {
            "dev_modules": list(cfg.dev_modules),
            "unseen_modules": list(cfg.unseen_modules) if cfg.include_unseen else [],
            "dev_base_seed": cfg.dev_base_seed, "unseen_base_seed": cfg.unseen_base_seed,
            "variation_scale": cfg.variation_scale, "fast": cfg.fast, "stratification": cfg.stratification,
            "episode_overrides": cfg.episode_overrides(),
            "boiloff_mode": cfg.boiloff_mode,
            "boiloff_normal_pct_per_day": C.BOILOFF_LADDER_PCT_PER_DAY[cfg.boiloff_mode]["normal"],
            "boiloff_switch": "hydrai_twin/physical_episode.py: PHYSICAL_DEFAULT_BOILOFF_MODE ('baseline' 0.30 %/day default, workbook Sec. 7 | 'target' 0.10 %/day, the handoff / Sec. 10 spec value)",
            "fill_rule": {"nominal_pct": 100 * SPEC_NOMINAL_FILL, "max_pct": 100 * SPEC_MAX_FILL,
                          "healthy_fill": "85 % + 5 % x Beta(1, 2.5): mostly nominal, never above 90 %",
                          "overfill": f"fill above {100 * SPEC_MAX_FILL:.0f} % (placeholder overfill_fill_fraction = {PH.value('overfill_fill_fraction')}); scenario_class overfill_hydraulic_lock"},
            "variants": [{"key": v.key, "family": v.family} for v in variant_matrix(cfg.fast)],
            "storage_snapshot_s": 60.0,
            "grid_note": "generator grid is 1 s for operations and event bursts; storage is recorded as 60 s snapshots of the same 1 s-grid instrument view (14 d at 1 s would be ~340 M rows)",
        },
        "module_profiles": {
            m: make_profile(m, cfg.dev_base_seed if m in cfg.dev_modules else cfg.unseen_base_seed, cfg.variation_scale).as_dict()
            for m in (*cfg.dev_modules, *(cfg.unseen_modules if cfg.include_unseen else ()))
        },
        "lomo_folds": lomo_folds(cfg.dev_modules),
        "unseen_policy": ("ONE-SHOT: score the unseen units once, after every model choice and threshold is frozen on dev/LOMO data. "
                          "They use a different profile seed and different episode seeds from the dev modules."),
        "dashboard": dash.to_dict(),
        "dashboard_tag_names": dash.tag_names(),
        "sample_periods_s": view.periods_s,
        "measurement_units": view.measurement_units(),
        "sensor_view": view.to_dict(),
        "model_visible_channels": sorted(dash.mask().enabled),
        "valve_states": {"available_to_detector": cfg.valve_states, "default": False,
                         "note": "a real historian side channel often does not expose valve states; recorded only when the switch is on"},
        "historian": {**cfg.historian.to_dict(), "compression_ratio_by_tag": {t: (v[0] / v[1] if v[1] else None) for t, v in comp.items()},
                      "layer_note": "applied separately to the 60 s slow layer and the 1 s fast layer"},
        "static_alarm_basis": "live DCS value (before the historian side channel), dashboard tags only",
        "static_alarm_status": PROVISIONAL_NOTE,
        "observability_definition": "see hydrai_twin/observability.py; ideal-observer bound, per-channel times recorded so any mask can be applied",
        "placeholders_used": sorted(placeholders.values(), key=lambda p: p["name"]),
        "unconfirmed_notice": ("Valve, vent, vacuum, pressure-builder, instrument-mode (H2 %LFL detector, log vacuum gauge, DP level), historian "
                               "and dashboard alarm values are PLACEHOLDERS / UNVERIFIED pending ENGINEER_QUESTIONS_VALVE_VENT.md; see placeholders_used."),
        "regen_command": "python scripts/generate_physical_dataset.py",
        "wall_seconds": round(time.time() - t0, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    return manifest


def load_slow_for_model(path: Path | str, dashboard: DashboardConfig, tag_names: bool = True):
    """Slow-layer table restricted to the columns a model on this dashboard may see: identifiers, enabled measurement tags
    and their OPC quality codes. Never ground truth, labels, live values or injected-fault labels. With `tag_names` the
    measurement columns are renamed to the dashboard's tag names (LH2-PT-101, ...)."""
    import pyarrow.parquet as pq
    cols = dashboard.mask().parquet_columns(pq.ParquetFile(path).schema.names)
    table = pq.read_table(path, columns=cols)
    if tag_names:
        names = dashboard.tag_names()
        table = table.rename_columns([(f"{c.split('__')[0]}__{names[c.split('__', 1)[1]]}" if c.startswith(("meas__", "q__")) and c.split("__", 1)[1] in names else c)
                                      for c in table.column_names])
    return table


def static_flags_from_parquet(path: Path | str, dash: DashboardConfig, level: str | None = None):
    """(t_s list, per-sample static-alarm flags) from a slow-layer Parquet file. Static alarms act on the LIVE DCS value
    (`live__` columns, present when the historian layer is on); without them the measurement columns are used."""
    import pyarrow.parquet as pq
    from hydrai_twin.channels import static_alarm_flags
    tags = sorted({a.channel for a in dash.alarms})
    names = set(pq.ParquetFile(path).schema.names)
    pref = "live__" if all(f"live__{c}" in names for c in tags) else "meas__"
    t = pq.read_table(path, columns=["ctx__t_s"] + [f"{pref}{c}" for c in tags])
    ts = t.column("ctx__t_s").to_pylist()
    cols = {c: t.column(f"{pref}{c}").to_pylist() for c in tags}
    rows = [{"system_context": {"t_s": ts[i]}, "measurements": {c: cols[c][i] for c in tags}} for i in range(len(ts))]
    return ts, static_alarm_flags(rows, dash, level, source="measurements")
