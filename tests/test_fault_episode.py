"""End-to-end checks on the fault-injection generator: pre-onset ticks look
normal, post-onset ticks carry the right label, and each scenario's
ground-truth trend matches the direction Sec.10's taxonomy table specifies."""

from hydrai_twin.fault_episode import FaultEpisodeConfig, FaultEpisodeGenerator

SCHEMA_KEYS = {"episode_id", "timestamp", "system_context", "measurements", "simulation_ground_truth", "labels"}


def _episode(fault_id, seed=1, **kwargs):
    cfg = FaultEpisodeConfig(
        fault_id=fault_id, seed=seed, idle_duration_s=120.0, ramp_duration_s=30.0, dt_s=2.0, **kwargs
    )
    return FaultEpisodeGenerator(cfg).generate()


def _pre_post(records):
    pre = [r for r in records if r["labels"]["fault_id"] == 0 and r["system_context"]["phase"] == "idle"]
    # Use the episode's own achieved max severity, not a fixed 0.99 -- a
    # variant with max_severity < 1.0 never reaches 0.99, so a fixed
    # threshold would silently return an empty "post" slice for it.
    max_sev = max((r["system_context"]["fault_severity"] for r in records), default=0.0)
    post = [r for r in records if max_sev > 0 and r["system_context"]["fault_severity"] >= max_sev - 1e-9]
    return pre, post


def test_schema_and_pre_onset_label_is_normal():
    records = _episode(2)
    for r in records:
        assert set(r.keys()) == SCHEMA_KEYS
    pre, _ = _pre_post(records)
    assert len(pre) > 0
    assert all(r["labels"]["ai_label"] == 0 for r in pre)


def test_sensor_fault_never_touches_ground_truth_pressure():
    records = _episode(1)
    pressures = [r["simulation_ground_truth"]["pressure_bar_a"] for r in records]
    # sensor fault (label 1) must not move the true physical pressure envelope
    assert max(pressures) <= 1.5 + 1e-6
    assert min(pressures) >= 1.0 - 1e-6


def test_insulation_degradation_boiloff_matches_sec10_table_at_full_severity():
    records = _episode(2)
    _, post = _pre_post(records)
    assert len(post) > 0
    rates = [r["simulation_ground_truth"]["boiloff_rate_pct_day"] for r in post]
    # Sec.10 staging: 40% health -> 2.5x baseline. baseline mode normal = 0.30%/day.
    for r in rates:
        assert abs(r - 0.30 * 2.5) < 0.02


def test_vacuum_degradation_moves_vacuum_sensor_but_insulation_does_not():
    insulation_records = _episode(2)
    vacuum_records = _episode(3)
    _, ins_post = _pre_post(insulation_records)
    _, vac_post = _pre_post(vacuum_records)
    ins_vacuum = [r["simulation_ground_truth"]["vacuum_pressure_pa"] for r in ins_post]
    vac_vacuum = [r["simulation_ground_truth"]["vacuum_pressure_pa"] for r in vac_post]
    assert max(ins_vacuum) < 1.0        # insulation degradation: vacuum sensor stays healthy
    assert min(vac_vacuum) > 100.0      # vacuum degradation: vacuum sensor clearly elevated


def test_containment_anomaly_raises_h2_concentration():
    records = _episode(5)
    pre, post = _pre_post(records)
    pre_h2 = max(r["simulation_ground_truth"]["h2_concentration_pct"] for r in pre)
    post_h2 = max(r["simulation_ground_truth"]["h2_concentration_pct"] for r in post)
    assert post_h2 > pre_h2
    assert post_h2 > 0.5  # meaningfully above the near-zero normal baseline


def test_abnormal_pressure_rise_exceeds_normal_band():
    records = _episode(4)
    _, post = _pre_post(records)
    pressures = [r["simulation_ground_truth"]["pressure_bar_a"] for r in post]
    assert max(pressures) > 1.5  # breaches Sec.5 normal operating range


def test_structural_concern_elevates_strain_without_moving_h2():
    records = _episode(6)
    pre, post = _pre_post(records)
    pre_strain = [abs(r["simulation_ground_truth"]["strain_ue"]) for r in pre]
    post_strain = [abs(r["simulation_ground_truth"]["strain_ue"]) for r in post]
    # SCF ramps the pressure-strain term up sharply -> total |strain| should shrink
    # from its large negative thermal-dominated baseline as severity ramps in.
    assert min(post_strain) < min(pre_strain)
    post_h2 = max(r["simulation_ground_truth"]["h2_concentration_pct"] for r in post)
    assert post_h2 < 0.5


