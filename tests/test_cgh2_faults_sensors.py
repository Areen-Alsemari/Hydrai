import numpy as np
import pytest

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import make_class
from hydrai_twin.cgh2.dashboard import CGH2Dashboard
from hydrai_twin.cgh2.episode import CGH2EpisodeConfig, CGH2EpisodeGenerator, FAULT_LABELS, generate_cgh2_episode
from hydrai_twin.cgh2.profile import make_profile
from hydrai_twin.cgh2.sensor_view import (CGH2SensorView, CGH2ViewConfig, CONT, DISCRETE, PERIODS_S, accuracy, ou_drift_unit, obs_sigma_fn)
from hydrai_twin.channels import first_static_alarm_s
from hydrai_twin.sensors import SensorErrorSplit

DAY = 86400.0
CLS = make_class("medium")
KW = dict(seed=11, days=8.0, onset_day_range=(3.0, 4.0))


def gt(r, key, layer="slow"):
    return np.array([x["simulation_ground_truth"][key] for x in getattr(r, layer)])


def after(r, key, layer="slow"):
    t = np.array([x["system_context"]["t_s"] for x in getattr(r, layer)])
    return gt(r, key, layer)[t >= r.meta["onset_s"]]


# --- fault classes (register Sec. 6 names) ----------------------------------------------------------------------------------------

def test_class_ids_and_names():
    assert FAULT_LABELS == {0: "normal", 1: "sensor_fault", 2: "thermal_anomaly", 3: "small_slow_leak", 4: "abnormal_pressure_behaviour",
                            5: "containment_anomaly", 6: "structural_concern", -1: "unknown_anomaly"}


def test_small_slow_leak_loses_mass_at_the_choked_rate_and_is_labelled_not_observable_on_flows():
    r = generate_cgh2_episode(fault_id=3, leak_diameter_mm=0.5, leak_cd=1.0, **KW)
    m = r.meta
    expected = G.leak_mass_rate_kg_s(0.5, 280.0, 300.0) * 3600 * (m["duration_s"] - m["onset_s"]) / 3600
    assert 0.5 * expected < m["leaked_kg"] < 1.5 * expected
    assert abs(m["mass_residual_kg"]) < 1e-6 and m["first_observable_s"] is not None and m["first_observable_s"] >= m["onset_s"]
    assert m["scenario"] == "small_slow_leak" and m["expected_miss"] is False


def test_stress_leak_set_carries_the_expected_miss_label():
    r = generate_cgh2_episode(fault_id=3, leak_diameter_mm=0.03, expected_miss=True, **KW)
    assert r.meta["expected_miss"] is True and r.slow[0]["system_context"]["expected_miss"] is True
    assert r.meta["leaked_kg"] < 5.0                                           # 0.03 mm: ~0.05 kg/h


def test_compressor_overrun_reaches_the_relief_valve_which_holds_the_pressure():
    r = generate_cgh2_episode(fault_id=4, pressure_variant="compressor_overrun", **KW)
    P = after(r, "pressure_bar_a")
    assert r.meta["prv_lift_events"] >= 1 and CLS.pahh_bar < P.max() <= 1.12 * CLS.mawp_bar
    assert r.meta["vented_prv_kg"] > 0 and r.meta["ended_reason"] is None


def test_blocked_relief_fails_the_vessel():
    r = generate_cgh2_episode(fault_id=4, pressure_variant="blocked_relief", **KW)
    assert r.meta["prv_lift_events"] == 0 and "overpressure failure" in r.meta["ended_reason"]
    assert gt(r, "pressure_bar_a").max() > 1.4 * CLS.mawp_bar


def test_fire_exposure_heats_the_shell_and_lifts_the_relief_valve_at_the_fire_accumulation():
    r = generate_cgh2_episode(fault_id=4, pressure_variant="fire", **KW)
    assert after(r, "outer_wall_temp_c").max() > 150.0 and r.meta["prv_lift_events"] >= 1
    assert after(r, "pressure_bar_a").max() < 1.25 * CLS.mawp_bar              # relieved at the 121 % fire accumulation, not left to fail
    assert first_static_alarm_s(r.slow, CGH2Dashboard.reference("medium"))["any"] is not None


