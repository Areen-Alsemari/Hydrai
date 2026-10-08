import json
from pathlib import Path

import numpy as np
import pytest

from hydrai_twin import constants as C
from hydrai_twin.channels import (ALL_CHANNELS, LFL_PER_VOL, MEASURED_CHANNELS, PROVISIONAL_NOTE, REFERENCE_LABEL, VALVE_STATE_CHANNELS,
                                  AlarmLimit, ChannelMask, DashboardConfig, first_static_alarm_s, static_alarm_flags)

ROOT = Path(__file__).resolve().parent.parent


def _row(t, **meas):
    return {"system_context": {"t_s": float(t)}, "measurements": dict(meas)}


def test_mask_rejects_unknown_and_defaults_exclude_valve_states():
    with pytest.raises(ValueError):
        ChannelMask.of(["pressure_bar_a", "not_a_tag"])
    m = ChannelMask.all_measured()
    assert m.enabled == set(MEASURED_CHANNELS)
    assert not set(VALVE_STATE_CHANNELS) & m.enabled          # often not on a historian side channel (Q5): off unless switched on


def test_mask_filters_measurements_and_strips_evaluation_data():
    rec = {"measurements": {"pressure_bar_a": 1.2, "liquid_temp_c": -251.0}, "measurement_quality": {"pressure_bar_a": "Good", "liquid_temp_c": "Good"},
           "simulation_ground_truth": {"x": 1}, "labels": {"fault_id": 0}, "measurements_live": {"pressure_bar_a": 1.2}, "data_faults": {"pressure_bar_a": "none"}}
    out = ChannelMask.of(["pressure_bar_a"]).apply_to_record(rec)
    assert out["measurements"] == {"pressure_bar_a": 1.2} and out["measurement_quality"] == {"pressure_bar_a": "Good"}
    assert not {"simulation_ground_truth", "labels", "measurements_live", "data_faults"} & set(out)
    assert "liquid_temp_c" in rec["measurements"]            # input untouched


def test_parquet_columns_exclude_ground_truth_labels_live_and_fault_labels():
    avail = ["episode_id", "timestamp", "ctx__t_s", "ctx__scenario", "meas__pressure_bar_a", "meas__liquid_temp_c", "q__pressure_bar_a",
             "gt__pressure_bar_a", "label__fault_id", "label__has_data_fault", "live__pressure_bar_a", "dfault__pressure_bar_a"]
    cols = ChannelMask.of(["pressure_bar_a"]).parquet_columns(avail)
    assert set(cols) == {"episode_id", "timestamp", "ctx__t_s", "meas__pressure_bar_a", "q__pressure_bar_a"}


def test_reference_dashboard_is_labeled_and_carries_tags_units_ranges_and_periods():
    d = DashboardConfig.reference()
    assert d.status == "REFERENCE - not a verified Saudi system"
    assert REFERENCE_LABEL == "reference configuration, not a verified Saudi system"
    assert d.level == "reference"
    names = d.tag_names()
    assert names["pressure_bar_a"] == "LH2-PT-101" and names["h2_concentration_pct"] == "LH2-AT-101" and names["vacuum_pressure_pa"] == "LH2-PT-201"
    assert d.periods_s() == {"pressure_bar_a": 1, "liquid_temp_c": 1, "outer_wall_temp_c": 5, "h2_concentration_pct": 0.2, "liquid_level_pct": 1,
                             "mass_flow_fill_kg_s": 0.1, "mass_flow_discharge_kg_s": 0.1, "strain_ue": 0.1, "vacuum_pressure_pa": 10, "ambient_temp_c": 10}
    assert d.tag_for("pressure_bar_a").range == (0, 6) and d.tag_for("h2_concentration_pct").unit == "%LFL"
    assert d.tag_for("liquid_level_pct").technique == "DP gauge"
    assert "inner_wall_temp_c" not in d.mask().enabled        # no inner-wall tag on the reference dashboard
    assert d.historian_defaults["compression_forced_point_s"] == 28800 and d.alarm_load["agent_target"].startswith("no more than about 1")