def test_unknown_anomaly_composes_two_named_faults():
    records = _episode(-1, seed=42)
    sub_faults = records[0]["system_context"]["unknown_sub_faults"]
    assert len(sub_faults) == 2
    assert all(fid in (2, 3, 4, 5, 6) for fid in sub_faults)
    _, post = _pre_post(records)
    assert all(r["labels"]["ai_label"] == -1 for r in post)
    assert all(r["labels"]["fault_name"] == "unknown_anomaly" for r in post)


# --- diversity knobs: one severity/size variant check per varied scenario --

def test_containment_anomaly_leak_severity_variant_scales_h2_and_mass_loss():
    small = _episode(5, seed=5, leak_severity="small")
    full_bore = _episode(5, seed=5, leak_severity="full_bore")
    _, small_post = _pre_post(small)
    _, full_post = _pre_post(full_bore)
    small_h2 = max(r["simulation_ground_truth"]["h2_concentration_pct"] for r in small_post)
    full_h2 = max(r["simulation_ground_truth"]["h2_concentration_pct"] for r in full_post)
    assert full_h2 > small_h2 * 5  # full-bore should be dramatically worse than "small"


def test_insulation_degradation_target_health_variant_changes_boiloff():
    degraded = _episode(2, seed=6, target_health_pct=70.0)
    severe = _episode(2, seed=6, target_health_pct=40.0)
    _, degraded_post = _pre_post(degraded)
    _, severe_post = _pre_post(severe)
    degraded_rate = degraded_post[-1]["simulation_ground_truth"]["boiloff_rate_pct_day"]
    severe_rate = severe_post[-1]["simulation_ground_truth"]["boiloff_rate_pct_day"]
    assert abs(degraded_rate - 0.30 * 1.5) < 0.02   # Sec.10: 70% health -> 1.5x
    assert abs(severe_rate - 0.30 * 2.5) < 0.02      # Sec.10: 40% health -> 2.5x
    assert severe_rate > degraded_rate


def test_abnormal_pressure_rise_max_severity_variant_caps_pressure():
    mild = _episode(4, seed=7, max_severity=0.4)
    severe = _episode(4, seed=7, max_severity=1.0)
    _, mild_post = _pre_post(mild)
    _, severe_post = _pre_post(severe)
    mild_p = max(r["simulation_ground_truth"]["pressure_bar_a"] for r in mild_post)
    severe_p = max(r["simulation_ground_truth"]["pressure_bar_a"] for r in severe_post)
    assert severe_p > mild_p


def test_structural_concern_max_severity_variant_changes_strain():
    mild = _episode(6, seed=8, max_severity=0.3)
    severe = _episode(6, seed=8, max_severity=1.0)
    _, mild_post = _pre_post(mild)
    _, severe_post = _pre_post(severe)
    mild_strain = min(abs(r["simulation_ground_truth"]["strain_ue"]) for r in mild_post)
    severe_strain = min(abs(r["simulation_ground_truth"]["strain_ue"]) for r in severe_post)
    assert severe_strain < mild_strain  # more severity -> further off the thermal baseline


def test_sensor_fault_onset_variant_moves_onset_tick():
    early = _episode(1, seed=9, onset_frac_of_idle=0.1)
    late = _episode(1, seed=9, onset_frac_of_idle=0.8)
    early_onset = next(i for i, r in enumerate(early) if r["labels"]["ai_label"] == 1)
    late_onset = next(i for i, r in enumerate(late) if r["labels"]["ai_label"] == 1)
    assert late_onset > early_onset


def test_unknown_anomaly_explicit_subfault_pair_is_respected():
    records = _episode(-1, seed=10, unknown_sub_fault_ids=(3, 6))
    assert records[0]["system_context"]["unknown_sub_faults"] == [3, 6]


def test_containment_anomaly_initial_pressure_variant_is_applied_at_onset():
    records = _episode(5, seed=11, initial_pressure_bar=1.45)
    onset_idx = next(i for i, r in enumerate(records) if r["system_context"]["fault_severity"] > 0.0)
    assert abs(records[onset_idx]["simulation_ground_truth"]["pressure_bar_a"] - 1.45) < 0.05
