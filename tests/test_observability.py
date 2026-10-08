import numpy as np
import pytest

from hydrai_twin.observability import (K_CLEAR, K_SENSITIVE, N_CONSECUTIVE, _first_run, first_deviation_times, observable_time,
                                       sensor_sigma)
from hydrai_twin.physical_episode import PhysicalEpisodeConfig, PhysicalEpisodeGenerator, generate_physical_episode

KW = dict(seed=17, storage_days=6.0, onset_day_range=(1.5, 2.5), boiloff_mode="baseline")   # 0.30 %/day: valve faults show within days


def _t(rec):
    return rec["system_context"]["t_s"]


def test_first_run_needs_n_consecutive():
    m = np.array([0, 1, 1, 0, 1, 1, 1, 1], dtype=bool)
    assert _first_run(m, 3) == 4
    assert _first_run(m, 5) is None
    assert _first_run(np.array([1, 1], dtype=bool), 3) is None


def test_sensor_sigma_is_half_the_stated_accuracy():
    from hydrai_twin.sensors import accuracy_abs
    assert sensor_sigma("liquid_temp_c") == pytest.approx(accuracy_abs("liquid_temp_c") / 2)


def test_fault_run_and_healthy_twin_share_identical_pre_onset_physics():
    f = PhysicalEpisodeGenerator(PhysicalEpisodeConfig(fault_id=4, compute_observability=False, **KW)).generate()
    h = PhysicalEpisodeGenerator(PhysicalEpisodeConfig(fault_id=0, compute_observability=False, **KW)).generate()
    onset = f.meta["onset_s"]
    pre_f = [r for r in f.slow if _t(r) < onset]
    pre_h = [r for r in h.slow if _t(r) < onset]
    assert len(pre_f) == len(pre_h) > 1000
    for a, b in zip(pre_f, pre_h):
        for k in ("pressure_bar_a", "liquid_temp_c", "outer_wall_temp_c", "ambient_temp_c", "liquid_level_pct"):
            assert a["simulation_ground_truth"][k] == b["simulation_ground_truth"][k]
    assert h.meta["onset_s"] is None


def test_onset_label_and_observable_label_are_separate_and_ordered():
    r = generate_physical_episode(fault_id=4, **KW)       # PCV stuck closed
    m = r.meta
    assert m["onset_s"] is not None and m["first_observable_s"] is not None
    assert m["first_observable_s"] > m["onset_s"]
    assert m["onset_to_first_observable_s"] == pytest.approx(m["first_observable_s"] - m["onset_s"])
    assert m["first_observable_clear_s"] is None or m["first_observable_clear_s"] >= m["first_observable_s"]
    for rec in r.slow + r.fast:
        t = _t(rec)
        lab = rec["labels"]
        assert lab["ai_label"] == (4 if t >= m["onset_s"] else 0)
        assert lab["ai_label_observable"] == (4 if t >= m["first_observable_s"] else 0)
    assert any(x["labels"]["ai_label"] == 4 and x["labels"]["ai_label_observable"] == 0 for x in r.slow)   # the gap exists


def test_normal_episode_has_no_onset_or_observable_time():
    r = generate_physical_episode(fault_id=0, **KW)
    assert r.meta["onset_s"] is None and r.meta["first_observable_s"] is None and r.meta["per_channel_deviation_s"] == {}
    assert all(x["labels"]["ai_label"] == 0 and x["labels"]["ai_label_observable"] == 0 for x in r.slow)
    assert r.meta["healthy_exposure_s"] == pytest.approx(r.meta["duration_s"])


def test_pre_onset_exposure_is_onset_for_fault_episodes():
    r = generate_physical_episode(fault_id=2, **KW)
    assert r.meta["healthy_exposure_s"] == pytest.approx(r.meta["onset_s"])
    assert r.meta["time_onset_to_end_s"] == pytest.approx(r.meta["duration_s"] - r.meta["onset_s"])


def test_per_channel_times_allow_recomputing_under_a_mask():
    r = generate_physical_episode(fault_id=6, **KW)       # structural: strain first
    pc = r.meta["per_channel_deviation_s"]
    assert observable_time(pc, None, "k3") == r.meta["first_observable_s"]
    assert pc["strain_ue"]["k3"] == r.meta["first_observable_s"]
    # a dashboard without the strain tag cannot see this fault early (or at all)
    other = observable_time(pc, {"pressure_bar_a", "liquid_temp_c", "ambient_temp_c"}, "k3")
    assert other is None or other > r.meta["first_observable_s"]


def test_k10_is_not_earlier_than_k3_on_any_channel():
    r = generate_physical_episode(fault_id=2, **KW)
    for tag, v in r.meta["per_channel_deviation_s"].items():
        if v["k3"] is not None and v["k10"] is not None:
            assert v["k10"] >= v["k3"], tag
        if v["k3"] is None:
            assert v["k10"] is None, tag
    assert K_SENSITIVE < K_CLEAR and N_CONSECUTIVE >= 2


def test_sensor_fault_observable_is_a_single_outlier_on_liquid_temp():
    r = generate_physical_episode(fault_id=1, **KW)
    pc = r.meta["per_channel_deviation_s"]
    assert pc["liquid_temp_c"]["k3"] is not None and pc["liquid_temp_c"]["k3"] >= r.meta["onset_s"]
    assert r.meta["first_observable_s"] == pc["liquid_temp_c"]["k3"]
