"""End-to-end checks on the normal-operation generator: schema shape, phase
ordering, mass balance direction per phase, and envelope compliance."""

from hydrai_twin import constants as C
from hydrai_twin.episode import NormalEpisodeConfig, NormalEpisodeGenerator

SCHEMA_KEYS = {"episode_id", "timestamp", "system_context", "measurements", "simulation_ground_truth", "labels"}


def _small_episode(seed=1):
    cfg = NormalEpisodeConfig(seed=seed, idle_duration_s=30.0, dt_s=2.0)
    return NormalEpisodeGenerator(cfg).generate()


def test_schema_keys_present_on_every_record():
    records = _small_episode()
    assert len(records) > 0
    for r in records:
        assert set(r.keys()) == SCHEMA_KEYS
        assert set(r["measurements"].keys()) == set(C.SENSOR_SPECS.keys())


def test_all_records_share_one_episode_id():
    records = _small_episode()
    ids = {r["episode_id"] for r in records}
    assert len(ids) == 1


def test_phases_occur_in_order_filling_idle_discharge():
    records = _small_episode()
    phases = [r["system_context"]["phase"] for r in records]
    assert phases[0] == "filling"
    assert "idle" in phases
    assert phases[-1] == "discharge"
    # no phase re-entry once we've moved on
    seen = []
    for p in phases:
        if not seen or seen[-1] != p:
            seen.append(p)
    assert seen == ["filling", "idle", "discharge"]


def test_mass_balance_direction_per_phase():
    records = _small_episode()
    by_phase = {}
    for r in records:
        by_phase.setdefault(r["system_context"]["phase"], []).append(r["simulation_ground_truth"]["mass_kg"])

    assert by_phase["filling"][-1] > by_phase["filling"][0]     # mass rises while filling
    assert by_phase["discharge"][-1] < by_phase["discharge"][0]  # mass falls while discharging
    # idle: boil-off only, mass should not increase
    assert by_phase["idle"][-1] <= by_phase["idle"][0]


def test_pressure_stays_within_normal_band():
    records = _small_episode()
    lo, hi = C.PCV_BAND_BAR
    for r in records:
        p = r["simulation_ground_truth"]["pressure_bar_a"]
        assert lo - 1e-9 <= p <= hi + 1e-9


def test_all_labels_are_normal():
    records = _small_episode()
    assert all(r["labels"]["ai_label"] == 0 for r in records)
    assert all(r["labels"]["fault_name"] == "normal" for r in records)


def test_deterministic_with_fixed_seed():
    a = _small_episode(seed=7)
    b = _small_episode(seed=7)
    assert len(a) == len(b)
    assert a[10]["simulation_ground_truth"]["pressure_bar_a"] == b[10]["simulation_ground_truth"]["pressure_bar_a"]
