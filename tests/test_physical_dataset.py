from dataclasses import replace
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from hydrai_twin import constants as C
from hydrai_twin.channels import REFERENCE_LABEL, DashboardConfig
from hydrai_twin.historian import HistorianConfig
from hydrai_twin.physical_dataset import (DEV_MODULES, UNSEEN_MODULES, PhysicalDatasetConfig, build_jobs, generate_physical_dataset,
                                          load_slow_for_model, lomo_folds, run_job, static_flags_from_parquet, variant_matrix)
from hydrai_twin.physical_episode import PHYSICAL_DEFAULT_BOILOFF_MODE, PhysicalEpisodeConfig


def test_variant_matrix_covers_every_cause_and_labels_overfill_above_spec_max():
    fam = {v.family for v in variant_matrix()}
    assert fam == {"normal", "sensor", "insulation", "vacuum", "pcv", "leak", "structural", "composite", "overfill"}
    keys = [v.key for v in variant_matrix()]
    assert len(keys) == len(set(keys))
    over = [v for v in variant_matrix() if v.family == "overfill"]
    assert all(v.kwargs["allow_overfill"] and v.kwargs["fill_target_frac"] > C.MAX_MODELED_FILL_PCT / 100 for v in over)   # above the 90 % spec max
    assert not any(v.kwargs.get("allow_overfill") for v in variant_matrix() if v.family != "overfill")
    assert {v.kwargs.get("leak_severity") for v in variant_matrix() if v.family == "leak"} == {"pinhole", "small", "small_medium", "medium_large", "full_bore"}
    assert len(variant_matrix(fast=True)) < len(variant_matrix())


def test_unseen_units_have_their_own_profile_and_seeds_and_lomo_folds_partition():
    cfg = PhysicalDatasetConfig(fast=True)
    jobs = build_jobs(cfg, Path("/tmp/x"))
    dev = [j for j in jobs if j.role == "dev"]
    uns = [j for j in jobs if j.role == "unseen"]
    assert {j.module_id for j in dev} == set(DEV_MODULES) and {j.module_id for j in uns} == set(UNSEEN_MODULES)
    assert not {j.seed for j in dev} & {j.seed for j in uns}
    pdev, puns = {j.module_id: j.profile for j in dev}, {j.module_id: j.profile for j in uns}
    assert all(pdev[m] != puns[u] for m in pdev for u in puns)
    assert len({j.name for j in jobs}) == len(jobs)
    for f in lomo_folds(DEV_MODULES):
        assert f["test_module"] not in f["train_modules"] and set(f["train_modules"]) | {f["test_module"]} == set(DEV_MODULES)
    assert sum(1 for j in jobs if j.role == "commissioning") == len(DEV_MODULES) + len(UNSEEN_MODULES)


def test_defaults_boiloff_historian_view_and_valve_states():
    cfg = PhysicalDatasetConfig()
    assert cfg.boiloff_mode == PHYSICAL_DEFAULT_BOILOFF_MODE == "baseline"       # Sec. 7: real 10 m^3 tanks run 0.3-0.6 %/day
    assert C.BOILOFF_LADDER_PCT_PER_DAY[cfg.boiloff_mode]["normal"] == 0.30
    assert PhysicalEpisodeConfig().boiloff_mode == "baseline"
    assert C.BOILOFF_LADDER_PCT_PER_DAY["target"]["normal"] == 0.10               # the spec value stays available as the switch
    assert C.DEFAULT_BOILOFF_MODE == "baseline"                        # the LEGACY generators are untouched
    assert cfg.historian.enabled is True and cfg.valve_states is False and cfg.channel_sampling is True
    v = cfg.sensor_view()
    assert (v.h2_mode, v.vacuum_mode, v.level_mode, v.valve_states) == ("lfl", "log_gauge", "dp", False)
    assert v.periods_s["outer_wall_temp_c"] == 5 and v.periods_s["vacuum_pressure_pa"] == 10
    assert "pcv_state" not in cfg.dashboard_for_view().mask().enabled
    assert "pcv_state" in replace(cfg, valve_states=True).dashboard_for_view().mask().enabled
    assert PhysicalDatasetConfig(boiloff_mode="target").episode_overrides()["boiloff_mode"] == "target"           # one-line switch to the spec value
    assert cfg.dashboard_for_view().with_h2_mode("lfl").tag_for("h2_concentration_pct").unit == "%LFL"
    assert replace(cfg, h2_mode="spec").dashboard_for_view().tag_for("h2_concentration_pct").unit == "%vol"


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    out = tmp_path_factory.mktemp("pds")
    cfg = PhysicalDatasetConfig(dev_modules=("M01",), unseen_modules=("U01",), fast=True)
    m = generate_physical_dataset(cfg, out, workers=1, progress=False)
    return out, m, cfg


