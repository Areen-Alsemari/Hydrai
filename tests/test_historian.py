import numpy as np
import pytest

from hydrai_twin.historian import (FAULT_TYPES, NO_FAULT, QUALITY_OF_FAULT, HistorianConfig, TagInfo, apply_historian, exception_filter,
                                   fault_windows, swinging_door)

TAGS = {"pressure_bar_a": TagInfo("pressure_bar_a", 0.0, 6.0), "vacuum_pressure_pa": TagInfo("vacuum_pressure_pa", 0.1, 1e5, log=True)}
DAY = 86400.0


def recs(n=3000, dt=60.0, fn=None, vac=1.0):
    out = []
    for i in range(n):
        p = fn(i * dt) if fn else 1.2 + 0.0005 * np.sin(i / 40.0)
        out.append({"episode_id": "E", "timestamp": str(i), "system_context": {"t_s": i * dt},
                    "measurements": {"pressure_bar_a": float(p), "vacuum_pressure_pa": vac, "inner_wall_temp_c": -250.0},
                    "simulation_ground_truth": {"x": 1}, "labels": {"fault_id": 0, "ai_label": 0, "ai_label_observable": 0}})
    return out


def quiet(**kw):
    return HistorianConfig(inject_faults=False, **kw)


def test_off_is_the_ideal_data_identity():
    r = recs(50)
    out, stats = apply_historian(r, HistorianConfig(enabled=False), 1, TAGS, 3000 * 60.0)
    assert out is r and stats == {}


def test_input_is_not_modified_and_layers_are_added():
    r = recs(500)
    import copy
    before = copy.deepcopy(r)
    out, _ = apply_historian(r, HistorianConfig(), 1, TAGS, 500 * 60.0)
    assert r == before
    x = out[10]
    assert set(x["measurement_quality"]) == set(TAGS) and set(x["data_faults"]) == set(TAGS) and "has_data_fault" in x["labels"]
    assert x["measurements_live"]["pressure_bar_a"] == before[10]["measurements"]["pressure_bar_a"]
    assert x["measurements"]["inner_wall_temp_c"] == -250.0           # a channel with no tag passes through untouched
    assert x["labels"]["ai_label"] == 0 and x["labels"]["ai_label_observable"] == 0     # physical labels never touched


def test_exception_filter_passes_only_moves_beyond_the_deadband_or_forced_points():
    t = np.arange(0, 3000.0, 10.0)
    x = np.zeros(len(t))
    x[100:] = 1.0                                                     # a step
    idx = exception_filter(t, x, np.ones(len(t), bool), deadband=0.5, forced_s=600.0)
    assert 0 in idx and 100 in idx                                    # first value and the step pass
    assert all(t[b] - t[a] <= 600.0 + 1e-9 for a, b in zip(idx, idx[1:]))      # a forced point at least every 600 s
    assert len(idx) < len(t) / 5


def test_swinging_door_keeps_corners_drops_straight_lines_and_forces_points():
    t = np.arange(0, 20 * 3600.0, 60.0)
    x = np.where(t < 10 * 3600.0, 0.001 * t, 36.0 + 0.0 * t)          # a ramp then a flat top: one corner
    keep = swinging_door(t, x, dev=0.5, forced_s=1e9)
    assert len(keep) <= 5 and keep[0] == 0 and keep[-1] == len(t) - 1
    flat = swinging_door(t, np.zeros(len(t)), dev=0.5, forced_s=8 * 3600.0)
    assert len(flat) == len(np.unique(np.r_[0, np.arange(len(t))[t % (8 * 3600.0) == 0][1:], len(t) - 1]))     # forced every 8 h
    assert all(t[b] - t[a] <= 8 * 3600.0 + 60.0 for a, b in zip(flat, flat[1:]))
    # PI-style: the archived point is the last RAW point before the door closes, so the reconstruction can overshoot the
    # compression deviation at a corner (here 0.94 for dev 0.5); it stays within about twice it.
    k = swinging_door(t, x, dev=0.5, forced_s=1e9)
    assert np.max(np.abs(np.interp(t, t[k], x[k]) - x)) <= 2 * 0.5 + 1e-9


