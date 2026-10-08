import math

import numpy as np
import pytest

from hydrai_twin import constants as C
from hydrai_twin import placeholders as PH
from hydrai_twin.physical_episode import generate_physical_episode
from hydrai_twin.sensor_view import DEFAULT_PERIODS_S, SensorView, SensorViewConfig
from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs

SPLIT = SensorErrorSplit(0.5, 0.3, 0.1, 3 * 86400.0)
T = np.arange(0.0, 86400.0, 1.0)


def make_view(cfg=None, u=0.0, drift=0.0, seed=0, split=SPLIT):
    z = {k: np.full(len(T), drift) for k in C.SENSOR_SPECS}
    return SensorView(cfg or SensorViewConfig(), split, {k: u for k in C.SENSOR_SPECS}, z, T, np.random.default_rng(seed))


def test_default_periods_are_the_sec9_sampling_rates():
    assert DEFAULT_PERIODS_S["pressure_bar_a"] == 1 and DEFAULT_PERIODS_S["outer_wall_temp_c"] == 5
    assert DEFAULT_PERIODS_S["vacuum_pressure_pa"] == 10 and DEFAULT_PERIODS_S["ambient_temp_c"] == 10
    assert DEFAULT_PERIODS_S["h2_concentration_pct"] == pytest.approx(0.2) and DEFAULT_PERIODS_S["strain_ue"] == pytest.approx(0.1)


def test_slow_tags_hold_their_reading_for_the_period():
    v = make_view()
    vals = [v._read_one("outer_wall_temp_c", 10.0, float(t), {}) for t in range(0, 31)]
    for k in range(0, 30, 5):                         # 5 s tag: six distinct readings, each held for 5 rows
        assert len(set(vals[k:k + 5])) == 1
    assert len(set(vals)) > 1
    vac = [v._read_one("vacuum_pressure_pa", 1.0, float(t), {}) for t in range(0, 31)]
    assert all(len(set(vac[k:k + 10])) == 1 for k in range(0, 30, 10)) and len(set(vac)) > 1


def test_same_instant_returns_the_same_reading_for_both_layers():
    v = make_view()
    a = v.read(100.0, {"pressure_bar_a": 1.3, "outer_wall_temp_c": 5.0})
    b = v.read(100.0, {"pressure_bar_a": 1.3, "outer_wall_temp_c": 5.0})
    assert a == b


def test_fast_channels_are_aggregated_not_dropped():
    """Flows / strain (0.1 s native) and H2 (0.2 s): the 1 s value is a mean of n native samples, so noise is sigma/sqrt(n)."""
    for tag, n in (("mass_flow_fill_kg_s", 10), ("strain_ue", 10)):
        v = make_view(seed=1)
        x = np.array([v._read_one(tag, 0.5 if tag.startswith("mass") else 0.0, float(t), {}) for t in range(0, 20000)])
        sigma = SPLIT.get(tag, "noise_sigma_frac") * accuracy_abs(tag) / math.sqrt(n)
        assert np.std(x) == pytest.approx(sigma, rel=0.05)
    v = make_view(seed=2)
    x = np.array([v._read_one("pressure_bar_a", 1.2, float(t), {}) for t in range(0, 20000)])
    assert np.std(x) == pytest.approx(SPLIT.sigma_noise("pressure_bar_a"), rel=0.05)         # 1 s tag: n = 1


def test_h2_lfl_mode_scales_to_lfl_and_has_the_5_lfl_accuracy():
    cfg = SensorViewConfig(h2_mode="lfl")
    assert cfg.measurement_units()["h2_concentration_pct"] == "%LFL" and cfg.measurement_ranges()["h2_concentration_pct"] == (0.0, 100.0)
    assert cfg.accuracy_in_measurement_units("h2_concentration_pct") == 5.0
    v = make_view(cfg, seed=3)
    x = np.array([v._read_one("h2_concentration_pct", 2.0, float(t), {}) for t in range(0, 5000)])      # 2 %vol = 50 %LFL
    assert x.mean() == pytest.approx(50.0, abs=0.5)
    assert np.std(x) == pytest.approx(0.1 * 5.0 / math.sqrt(5), rel=0.1)
    big = make_view(cfg, seed=3)._read_one("h2_concentration_pct", 50.0, 0.0, {})                       # 50 %vol saturates the 0-100 %LFL detector
    assert big == 100.0


