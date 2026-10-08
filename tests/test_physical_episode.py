"""PhysicalEpisodeGenerator: layers and sampling, the fill rule, normal
behavior, each cause-based scenario, the overfill/hydraulic-lock contrast,
determinism, and Parquet/JSONL round trips. Valve parameters are placeholders,
so these tests check physical behavior and bookkeeping, not engineering numbers."""

import json
from datetime import datetime

import pyarrow.parquet as pq
import pytest

from hydrai_twin import placeholders as PH
from hydrai_twin.layers import write_episode_layers
from hydrai_twin.module_profile import ModuleProfile
from hydrai_twin.physical_episode import PhysicalEpisodeConfig, PhysicalEpisodeGenerator, generate_physical_episode

DAY = 86400.0
SEED = 7


def _t(rec):
    return datetime.fromisoformat(rec["timestamp"]).timestamp()


def run(**kw):
    kw.setdefault("seed", SEED)
    return generate_physical_episode(**kw)


@pytest.fixture(scope="module")
def normal():
    return run(fault_id=0)


def _gt(rows, key):
    return [r["simulation_ground_truth"][key] for r in rows]


# --- layers and sampling -------------------------------------------------------

def test_slow_layer_is_a_60s_grid_over_the_whole_timeline(normal):
    ts = [_t(r) for r in normal.slow]
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    # exactly 60 s, except where a valve event splits a step and shifts one record by < 1 s (the grid re-aligns at the next record)
    assert all(abs(g - 60) < 1.0 for g in gaps) and sum(1 for g in gaps if abs(g - 60) > 1e-3) <= 0.01 * len(gaps)
    assert normal.meta["duration_s"] == pytest.approx(ts[-1] - ts[0], abs=60)
    assert {r["system_context"]["layer"] for r in normal.slow} == {"slow"}
    assert {r["system_context"]["phase"] for r in normal.slow} == {"filling", "storage", "discharge"}


def test_fast_layer_is_1s_and_limited_to_operations_and_bursts(normal):
    ts = [_t(r) for r in normal.fast]
    assert min(b - a for a, b in zip(ts, ts[1:])) >= 0.99
    phases = {r["system_context"]["phase"] for r in normal.fast}
    assert {"filling", "discharge"} <= phases
    storage_fast = [r for r in normal.fast if r["system_context"]["phase"] == "storage"]
    assert storage_fast, "valve actuations should produce burst rows"
    storage_slow = [r for r in normal.slow if r["system_context"]["phase"] == "storage"]
    assert len(storage_fast) < 0.2 * len(storage_slow) * 60   # bursts are a small share of storage seconds
    assert {r["system_context"]["sample_period_s"] for r in normal.fast} == {1.0}


def test_every_valve_opening_has_a_burst():
    normal = run(fault_id=0, boiloff_mode="baseline")          # 0.30 %/day: ~1.2 d PCV cycle, several openings in 14 d
    slow_open = [r for r in normal.slow if r["simulation_ground_truth"]["pcv_open"]]
    fast_open_t = {_t(r) for r in normal.fast if r["simulation_ground_truth"]["pcv_open"]}
    assert normal.meta["pcv_open_events"] >= 5
    assert fast_open_t, "PCV opened but no fast rows captured it"
    assert slow_open == [] or len(fast_open_t) >= len(slow_open)


# --- fill rule -----------------------------------------------------------------

