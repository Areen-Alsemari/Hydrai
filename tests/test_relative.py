"""Module-relative features and LOMO: the properties that make them legitimate
(not leakage), plus fold hygiene."""

import copy

import numpy as np
import pytest

from hydrai_twin.dataset import DatasetConfig, generate_commissioning, generate_dataset
from ml.features import FEATURE_NAMES, episode_windows
from ml.lomo import run_lomo
from ml.relative import FEATURE_SETS, ModuleBaselines, columns_for, names_for, prepare
from ml.util import strip_private


def _cfg():
    return DatasetConfig(
        modules=("M01", "M02", "M03"), fault_ids=(2, 3), idle_duration_s_normal=60.0,
        idle_duration_s_fault=120.0, dt_s=5.0, base_seed=3,
    )


def _by_episode(records):
    eps, order = {}, []
    for r in records:
        if r["episode_id"] not in eps:
            eps[r["episode_id"]], _ = [], order.append(r["episode_id"])
        eps[r["episode_id"]].append(r)
    return [eps[i] for i in order]


def _feats(records):
    parts = [p for p in (episode_windows(e) for e in _by_episode(records)) if p]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


@pytest.fixture(scope="module")
def data():
    cfg = _cfg()
    records, _ = generate_dataset(cfg)
    comm = generate_commissioning(cfg)
    return records, comm


def _baselines(comm_feats):
    return ModuleBaselines().fit(comm_feats["X"], comm_feats["module"], comm_feats["phase"])


def test_relative_features_are_invariant_to_a_constant_sensor_bias(data):
    records, comm = data
    bias = 0.03  # bar, on the pressure sensor, applied to BOTH the unit's commissioning run and its operation

    def biased(recs):
        recs = copy.deepcopy(recs)
        for r in recs:
            r["measurements"]["pressure_bar_a"] += bias
        return recs

    f0, c0 = _feats(records), _feats(comm)
    f1, c1 = _feats(biased(records)), _feats(biased(comm))
    rel0, _ = prepare(f0, _baselines(c0), "relative_multi")
    rel1, _ = prepare(f1, _baselines(c1), "relative_multi")
    assert np.allclose(rel0, rel1, atol=1e-3)
    abs0, _ = prepare(f0, None, "absolute")
    abs1, _ = prepare(f1, None, "absolute")
    assert not np.allclose(abs0, abs1, atol=1e-3)  # ...whereas absolute features do move with it


def test_relative_features_do_not_use_labels_or_severity(data):
    records, comm = data
    f, c = _feats(records), _feats(comm)
    base = _baselines(c)
    a, _ = prepare(f, base, "relative_multi")
    scrambled = dict(f)
    rng = np.random.default_rng(0)
    scrambled["y"] = rng.integers(0, 7, size=len(f["y"]))
    scrambled["sev_frac"] = rng.random(len(f["y"]))
    b, _ = prepare(scrambled, base, "relative_multi")
    assert np.array_equal(a, b)


def test_baseline_for_a_unit_is_independent_of_other_units(data):
    _, comm = data
    c = _feats(comm)
    both = ModuleBaselines().fit(c["X"], c["module"], c["phase"])
    only_m01 = c["module"] == "M01"
    alone = ModuleBaselines().fit(c["X"][only_m01], c["module"][only_m01], c["phase"][only_m01])
    for phase in ("filling", "idle", "discharge", "*"):
        assert np.array_equal(both.base_["M01"][phase], alone.base_["M01"][phase])


def test_transform_without_a_commissioning_baseline_fails_loudly(data):
    records, comm = data
    c = _feats(comm)
    m01 = c["module"] == "M01"
    base = ModuleBaselines().fit(c["X"][m01], c["module"][m01], c["phase"][m01])
    with pytest.raises(KeyError):
        prepare(_feats(records), base, "relative")  # M02/M03 have no baseline


def test_commissioning_runs_are_healthy_separate_episodes(data):
    records, comm = data
    assert all(r["labels"]["ai_label"] == 0 for r in comm)
    assert {r["system_context"]["variant_tag"] for r in comm} == {"commissioning"}
    assert {r["episode_id"] for r in comm}.isdisjoint({r["episode_id"] for r in records})
    assert min(r["timestamp"] for r in records) > max(r["timestamp"] for r in comm)  # commissioning precedes operation


def test_feature_set_column_selection():
    assert len(columns_for("absolute")) == len(columns_for("relative")) == 48
    assert len(columns_for("relative_multi")) == len(FEATURE_NAMES)
    assert len(names_for("relative")) == 48
    with pytest.raises(ValueError):
        columns_for("nope")


def test_lomo_folds_never_train_on_the_held_out_module(data):
    records, comm = data
    f, c = _feats(records), _feats(comm)
    res = run_lomo(f, _baselines(c), "relative_multi", stride_s=10.0, seed=0)
    assert set(res["folds"]) == {"M01", "M02", "M03"}   # run_lomo asserts train/test module disjointness per fold
    assert len(res["oof"]["y"]) == len(f["y"])           # every window is scored exactly once, out-of-fold
    assert set(res["oof"]["module"]) == {"M01", "M02", "M03"}
    assert 0.0 <= res["aggregate"]["model_b"]["accuracy_settled"]["mean"] <= 1.0


def test_strip_private_makes_results_json_safe():
    import json
    obj = {"a": np.float32(1.5), "_arr": np.zeros(3), "oof": {"x": np.ones(2)}, "n": {"_p": 1, "q": np.int64(2)}}
    assert json.loads(json.dumps(strip_private(obj))) == {"a": 1.5, "n": {"q": 2}}
