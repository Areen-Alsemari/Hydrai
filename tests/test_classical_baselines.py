import numpy as np
import pytest

from ml.classical_baselines import (ROC_WINDOW, Episode, Residualizer, count_events, cusum, detect, ewma_abs, fit_threshold, roc_rise, train)
from ml.headline_metrics import alarm_events


def test_roc_rise_recovers_a_ramp_in_units_per_hour_and_is_zero_before_the_window_fills():
    x = 1.2 + 0.001 * np.arange(600)                          # +0.001 per 60 s sample = 0.06 per hour
    s = roc_rise(x)
    assert np.allclose(s[ROC_WINDOW:], 0.06, atol=1e-9) and np.all(s[:ROC_WINDOW - 1] == 0)
    assert np.allclose(roc_rise(np.full(600, 3.0))[ROC_WINDOW:], 0.0, atol=1e-12)
    assert roc_rise(-x)[300] < 0                                # rise only: a fall is a negative statistic


def test_ewma_and_cusum_respond_to_a_sustained_shift_not_to_zero_mean_noise():
    rng = np.random.default_rng(0)
    r = rng.normal(0, 1, 5000)
    r2 = r.copy()
    r2[3000:] += 1.0
    assert ewma_abs(r2)[3500:].mean() > 3 * ewma_abs(r)[3500:].mean()
    assert cusum(r2, 0.5)[-1] > 5 * cusum(r, 0.5).max() * 0.2 and cusum(r2, 0.5)[-1] > 200
    assert cusum(r, 0.5).max() < 30                              # zero-mean noise with k = 0.5 sigma barely accumulates


def test_count_events_equals_the_reference_implementation():
    rng = np.random.default_rng(1)
    t = np.arange(0, 86400.0 * 3, 60.0)
    for p in (0.001, 0.01, 0.1):
        f = rng.random(len(t)) < p
        assert count_events(t, f) == len(alarm_events(t, f, 3600.0))


def test_fit_threshold_meets_the_budget_and_is_tight():
    rng = np.random.default_rng(2)
    t = np.arange(0, 86400.0 * 28, 60.0)
    series = [(t, np.abs(rng.normal(0, 1, len(t)))) for _ in range(3)]
    for budget in (1.0, 6.0, 20.0):
        thr = fit_threshold(series, budget)
        assert sum(count_events(tt, s > thr) for tt, s in series) <= budget
        assert sum(count_events(tt, s > thr * 0.97) for tt, s in series) > budget - 1e-9 or thr == 0.0       # tight: a slightly lower threshold breaks it
    assert fit_threshold(series, 1e9) == 0.0                     # a huge budget needs no threshold


def make_episode(module, n, fault_at=None, shift=0.0, seed=0, role="dev", fault_id=0, vac_shift=0.0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) * 60.0
    p = 1.4 + rng.normal(0, 0.002, n) + 0.03 * np.sin(np.arange(n) / 400.0)
    T = -251.0 + 5.0 * (p - 1.4) + rng.normal(0, 0.05, n)
    v = np.full(n, 1.0) * 10 ** rng.normal(0, 0.02, n)
    if fault_at is not None:
        p[fault_at:] += shift
        v[fault_at:] *= 10 ** vac_shift
    entry = {"module_id": module, "role": role, "fault_id": fault_id, "episode_id": f"{module}-{seed}", "onset_s": None if fault_at is None else fault_at * 60.0,
             "first_observable_s": None, "duration_s": t[-1], "healthy_exposure_s": t[-1] if fault_at is None else fault_at * 60.0, "scenario_class": "standard"}
    return Episode(entry, t, t, np.ones(n, bool), {"pressure": p, "temp": T, "vac": v}, np.zeros(n, bool))


def test_trained_detectors_stay_quiet_on_healthy_and_fire_on_faults():
    n = 20000
    healthy = [make_episode("M01", n, seed=s) for s in range(6)] + [make_episode("M02", n, seed=10 + s) for s in range(6)]
    comm = {"M01": make_episode("M01", n, seed=100), "M02": make_episode("M02", n, seed=101)}
    model = train(healthy, comm, budget_per_week=1.0)
    assert model["train_weeks"] > 10
    held = make_episode("M01", n, seed=50)
    flags = detect(model, held, comm["M01"])
    for det, f in flags.items():
        assert count_events(held.t, f) / (n * 60.0 / (7 * 86400.0)) <= 3.0, det          # near the 1/wk budget on a fresh healthy run
    p_fault = make_episode("M01", n, fault_at=12000, shift=0.25, seed=51, fault_id=4)
    v_fault = make_episode("M01", n, fault_at=12000, vac_shift=1.0, seed=52, fault_id=3)
    fp = detect(model, p_fault, comm["M01"])
    fv = detect(model, v_fault, comm["M01"])
    assert fp["ewma"][12000:].any() and fp["cusum"][12000:].any()
    assert fv["ewma"][12000:].any() and fv["cusum"][12000:].any()                       # a decade vacuum step
    assert fp["roc"][12000:12500].any()                                                 # a step is a brief but large rate of rise
    assert not fv["roc"][12000:].any()                                                  # ROC watches pressure and temperature only: a vacuum step is invisible to it
    for det, f in fp.items():                                                           # pre-onset: at most a couple of false-alarm events in 8 days
        assert count_events(p_fault.t[:12000], f[:12000]) <= 3, det


def test_thresholds_depend_only_on_healthy_training_data():
    n = 12000
    comm = {"M01": make_episode("M01", n, seed=100)}
    healthy = [make_episode("M01", n, seed=s) for s in range(4)]
    a = train(healthy, comm, 1.0)
    faulty = make_episode("M01", n, fault_at=6000, shift=0.5, seed=77, fault_id=4)
    b = train(healthy, comm, 1.0)                                  # training never sees `faulty`; same inputs, same thresholds
    assert a["thr"] == b["thr"]
    assert train(healthy, comm, 0.25)["thr"]["ewma"]["pressure"] >= a["thr"]["ewma"]["pressure"]       # a tighter budget never lowers a threshold


def test_residualizer_removes_the_unit_offset_and_the_saturation_dependence():
    n = 5000
    e = make_episode("M01", n, seed=3)
    rz = Residualizer.fit([e])
    comm = make_episode("M01", n, seed=4)
    base = rz.baseline(comm)
    r = rz.residuals(e, base)
    assert abs(np.median(r["pressure"])) < 0.01 and abs(np.median(r["temp"])) < 0.05 and abs(np.median(r["vac"])) < 0.05
    assert np.std(r["temp"]) < 0.2                                  # T follows p: the p-dependence is regressed out
