"""Locks in the two-tier boil-off model staying two separate, un-blended
tiers (Sec.7's explicit decision)."""

import pytest

from hydrai_twin.boiloff import boiloff_rate_kg_s, boiloff_rate_pct_per_day
from hydrai_twin.constants import BOILOFF_LADDER_PCT_PER_DAY


def test_baseline_and_target_ladders_are_distinct():
    assert BOILOFF_LADDER_PCT_PER_DAY["baseline"]["normal"] == 0.30
    assert BOILOFF_LADDER_PCT_PER_DAY["target"]["normal"] == 0.10
    assert BOILOFF_LADDER_PCT_PER_DAY["baseline"] != BOILOFF_LADDER_PCT_PER_DAY["target"]


def test_rate_kg_s_matches_pct_per_day_definition():
    mass = 603.2
    rate = boiloff_rate_kg_s(mass, "baseline", "normal")
    expected = mass * (0.30 / 100.0) / 86400.0
    assert abs(rate - expected) < 1e-9


def test_unknown_mode_or_stage_raises():
    with pytest.raises(ValueError):
        boiloff_rate_kg_s(100.0, mode="blended")
    with pytest.raises(ValueError):
        boiloff_rate_kg_s(100.0, mode="baseline", stage="catastrophic")


def test_severity_ladder_is_monotonic_within_each_mode():
    for mode in ("baseline", "target"):
        stages = ["excellent", "normal", "mild", "severe", "major"]
        rates = [boiloff_rate_pct_per_day(mode, s) for s in stages]
        assert rates == sorted(rates)
