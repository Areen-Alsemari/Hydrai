import numpy as np
import pytest

from ml.cgh2_baselines import DETECTORS, Episode, base_of, detect, hold_slope, residuals, train
from ml.classical_baselines import count_events


def make_episode(module, n=12000, leak_kg_h=0.0, fault_at=None, seed=0, role="dev", fault_id=0, hot=0.0, V=10.0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) * 60.0
    hour = (t / 3600.0) % 24
    Ta = 30 + 8 * np.sin(2 * np.pi * (hour - 9) / 24)
    Tw = Ta + 3 + rng.normal(0, 0.1, n)
    run = np.zeros(n, bool)
    Tg = 0.5 * Tw + 0.5 * Ta + 1.0 + rng.normal(0, 0.3, n) + 6.0 * run
    if fault_at is not None:
        Tg[fault_at:] += hot
    inv = np.full(n, 150.0) + rng.normal(0, 0.15, n)
    if fault_at is not None and leak_kg_h:
        inv[fault_at:] -= leak_kg_h * (np.arange(n - fault_at) / 60.0)
    P = 200.0 + (inv - 150.0) * 1.5 + 1.0 * (Tg - 30.0) + rng.normal(0, 0.3, n)
    z = np.zeros(n)
    x = {"P": P, "T": Tg, "Tw": Tw, "Ta": Ta, "fill": z, "disc": z}
    ep = Episode({"module_id": module, "role": role, "fault_id": fault_id, "episode_id": f"{module}-{seed}", "onset_s": None if fault_at is None else fault_at * 60.0,
                  "first_observable_s": None, "duration_s": t[-1], "healthy_exposure_s": t[-1] if fault_at is None else fault_at * 60.0,
                  "scenario_class": "standard", "family": "x", "variant_tag": "x"}, t, x, run, np.zeros(n, bool), V)
    ep.inv = inv
    ep.pc = P - 1.0 * (Tg - 50.0) * 0                       # pressure at the reference temperature: monotone in the inventory
    return ep


def test_hold_slope_is_zero_outside_hold_windows_and_recovers_the_inventory_trend_inside():
    e = make_episode("M01", leak_kg_h=2.0, fault_at=4000)
    s = hold_slope(e)
    assert np.all(s[:119] == 0.0)
    assert np.median(s[6000:9000]) == pytest.approx(-2.0, abs=0.3) and abs(np.median(s[1000:3000])) < 0.2
    run = e.status_run.copy(); run[6000:6100] = True; e.status_run = run
    assert np.all(hold_slope(e)[6000:6100 + 119] == 0.0)                       # a compressor run (or draw) interrupts the hold window


def test_trained_detectors_respect_the_budget_and_see_a_leak_and_a_thermal_fault():
    healthy = [make_episode("M01", seed=s) for s in range(5)] + [make_episode("M02", seed=10 + s) for s in range(5)]
    comm = {"M01": make_episode("M01", seed=100), "M02": make_episode("M02", seed=101)}
    model = train(healthy, comm, budget_per_week=1.0)
    assert model.train_weeks > 10
    held = make_episode("M01", seed=50)
    for det, f in detect(model, held, comm["M01"]).items():
        assert count_events(held.t, f) / (held.t[-1] / (7 * 86400.0)) <= 3.0, det           # near the budget on a fresh healthy run
    leak = make_episode("M01", leak_kg_h=3.0, fault_at=6000, seed=51, fault_id=3)
    hot = make_episode("M01", hot=6.0, fault_at=6000, seed=52, fault_id=2)
    fl, fh = detect(model, leak, comm["M01"]), detect(model, hot, comm["M01"])
    assert fl["inv"][6000:].any() and fl["cusum"][6000:].any()                                 # inventory slope and compensated pressure
    assert fh["cusum"][6000:].any() and fh["ewma"][6000:].any()                                 # gas temperature vs shell and ambient
    assert not fl["inv"][:6000].any() or count_events(leak.t[:6000], fl["inv"][:6000]) <= 2


def test_thresholds_depend_only_on_healthy_training_data_and_tighter_budget_never_lowers_them():
    comm = {"M01": make_episode("M01", seed=100)}
    healthy = [make_episode("M01", seed=s) for s in range(4)]
    a, b = train(healthy, comm, 1.0), train(healthy, comm, 1.0)
    assert a.thr == b.thr
    assert train(healthy, comm, 0.25).thr["ewma"]["Pc"] >= a.thr["ewma"]["Pc"]
    assert set(a.thr) == set(DETECTORS)


def test_residuals_remove_the_unit_offset():
    healthy = [make_episode("M01", seed=s) for s in range(3)]
    m = train(healthy, {"M01": make_episode("M01", seed=100)}, 1.0)
    r = residuals(healthy[0], m.temp_coef, m.bases["M01"])
    assert abs(np.median(r["Pc"])) < 2.0 and abs(np.median(r["T_res"])) < 0.5


def test_thresholds_are_never_degenerate_and_the_alarm_is_not_on_most_of_the_time():
    """Regression: an always-on statistic is ONE merged event, so an event-count budget alone returned threshold 0.0 (ROC pressure, EWMA)."""
    healthy = [make_episode("M01", seed=s) for s in range(5)] + [make_episode("M02", seed=10 + s) for s in range(5)]
    comm = {"M01": make_episode("M01", seed=100), "M02": make_episode("M02", seed=101)}
    model = train(healthy, comm, budget_per_week=1.0)
    for det, chans in model.thr.items():
        assert all(v > 0.0 for v in chans.values()), (det, chans)
    held = make_episode("M01", seed=50)
    for det, f in detect(model, held, comm["M01"]).items():
        assert f.mean() < 0.06, (det, f.mean())                 # roughly the 2 % cap on the training data, a little looser on a fresh run