def test_compression_reduces_points_and_reconstruction_stays_within_two_deadbands():
    r = recs(4000)
    out, stats = apply_historian(r, quiet(), 1, TAGS, 4000 * 60.0)
    s = stats["pressure_bar_a"]
    assert s["n_archived"] < 0.1 * s["n_valid"] and s["compression_ratio"] > 10
    db = 0.1 / 100.0 * 6.0
    err = max(abs(a["measurements"]["pressure_bar_a"] - b["measurements"]["pressure_bar_a"]) for a, b in zip(out, r))
    assert err <= 5 * db + 1e-9                                       # exception (1x) + compression (up to ~2 x 2x) deviations


def test_compression_can_be_switched_off():
    out, stats = apply_historian(recs(1000), quiet(compression=False), 1, TAGS, 6e4)
    assert stats["pressure_bar_a"]["n_archived"] == stats["pressure_bar_a"]["n_exception_passed"]


def test_log_channel_is_filtered_in_log_space():
    r = recs(2000, vac=0.5)
    for i, x in enumerate(r):
        x["measurements"]["vacuum_pressure_pa"] = 0.5 if i < 1000 else 5.0          # a decade jump of a sub-Pa reading
    out, _ = apply_historian(r, quiet(), 1, TAGS, 2000 * 60.0)
    vals = np.array([o["measurements"]["vacuum_pressure_pa"] for o in out])
    assert vals[:990].max() == pytest.approx(0.5, rel=0.1) and vals[1010:].min() > 4.0     # a linear 0.5 % of 1e5 Pa deadband would erase this


def test_injected_faults_are_labeled_quality_coded_and_reproducible():
    cfg = HistorianConfig(fault_rates={"dropout": (6.0, 300.0), "stale_value": (6.0, 900.0), "flat_line": (3.0, 3600.0), "out_of_range": (3.0, 300.0)})
    r = recs(20000)
    a, st = apply_historian(r, cfg, 7, TAGS, 20000 * 60.0)
    b, _ = apply_historian(r, cfg, 7, TAGS, 20000 * 60.0)
    c, _ = apply_historian(r, cfg, 8, TAGS, 20000 * 60.0)
    assert a == b and a != c
    seen = set()
    for x in a:
        for tag, ft in x["data_faults"].items():
            q = x["measurement_quality"][tag]
            if ft == NO_FAULT:
                assert q == "Good"
            else:
                seen.add(ft)
                assert q == QUALITY_OF_FAULT[ft]
                if ft == "dropout":
                    assert x["measurements"][tag] is None
        assert x["labels"]["has_data_fault"] == any(f != NO_FAULT for f in x["data_faults"].values())
    assert seen == set(FAULT_TYPES)
    assert QUALITY_OF_FAULT == {"dropout": "Bad", "stale_value": "Uncertain", "flat_line": "Good", "out_of_range": "Uncertain"}
    assert sum(st["pressure_bar_a"]["fault_samples"].values()) > 0


def test_faults_are_not_physical_anomalies():
    r = recs(20000)
    out, _ = apply_historian(r, HistorianConfig(), 3, TAGS, 20000 * 60.0)
    assert any(o["labels"]["has_data_fault"] for o in out)
    assert all(o["labels"]["ai_label"] == 0 and o["labels"]["fault_id"] == 0 and o["labels"]["ai_label_observable"] == 0 for o in out)
    assert all(o["simulation_ground_truth"] == {"x": 1} for o in out)


def test_fault_windows_are_the_same_for_both_layers_and_low_rate():
    w = fault_windows(5, "pressure_bar_a", 14 * DAY, HistorianConfig())
    assert w == fault_windows(5, "pressure_bar_a", 14 * DAY, HistorianConfig())
    assert 0 < len(w) < 40                                            # about 0.4 events/day/tag over 14 d
    assert all(0 <= a < b <= 14 * DAY for a, b, _ in w)
    assert fault_windows(5, "pressure_bar_a", 14 * DAY, HistorianConfig(inject_faults=False)) == []


