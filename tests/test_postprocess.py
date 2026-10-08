"""Post-processing must be strictly causal and episode-local."""

import numpy as np

from ml.postprocess import detection_delays, labels_from_proba, persistent_alarm, smooth_proba


def _proba(rows):
    return np.array(rows, dtype=float)


def test_smooth_proba_is_causal():
    rng = np.random.default_rng(0)
    p = rng.dirichlet(np.ones(8), size=12)
    ep = np.array(["a"] * 12)
    base = smooth_proba(p, ep, k=4)
    p2 = p.copy()
    p2[8:] = rng.dirichlet(np.ones(8), size=4)          # change the FUTURE
    assert np.allclose(base[:8], smooth_proba(p2, ep, k=4)[:8])


def test_smooth_proba_does_not_bleed_across_episodes():
    p = np.vstack([np.tile([1.0] + [0.0] * 7, (3, 1)), np.tile([0.0, 1.0] + [0.0] * 6, (3, 1))])
    ep = np.array(["a"] * 3 + ["b"] * 3)
    out = smooth_proba(p, ep, k=5)
    assert np.allclose(out[3], p[3])                    # first window of episode b is untouched by episode a


def test_smooth_proba_averages_last_k():
    p = _proba([[1, 0], [1, 0], [0, 1]])
    out = smooth_proba(p, np.array(["a"] * 3), k=3)
    assert np.allclose(out[2], [2 / 3, 1 / 3])


def test_persistent_alarm_k_of_m_and_causality():
    alarm = np.array([0, 1, 0, 1, 1, 0, 0, 0], dtype=bool)
    ep = np.array(["a"] * 8)
    out = persistent_alarm(alarm, ep, k=3, m=2)
    assert out.tolist() == [False, False, False, True, True, True, False, False]
    alarm2 = alarm.copy()
    alarm2[6:] = True                                    # future change
    assert persistent_alarm(alarm2, ep, 3, 2)[:6].tolist() == out[:6].tolist()


def test_labels_from_proba_uses_label_order():
    p = _proba([[0, 0, 0, 0, 0, 0, 0, 1.0]])
    assert labels_from_proba(p).tolist() == [-1]


def test_detection_delay_and_misses():
    ep = np.array(["a"] * 6 + ["b"] * 6 + ["c"] * 4)
    y = np.array([0, 0, 2, 2, 2, 2] + [0, 0, 0, 3, 3, 3] + [0, 0, 0, 0])
    alarm = np.array([0, 0, 0, 0, 1, 1] + [0, 0, 0, 0, 0, 0] + [0, 0, 0, 0], dtype=bool)
    d = detection_delays(ep, y, alarm, stride_s=10.0)
    assert d["n_fault_episodes"] == 2                    # episode c has no fault
    assert d["detected_fraction"] == 0.5                 # b is never detected
    assert d["median_delay_s"] == 20.0                   # a: onset at idx 2, first alarm at idx 4