def test_liquid_temperature_stays_in_degC_the_spec_wins_over_the_K_in_the_reference_file():
    raw = json.loads((ROOT / "dashboard_tags.json").read_text())
    assert [t for t in raw["tags"] if t["tag"] == "LH2-TT-101"][0]["unit"] == "K"
    assert DashboardConfig.reference().tag_for("liquid_temp_c").unit == "C"


def test_alarms_are_spec_simulation_thresholds_plus_the_unverified_h2_levels():
    d = DashboardConfig.reference()
    by = {(a.channel, a.name): a for a in d.alarms}
    assert by[("pressure_bar_a", "PAH")].limit == C.PRESSURE_HIGH_WARNING_BAR and by[("pressure_bar_a", "PAHH")].limit == C.PRESSURE_CRITICAL_BAR
    assert by[("pressure_bar_a", "PAL")].limit == C.PRESSURE_LOW_WARNING_BAR
    assert by[("h2_concentration_pct", "AAH")].limit == 20 and by[("h2_concentration_pct", "AAHH")].limit == 40
    assert "UNVERIFIED" in by[("h2_concentration_pct", "AAH")].basis
    assert by[("pressure_bar_a", "PAH")].basis == "simulation threshold"
    assert not d.alarms_for("inner_wall_temp_c")              # no tag, no alarm
    assert "PROVISIONAL" in PROVISIONAL_NOTE


def test_h2_mode_conversion_is_exact_and_idempotent():
    d = DashboardConfig.reference()
    spec = d.with_h2_mode("spec")
    assert spec.tag_for("h2_concentration_pct").unit == "%vol"
    lim = {a.name: a.limit for a in spec.alarms_for("h2_concentration_pct")}
    assert lim == pytest.approx({"AAH": 0.8, "AAHH": 1.6})   # 100 %LFL = 4 %vol
    assert spec.with_h2_mode("spec") is spec
    back = spec.with_h2_mode("lfl")
    assert {a.name: a.limit for a in back.alarms_for("h2_concentration_pct")} == pytest.approx({"AAH": 20, "AAHH": 40})
    assert LFL_PER_VOL == 25.0


def test_json_roundtrip_and_example_file_loads(tmp_path):
    d = DashboardConfig.reference()
    p = tmp_path / "d.json"
    p.write_text(json.dumps(d.to_dict()))
    d2 = DashboardConfig.from_json(p)
    assert d2.to_dict() == d.to_dict()
    ex = DashboardConfig.from_json(ROOT / "dashboard_tags.example.json")
    assert ex.mask().enabled == {"pressure_bar_a", "liquid_temp_c", "liquid_level_pct", "vacuum_pressure_pa"}
    assert ex.level == "user_supplied" and ex.tags[3].period_s == 600


def test_valve_states_are_off_unless_switched_on():
    assert set(VALVE_STATE_CHANNELS).isdisjoint(DashboardConfig.reference().mask(valve_states=False).enabled)
    assert set(VALVE_STATE_CHANNELS) <= DashboardConfig.reference().mask(valve_states=True).enabled


def test_config_rejects_bad_channels_and_alarms_without_tags():
    with pytest.raises(ValueError):
        DashboardConfig.from_dict({"tags": [{"name": "x", "channel": "nope"}]})
    with pytest.raises(ValueError):
        DashboardConfig.from_dict({"tags": [{"name": "p", "channel": "pressure_bar_a"}],
                                   "alarms": [{"channel": "liquid_temp_c", "direction": "high", "limit": -248}]})


def test_static_alarm_first_time_levels_and_on_delay():
    d = DashboardConfig([], [AlarmLimit("pressure_bar_a", "high", 2.0, "warning", on_delay_samples=2),
                             AlarmLimit("pressure_bar_a", "high", 3.0, "critical")], "user_supplied")
    rows = [_row(0, pressure_bar_a=1.2), _row(60, pressure_bar_a=2.5), _row(120, pressure_bar_a=1.2),
            _row(180, pressure_bar_a=2.5), _row(240, pressure_bar_a=3.5), _row(300, pressure_bar_a=3.5)]
    assert first_static_alarm_s(rows, d, "warning")["any"] == 240.0
    assert first_static_alarm_s(rows, d, "critical")["any"] == 240.0
    assert first_static_alarm_s(rows, d)["by_channel"] == {"pressure_bar_a": 240.0}
    assert static_alarm_flags(rows, d, "warning") == [False, False, False, False, True, True]