def test_flat_line_keeps_quality_good_while_stale_is_uncertain():
    cfg = HistorianConfig(fault_rates={"dropout": (0, 1), "stale_value": (0, 1), "flat_line": (20.0, 3600.0), "out_of_range": (0, 1)}, compression=False)
    out, _ = apply_historian(recs(5000, fn=lambda t: 1.2 + 0.0004 * t / 60), cfg, 2, TAGS, 5000 * 60.0)
    flat = [o for o in out if o["data_faults"]["pressure_bar_a"] == "flat_line"]
    assert flat and all(o["measurement_quality"]["pressure_bar_a"] == "Good" for o in flat)      # silent: no quality warning
    vals = [o["measurements_live"]["pressure_bar_a"] for o in flat]
    assert max(vals) > min(vals)                                       # the live value kept moving; the historian copy is stuck


def test_static_alarms_are_unaffected_by_the_historian_layer():
    from hydrai_twin.channels import AlarmLimit, DashboardConfig, first_static_alarm_s
    r = recs(300, fn=lambda t: 1.2 if t < 6000 else 2.5)
    out, _ = apply_historian(r, HistorianConfig(), 1, TAGS, 300 * 60.0)
    d = DashboardConfig([], [AlarmLimit("pressure_bar_a", "high", 2.0, "warning")], "user_supplied")
    assert first_static_alarm_s(out, d)["any"] == first_static_alarm_s(r, d)["any"] == 6000.0      # live value, whatever the historian stored


def test_fault_windows_have_a_minimum_length_so_the_slow_layer_sees_every_event():
    from hydrai_twin.historian import MIN_WINDOW_S
    cfg = HistorianConfig(fault_rates={"dropout": (200.0, 5.0), "stale_value": (0, 1), "flat_line": (0, 1), "out_of_range": (200.0, 5.0)})
    w = fault_windows(3, "pressure_bar_a", 5 * DAY, cfg)
    assert MIN_WINDOW_S == 60.0 and w and all(b - a >= MIN_WINDOW_S - 1e-9 for a, b, _ in w[:-1] + [x for x in w[-1:] if x[1] < 5 * DAY])


def test_run_starts_ignore_burst_boundaries_and_layers_agree_on_rates():
    """Slow (60 s, whole timeline) and fast (1 s, bursts only) layers must give the same fault run-start rate per channel-day,
    even though one long window is cut into many pieces by the bursts."""
    cfg = HistorianConfig(fault_rates={"dropout": (30.0, 120.0), "stale_value": (30.0, 200.0), "flat_line": (10.0, 600.0), "out_of_range": (10.0, 100.0)},
                          compression=False)
    horizon = 10 * DAY
    slow = recs(int(horizon / 60), 60.0)
    fast = []
    for k in range(400):                                   # 400 bursts of 600 s spread over the 10 days
        t0 = k * horizon / 400
        for j in range(600):
            r = recs(1, 1.0)[0]
            r["system_context"] = {"t_s": t0 + j}
            fast.append(r)
    _, ss = apply_historian(slow, cfg, 5, TAGS, horizon, 60.0)
    _, sf = apply_historian(fast, cfg, 5, TAGS, horizon, 1.0)
    def rate(st):
        runs = sum(sum(v["fault_run_starts"].values()) for v in st.values())
        days = sum(v["exposure_channel_days"] for v in st.values())
        return runs / days
    rs, rf = rate(ss), rate(sf)
    assert 0.8 < rf / rs < 1.25, (rs, rf)
    # exposure excludes each burst's first row (no contiguous predecessor): 400 bursts x 599 rows x 1 s per tag
    assert sf["pressure_bar_a"]["exposure_channel_days"] == pytest.approx(400 * 599 / 86400.0)
    assert ss["pressure_bar_a"]["exposure_channel_days"] == pytest.approx((len(slow) - 1) * 60.0 / 86400.0)
    # fraction of TIME in fault also agrees
    ts = sum(sum(v["fault_samples"].values()) for v in ss.values()) / sum(v["n_samples"] for v in ss.values())
    tf = sum(sum(v["fault_samples"].values()) for v in sf.values()) / sum(v["n_samples"] for v in sf.values())
    assert 0.7 < tf / ts < 1.4