def test_discharge_valve_stuck_open_is_a_continuous_draw_visible_on_the_flow_meter_only():
    r = generate_cgh2_episode(fault_id=4, pressure_variant="stuck_open", **KW)
    pc = r.meta["per_channel_deviation_s"]
    assert pc["mass_flow_discharge_kg_s"]["k3"] is not None and r.meta["dispensed_kg"] > 30
    assert first_static_alarm_s(r.slow, CGH2Dashboard.reference("medium"))["any"] is None           # no alarm defined on the flow meter


def test_containment_leak_is_picked_up_by_the_hydrogen_detector_and_a_rupture_is_a_dense_blowdown():
    r = generate_cgh2_episode(fault_id=5, containment_variant="leak", leak_diameter_mm=3.0, **KW)
    assert after(r, "h2_concentration_pct").max() * 25 > R.value("h2_alarm_lfl")                      # in %LFL
    assert first_static_alarm_s(r.slow, CGH2Dashboard.reference("medium"))["by_channel"]["h2_concentration_pct"] is not None
    rp = generate_cgh2_episode(fault_id=5, containment_variant="rupture", rupture_diameter_mm=50.0, **KW)
    m = rp.meta
    assert (m["duration_s"] - m["onset_s"]) < 600 and "emptied" in m["ended_reason"]
    assert m["first_observable_s"] is not None and m["first_observable_s"] - m["onset_s"] < 60           # fast fallback: the 60 s grid has no post-onset samples
    on = m["onset_s"]
    dense = [x for x in rp.fast if x["system_context"]["t_s"] >= on]
    assert len(dense) > 20 and gt(rp, "pressure_bar_a", "fast")[-1] < 3.0           # a 50 mm rupture is over in under a minute: all of it on the 1 s layer


def test_thermal_anomaly_variants_heat_the_gas_or_the_shell():
    ic = generate_cgh2_episode(fault_id=2, thermal_variant="intercooler", ramp_duration_s=3600.0, **KW)
    ext = generate_cgh2_episode(fault_id=2, thermal_variant="external_heat", ramp_duration_s=3600.0, **KW)
    base = generate_cgh2_episode(fault_id=0, seed=11, days=8.0, onset_day_range=(3.0, 4.0))
    assert gt(ic, "ic_dT_k").max() > 40.0 and gt(ext, "q_wall_gas_w").max() > gt(base, "q_wall_gas_w").max()
    assert after(ext, "outer_wall_temp_c").max() > gt(base, "outer_wall_temp_c").max() + 5.0


def test_structural_concern_grows_the_stress_concentration_with_the_pressure_cycle_count():
    r = generate_cgh2_episode(fault_id=6, seed=11, days=14.0, onset_day_range=(1.0, 1.5))
    scf = gt(r, "strain_scf")
    assert scf.max() > 2.0 and scf[0] == 1.0 and np.all(np.diff(scf) >= -1e-12)          # monotone growth, driven by compressor cycles
    assert r.meta["per_channel_deviation_s"]["strain_ue"]["k3"] is not None


def test_sensor_fault_first_observable_is_after_onset_and_on_the_gas_temperature_probe():
    r = generate_cgh2_episode(fault_id=1, **KW)
    pc = r.meta["per_channel_deviation_s"]
    assert pc["gas_temp_c"]["k3"] is not None and pc["gas_temp_c"]["k3"] >= r.meta["onset_s"]


def test_onset_and_observable_labels_are_separate_and_ordered():
    r = generate_cgh2_episode(fault_id=3, leak_diameter_mm=0.1, leak_cd=1.0, **KW)
    m = r.meta
    assert m["first_observable_s"] > m["onset_s"] and m["onset_to_first_observable_s"] == pytest.approx(m["first_observable_s"] - m["onset_s"])
    for rec in r.slow[::50]:
        t = rec["system_context"]["t_s"]
        assert rec["labels"]["ai_label"] == (3 if t >= m["onset_s"] else 0) and rec["labels"]["ai_label_observable"] == (3 if t >= m["first_observable_s"] else 0)
    assert any(x["labels"]["ai_label"] == 3 and x["labels"]["ai_label_observable"] == 0 for x in r.slow)


