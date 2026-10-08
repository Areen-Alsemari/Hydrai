"""Per-module variation: profiles are deterministic, bounded, inside the
workbook's own envelopes, actually change the generated data, and the whole
dataset is reproducible across processes (regression test for the
hash()-based seeding bug)."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin.dataset import DatasetConfig, generate_dataset, module_profiles
from hydrai_twin.episode import NormalEpisodeConfig, NormalEpisodeGenerator
from hydrai_twin.fault_episode import FaultEpisodeConfig, FaultEpisodeGenerator
from hydrai_twin.module_profile import NOMINAL_PROFILE, VARIATION_HALF_RANGE, ModuleProfile, make_profile
from hydrai_twin.sensors import accuracy_abs

ROOT = Path(__file__).resolve().parent.parent


# --- profiles themselves ----------------------------------------------------

def test_profile_is_deterministic_and_differs_between_modules():
    assert make_profile("M01", 7) == make_profile("M01", 7)
    assert make_profile("M01", 7) != make_profile("M02", 7)
    assert make_profile("M01", 7) != make_profile("M01", 8)


def test_scale_zero_reproduces_the_identical_modules_twin():
    p = make_profile("M03", 7, scale=0.0)
    for name in VARIATION_HALF_RANGE:
        assert getattr(p, name) == getattr(NOMINAL_PROFILE, name), name
    assert all(b == 0.0 for b in p.sensor_bias.values())


def test_profile_values_stay_inside_declared_bounds_and_workbook_envelopes():
    for seed in range(40):
        p = make_profile("M01", seed)
        lo, hi = C.PCV_BAND_BAR
        setpoint = C.PCV_SETPOINT_BAR + p.pcv_setpoint_offset_bar
        assert lo < setpoint < hi                       # Sec.5 normal band
        assert 0.3 <= p.vacuum_baseline_pa <= 2.0
        assert abs(p.insulation_leak_mult - 1.0) <= 0.20 + 1e-9
        assert abs(p.tank_volume_m3 - C.TANK_INTERNAL_VOLUME_M3) <= 0.02 * C.TANK_INTERNAL_VOLUME_M3 + 1e-9
        for s, b in p.sensor_bias.items():
            assert abs(b) <= 0.5 * accuracy_abs(s) + 1e-12  # biased sensor is still within Sec.9 spec


# --- profiles change the physics/measurements as intended -----------------

def _normal(profile=None, seed=1, **kw):
    cfg = NormalEpisodeConfig(seed=seed, idle_duration_s=120.0, dt_s=2.0, **({"profile": profile} if profile else {}), **kw)
    return NormalEpisodeGenerator(cfg).generate()


def test_default_profile_equals_explicit_nominal_profile():
    a = _normal()
    b = _normal(profile=NOMINAL_PROFILE)
    assert [r["measurements"] for r in a] == [r["measurements"] for r in b]


def test_insulation_leak_mult_scales_boiloff_ground_truth():
    base = _normal()[10]["simulation_ground_truth"]["boiloff_rate_pct_day"]
    worse = _normal(profile=ModuleProfile(insulation_leak_mult=1.2))[10]["simulation_ground_truth"]["boiloff_rate_pct_day"]
    assert abs(worse / base - 1.2) < 1e-9


def test_tank_volume_changes_mass_but_still_fills_to_target_level():
    big = _normal(profile=ModuleProfile(tank_volume_m3=10.2))
    base = _normal()
    assert big[-1]["system_context"]["tank_volume_m3"] == 10.2
    idle = lambda recs: next(r for r in recs if r["system_context"]["phase"] == "idle")
    assert idle(big)["simulation_ground_truth"]["mass_kg"] > idle(base)["simulation_ground_truth"]["mass_kg"]
    assert abs(idle(big)["simulation_ground_truth"]["liquid_level_pct"] - C.TARGET_FILL_PCT) < 2.0


def test_sensor_bias_shifts_measurements_not_ground_truth():
    bias = 0.02
    recs = _normal(profile=ModuleProfile(sensor_bias={"pressure_bar_a": bias}))
    diffs = [r["measurements"]["pressure_bar_a"] - r["simulation_ground_truth"]["pressure_bar_a"] for r in recs]
    assert abs(np.mean(diffs) - bias) < 0.002


def test_pcv_setpoint_offset_moves_pressure_level():
    low = _normal(profile=ModuleProfile(pcv_setpoint_offset_bar=-0.1))
    high = _normal(profile=ModuleProfile(pcv_setpoint_offset_bar=+0.1))
    mean_p = lambda recs: np.mean([r["simulation_ground_truth"]["pressure_bar_a"] for r in recs if r["system_context"]["phase"] == "idle"])
    assert mean_p(high) > mean_p(low) + 0.05


def test_fault_episode_vacuum_is_relative_to_module_baseline():
    prof = ModuleProfile(vacuum_baseline_pa=1.8)
    cfg = FaultEpisodeConfig(fault_id=3, seed=2, idle_duration_s=120.0, ramp_duration_s=30.0, dt_s=2.0, profile=prof)
    recs = FaultEpisodeGenerator(cfg).generate()
    pre = [r for r in recs if r["labels"]["ai_label"] == 0]
    post_max = max(r["simulation_ground_truth"]["vacuum_pressure_pa"] for r in recs)
    assert all(abs(r["simulation_ground_truth"]["vacuum_pressure_pa"] - 1.8) < 1e-9 for r in pre)
    assert abs(post_max - (1.8 + 499.5)) < 1e-6


# --- dataset-level --------------------------------------------------------

def _tiny_cfg(**kw):
    return DatasetConfig(
        modules=("M01", "M02"), fault_ids=(2,), idle_duration_s_normal=30.0,
        idle_duration_s_fault=60.0, dt_s=5.0, base_seed=11, **kw,
    )


def test_modules_in_a_generated_dataset_actually_differ():
    records, _ = generate_dataset(_tiny_cfg())
    vols = {r["system_context"]["module_id"]: r["system_context"]["tank_volume_m3"] for r in records}
    assert vols["M01"] != vols["M02"]
    profiles = module_profiles(_tiny_cfg())
    assert profiles["M01"] != profiles["M02"]


def test_variation_scale_zero_gives_identical_modules():
    records, _ = generate_dataset(_tiny_cfg(variation_scale=0.0))
    assert {r["system_context"]["tank_volume_m3"] for r in records} == {C.TANK_INTERNAL_VOLUME_M3}


def test_dataset_is_reproducible_in_process():
    a, _ = generate_dataset(_tiny_cfg())
    b, _ = generate_dataset(_tiny_cfg())
    assert json.dumps(a) == json.dumps(b)


def test_dataset_is_reproducible_across_processes_with_different_hash_seeds():
    code = (
        "import json, hashlib;"
        "from hydrai_twin.dataset import DatasetConfig, generate_dataset;"
        "cfg = DatasetConfig(modules=('M01',), fault_ids=(2,), idle_duration_s_normal=30.0,"
        " idle_duration_s_fault=60.0, dt_s=5.0, base_seed=11);"
        "recs, _ = generate_dataset(cfg);"
        "print(hashlib.sha256(json.dumps(recs).encode()).hexdigest())"
    )
    digests = []
    for hash_seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(ROOT)}
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, check=True)
        digests.append(out.stdout.strip())
    assert digests[0] == digests[1] and len(digests[0]) == 64