def test_manifest_labels_reference_config_provisional_alarms_and_choices(tiny):
    _, m, _ = tiny
    assert m["dashboard_label"] == REFERENCE_LABEL == "reference configuration, not a verified Saudi system"
    assert "PROVISIONAL" in m["static_alarm_status"] and m["dashboard"]["status"].startswith("REFERENCE")
    assert m["config"]["boiloff_mode"] == "baseline" and m["config"]["boiloff_normal_pct_per_day"] == 0.30 and "PHYSICAL_DEFAULT_BOILOFF_MODE" in m["config"]["boiloff_switch"]
    assert m["config"]["fill_rule"]["nominal_pct"] == 85.0 and m["config"]["fill_rule"]["max_pct"] == 90.0
    assert m["sample_periods_s"]["h2_concentration_pct"] == 0.2 and m["sample_periods_s"]["outer_wall_temp_c"] == 5
    assert m["measurement_units"]["h2_concentration_pct"] == "%LFL" and m["dashboard_tag_names"]["pressure_bar_a"] == "LH2-PT-101"
    assert m["historian"]["enabled"] is True and m["historian"]["compression_forced_point_s"] == 28800 and m["historian"]["exception_forced_point_s"] == 600
    assert m["valve_states"]["default"] is False and m["valve_states"]["available_to_detector"] is False
    assert "pcv_state" not in m["model_visible_channels"] and "inner_wall_temp_c" not in m["model_visible_channels"]
    assert "ONE-SHOT" in m["unseen_policy"]
    names = {p["name"] for p in m["placeholders_used"]}
    assert {"pcv_open_bar_a", "prv_set_bar_a", "h2_detector_accuracy_lfl", "h2_alarm_h_lfl", "vacuum_gauge_rel_accuracy", "sensor_noise_sigma_frac",
            "historian_fault_dropout_per_day", "overfill_fill_fraction", "first_fill_max_fraction"} <= names
    assert all(p["level"] in ("placeholder", "literature") for p in m["placeholders_used"])


def test_manifest_records_both_reference_times_static_alarms_and_compression(tiny):
    _, m, _ = tiny
    faults = [e for e in m["episodes"] if e["fault_id"] != 0]
    for e in faults:
        for k in ("onset_s", "first_observable_s", "first_observable_clear_s", "first_observable_dashboard_s", "per_channel_deviation_s",
                  "static_alarm_first_s", "healthy_exposure_s", "scenario_class", "fill_target_pct"):
            assert k in e
        if e["first_observable_s"] is not None:
            assert e["first_observable_s"] >= e["onset_s"]
        assert e["static_alarm_status"].startswith("PROVISIONAL")
    assert all(e["onset_s"] is None and e["first_observable_s"] is None for e in m["episodes"] if e["fault_id"] == 0)
    ratios = m["historian"]["compression_ratio_by_tag"]
    assert ratios["pressure_bar_a"] > 5 and all(v is None or v >= 1 for v in ratios.values())
    h = m["episodes"][0]["historian"]
    assert set(h["injected_fault_samples"]) == {"dropout", "stale_value", "flat_line", "out_of_range"}
    assert abs(max(abs(e["mass_residual_kg"]) for e in m["episodes"])) < 1e-6


