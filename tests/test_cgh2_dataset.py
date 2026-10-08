import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

from hydrai_twin import systems
from hydrai_twin.cgh2.dashboard import CGH2Dashboard
from hydrai_twin.cgh2.dataset import (DEV_MODULES, RUPTURE_MODULES, UNSEEN_MODULES, CGH2DatasetConfig, build_jobs, cgh2_historian, generate_cgh2_dataset,
                                      load_slow_for_model, lomo_folds, run_job, variant_matrix)
from hydrai_twin.cgh2.sensor_view import DISCRETE
from hydrai_twin.historian import FAULT_TYPES


def test_variant_matrix_covers_every_class_and_labels_the_stress_set():
    fam = {v.family for v in variant_matrix()}
    assert fam == {"normal", "sensor", "thermal", "leak", "leak-stress", "pressure", "containment", "structural", "composite"}
    keys = [v.key for v in variant_matrix()]
    assert len(keys) == len(set(keys))
    assert {v.kwargs["leak_diameter_mm"] for v in variant_matrix() if v.family == "leak"} == {0.1, 0.25, 0.5, 1.0}
    stress = [v for v in variant_matrix() if v.family == "leak-stress"]
    assert {v.kwargs["leak_diameter_mm"] for v in stress} == {0.03, 0.05} and all(v.kwargs["expected_miss"] for v in stress)
    assert {v.kwargs["pressure_variant"] for v in variant_matrix() if v.family == "pressure"} == {"compressor_overrun", "blocked_relief", "fire", "stuck_open"}
    assert {v.kwargs["leak_diameter_mm"] for v in variant_matrix() if v.family == "containment"} == {2.0, 3.5, 5.0}      # 2-5 mm
    assert any(v.kwargs.get("demand_pattern") == "industrial" for v in variant_matrix()) and any(v.kwargs.get("solar") == "dark" for v in variant_matrix())
    assert len(variant_matrix(fast=True)) < len(variant_matrix())


def test_rupture_is_rare_and_the_split_structure_matches_lh2():
    jobs = build_jobs(CGH2DatasetConfig(), Path("/tmp/x"))
    rup = [j for j in jobs if j.variant.family == "rupture"]
    faults = [j for j in jobs if j.variant.kwargs.get("fault_id", 0) != 0]
    assert len(rup) == len(RUPTURE_MODULES) == 3 and len(rup) / len(faults) < 0.02                        # < 2 % of fault episodes
    dev = [j for j in jobs if j.role == "dev"]; uns = [j for j in jobs if j.role == "unseen"]
    assert {j.module_id for j in dev} == set(DEV_MODULES) and {j.module_id for j in uns} == set(UNSEEN_MODULES)
    assert not {j.seed for j in dev} & {j.seed for j in uns} and all(a.profile != b.profile for a in dev[:3] for b in uns[:3])
    assert sum(1 for j in jobs if j.role == "commissioning") == len(DEV_MODULES) + len(UNSEEN_MODULES) and len({j.name for j in jobs}) == len(jobs)
    for f in lomo_folds(DEV_MODULES):
        assert f["test_module"] not in f["train_modules"] and set(f["train_modules"]) | {f["test_module"]} == set(DEV_MODULES)


def test_ood_sets_are_small_use_the_other_classes_and_skip_the_unholdable_low_dark_case():
    low = build_jobs(CGH2DatasetConfig(pressure_class="low", roles="ood", dev_modules=("M01", "M02", "M03"), include_unseen=False, reduced=True), Path("/tmp/x"))
    assert {j.role for j in low} == {"ood", "commissioning"} and len(low) < 60 and not any("dark" in j.variant.key for j in low)
    assert all(j.overrides["pressure_class"] == "low" for j in low) and not any(j.variant.family == "rupture" for j in low)
    high = build_jobs(CGH2DatasetConfig(pressure_class="high", roles="ood", dev_modules=("M01", "M02", "M03"), include_unseen=False, reduced=True), Path("/tmp/x"))
    assert any("dark" in j.variant.key for j in high) and high[0].dashboard["pressure_class"] == "high"


def test_defaults_detector_valve_states_historian_and_system_switch():
    cfg = CGH2DatasetConfig()
    assert (cfg.pressure_class, cfg.h2_mode, cfg.flow_mode, cfg.valve_states, cfg.historian.enabled) == ("medium", "lfl", "datasheet", True, True)
    assert systems.DEFAULT_SYSTEM == "lh2" and systems.SYSTEMS == ("lh2", "cgh2")
    with pytest.raises(ValueError):
        systems.check("lng")
    r = systems.generate_episode("cgh2", fault_id=0, seed=2, days=1.0)
    assert r.meta["system"] == "cgh2"
    l = systems.generate_episode("lh2", fault_id=0, seed=2, storage_days=1.0)
    assert "system" not in l.meta and l.meta["scenario"] == "normal"                                       # the LH2 path is untouched


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    out = tmp_path_factory.mktemp("cgh2")
    cfg = CGH2DatasetConfig(fast=True, dev_modules=("M01",), include_unseen=False)
    return out, generate_cgh2_dataset(cfg, out, workers=1, progress=False), cfg