def test_default_fill_follows_the_spec_85_nominal_90_max():
    fills = [PhysicalEpisodeGenerator(PhysicalEpisodeConfig(seed=s)).fill_target for s in range(60)]
    assert all(0.85 <= f <= 0.90 for f in fills)               # Sec. 2/8: 85 % nominal, 90 % maximum; no 55-75 % range any more
    assert min(fills) < 0.86 and max(fills) > 0.875             # varied, mostly near nominal
    assert sorted(fills)[len(fills) // 2] < 0.875


def test_overfill_requires_an_explicit_flag_and_is_labeled():
    with pytest.raises(ValueError, match="allow_overfill"):
        PhysicalEpisodeGenerator(PhysicalEpisodeConfig(seed=1, fill_target_frac=0.92))      # above the 90 % spec maximum
    g = PhysicalEpisodeGenerator(PhysicalEpisodeConfig(seed=1, fill_target_frac=0.93, allow_overfill=True))
    assert g.scenario_class == "overfill_hydraulic_lock"
    for f in (0.70, 0.85, 0.90):                                # spec nominal and maximum are NOT overfill
        assert PhysicalEpisodeGenerator(PhysicalEpisodeConfig(seed=1, fill_target_frac=f)).scenario_class == "standard"


# --- normal behavior -----------------------------------------------------------

def test_normal_episode_physics(normal):
    p = _gt(normal.slow, "pressure_bar_a")
    assert 1.10 <= min(p) and max(p) < 1.51          # the pressure builder holds >= 1.10 during discharge; PCV caps at 1.5
    m = normal.meta
    assert m["prv_lift_events"] == 0 and m["liquid_full_events"] == 0 and m["ended_reason"] is None
    assert m["pcv_open_events"] >= 1
    assert abs(m["mass_residual_kg"]) < 1e-6
    assert all(r["labels"]["ai_label"] == 0 for r in normal.slow)
    assert m["onset_s"] is None


def test_deterministic_for_a_seed():
    a = run(fault_id=0, storage_days=3)
    b = run(fault_id=0, storage_days=3)
    c = run(fault_id=0, storage_days=3, seed=SEED + 1)
    assert json.dumps(a.slow) == json.dumps(b.slow)
    assert json.dumps(a.slow) != json.dumps(c.slow)


def test_profile_changes_the_episode():
    ep = run(fault_id=0, boiloff_mode="baseline", profile=ModuleProfile(tank_volume_m3=10.2, pcv_setpoint_offset_bar=0.10))
    assert ep.slow[0]["system_context"]["tank_volume_m3"] == 10.2
    p = _gt(ep.slow, "pressure_bar_a")
    assert 1.55 < max(p) < 1.61                                # PCV now opens near 1.6, not 1.5


# --- cause-based scenarios -----------------------------------------------------

def _onset_rows(res, rows):
    on = res.meta["onset_s"]
    t0 = _t(res.slow[0])
    return [r for r in rows if _t(r) - t0 >= on]


def test_labels_flip_at_onset_and_onset_is_randomized_in_days_3_to_5():
    onsets = []
    for s in range(6):
        r = run(fault_id=4, seed=s, storage_days=7, include_discharge=False)
        storage0 = r.meta["storage_start_s"]
        onsets.append((r.meta["onset_s"] - storage0) / DAY)
        t0 = _t(r.slow[0])
        before = [x for x in r.slow if _t(x) - t0 < r.meta["onset_s"]]
        after = [x for x in r.slow if _t(x) - t0 >= r.meta["onset_s"]]
        assert all(x["labels"]["ai_label"] == 0 for x in before) and all(x["labels"]["ai_label"] == 4 for x in after)
    assert all(3.0 <= o <= 5.0 for o in onsets) and len(set(round(o, 3) for o in onsets)) > 1


def test_insulation_degradation_doubles_valve_cycling(normal):
    r = run(fault_id=2)
    assert r.meta["pcv_open_events"] > 1.5 * normal.meta["pcv_open_events"]
    assert max(_gt(r.slow, "insulation_mult")) == pytest.approx(2.5, rel=0.01)


def test_vacuum_degradation_vents_far_more_and_raises_the_gauge(normal):
    r = run(fault_id=3)
    assert r.meta["vented_kg"] > 5 * normal.meta["vented_kg"]
    base = r.slow[0]["simulation_ground_truth"]["vacuum_pressure_pa"]
    assert max(_gt(r.slow, "vacuum_pressure_pa")) > base + 10.0
    assert max(_gt(r.slow, "heat_flux_w_m2")) > 40.0           # soft-vacuum rung, ~52 W/m2


def test_vacuum_loss_can_empty_the_tank_and_ends_the_episode_cleanly():
    r = run(fault_id=3, vacuum_target_dp_pa=100.0)
    assert r.meta["ended_reason"] and "dry" in r.meta["ended_reason"]
    assert r.meta["duration_s"] < 14 * DAY
    assert all(x["labels"]["ai_label"] in (0, 3) for x in r.slow)
    assert abs(r.meta["mass_residual_kg"]) < 0.5               # only the aborted final step is unaccounted


def test_stuck_closed_pcv_stops_venting_and_pressure_climbs():
    normal = run(fault_id=0, boiloff_mode="baseline")
    r = run(fault_id=4, boiloff_mode="baseline")
    on = r.meta["onset_s"]
    t0 = _t(r.slow[0])
    after_fast = [x for x in r.fast if _t(x) - t0 > on + 600]
    assert not any(x["simulation_ground_truth"]["pcv_open"] for x in after_fast)
    p_after = [x["simulation_ground_truth"]["pressure_bar_a"] for x in _onset_rows(r, r.slow)]
    assert max(p_after) > 1.7 > max(_gt(normal.slow, "pressure_bar_a"))
    assert r.meta["prv_lift_events"] == 0                       # healthy heat leak: days away from 6 bar


def test_stuck_closed_pcv_is_slow_at_the_spec_boiloff_tier():
    """Documented consequence of the 0.10 %/day spec tier ('target'): 1.2 -> 1.5 bar takes ~19 d, so a 14 d episode with onset on
    days 3-5 shows almost nothing on the pressure channel. (The 0.30 %/day default shows it clearly: previous test.)"""
    normal, r = run(fault_id=0, boiloff_mode="target"), run(fault_id=4, boiloff_mode="target")
    on = r.meta["onset_s"]
    p_after = [x["simulation_ground_truth"]["pressure_bar_a"] for x in r.slow if x["system_context"]["t_s"] >= on]
    assert max(p_after) < 1.65
    assert r.meta["prv_lift_events"] == 0 and r.meta["pcv_open_events"] <= normal.meta["pcv_open_events"]


def test_blocked_vent_is_a_distinct_valve_cause():
    r = run(fault_id=4, pcv_fault="blocked", boiloff_mode="baseline")
    assert r.meta["pcv_open_events"] < run(fault_id=0, boiloff_mode="baseline").meta["pcv_open_events"]   # stays open longer, so fewer openings


def test_leak_lowers_pressure_and_marks_hydrogen_outside(normal):
    r = run(fault_id=5)
    assert r.meta["leaked_kg"] > 50.0
    before = _gt([x for x in r.slow if _t(x) - _t(r.slow[0]) < r.meta["onset_s"] - 3 * 3600][-2000:], "pressure_bar_a")
    late = _gt(r.slow[-2880:], "pressure_bar_a")                 # the last two days
    assert sum(late) / len(late) < sum(before) / len(before) - 0.05
    assert max(_gt(r.slow, "h2_concentration_pct")) > 1.0
    assert max(_gt(normal.slow, "h2_concentration_pct")) < 0.2
    assert abs(r.meta["mass_residual_kg"]) < 1e-6


def test_sensor_fault_corrupts_measurements_only():
    r = run(fault_id=1)
    t0 = _t(r.slow[0])
    spiky_after = [x for x in r.slow if _t(x) - t0 >= r.meta["onset_s"]
                   and abs(x["measurements"]["liquid_temp_c"] - x["simulation_ground_truth"]["liquid_temp_c"]) > 5.0]
    spiky_before = [x for x in r.slow if _t(x) - t0 < r.meta["onset_s"]
                    and abs(x["measurements"]["liquid_temp_c"] - x["simulation_ground_truth"]["liquid_temp_c"]) > 5.0]
    n_after = len(_onset_rows(r, r.slow))
    assert spiky_before == []
    assert 0.08 < len(spiky_after) / n_after < 0.22
    assert r.meta["pcv_open_events"] > 0 and max(_gt(r.slow, "pressure_bar_a")) < 1.51   # physics untouched


def test_structural_concern_changes_strain_not_pressure(normal):
    r = run(fault_id=6)
    scf = _gt(r.slow, "strain_scf")
    assert max(scf) == pytest.approx(4.0, rel=0.02)
    assert abs(r.meta["pcv_open_events"] - normal.meta["pcv_open_events"]) <= 2
    assert max(_gt(r.slow, "pressure_bar_a")) < 1.51


def test_composite_records_its_causes_and_label():
    r = run(fault_id=-1, unknown_sub_fault_ids=(2, 5))
    assert r.slow[0]["system_context"]["unknown_sub_faults"] == [2, 5]
    assert r.meta["leaked_kg"] > 0 and max(_gt(r.slow, "insulation_mult")) > 1.1
    assert {x["labels"]["ai_label"] for x in r.slow} == {0, -1}


# --- overfill / hydraulic lock -------------------------------------------------

def test_hydraulic_lock_above_spec_max_fill_is_labeled_overfill():
    """Overfill = ABOVE the 90 % spec maximum. The liquid-full hydraulic-lock state itself is kept: a blocked vent plus lost vacuum
    drives a closed tank liquid-full whenever the ullage is small, labeled overfill only above 90 %."""
    kw = dict(fault_id=-1, unknown_sub_fault_ids=(3, 4), include_discharge=False)
    over = run(fill_target_frac=0.93, allow_overfill=True, **kw)
    nom = run(fill_target_frac=0.85, **kw)
    assert over.meta["scenario_class"] == "overfill_hydraulic_lock" and nom.meta["scenario_class"] == "standard"
    assert over.meta["liquid_full_events"] >= 1 and over.meta["liquid_vented_kg"] > 5.0
    assert any(x["simulation_ground_truth"]["liquid_full"] for x in over.fast)
    assert nom.meta["prv_lift_events"] >= 1


# --- stratification variant ----------------------------------------------------

def test_stratified_variant_is_labeled_and_pressurizes_faster():
    off = run(fault_id=4, storage_days=9, include_discharge=False)
    on = run(fault_id=4, storage_days=9, include_discharge=False, stratification="empirical")
    assert off.slow[0]["system_context"]["stratification"] == "off"
    assert on.slow[0]["system_context"]["stratification"] == "empirical"
    # compare the RATE of rise over the last day (stuck-closed, no venting): the faster-pressurising variant may have vented once
    # before onset, which lowers its end pressure but not its slope
    def last_day_rise(r):
        p = _gt(r.slow, "pressure_bar_a")
        return p[-1] - p[-1 - 1440]
    assert last_day_rise(on) > last_day_rise(off)


# --- bookkeeping and output ----------------------------------------------------

def test_mass_is_conserved_in_a_leak_episode_with_fill_and_discharge():
    r = run(fault_id=5, leak_severity="small")
    assert r.meta["mass_in_kg"] > 100 and r.meta["mass_liquid_out_kg"] > 100
    assert abs(r.meta["mass_residual_kg"]) < 1e-6


def test_placeholders_used_are_listed_in_meta_with_questions(normal):
    names = {p["name"] for p in normal.meta["placeholders_used"]}
    assert {"pcv_open_bar_a", "pbr_open_bar_a", "first_fill_max_fraction", "ambient_bar_a"} <= names
    assert all(p["question"] for p in normal.meta["placeholders_used"])


def test_parquet_and_jsonl_round_trip(tmp_path, normal):
    paths = write_episode_layers(normal, tmp_path, "ep")
    table = pq.read_table(paths["slow"])
    assert table.num_rows == len(normal.slow) == paths["n_slow"]
    for col in ("episode_id", "timestamp", "meas__pressure_bar_a", "gt__pcv_open", "label__ai_label", "ctx__phase"):
        assert col in table.column_names
    lines = paths["fast"].read_text().splitlines()
    assert len(lines) == len(normal.fast) == paths["n_fast"]
    assert json.loads(lines[0])["system_context"]["layer"] == "fast"
    assert json.loads(paths["meta"].read_text())["episode_id"] == normal.meta["episode_id"]


def test_parquet_handles_columns_that_exist_only_in_some_episodes(tmp_path):
    r = run(fault_id=-1, unknown_sub_fault_ids=(6,), storage_days=3, onset_day_range=(0.5, 1.0))
    paths = write_episode_layers(r, tmp_path, "comp")
    assert "ctx__unknown_sub_faults" in pq.read_table(paths["slow"]).column_names