def test_roles_fill_rule_and_overfill_labels(tiny):
    _, m, _ = tiny
    assert {e["role"] for e in m["episodes"]} == {"dev", "unseen", "commissioning"}
    over = [e for e in m["episodes"] if e["family"] == "overfill"]
    assert over and all(e["scenario_class"] == "overfill_hydraulic_lock" and e["fill_target_pct"] > 90.0 for e in over)
    std = [e for e in m["episodes"] if e["family"] != "overfill"]
    assert all(e["scenario_class"] == "standard" and 85.0 <= e["fill_target_pct"] <= 90.0 for e in std)     # no 55-75 % healthy range
    assert all(e["boiloff_mode"] == "baseline" and e["boiloff_normal_pct_per_day"] == 0.30 for e in m["episodes"])


def test_files_model_loader_hides_untagged_channels_gt_labels_live_and_faults(tiny):
    out, m, _ = tiny
    e = m["episodes"][0]
    slow = out / e["slow_file"]
    assert slow.exists() and (out / e["fast_file"]).exists()
    full = pq.read_table(slow).column_names
    assert all(any(c.startswith(p) for c in full) for p in ("gt__", "label__", "live__", "dfault__", "q__"))
    dash = DashboardConfig.from_dict(m["dashboard"])
    cols = load_slow_for_model(slow, dash).column_names
    assert not any(c.startswith(("gt__", "label__", "live__", "dfault__")) for c in cols)
    assert "meas__LH2-PT-101" in cols and "q__LH2-PT-101" in cols and "meas__inner_wall_temp_c" not in cols
    raw = load_slow_for_model(slow, dash, tag_names=False).column_names
    assert "meas__pressure_bar_a" in raw and not any(c.startswith("meas__pcv") for c in raw)


def test_historian_off_gives_the_ideal_view_with_no_extra_columns(tmp_path):
    base = dict(dev_modules=("M01",), include_unseen=False, include_commissioning=False, fast=True)
    cfg_off = PhysicalDatasetConfig(historian=replace(HistorianConfig.from_registry(), enabled=False), **base)
    job = [j for j in build_jobs(cfg_off, tmp_path) if j.variant.key == "normal-fill0"][0]
    e = run_job(job)
    cols = pq.read_table(tmp_path / e["slow_file"]).column_names
    assert not any(c.startswith(("q__", "live__", "dfault__")) for c in cols) and e["historian"]["tags"] == {}
    t = pq.read_table(tmp_path / e["slow_file"]).to_pydict()
    gap = max(abs(a - b) for a, b in zip(t["meas__pressure_bar_a"], t["gt__pressure_bar_a"]))
    assert gap < 0.05                                                   # ideal view: measurement = truth + small instrument error


def test_static_alarms_come_from_live_columns_and_are_unaffected_by_faults(tmp_path):
    base = dict(dev_modules=("M01",), include_unseen=False, include_commissioning=False, fast=True)
    cfg = PhysicalDatasetConfig(**base)
    job = [j for j in build_jobs(cfg, tmp_path) if j.variant.key == "leak-small_medium"][0]
    e = run_job(job)
    dash = DashboardConfig.from_dict(job.dashboard)
    ts, flags = static_flags_from_parquet(tmp_path / e["slow_file"], dash)
    first = next((t for t, f in zip(ts, flags) if f), None)
    assert first == e["static_alarm_first_s"]["any"] and first is not None and first >= e["onset_s"]


def test_manifest_is_reproducible(tmp_path):
    cfg = PhysicalDatasetConfig(dev_modules=("M02",), include_unseen=False, include_commissioning=False, fast=True)
    j = [x for x in build_jobs(cfg, tmp_path) if x.variant.key == "insulation-x2.5-r2d"][0]
    a, b = run_job(j), run_job(j)
    for k in ("onset_s", "first_observable_s", "static_alarm_first_s", "duration_s", "fill_target_pct", "pcv_open_events", "historian"):
        assert a[k] == b[k]
