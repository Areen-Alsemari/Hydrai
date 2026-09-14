"""Locks in the EOS backend validation done by hand while building this:
right fluid, right EOS (Leachman 2009), saturation states land inside the
workbook's own Sec.6 normal operating bands."""

from hydrai_twin import constants as C
from hydrai_twin.eos import H2EOS


def test_backend_is_leachman_eos():
    import CoolProp.CoolProp as CP
    assert "Leachman" in CP.get_BibTeXKey("Hydrogen", "EOS")


def test_saturation_state_matches_sec6_normal_band_at_normal_pressure():
    eos = H2EOS()
    lo, hi = C.PRESSURE_NORMAL_RANGE_BAR
    for p in (lo, C.PRESSURE_NORMAL_BAR, hi):
        sat = eos.saturation_state(p)
        band_lo, band_hi = C.TEMP_LH2_NORMAL_C
        assert band_lo <= sat.t_sat_c <= band_hi, f"P={p} bar(a) -> T_sat={sat.t_sat_c} C outside Sec.6 normal band"


def test_liquid_denser_than_vapor_across_envelope():
    eos = H2EOS()
    for p in (C.PRESSURE_MIN_MODELED_BAR, C.PRESSURE_NORMAL_BAR, C.PRESSURE_MAWP_BAR):
        sat = eos.saturation_state(p)
        assert sat.liquid_density_kg_m3 > sat.vapor_density_kg_m3
        assert sat.latent_heat_j_kg > 0


def test_liquid_density_near_sec3_reference_at_1atm():
    eos = H2EOS()
    rho = eos.liquid_density(1.01325)
    assert abs(rho - 70.97) < 1.0  # Sec.3: ~70.97 kg/m3 at NBP
