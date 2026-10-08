"""
Multi-episode CGH2 dataset driver: same split structure as the LH2 driver.

  medium class (PRIMARY, MOP 300 bar): dev modules M01-M06 (leave-one-module-out folds), commissioning run per unit, unseen units
  U01-U03 (own profile and episode seeds; ONE-SHOT).
  low (MOP 50) and high (MOP 350) classes: smaller OUT-OF-DISTRIBUTION sets (modules M01-M03, reduced variant matrix, role "ood").

Everything an episode contains is written to a slow Parquet file (60 s snapshots of the whole timeline) and a fast JSONL.gz file (1 s rows
during dispenser fills, compressor transitions and events such as PRV lifts, pressure above PAH and leak/rupture onsets). The manifest
carries, per episode, BOTH reference times (true onset and first observable deviation, per channel, with and without the dashboard mask),
the first PROVISIONAL static-alarm times and the historian statistics, and at dataset level the class parameters, detector mode, valve-state
switch, sensor split, historian settings and the registry entries used (with source tags).

Reference configuration, not a verified Saudi system.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrai_twin.channels import first_static_alarm_s
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import CLASS_NAMES, PRIMARY, make_class
from hydrai_twin.cgh2.dashboard import PROVISIONAL_NOTE, REFERENCE_LABEL, CGH2Dashboard
from hydrai_twin.cgh2.episode import CGH2EpisodeConfig, CGH2EpisodeGenerator, FAULT_LABELS
from hydrai_twin.cgh2.profile import CGH2Profile, make_profile
from hydrai_twin.cgh2.sensor_view import CONT, DISCRETE, CGH2ViewConfig, ranges
from hydrai_twin.historian import HistorianConfig, TagInfo, apply_historian
from hydrai_twin.layers import write_fast_jsonl, write_slow_parquet
from hydrai_twin.observability import observable_time
from hydrai_twin.seeding import stable_seed

DAY = 86400.0
DEV_MODULES = ("M01", "M02", "M03", "M04", "M05", "M06")
UNSEEN_MODULES = ("U01", "U02", "U03")
OOD_MODULES = ("M01", "M02", "M03")
DEV_BASE_SEED = 20260401
UNSEEN_BASE_SEED = 20270401
RUPTURE_MODULES = ("M01", "M04", "U01")          # 3 ruptures in ~225 fault episodes = 1.3 % (< 2 %)

CGH2_DEADBAND_PCT = {"pressure_bar_a": 0.1, "gas_temp_c": 0.1, "outer_wall_temp_c": 0.2, "h2_concentration_pct": 0.5,
                     "mass_flow_fill_kg_s": 0.2, "mass_flow_discharge_kg_s": 0.2, "strain_ue": 0.2, "ambient_temp_c": 0.2}


@dataclass(frozen=True)
class Variant:
    key: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    family: str = ""


def variant_matrix(fast: bool = False) -> list[Variant]:
    v: list[Variant] = []

    def add(family: str, key: str, **kw: Any) -> None:
        v.append(Variant(f"{family}-{key}", kw, family))

    for i in range(1 if fast else 4):
        add("normal", f"refuelling{i}", fault_id=0)
    add("normal", "industrial", fault_id=0, demand_pattern="industrial")
    add("normal", "dark-vessel", fault_id=0, solar="dark")
    for i in range(1 if fast else 2):
        add("sensor", f"spike{i}", fault_id=1)
    for ramp_h in ((6.0,) if fast else (1.0, 6.0)):
        add("thermal", f"intercooler-r{ramp_h:g}h", fault_id=2, thermal_variant="intercooler", ramp_duration_s=ramp_h * 3600.0)
        add("thermal", f"external-heat-r{ramp_h:g}h", fault_id=2, thermal_variant="external_heat", ramp_duration_s=ramp_h * 3600.0)
    for d in ((0.25, 1.0) if fast else (0.1, 0.25, 0.5, 1.0)):
        add("leak", f"{d:g}mm", fault_id=3, leak_diameter_mm=d)
    for d in ((0.05,) if fast else (0.03, 0.05)):
        add("leak-stress", f"{d:g}mm", fault_id=3, leak_diameter_mm=d, expected_miss=True)
    for pv in ("compressor_overrun", "blocked_relief", "fire", "stuck_open"):
        add("pressure", pv, fault_id=4, pressure_variant=pv)
    for d in ((3.5,) if fast else (2.0, 3.5, 5.0)):
        add("containment", f"leak-{d:g}mm", fault_id=5, containment_variant="leak", leak_diameter_mm=d)
    for sev in ((1.0,) if fast else (0.5, 1.0)):
        add("structural", f"sev{sev:g}", fault_id=6, max_severity=sev)
    for pair in (((2, 3),) if fast else ((2, 3), (3, 6), (4, 5), (2, 6))):
        add("composite", "+".join(map(str, pair)), fault_id=-1, unknown_sub_fault_ids=pair)
    return v


RUPTURE_VARIANT = Variant("rupture-50mm", dict(fault_id=5, containment_variant="rupture", rupture_diameter_mm=50.0), "rupture")


@dataclass
class CGH2DatasetConfig:
    pressure_class: str = PRIMARY
    roles: str = "main"                                # "main" (dev + unseen + commissioning) | "ood" (smaller set, role ood)
    dev_modules: tuple[str, ...] = DEV_MODULES
    unseen_modules: tuple[str, ...] = UNSEEN_MODULES
    include_unseen: bool = True
    include_commissioning: bool = True
    include_rupture: bool = True
    dev_base_seed: int = DEV_BASE_SEED
    unseen_base_seed: int = UNSEEN_BASE_SEED
    variation_scale: float = 1.0
    fast: bool = False                                 # smoke test: 5-day episodes AND the reduced matrix
    reduced: bool = False                              # reduced variant matrix, full-length episodes (the out-of-distribution sets)
    h2_mode: str = "lfl"                               # "lfl" realistic detector | "spec" workbook Sec. 9 model
    flow_mode: str = "datasheet"                       # "datasheet" | "spec" (1 % FS)
    valve_states: bool = True                          # compressor status + valve states on the dashboard (default ON for CGH2)
    prv_blowdown: str = "nominal"
    historian: HistorianConfig = field(default_factory=lambda: cgh2_historian())
    gzip_fast: bool = True
    start_time: datetime = datetime(2026, 7, 1, tzinfo=timezone.utc)

    def view(self) -> CGH2ViewConfig:
        return CGH2ViewConfig(h2_mode=self.h2_mode, flow_mode=self.flow_mode, valve_states=self.valve_states)

    def dashboard(self) -> CGH2Dashboard:
        return CGH2Dashboard.reference(self.pressure_class, self.valve_states, self.h2_mode)

    def overrides(self) -> dict[str, Any]:
        ov: dict[str, Any] = {"pressure_class": self.pressure_class, "prv_blowdown": self.prv_blowdown}
        if self.fast:
            ov.update(days=5.0, onset_day_range=(1.5, 2.5))
        return ov


def cgh2_historian(enabled: bool = True) -> HistorianConfig:
    return HistorianConfig(
        enabled=enabled, deadband_pct_span=dict(CGH2_DEADBAND_PCT), exception_forced_s=R.value("historian_exception_forced_s"),
        compression=True, compdev_mult=R.value("historian_compdev_mult"), compression_forced_s=R.value("historian_compression_forced_s"),
        fault_rates={"dropout": (R.value("historian_fault_dropout_per_day"), 300.0), "stale_value": (R.value("historian_fault_stale_per_day"), 900.0),
                     "flat_line": (R.value("historian_fault_flatline_per_day"), 7200.0), "out_of_range": (R.value("historian_fault_outofrange_per_day"), 120.0)})


@dataclass
class Job:
    name: str
    role: str
    module_id: str
    variant: Variant
    seed: int
    profile: CGH2Profile
    overrides: dict[str, Any]
    dashboard: dict[str, Any]
    view: CGH2ViewConfig
    historian: HistorianConfig
    out_dir: str
    gzip_fast: bool
    start_time: datetime


def build_jobs(cfg: CGH2DatasetConfig, out_dir: Path) -> list[Job]:
    jobs: list[Job] = []
    ov = cfg.overrides()
    dash = cfg.dashboard().to_dict()
    if cfg.roles == "ood":
        groups = [("ood", cfg.dev_modules, cfg.dev_base_seed)]
    else:
        groups = [("dev", cfg.dev_modules, cfg.dev_base_seed)]
        if cfg.include_unseen:
            groups.append(("unseen", cfg.unseen_modules, cfg.unseen_base_seed))
    for role, modules, base_seed in groups:
        for m in modules:
            profile = make_profile(m, base_seed, cfg.variation_scale)
            variants = list(variant_matrix(cfg.fast or cfg.reduced))
            if cfg.pressure_class == "low":                       # healthy dark-vessel runs cannot be held below PAH in the low class (see registry)
                variants = [x for x in variants if "dark" not in x.key]
            if cfg.include_rupture and cfg.roles != "ood" and m in RUPTURE_MODULES:
                variants.append(RUPTURE_VARIANT)
            if cfg.include_commissioning:
                variants.append(Variant("commissioning", dict(fault_id=0), "commissioning"))
            for var in variants:
                r = "commissioning" if var.family == "commissioning" else role
                seed = stable_seed(base_seed, m, var.key, cfg.pressure_class)
                jobs.append(Job(f"{m}__{var.key}", r, m, var, seed, profile, ov, dash, cfg.view(), cfg.historian, str(out_dir / r / m), cfg.gzip_fast, cfg.start_time))
    return jobs


def _tag_infos(view: CGH2ViewConfig, p_range_bar: float) -> dict[str, TagInfo]:
    rg = ranges(view, p_range_bar)
    return {c: TagInfo(c, rg[c][0], rg[c][1], False) for c in CONT}


def _layer_stats(st: dict[str, Any]) -> dict[str, Any]:
    return {t: {"fault_run_starts": v["fault_run_starts"], "exposure_channel_days": v["exposure_channel_days"], "fault_samples": v["fault_samples"],
                "n_samples": v["n_samples"]} for t, v in st.items()}


def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = {k: dict(v) for k, v in a.items()}
    for tag, v in b.items():
        if tag not in out:
            out[tag] = dict(v)
            continue
        o = out[tag]
        for k in ("n_samples", "n_valid", "n_exception_passed", "n_archived"):
            o[k] += v[k]
        o["fault_samples"] = {ft: o["fault_samples"][ft] + v["fault_samples"][ft] for ft in o["fault_samples"]}
        o.pop("fault_run_starts", None)
        o.pop("exposure_channel_days", None)
        o["compression_ratio"] = (o["n_valid"] / o["n_archived"]) if o["n_archived"] else None
    return out


def run_job(job: Job) -> dict[str, Any]:
    dash = CGH2Dashboard.from_dict(job.dashboard)
    ecfg = CGH2EpisodeConfig(module_id=job.module_id, seed=job.seed, start_time=job.start_time, profile=job.profile, variant_tag=job.variant.key,
                             sensor_view=job.view, **{**job.variant.kwargs, **job.overrides})
    res = CGH2EpisodeGenerator(ecfg).generate()
    meta = res.meta
    static = {lvl: first_static_alarm_s(res.slow, dash, lvl) for lvl in (None, "warning", "critical")}
    mask = dash.mask()
    per_ch = meta["per_channel_deviation_s"]
    obs_masked = {k: (observable_time(per_ch, mask, k) if per_ch else None) for k in ("k3", "k10")}
    infos = _tag_infos(job.view, meta["class"]["transmitter_range_bar"])
    seed_h = stable_seed(job.seed, "hist")
    slow, st_slow = apply_historian(res.slow, job.historian, seed_h, infos, meta["duration_s"], 60.0, DISCRETE)
    fast, st_fast = apply_historian(res.fast, job.historian, seed_h, infos, meta["duration_s"], 1.0, DISCRETE)
    out = Path(job.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slow_p = out / f"{job.name}.slow.parquet"
    fast_p = out / (f"{job.name}.fast.jsonl.gz" if job.gzip_fast else f"{job.name}.fast.jsonl")
    write_slow_parquet(slow, slow_p)
    write_fast_jsonl(fast, fast_p)
    hist_stats = _merge(st_slow, st_fast)
    fault_counts = ({ft: sum(v["fault_samples"][ft] for v in hist_stats.values()) for ft in ("dropout", "stale_value", "flat_line", "out_of_range")}
                    if hist_stats else {})
    return {
        "name": job.name, "role": job.role, "module_id": job.module_id, "family": job.variant.family, "variant_tag": job.variant.key,
        "episode_id": meta["episode_id"], "seed": job.seed, "fault_id": meta["fault_id"], "scenario": meta["scenario"],
        "scenario_class": meta["scenario_class"], "pressure_class": meta["pressure_class"], "expected_miss": meta["expected_miss"],
        "demand_pattern": meta["demand_pattern"], "demand_kg_per_day": meta["demand_kg_per_day"], "stop_mode": meta["stop_mode"],
        "compensation_ref_temp_c": meta["compensation_ref_temp_c"], "solar": meta["solar"],
        "onset_s": meta["onset_s"], "first_observable_s": meta["first_observable_s"], "first_observable_clear_s": meta["first_observable_clear_s"],
        "first_observable_dashboard_s": obs_masked["k3"], "first_observable_clear_dashboard_s": obs_masked["k10"],
        "onset_to_first_observable_s": meta["onset_to_first_observable_s"], "per_channel_deviation_s": per_ch,
        "static_alarm_first_s": {k or "any": v["any"] for k, v in static.items()}, "static_alarm_first_by_channel_s": static[None]["by_channel"],
        "static_alarm_status": "PROVISIONAL", "healthy_exposure_s": meta["healthy_exposure_s"], "time_onset_to_end_s": meta["time_onset_to_end_s"],
        "duration_s": meta["duration_s"], "ended_reason": meta["ended_reason"], "n_slow": meta["n_slow"], "n_fast": meta["n_fast"],
        "compressor_stop_events": meta["compressor_stop_events"], "prv_lift_events": meta["prv_lift_events"], "prv_set_bar_actual": meta["prv_set_bar_actual"],
        "vented_prv_kg": meta["vented_prv_kg"], "leaked_kg": meta["leaked_kg"], "dispensed_kg": meta["dispensed_kg"], "charged_kg": meta["charged_kg"],
        "mass_residual_kg": meta["mass_residual_kg"], "unknown_sub_faults": meta["unknown_sub_faults"], "meter_delay_s": meta["meter_delay_s"],
        "historian": {"tags": hist_stats, "injected_fault_samples": fault_counts,
                      "layers": {"slow": _layer_stats(st_slow), "fast": _layer_stats(st_fast)}},
        "slow_file": str(slow_p.relative_to(out.parent.parent)), "fast_file": str(fast_p.relative_to(out.parent.parent)),
        "_registry": meta["registry_used"], "_class": meta["class"], "_split": meta["sensor_split"],
    }


def lomo_folds(modules: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{"test_module": m, "train_modules": [x for x in modules if x != m]} for m in modules]


def generate_cgh2_dataset(cfg: CGH2DatasetConfig, out_dir: Path, workers: int = 1, progress: bool = True) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = build_jobs(cfg, out_dir)
    t0 = time.time()
    if workers > 1:
        entries = []
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for i, e in enumerate(ex.map(run_job, jobs, chunksize=2), 1):
                entries.append(e)
                if progress and i % 20 == 0:
                    print(f"  {i}/{len(jobs)} episodes ({time.time() - t0:.0f}s)", flush=True)
    else:
        entries = [run_job(j) for j in jobs]

    registry: dict[str, dict] = {}
    cls_dict = entries[0]["_class"] if entries else make_class(cfg.pressure_class).to_dict()
    split = entries[0]["_split"] if entries else {}
    for name in ("h2_alarm_lfl", "h2_trip_lfl", "gas_temp_alarm_c", "pah_over_mop", "pahh_over_mop", "historian_exception_forced_s", "historian_compression_forced_s",
                 "historian_compdev_mult", "historian_fault_dropout_per_day", "historian_fault_stale_per_day", "historian_fault_flatline_per_day",
                 "historian_fault_outofrange_per_day", "demand_scaling_by_class", "compensated_ref_temp_c_low", "compensated_ref_temp_c_dark",
                 "compensated_ref_temp_c_dark_low", "fire_duration_s", "wall_failure_temp_k"):
        R.value(name)
    for u in R.used():
        registry[u["name"]] = u
    for e in entries:
        for u in e.pop("_registry"):
            registry[u["name"]] = u
        e.pop("_class")
        e.pop("_split")
    comp: dict[str, list] = {}
    for e in entries:
        for tag, v in e["historian"]["tags"].items():
            c = comp.setdefault(tag, [0, 0])
            c[0] += v["n_valid"]
            c[1] += v["n_archived"]
    view, dash = cfg.view(), cfg.dashboard()
    faults = [e for e in entries if e["fault_id"] != 0]
    manifest = {
        "schema": "hydrai-cgh2-dataset/1", "system": "cgh2", "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dashboard_label": REFERENCE_LABEL,
        "episodes": sorted(entries, key=lambda e: (e["role"], e["module_id"], e["name"])), "n_episodes": len(entries),
        "config": {
            "pressure_class": cfg.pressure_class, "roles": cfg.roles, "dev_modules": list(cfg.dev_modules),
            "unseen_modules": list(cfg.unseen_modules) if (cfg.include_unseen and cfg.roles == "main") else [],
            "dev_base_seed": cfg.dev_base_seed, "unseen_base_seed": cfg.unseen_base_seed, "variation_scale": cfg.variation_scale, "fast": cfg.fast,
            "episode_overrides": cfg.overrides(), "boiloff": "n/a (compressed gas)", "compressor_stop": "stop pressure compensated to a design gas temperature (60 C reference; 70 C dark-vessel stress case; 65 C low class); MOP is the rating at that temperature; stop_mode='fixed' stops at the raw MOP", "h2_detector_mode": cfg.h2_mode, "flow_mode": cfg.flow_mode,
            "valve_states_and_compressor_status": cfg.valve_states, "prv_blowdown": cfg.prv_blowdown,
            "reduced_matrix": cfg.reduced or cfg.fast, "variants": [{"key": v.key, "family": v.family} for v in variant_matrix(cfg.fast or cfg.reduced)],
            "rupture_episodes": sum(1 for e in entries if e["family"] == "rupture"), "fault_episodes": len(faults),
            "rupture_fraction_of_fault_episodes": (sum(1 for e in entries if e["family"] == "rupture") / len(faults)) if faults else 0.0,
            "expected_miss_episodes": sum(1 for e in entries if e["expected_miss"]),
            "storage_snapshot_s": 60.0, "fast_layer": "1 s rows during dispenser fills, compressor transitions (+/-120 s) and events (PRV lift, P > PAH, leak/rupture onset)",
        },
        "class_parameters": cls_dict, "module_profiles": {m: make_profile(m, cfg.dev_base_seed if m in cfg.dev_modules else cfg.unseen_base_seed, cfg.variation_scale).as_dict()
                                                          for m in (*cfg.dev_modules, *(cfg.unseen_modules if (cfg.include_unseen and cfg.roles == 'main') else ()))},
        "lomo_folds": lomo_folds(cfg.dev_modules),
        "unseen_policy": "ONE-SHOT: score the unseen units once, after every model choice and threshold is frozen on dev/LOMO data (own profile seed and episode seeds).",
        "dashboard": dash.to_dict(), "dashboard_tag_names": dash.tag_names(), "sample_periods_s": view.periods_s, "measurement_units": view.units(),
        "sensor_view": view.to_dict(), "sensor_split": split, "model_visible_channels": sorted(dash.mask()),
        "valve_states": {"available_to_detector": cfg.valve_states, "default": True, "note": "default ON for CGH2; run the ablation with valve_states=False"},
        "channels_without_static_alarm": dash.channels_without_alarm(),
        "historian": {**cfg.historian.to_dict(), "compression_ratio_by_tag": {t: (v[0] / v[1] if v[1] else None) for t, v in comp.items()}, "layer_note": "applied separately to the 60 s and the 1 s layer"},
        "static_alarm_basis": "live DCS value (before the historian side channel), dashboard tags only", "static_alarm_status": PROVISIONAL_NOTE,
        "registry_used": sorted(registry.values(), key=lambda u: u["name"]),
        "placeholders_used": sorted([u for u in registry.values() if u["placeholder"]], key=lambda u: u["name"]),
        "register_conflicts_resolved": R.conflicts(),
        "unconfirmed_notice": ("The decision register file was NOT available when this was built; values it would define that the instruction and Addendum 1 do not (tag table, "
                               "per-class thermal constants, section-2 conflicts) are defaults tagged JUDGE/REG-UNREAD. Everything tagged U, JUDGE or REG-UNREAD is a placeholder."),
        "regen_command": f"python scripts/cgh2_generate.py --class {cfg.pressure_class}", "wall_seconds": round(time.time() - t0, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    return manifest


def load_slow_for_model(path: Path | str, dashboard: CGH2Dashboard, tag_names: bool = True):
    """Slow-layer table restricted to what a model on this dashboard may see: identifiers, the dashboard's tags and their OPC quality codes. Never
    ground truth, labels, live values or injected-fault labels."""
    import pyarrow.parquet as pq
    keep = {"episode_id", "timestamp", "ctx__phase", "ctx__layer", "ctx__t_s"}
    mask = dashboard.mask()
    names = pq.ParquetFile(path).schema.names
    cols = [c for c in names if c in keep or (c.startswith(("meas__", "q__")) and c.split("__", 1)[1] in mask)]
    table = pq.read_table(path, columns=cols)
    if tag_names:
        tn = dashboard.tag_names()
        table = table.rename_columns([f"{c.split('__')[0]}__{tn[c.split('__', 1)[1]]}" if c.startswith(("meas__", "q__")) and c.split("__", 1)[1] in tn else c
                                      for c in table.column_names])
    return table
