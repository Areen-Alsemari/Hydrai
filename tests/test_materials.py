"""Locks in the material-formula validation points from Sec.4.2/4.3,
including the two transcription-error corrections found and fixed
(thermal expansion -- caught in the workbook itself; specific heat --
caught while building this twin). If any of these regress, the workbook's
own cross-checks (self-consistency at 293K, Fermilab's 77K figure) would
start failing again."""

import math

from hydrai_twin.materials import (
    specific_heat_j_kgk,
    thermal_conductivity_w_mk,
    thermal_expansion_dl_l,
    youngs_modulus_gpa,
)


def test_dl_l_self_consistency_at_293k():
    # dL/L is defined relative to 293K, so it must be ~0 there.
    assert abs(thermal_expansion_dl_l(293.0)) < 1e-4


def test_dl_l_matches_fermilab_77k_cross_check():
    # Workbook Sec.4.2: independent Fermilab paper reports -0.281% at 77K;
    # corrected formula should land within 0.01 percentage points.
    pct = thermal_expansion_dl_l(77.0) * 100.0
    assert abs(pct - (-0.281)) < 0.01


def test_cp_increases_toward_room_temperature():
    # The bug this test guards against: the original transcribed
    # coefficients made cp *decrease* to ~0 as T -> 293K, which is backwards.
    cp_20 = specific_heat_j_kgk(20.0)
    cp_77 = specific_heat_j_kgk(77.0)
    cp_293 = specific_heat_j_kgk(293.0)
    assert cp_20 < cp_77 < cp_293
    assert 5.0 < cp_20 < 30.0          # workbook-independent sanity band
    assert 400.0 < cp_293 < 550.0      # ~470 J/kgK expected for 304 SS at RT


def test_k_reference_point_near_minus_253c():
    # Sec.4.2 sanity-check point: k ~ 1-3 W/m*K near -253 C (~20 K),
    # 2.71 W/m*K cited as a reference value.
    k = thermal_conductivity_w_mk(20.0)
    assert 1.0 < k < 3.5


def test_youngs_modulus_stays_positive_and_in_plausible_range():
    for t in (5.0, 20.0, 57.0, 150.0, 293.0):
        e = youngs_modulus_gpa(t)
        assert 150.0 < e < 250.0  # 304 SS: ~190-215 GPa typical


def test_materials_clip_out_of_range_inputs_without_erroring():
    # Should clip rather than raise for T outside the stated valid ranges.
    assert math.isfinite(thermal_conductivity_w_mk(1.0))
    assert math.isfinite(thermal_conductivity_w_mk(500.0))
    assert math.isfinite(specific_heat_j_kgk(500.0))
