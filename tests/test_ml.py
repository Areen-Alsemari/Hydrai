"""Checks for the Model A / Model B baselines: feature leakage rules,
windowing/label alignment, caching, and that both models run end-to-end on a
tiny generated dataset."""

import copy
import json

import numpy as np
import pytest

from hydrai_twin.dataset import DatasetConfig, generate_dataset
from ml.features import (
    FEATURE_NAMES,
    build_feature_set,
    episode_windows,
)
from ml.model_a import IForestModel, ZScoreModel, calibrate_threshold, evaluate, run_model_a
from ml.model_b import run_model_b


@pytest.fixture(scope="module")
def tiny_records():
    cfg = DatasetConfig(
        modules=("M01", "M02", "M03"),
        fault_ids=(2, 3),
        idle_duration_s_normal=60.0,
        idle_duration_s_fault=120.0,
        dt_s=5.0,
        base_seed=3,
    )
    records, _ = generate_dataset(cfg)
    return records


def _by_episode(records):
    eps, order = {}, []
    for r in records:
        if r["episode_id"] not in eps:
            eps[r["episode_id"]] = []
            order.append(r["episode_id"])
        eps[r["episode_id"]].append(r)
    return [eps[i] for i in order]


def _feature_set(records):
    parts = [p for p in (episode_windows(ep) for ep in _by_episode(records)) if p]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def test_feature_matrix_shape_and_finite(tiny_records):
    fs = _feature_set(tiny_records)
    assert fs["X"].shape[1] == len(FEATURE_NAMES)
    assert np.isfinite(fs["X"]).all()
    assert len(fs["X"]) == len(fs["y"]) == len(fs["module"])


def test_features_ignore_ground_truth_labels_and_severity(tiny_records):
    # Features must come from measurements (+ phase) only. Scrambling
    # everything the model must NOT see must leave X untouched.
    ep = next(e for e in _by_episode(tiny_records) if e[0]["labels"]["fault_id"] == 0 and any(r["labels"]["ai_label"] for r in e))
    original = episode_windows(ep)["X"]

    tampered = copy.deepcopy(ep)
    rng = np.random.default_rng(0)
    for r in tampered:
        for k in r["simulation_ground_truth"]:
            if isinstance(r["simulation_ground_truth"][k], (int, float)):
                r["simulation_ground_truth"][k] = float(rng.normal())
        r["labels"]["ai_label"] = int(rng.integers(0, 7))
        r["system_context"]["fault_severity"] = float(rng.random())
        r["system_context"]["variant_tag"] = "scrambled"

    assert np.array_equal(original, episode_windows(tampered)["X"])


def test_feature_names_do_not_reference_ground_truth_fields():
    banned = ("mass_kg", "t_sat", "leak_rate", "apparent_boiloff", "severity", "density", "strain_pressure", "material")
    assert not any(b in n for n in FEATURE_NAMES for b in banned)


def test_window_label_is_label_at_last_tick(tiny_records):
    ep = next(e for e in _by_episode(tiny_records) if any(r["labels"]["ai_label"] for r in e))
    w = episode_windows(ep, window_s=60.0, stride_s=10.0)
    n_win, stride = 12, 2  # dt = 5 s
    ends = np.arange(n_win - 1, len(ep), stride)
    assert np.array_equal(w["y"], np.array([ep[i]["labels"]["ai_label"] for i in ends]))


def test_build_feature_set_cache_roundtrip(tmp_path, tiny_records):
    src = tmp_path / "d.jsonl"
    src.write_text("".join(json.dumps(r) + "\n" for r in tiny_records))
    cache = tmp_path / "f.npz"
    a = build_feature_set(src, cache)
    assert cache.exists()
    b = build_feature_set(src, cache)  # served from cache
    assert np.array_equal(a["X"], b["X"]) and np.array_equal(a["y"], b["y"])


def test_zscore_scores_shifted_data_higher():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 6))
    m = ZScoreModel().fit(X)
    assert m.score(X + 5.0).mean() > m.score(X).mean()


def test_iforest_scores_outliers_higher():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 6))
    m = IForestModel(seed=0, n_estimators=50).fit(X)
    assert m.score(X + 6.0).mean() > m.score(X).mean()


def test_calibration_threshold_is_out_of_fold_and_finite():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(600, 4))
    mods = np.repeat(np.array(["a", "b", "c"]), 200)
    thr = calibrate_threshold(ZScoreModel, X, mods)
    assert np.isfinite(thr) and thr > 0


def test_model_a_and_b_run_end_to_end(tiny_records):
    fs = _feature_set(tiny_records)
    train_mask = fs["module"] != "M03"
    train = {k: v[train_mask] for k, v in fs.items()}
    test = {k: v[~train_mask] for k, v in fs.items()}

    a = run_model_a(train, test, stride_s=10.0, seed=0)
    for name in ("zscore", "iforest"):
        m = a["models"][name]
        assert 0.0 <= m["auroc_all"] <= 1.0
        assert 0.0 <= m["false_alarm_window_rate"] <= 1.0

    b = run_model_b(train, test, seed=0)
    assert 0.0 <= b["all"]["accuracy"] <= 1.0
    assert "ablation_no_vacuum_sensor" in b
    cm = np.array(b["all"]["confusion_matrix"]["rows_true_cols_pred"])
    assert cm.sum() == len(test["y"])