def test_composite_records_its_causes():
    r = generate_cgh2_episode(fault_id=-1, unknown_sub_fault_ids=(2, 3), **KW)
    assert r.meta["unknown_sub_faults"] == [2, 3] and r.meta["leaked_kg"] > 0 and gt(r, "ic_dT_k").max() > 5.0


# --- sensors ------------------------------------------------------------------------------------------------------------------

def make_view(cfg=None, seed=0):
    t = np.arange(0.0, 86400.0, 1.0)
    split = SensorErrorSplit(0.5, 0.3, 0.1, 3 * 86400.0)
    zeros = {k: np.zeros(len(t)) for k in CONT}
    return CGH2SensorView(cfg or CGH2ViewConfig(), split, 400.0, {k: 0.0 for k in CONT}, zeros, t, np.random.default_rng(seed),
                          {"fill": 5.0, "discharge": 5.0}, np.random.default_rng(seed + 1))


def test_periods_and_aggregation_match_the_reference_rates():
    assert PERIODS_S["outer_wall_temp_c"] == 5.0 and PERIODS_S["ambient_temp_c"] == 10.0 and PERIODS_S["h2_concentration_pct"] == pytest.approx(0.2)
    v = make_view()
    vals = [v._read_one("outer_wall_temp_c", 30.0, float(t), {}) for t in range(0, 31)]
    assert all(len(set(vals[k:k + 5])) == 1 for k in range(0, 30, 5)) and len(set(vals)) > 1                 # 5 s tag holds 5 rows
    x = np.array([make_view(seed=2)._read_one("strain_ue", 0.0, 1.0, {}) for _ in range(1)])
    v2 = make_view(seed=3)
    sd = np.std([v2._read_one("strain_ue", 0.0, float(t), {}) for t in range(0, 20000)])
    assert sd == pytest.approx(0.1 * accuracy("strain_ue", CGH2ViewConfig(), 400.0) / np.sqrt(10), rel=0.06)   # 0.1 s channel: mean of 10 samples


def test_flow_meter_error_datasheet_mode_is_half_percent_of_reading_plus_zero_stability_and_spec_mode_is_1_percent_fs():
    c, s = CGH2ViewConfig(), CGH2ViewConfig(flow_mode="spec")
    zero = 0.009 / 60.0
    assert accuracy("mass_flow_discharge_kg_s", c, 400.0, 0.0) == pytest.approx(zero)
    assert accuracy("mass_flow_discharge_kg_s", c, 400.0, 0.05) == pytest.approx(0.005 * 0.05 + zero)
    assert accuracy("mass_flow_discharge_kg_s", s, 400.0) == pytest.approx(0.01 * 4.0 / 60.0)             # 1 % FS of 4 kg/min = 2.4 kg/h
    assert accuracy("mass_flow_discharge_kg_s", s, 400.0) * 3600 == pytest.approx(2.4)
    assert accuracy("pressure_bar_a", c, 400.0) == pytest.approx(1.0) and accuracy("gas_temp_c", c, 400.0) == 0.5 and accuracy("ambient_temp_c", c, 400.0) == 0.3


def test_coriolis_meter_delay_is_a_first_order_lag_in_the_two_to_nine_second_range():
    v = make_view()
    v.lagged_flow("mass_flow_fill_kg_s", 0.0, 0.0)
    y = [v.lagged_flow("mass_flow_fill_kg_s", 0.01, float(t)) for t in range(1, 40)]
    assert y[0] < 0.25 * 0.01 and y[-1] == pytest.approx(0.01, rel=0.01)
    prof = [make_profile(f"M0{i}", 20260401) for i in range(1, 7)]
    assert all(2.0 <= p.meter_delay_fill_s <= 9.0 and 2.0 <= p.meter_delay_discharge_s <= 9.0 for p in prof) and len({p.meter_delay_fill_s for p in prof}) > 3