def test_h2_detector_response_is_a_first_order_lag():
    v = make_view(SensorViewConfig(h2_mode="lfl"), seed=4)
    v._read_one("h2_concentration_pct", 0.0, 0.0, {})
    r = [v._read_one("h2_concentration_pct", 2.0, float(t), {}) for t in range(1, 61)]           # step to 50 %LFL
    tau = PH.value("h2_detector_t90_s") / 2.3
    assert r[0] < 0.25 * 50 and r[-1] == pytest.approx(50.0, abs=1.5)
    t90 = next(i + 1 for i, x in enumerate(r) if x >= 0.9 * 50)
    assert 9 <= t90 <= 16                                                                         # reference: T90 of 10-15 s
    assert tau == pytest.approx(5.43, abs=0.05)


def test_h2_spec_mode_keeps_the_sec9_model():
    cfg = SensorViewConfig(h2_mode="spec")
    assert cfg.measurement_units()["h2_concentration_pct"] == "%vol" and cfg.accuracy_in_measurement_units("h2_concentration_pct") == 2.0


def test_vacuum_log_gauge_error_scales_with_reading_and_spec_mode_does_not():
    log, spec = SensorViewConfig(vacuum_mode="log_gauge"), SensorViewConfig(vacuum_mode="spec")
    assert log.accuracy_in_measurement_units("vacuum_pressure_pa", 1.0) == pytest.approx(0.2 * 1.0 + 0.05)
    assert log.accuracy_in_measurement_units("vacuum_pressure_pa", 100.0) == pytest.approx(20.05)
    assert spec.accuracy_in_measurement_units("vacuum_pressure_pa", 1.0) == spec.accuracy_in_measurement_units("vacuum_pressure_pa", 100.0) == 10.0
    lo, hi = log.measurement_ranges()["vacuum_pressure_pa"]
    assert (lo, hi) == (0.1, 1.0e5) and "vacuum_pressure_pa" in log.log_scale_channels() and not spec.log_scale_channels()
    v = make_view(log, seed=5)
    sd = lambda x: np.std([v._read_one("vacuum_pressure_pa", x, float(t) * 10.0, {}) for t in range(0, 4000)])
    assert sd(100.0) > 20 * sd(1.0)                                   # relative error
    assert make_view(spec, seed=5)._read_one("vacuum_pressure_pa", 0.5, 0.0, {}) >= 0.0


def test_level_dp_gauge_is_biased_by_density_and_ideal_is_not():
    import CoolProp.CoolProp as CP
    from hydrai_twin.eos import FLUID
    pref = PH.value("level_dp_reference_pressure_bar_a") * 1e5
    rf0, rg0 = CP.PropsSI("D", "P", pref, "Q", 0, FLUID), CP.PropsSI("D", "P", pref, "Q", 1, FLUID)
    p = 1.5e5
    rf, rg = CP.PropsSI("D", "P", p, "Q", 0, FLUID), CP.PropsSI("D", "P", p, "Q", 1, FLUID)
    dp = make_view(SensorViewConfig(level_mode="dp"), seed=6)
    ideal = make_view(SensorViewConfig(level_mode="ideal"), seed=6)
    x_dp = np.mean([dp._read_one("liquid_level_pct", 85.0, float(t), {"rho_f": rf, "rho_g": rg}) for t in range(2000)])
    x_id = np.mean([ideal._read_one("liquid_level_pct", 85.0, float(t), {"rho_f": rf, "rho_g": rg}) for t in range(2000)])
    assert x_id == pytest.approx(85.0, abs=0.05)
    assert x_dp == pytest.approx(85.0 * (rf - rg) / (rf0 - rg0), abs=0.05) and x_dp < x_id - 0.5      # denser-vapour, lighter-liquid at 1.5 bar reads low