def test_manifest_content(tiny):
    _, m, _ = tiny
    assert m["dashboard_label"] == "reference configuration, not a verified Saudi system" and m["dashboard"]["status"] == "REFERENCE - not a verified Saudi system"
    assert m["system"] == "cgh2" and m["config"]["boiloff"].startswith("n/a") and m["config"]["pressure_class"] == "medium"
    assert m["config"]["h2_detector_mode"] == "lfl" and m["config"]["valve_states_and_compressor_status"] is True and m["valve_states"]["default"] is True
    assert m["sensor_split"]["bias_frac"] == 0.5 and m["historian"]["enabled"] is True and m["historian"]["compression_forced_point_s"] == 28800.0
    assert m["class_parameters"]["mop_bar"] == 300.0 and m["class_parameters"]["tau_wall_ambient_s"] > 3600
    assert "PROVISIONAL" in m["static_alarm_status"] and "NOT available" in m["unconfirmed_notice"]
    assert set(m["channels_without_static_alarm"]) >= {"strain_ue", "compressor_status", "outer_wall_temp_c"}
    assert m["measurement_units"]["h2_concentration_pct"] == "%LFL" and m["sample_periods_s"]["outer_wall_temp_c"] == 5.0
    assert all(p["placeholder"] for p in m["placeholders_used"]) and any(p["tag"] == "REG-UNREAD" for p in m["placeholders_used"])
    assert {"V1", "V2", "CALC", "JUDGE"} <= {u["tag"] for u in m["registry_used"]}
    names = {c["name"] for c in m["register_conflicts_resolved"]}
    assert {"pah_over_mop", "tprd_fitted", "prv_blowdown_nominal"} <= names
    assert "ONE-SHOT" in m["unseen_policy"] and m["lomo_folds"]


def test_episode_entries_carry_both_reference_times_and_static_alarms(tiny):
    _, m, _ = tiny
    for e in [x for x in m["episodes"] if x["fault_id"] != 0]:
        for k in ("onset_s", "first_observable_s", "first_observable_clear_s", "first_observable_dashboard_s", "per_channel_deviation_s", "static_alarm_first_s",
                  "healthy_exposure_s", "expected_miss", "stop_mode", "pressure_class"):
            assert k in e
        if e["first_observable_s"] is not None:
            assert e["first_observable_s"] >= e["onset_s"]
        assert e["static_alarm_status"] == "PROVISIONAL"
    assert all(e["onset_s"] is None for e in m["episodes"] if e["fault_id"] == 0)
    assert abs(max(abs(e["mass_residual_kg"]) for e in m["episodes"])) < 1e-6
    assert any(e["expected_miss"] for e in m["episodes"]) and any(e["family"] == "rupture" for e in m["episodes"])


def test_model_loader_hides_ground_truth_labels_live_values_and_fault_labels(tiny):
    out, m, _ = tiny
    e = m["episodes"][0]
    full = pq.read_table(out / e["slow_file"]).column_names
    assert all(any(c.startswith(p) for c in full) for p in ("gt__", "label__", "live__", "dfault__", "q__"))
    d = CGH2Dashboard.from_dict(m["dashboard"])
    cols = load_slow_for_model(out / e["slow_file"], d).column_names
    assert not any(c.startswith(("gt__", "label__", "live__", "dfault__")) for c in cols)
    assert "meas__GH2-PT-101" in cols and "q__GH2-PT-101" in cols and "meas__compressor_status" in cols
    nm = d.tag_names()
    assert set(nm) == set(CGH2Dashboard.reference("medium").tag_names())


def test_valve_state_ablation_removes_the_discrete_inputs(tmp_path):
    cfg = CGH2DatasetConfig(fast=True, dev_modules=("M01",), include_unseen=False, include_commissioning=False, valve_states=False)
    job = [j for j in build_jobs(cfg, tmp_path) if j.variant.key == "normal-refuelling0"][0]
    e = run_job(job)
    cols = pq.read_table(tmp_path / e["slow_file"]).column_names
    assert not any(c == f"meas__{d}" for c in cols for d in DISCRETE)
    d = CGH2Dashboard.from_dict(job.dashboard)
    assert d.mask().isdisjoint(DISCRETE)


def test_injected_data_faults_are_labelled_and_rates_match_between_layers(tiny):
    out, m, _ = tiny
    heavy = replace(CGH2DatasetConfig(fast=True, dev_modules=("M01",), include_unseen=False, include_commissioning=False),
                    historian=replace(cgh2_historian(), fault_rates={"dropout": (6.0, 300.0), "stale_value": (6.0, 600.0), "flat_line": (3.0, 1800.0), "out_of_range": (3.0, 200.0)}))
    mm = generate_cgh2_dataset(heavy, out / "heavy", workers=1, progress=False)
    runs = {l: 0 for l in ("slow", "fast")}; days = {l: 0.0 for l in ("slow", "fast")}
    for e in mm["episodes"]:
        for layer in ("slow", "fast"):
            for v in e["historian"]["layers"][layer].values():
                runs[layer] += sum(v["fault_run_starts"].values()); days[layer] += v["exposure_channel_days"]
    rs, rf = runs["slow"] / days["slow"], runs["fast"] / days["fast"]
    assert 0.6 < rf / rs < 1.6, (rs, rf)                                                   # same rate per channel-day in both layers
    e0 = mm["episodes"][0]
    t = pq.read_table(out / "heavy" / e0["slow_file"]).to_pydict()
    assert any(v != "none" for v in t["dfault__pressure_bar_a"]) and set(t["q__pressure_bar_a"]) <= {"Good", "Uncertain", "Bad"}
    assert all(l == 0 for l in t["label__ai_label"]) or e0["fault_id"] != 0                  # data faults are not physical anomalies
    assert set(FAULT_TYPES) == {"dropout", "stale_value", "flat_line", "out_of_range"}