def test_hydrogen_detector_default_is_the_realistic_lfl_model_and_spec_mode_is_behind_a_switch():
    c = CGH2ViewConfig()
    assert c.h2_mode == "lfl" and c.units()["h2_concentration_pct"] == "%LFL" and accuracy("h2_concentration_pct", c, 400.0) == 5.0
    s = CGH2ViewConfig(h2_mode="spec")
    assert s.units()["h2_concentration_pct"] == "%vol" and accuracy("h2_concentration_pct", s, 400.0) == 2.0
    d = CGH2Dashboard.reference("medium")
    lim = {a.name: a.limit for a in d.alarms_for("h2_concentration_pct")}
    assert lim == {"AAH": 25.0, "AAHH": 50.0}
    sp = {a.name: a.limit for a in CGH2Dashboard.reference("medium", h2_mode="spec").alarms_for("h2_concentration_pct")}
    assert sp == pytest.approx({"AAH": 1.0, "AAHH": 2.0})                                                # 25 / 50 %LFL = 1 / 2 %vol


def test_gas_temperature_reading_carries_the_bulk_gradient_term():
    v = make_view(seed=5)
    hold = np.std([v._read_one("gas_temp_c", 20.0, float(t * 600), {"gradient_k": 0.0}) for t in range(120)])
    assert hold > 0.7                                                                                   # ~1 K of slow bulk gradient on top of the 0.25 C noise
    assert v._read_one("gas_temp_c", 20.0, 90000.0, {"gradient_k": 8.0}) > 25.0                         # +8 K right after a charge
    off = make_view(CGH2ViewConfig(gradient=False), seed=5)
    assert np.std([off._read_one("gas_temp_c", 20.0, float(t * 600), {}) for t in range(120)]) < 0.4


def test_valve_states_and_compressor_status_default_on_with_an_ablation_off():
    r = generate_cgh2_episode(fault_id=0, seed=3, days=2.0)
    assert set(DISCRETE) <= set(r.slow[0]["measurements"]) and r.slow[0]["measurements"]["compressor_status"] in ("run", "stop")
    off = generate_cgh2_episode(fault_id=0, seed=3, days=2.0, sensor_view=CGH2ViewConfig(valve_states=False))
    assert not set(DISCRETE) & set(off.slow[0]["measurements"])
    assert CGH2Dashboard.reference("medium", valve_states=False).mask().isdisjoint(DISCRETE)
    assert set(DISCRETE) <= CGH2Dashboard.reference("medium").mask()


def test_dashboard_drops_the_lh2_channels_and_labels_the_reference_configuration():
    d = CGH2Dashboard.reference("medium")
    ch = set(d.tag_names())
    assert not ch & {"liquid_level_pct", "vacuum_pressure_pa", "liquid_temp_c", "inner_wall_temp_c"}
    assert ch == set(CONT) and d.status == "REFERENCE - not a verified Saudi system"
    assert d.tag_names()["pressure_bar_a"] == "GH2-PT-101" and d.tag_for("pressure_bar_a").range == (0.0, 400.0)
    assert {"strain_ue", "mass_flow_fill_kg_s", "outer_wall_temp_c", "compressor_status"} <= set(d.channels_without_alarm())
    assert "PROVISIONAL" in d.to_dict()["provisional"]
    assert CGH2Dashboard.reference("high").tag_for("pressure_bar_a").range == (0.0, 500.0) and CGH2Dashboard.reference("low").alarms[0].limit == pytest.approx(51.0)


def test_observability_sigma_includes_the_gradient_and_the_meter_zero_stability():
    fn = obs_sigma_fn(CGH2ViewConfig(), 400.0)
    assert fn("gas_temp_c", np.zeros(1)) == pytest.approx(np.hypot(0.25, 1.0))
    assert fn("pressure_bar_a", np.zeros(1)) == pytest.approx(0.5)
    assert fn("mass_flow_fill_kg_s", np.array([0.0])) > 0
