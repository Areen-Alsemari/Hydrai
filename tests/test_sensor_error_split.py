import numpy as np
import pytest

from hydrai_twin import constants as C
from hydrai_twin.module_profile import make_profile
from hydrai_twin.physical_episode import generate_physical_episode
from hydrai_twin.sensors import (SensorErrorSplit, accuracy_abs, drift_series, measure, measure_split, rescale_unit_bias)

SP = SensorErrorSplit.from_registry()
T = np.arange(0, 14 * 86400, 60.0)


def test_split_parts_fit_inside_the_stated_accuracy_for_every_channel():
    """bias bound + drift bound + 2-sigma noise <= accuracy (generic channels), so total error stays inside the Sec. 9 spec."""
    for tag in C.SENSOR_SPECS:
        total = SP.bias_bound(tag) + SP.drift_bound(tag) + 2 * SP.sigma_noise(tag)
        assert total <= accuracy_abs(tag) * (1 + 1e-9), tag


def test_random_noise_is_much_smaller_than_the_legacy_white_noise():
    for tag in C.SENSOR_SPECS:
        assert SP.sigma_noise(tag) == pytest.approx(0.2 * accuracy_abs(tag) / 2)      # 0.1 x A  vs  legacy 0.5 x A
        assert SP.sigma_noise(tag) < 0.25 * accuracy_abs(tag) / 2 * 2


def test_split_values_are_registered_placeholders():
    from hydrai_twin import placeholders as PH
    for n in ("sensor_bias_frac", "sensor_drift_frac", "sensor_noise_sigma_frac", "sensor_drift_tau_days",
              "sensor_h2_zero_bias_frac", "sensor_h2_zero_drift_frac"):
        assert PH.REGISTRY[n].level == "placeholder" and PH.REGISTRY[n].question == "Q12"


def test_drift_is_slow_bounded_and_deterministic():
    tag = "pressure_bar_a"
    d = drift_series(tag, T, np.random.default_rng(1), SP)
    assert np.all(np.abs(d) <= SP.drift_bound(tag) + 1e-15)
    assert d.std() > 0.3 * SP.drift_sigma(tag)                                # actually wanders
    assert np.abs(np.diff(d)).max() < 0.1 * SP.drift_bound(tag)               # slow: no minute-scale jumps
    assert np.array_equal(d, drift_series(tag, T, np.random.default_rng(1), SP))
    assert not np.array_equal(d, drift_series(tag, T, np.random.default_rng(2), SP))


def test_drift_stationary_std_matches_the_split():
    tag = "liquid_temp_c"
    sd = [drift_series(tag, T, np.random.default_rng(i), SP).std() for i in range(60)]
    # unclipped stationary sigma is 0.15 A; clipping at 2 sigma trims it slightly; time-average within 14 d (tau 3 d) is noisy
    assert 0.5 * SP.drift_sigma(tag) < np.mean(sd) < 1.2 * SP.drift_sigma(tag)


def test_unit_bias_is_bounded_by_the_spec_for_every_channel_and_unit():
    for mod in ("M01", "M02", "M03", "U01", "U02"):
        prof = make_profile(mod, 20260301)
        for tag in C.SENSOR_SPECS:
            b = rescale_unit_bias(prof.sensor_bias[tag], tag, SP)
            assert abs(b) <= SP.bias_bound(tag) + 1e-12
            assert abs(b) <= accuracy_abs(tag)


def test_h2_channel_is_zero_referenced_with_smaller_offset_bounds():
    tag = "h2_concentration_pct"
    assert SP.bias_bound(tag) == pytest.approx(0.2) and SP.drift_bound(tag) == pytest.approx(0.2)     # %vol
    assert SP.sigma_noise(tag) == pytest.approx(0.2)
    assert SP.get(tag, "bias_frac") == 0.1 and SP.get(tag, "drift_frac") == 0.1
    assert SP.get("pressure_bar_a", "bias_frac") == SP.bias_frac


def test_measure_split_composition_and_clipping():
    rng = np.random.default_rng(0)
    vals = [measure_split("pressure_bar_a", 1.2, rng, SP, unit_bias=0.01, drift=0.002) for _ in range(20000)]
    assert np.mean(vals) == pytest.approx(1.212, abs=3 * SP.sigma_noise("pressure_bar_a") / np.sqrt(20000) + 1e-4)
    assert np.std(vals) == pytest.approx(SP.sigma_noise("pressure_bar_a"), rel=0.05)
    assert measure_split("pressure_bar_a", 0.0, rng, SP, -0.05, 0.0) == 0.0         # clipped at the range floor


def test_legacy_measure_is_unchanged():
    rng = np.random.default_rng(0)
    v = [measure("pressure_bar_a", 1.2, rng) for _ in range(20000)]
    assert np.std(v) == pytest.approx(accuracy_abs("pressure_bar_a") / 2, rel=0.05)


def _err(r, tag):
    return np.array([x["measurements"][tag] - x["simulation_ground_truth"][tag] for x in r.slow if x["system_context"]["phase"] == "storage"])


def test_episode_error_is_smaller_and_slowly_varying_under_the_split_model():
    kw = dict(fault_id=0, seed=5, storage_days=6.0)
    leg = generate_physical_episode(sensor_error_model="legacy_white", **kw)
    spl = generate_physical_episode(**kw)
    assert spl.meta["sensor_error_model"] == "split" and leg.meta["sensor_error_model"] == "legacy_white"
    e_l, e_s = _err(leg, "pressure_bar_a"), _err(spl, "pressure_bar_a")
    assert e_s.std() < 0.5 * e_l.std()
    # successive 1 h block means of the error vary slowly under the split (drift + noise/sqrt(60)), but are essentially white under legacy
    blocks = lambda e: e[: len(e) // 60 * 60].reshape(-1, 60).mean(axis=1)
    assert np.abs(np.diff(blocks(e_s))).mean() < 0.4 * SP.drift_bound("pressure_bar_a")
    assert spl.meta["sensor_error_split"]["level"].startswith("placeholder")
    assert "sensor_noise_sigma_frac" in {p["name"] for p in spl.meta["placeholders_used"]}


def test_fault_run_and_healthy_twin_share_identical_measurements_before_onset():
    """Same seed => same bias, same drift series and the same noise draws; so the fault and its healthy twin differ only after onset."""
    kw = dict(seed=9, storage_days=5.0, onset_day_range=(2.0, 3.0), compute_observability=False)
    a = generate_physical_episode(fault_id=0, **kw)
    b = generate_physical_episode(fault_id=2, **kw)
    on = b.meta["onset_s"]
    pre = [(x, y) for x, y in zip(a.slow, b.slow) if x["system_context"]["t_s"] < on]
    assert len(pre) > 1000
    for x, y in pre:
        assert x["measurements"] == y["measurements"]
    after = [(x, y) for x, y in zip(a.slow, b.slow) if x["system_context"]["t_s"] > on + 2 * 86400]
    assert any(x["measurements"]["pressure_bar_a"] != y["measurements"]["pressure_bar_a"] for x, y in after)
