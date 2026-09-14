"""Checks the dataset driver's variant matrix and the module/severity-aware
train/test split -- the two things the ML-readiness pass added."""

from hydrai_twin.dataset import (
    DatasetConfig,
    _fault_variants,
    generate_dataset,
    split_train_test,
)

FAULT_IDS = (1, 2, 3, 4, 5, 6, -1)


def test_every_scenario_has_multiple_variants():
    for fault_id in FAULT_IDS:
        variants = _fault_variants(fault_id)
        assert len(variants) >= 3, f"fault_id={fault_id} has too few variants: {len(variants)}"
        tags = [v["variant_tag"] for v in variants]
        assert len(tags) == len(set(tags)), f"fault_id={fault_id} has duplicate variant tags"


def test_containment_anomaly_variants_cover_full_leak_ladder():
    variants = _fault_variants(5)
    tags = {v["variant_tag"] for v in variants}
    assert tags == {"pinhole", "small", "small_medium", "medium_large", "full_bore"}


def test_insulation_degradation_variants_cover_both_severity_tiers():
    variants = _fault_variants(2)
    health_pcts = {v["target_health_pct"] for v in variants}
    assert health_pcts == {70.0, 40.0}
    ramp_durations = {v["ramp_duration_s"] for v in variants}
    assert len(ramp_durations) >= 2  # ramp speed is varied too


def _tiny_dataset():
    cfg = DatasetConfig(
        modules=("M01", "M02", "M06"),
        fault_ids=(2, 5),  # small subset, for a fast test
        idle_duration_s_normal=20.0,
        idle_duration_s_fault=30.0,
        dt_s=5.0,
        base_seed=1,
    )
    return generate_dataset(cfg)


def test_split_excludes_held_out_module_from_train():
    records, _ = _tiny_dataset()
    train, test = split_train_test(records, held_out_modules=("M06",))
    assert all(r["system_context"]["module_id"] != "M06" for r in train)
    assert any(r["system_context"]["module_id"] == "M06" for r in test)


def test_held_out_module_is_fully_and_only_in_test():
    records, _ = _tiny_dataset()
    train, test = split_train_test(records, held_out_modules=("M06",))
    m06_total = sum(1 for r in records if r["system_context"]["module_id"] == "M06")
    m06_in_test = sum(1 for r in test if r["system_context"]["module_id"] == "M06")
    m06_in_train = sum(1 for r in train if r["system_context"]["module_id"] == "M06")
    assert m06_in_test == m06_total  # all of M06 is in test
    assert m06_in_train == 0          # none of M06 leaks into train


def test_train_contains_every_severity_variant_present_in_the_full_dataset():
    # This is the fix's core guarantee: severity is NOT excluded from
    # training -- every (scenario, variant_tag) combo that exists anywhere
    # in the dataset for a non-held-out module must also appear in train.
    records, _ = _tiny_dataset()
    held_out_modules = ("M06",)
    train, _ = split_train_test(records, held_out_modules=held_out_modules)

    def scenario_variant(r):
        return r["system_context"]["scenario"], r["system_context"]["variant_tag"]

    full_variants_non_held_out = {
        scenario_variant(r) for r in records if r["system_context"]["module_id"] not in held_out_modules
    }
    train_variants = {scenario_variant(r) for r in train}
    assert full_variants_non_held_out == train_variants
    # in particular, the largest leak size must be present in train
    assert ("containment_anomaly", "full_bore") in train_variants


def test_split_is_a_true_partition():
    records, _ = _tiny_dataset()
    train, test = split_train_test(records, held_out_modules=("M06",))
    assert len(train) + len(test) == len(records)
    train_ids = {id(r) for r in train}
    test_ids = {id(r) for r in test}
    assert train_ids.isdisjoint(test_ids)