def test_valve_states_are_off_by_default_and_appear_only_with_the_switch():
    off = make_view(SensorViewConfig()).read(0.0, {"pressure_bar_a": 1.2}, {"pcv_open": True})
    assert "pcv_state" not in off and "prv_state" not in off
    on = make_view(SensorViewConfig(valve_states=True)).read(0.0, {"pressure_bar_a": 1.2}, {"pcv_open": True, "prv_open": False})
    assert on["pcv_state"] == "open" and on["prv_state"] == "closed"
    r = generate_physical_episode(fault_id=0, seed=3, storage_days=2.0)
    assert "pcv_state" not in r.slow[0]["measurements"]
    r2 = generate_physical_episode(fault_id=0, seed=3, storage_days=2.0, sensor_view=SensorViewConfig(valve_states=True))
    assert set(r2.slow[0]["measurements"]) >= {"pcv_state", "prv_state"}


def test_view_off_reproduces_the_previous_per_record_measurement():
    a = generate_physical_episode(fault_id=0, seed=3, storage_days=2.0, sensor_view=SensorViewConfig(enabled=False))
    assert a.meta["sensor_view"]["enabled"] is False and a.meta["measurement_units"]["h2_concentration_pct"] == "%vol"
    h2 = [x["measurements"]["h2_concentration_pct"] for x in a.slow]
    assert max(h2) < 3.0                                            # %vol scale, not %LFL


def test_episode_records_periods_units_and_holds():
    r = generate_physical_episode(fault_id=0, seed=3, storage_days=2.0)
    assert r.meta["sensor_view"]["periods_s"]["outer_wall_temp_c"] == 5 and r.meta["measurement_units"]["h2_concentration_pct"] == "%LFL"
    ow = [x["measurements"]["outer_wall_temp_c"] for x in r.fast[:60]]
    runs = [ow[i:i + 5] for i in range(0, 55, 5)]
    assert all(len(set(rr)) == 1 for rr in runs)                    # 5 s tag shows 5 identical 1 s rows
    assert r.slow[0]["system_context"]["t_s"] == 0.0


def test_obs_sigma_follows_the_instrument_mode():
    fn = SensorViewConfig().obs_sigma_fn()
    assert fn("h2_concentration_pct", np.zeros(1)) == pytest.approx(0.5 * 5.0 * 4.0 / 100.0)      # 0.1 %vol
    assert fn("vacuum_pressure_pa", np.array([1.0, 10.0]))[1] > 5 * fn("vacuum_pressure_pa", np.array([1.0, 10.0]))[0]
    spec = SensorViewConfig(h2_mode="spec", vacuum_mode="spec").obs_sigma_fn()
    assert spec("h2_concentration_pct", np.zeros(1)) == 1.0 and spec("vacuum_pressure_pa", np.zeros(1)) == 5.0


def test_soft_vacuum_is_visible_under_the_log_gauge_and_not_under_the_spec_gauge():
    kw = dict(fault_id=3, seed=11, storage_days=6.0, onset_day_range=(1.5, 2.0), vacuum_target_dp_pa=13.33, ramp_duration_s=86400.0)
    log = generate_physical_episode(sensor_view=SensorViewConfig(vacuum_mode="log_gauge"), **kw).meta["per_channel_deviation_s"]["vacuum_pressure_pa"]
    spec = generate_physical_episode(sensor_view=SensorViewConfig(vacuum_mode="spec"), **kw).meta["per_channel_deviation_s"]["vacuum_pressure_pa"]
    assert log["k3"] is not None and log["k10"] is not None
    assert spec["k3"] is None                                       # 13 Pa step < 1.5 x the 10 Pa FS accuracy (conservative scale)