def test_static_alarms_act_on_the_live_value_not_the_historian_copy():
    d = DashboardConfig([], [AlarmLimit("pressure_bar_a", "high", 2.0, "warning")], "user_supplied")
    r = {"system_context": {"t_s": 0.0}, "measurements": {"pressure_bar_a": 1.2}, "measurements_live": {"pressure_bar_a": 2.5}}
    assert first_static_alarm_s([r], d)["any"] == 0.0                     # live value breaches; the historian copy was filtered
    assert first_static_alarm_s([r], d, source="measurements")["any"] is None


def test_low_limit_and_missing_samples():
    d = DashboardConfig([], [AlarmLimit("pressure_bar_a", "low", 0.8, "warning")], "user_supplied")
    assert first_static_alarm_s([_row(0, pressure_bar_a=None), _row(60, pressure_bar_a=0.5)], d)["any"] == 60.0
    assert first_static_alarm_s([_row(0, pressure_bar_a=None)], d)["any"] is None


@pytest.mark.parametrize("boiloff", ["target", "baseline"])
@pytest.mark.parametrize("fill", [0.85, 0.90])
def test_healthy_runs_at_spec_nominal_and_max_fill_do_not_alarm(fill, boiloff):
    """Item 7a: healthy fill follows the spec (85 % nominal, 90 % max); a healthy tank there must neither alarm nor lift the PRV."""
    from hydrai_twin.module_profile import make_profile
    from hydrai_twin.physical_episode import generate_physical_episode
    d = DashboardConfig.reference()
    for mod in ("M01", "M04"):
        prof = make_profile(mod, 20260301)
        r = generate_physical_episode(fault_id=0, seed=21, module_id=mod, profile=prof, storage_days=14.0,
                                      fill_target_frac=fill, boiloff_mode=boiloff)
        assert r.meta["scenario_class"] == "standard"
        assert first_static_alarm_s(r.slow, d)["any"] is None, (mod, first_static_alarm_s(r.slow, d)["by_channel"])
        assert r.meta["prv_lift_events"] == 0 and r.meta["liquid_full_events"] == 0 and r.meta["ended_reason"] is None
        assert max(x["simulation_ground_truth"]["pressure_bar_a"] for x in r.slow) <= 1.5 + prof.pcv_setpoint_offset_bar + 2e-3   # PCV setpoint is per-unit


def test_realistic_h2_detector_has_no_false_alarms_across_units():
    """Many healthy units through the real instrument view: the 20 %LFL H alarm never fires (worst error << 20 %LFL)."""
    from hydrai_twin.sensor_view import SensorView, SensorViewConfig
    from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs, drift_series
    split = SensorErrorSplit(0.5, 0.3, 0.1, 3 * 86400.0)
    t = np.arange(0.0, 3 * 86400.0, 60.0)
    worst = 0.0
    for u in range(40):
        rng = np.random.default_rng(u)
        tag = "h2_concentration_pct"
        drift = {k: np.zeros(len(t)) for k in C.SENSOR_SPECS}
        drift[tag] = drift_series(tag, t, rng, split) / accuracy_abs(tag)
        view = SensorView(SensorViewConfig(), split, {k: 0.0 for k in C.SENSOR_SPECS} | {tag: rng.uniform(-1, 1)}, drift, t, rng)
        vals = [view._read_one(tag, abs(rng.normal(0, 0.02)), float(ti), {}) for ti in t]
        worst = max(worst, max(vals))
    assert worst < 10.0 < 20.0                                  # %LFL; the H alarm is 20


def test_registry_h2_alarm_levels_match_the_dashboard_file():
    from hydrai_twin import placeholders as PH
    lim = {a.name: a.limit for a in DashboardConfig.reference().alarms_for("h2_concentration_pct")}
    assert lim["AAH"] == PH.value("h2_alarm_h_lfl") and lim["AAHH"] == PH.value("h2_alarm_hh_lfl")
    assert PH.REGISTRY["h2_alarm_h_lfl"].level == "placeholder" and "UNVERIFIED" in PH.REGISTRY["h2_alarm_h_lfl"].basis
