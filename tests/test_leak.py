"""Locks in Sec.17.5's leak discharge model."""

from hydrai_twin import constants as C
from hydrai_twin.eos import H2EOS
from hydrai_twin.leak import is_choked, leak_area_m2, leak_mass_flow_kg_s


def test_choke_ratio_matches_workbook_value():
    assert abs(C.CHOKE_PRESSURE_RATIO - 0.528) < 1e-6


def test_normal_operating_pressure_is_unchoked():
    # Sec.17.5: "near normal operating pressure (1.0-1.5 bar(a)) a leak is unchoked/subsonic"
    assert not is_choked(1.2)


def test_mawp_is_choked():
    # Sec.17.5: "near MAWP (6.0 bar(a)) it would be choked"
    assert is_choked(C.PRESSURE_MAWP_BAR)


def test_leak_area_ladder_is_monotonic():
    severities = ["pinhole", "small", "small_medium", "medium_large", "full_bore"]
    areas = [leak_area_m2(s) for s in severities]
    assert areas == sorted(areas)
    assert areas[0] > 0.0


def test_mass_flow_increases_with_area():
    eos = H2EOS()
    sat = eos.saturation_state(1.2)
    flows = [
        leak_mass_flow_kg_s(leak_area_m2(s), 1.2, sat.vapor_density_kg_m3, sat.t_sat_k)
        for s in ("pinhole", "small", "small_medium", "medium_large", "full_bore")
    ]
    assert flows == sorted(flows)
    assert flows[0] > 0.0


def test_zero_area_gives_zero_flow():
    assert leak_mass_flow_kg_s(0.0, 1.2, 70.0, 21.0) == 0.0
