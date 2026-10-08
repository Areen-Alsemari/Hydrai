import numpy as np
import pytest

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import CLASS_NAMES, make_class, resolve_stop_policy

V = 10.0


@pytest.mark.parametrize("P,ref", [(30, 23.8), (50, 39.2), (200, 144.0), (300, 204.0), (350, 232.0), (700, 391.0)])
def test_inventory_in_10_m3_at_300_K_matches_the_reference_within_2_percent(P, ref):
    assert float(G.inventory_kg(P, 300.0, V)) == pytest.approx(ref, rel=0.02)


@pytest.mark.parametrize("P,ref", [(30, 0.101), (50, 0.168), (200, 0.688), (300, 1.04), (350, 1.21), (700, 2.40)])
def test_dPdT_at_constant_density_matches_the_reference_within_2_percent(P, ref):
    assert G.dPdT_rho_bar_per_K(P, 300.0) == pytest.approx(ref, rel=0.02)


@pytest.mark.parametrize("P,ref", [(300, 0.141), (350, 0.163)])
def test_choked_leak_0p1_mm_matches_the_reference_within_2_percent(P, ref):
    assert G.leak_mass_rate_kg_s(0.1, P, 300.0) * 1e3 == pytest.approx(ref, rel=0.02)


def test_30_bar_leak_matches_the_reference_to_its_two_significant_figures():
    v = G.leak_mass_rate_kg_s(0.1, 30, 300.0) * 1e3
    assert v == pytest.approx(0.0145, abs=2e-5) and round(v, 3) == 0.014          # quoted as 0.014 (2 s.f.): 0.014496 rounds to it


def test_fast_flux_table_agrees_with_the_direct_real_gas_solve():
    for P in (5, 30, 100, 300, 350, 420):
        assert G.choked_mass_flux_fast(P * 1e5, 300.0) == pytest.approx(G.choked_mass_flux(P * 1e5, 300.0), rel=0.005)
    assert G.choked_mass_flux(300e5, 300.0) < G.ideal_choked_mass_flux(300e5, 300.0)          # real gas flows less than ideal at 300 bar


def test_abel_noble_is_within_1_percent_over_the_operating_range_but_not_over_minus_40_C():
    assert G.abel_noble_max_error(350.0, 263.15, 333.15) < 0.01          # -10 .. 60 C: allowed as a fast path for derived features
    assert G.abel_noble_max_error(350.0, 233.15, 353.15) > 0.01          # -40 C: not within 1 %, so the physics never uses it (CoolProp always)
    assert float(G.abel_noble_rho(300.0, 300.0)) == pytest.approx(float(G.rho_PT(300.0, 300.0)), rel=0.01)


def test_rho_pt_vectorised_shapes_and_normal_hydrogen():
    assert G.rho_PT(np.ones((2, 3)) * 100, 300.0).shape == (2, 3)
    assert G.FLUID == "Hydrogen"                                                   # normal hydrogen, NOT ParaHydrogen


def test_real_gas_energy_derivative_is_not_the_ideal_gas_value():
    st = G.Gas().state(float(G.rho_PT(300.0, 300.0)), 300.0)
    assert abs(st["u_rho"]) > 1e3                                                  # (du/drho)_T is nonzero at 300 bar (zero for an ideal gas)


# --- registry ---------------------------------------------------------------------------------------------------------------

def test_every_entry_has_a_valid_source_tag_and_placeholders_are_flagged():
    for e in R.REGISTRY.values():
        assert e.tag in R.TAGS and e.source
        assert e.is_placeholder == (e.tag in ("U", "JUDGE", "REG-UNREAD"))
    assert R.REGISTRY["mop_bar_medium"].is_placeholder                              # the register was not readable: relayed values are placeholders


def test_addendum_overrides_are_in_the_registry_with_their_tags():
    v = R.value
    assert (v("prv_set_tolerance"), v("prv_blowdown_nominal"), v("prv_blowdown_conservative")) == (0.03, 0.07, 0.10)
    assert v("tprd_fitted") == 0.0 and (v("pah_over_mop"), v("pahh_over_mop")) == (1.02, 1.05)
    assert (v("flow_datasheet_pct_reading"), v("flow_datasheet_zero_kg_min")) == (0.5, 0.009) and v("flow_spec_pct_fs") == 1.0
    assert (v("h2_alarm_lfl"), v("h2_trip_lfl"), v("h2_detector_accuracy_lfl")) == (25.0, 50.0, 5.0)
    assert (v("solar_offset_light_k"), v("solar_offset_dark_k"), v("solar_peak_flux_w_m2")) == (10.0, 27.0, 1050.0)
    assert (v("ambient_july_max_c"), v("ambient_july_min_c"), v("ambient_record_c")) == (45.2, 29.6, 51.0)
    assert v("demand_weekend_factor") == 0.9 and v("fill_mean_kg") == 2.9 and v("fill_rate_kg_min") == 0.85
    assert v("demand_peak_hours") == ((7.0, 9.0), (17.0, 19.0)) and v("gas_temp_gradient_postfill_k") == (5.0, 10.0)
    assert v("flow_meter_delay_s") == (2.0, 9.0) and R.REGISTRY["prv_set_tolerance"].tag == "V2" and R.REGISTRY["flow_datasheet_zero_kg_min"].tag == "V1"
    names = {c["name"] for c in R.conflicts()}
    assert {"pah_over_mop", "pahh_over_mop", "prv_blowdown_nominal", "tprd_fitted", "flow_datasheet_pct_reading", "demand_weekend_factor",
            "solar_offset_light_k", "gas_temp_gradient_postfill_k", "demand_peak_hours", "fill_mean_kg"} <= names


def test_usage_is_recorded_and_the_cgh2_registry_never_leaks_into_lh2_manifests():
    from hydrai_twin import placeholders as PH
    R.reset_usage()
    PH.reset_usage()                  # the LH2 placeholder usage record is process-wide: earlier dataset tests leave it populated (the test was order-dependent)
    R.value("mop_bar_medium")
    assert [u["name"] for u in R.used()] == ["mop_bar_medium"]
    assert not {u["name"] for u in PH.used_placeholders()} & set(R.REGISTRY)           # separate registries
    assert not set(PH.REGISTRY) & {"mop_bar_medium", "pah_over_mop"}


def test_pressure_classes_follow_the_instruction():
    c = {n: make_class(n) for n in CLASS_NAMES}
    assert [c[n].mop_bar for n in CLASS_NAMES] == [50.0, 300.0, 350.0]
    for n in CLASS_NAMES:
        k = c[n]
        assert k.mawp_bar == pytest.approx(1.10 * k.mop_bar) and k.pah_bar == pytest.approx(1.02 * k.mop_bar) and k.pahh_bar == pytest.approx(1.05 * k.mop_bar)
        assert k.comp_start_bar == pytest.approx(0.85 * k.mop_bar) and k.comp_stop_bar == k.mop_bar
        assert k.transmitter_range_bar > 1.10 * 1.10 * k.mop_bar                       # the transmitter ranges above full relief lift
        assert 3600 * 0.1 < k.tau_wall_ambient_s() < 3600 * 24 and k.tau_gas_wall_s() > 60     # hours-scale shell time constants, follow from the wall
    assert c["medium"].tau_wall_ambient_s() > c["low"].tau_wall_ambient_s()               # thicker wall -> slower shell
    assert make_class("medium").to_dict()["tau_gas_wall_s"] > 0


def test_stop_policy_is_compensated_by_default_and_fixed_is_a_switch():
    assert resolve_stop_policy("medium", "light") == ("compensated", 60.0) and resolve_stop_policy("high", "light") == ("compensated", 60.0)
    assert resolve_stop_policy("medium", "light", "fixed") == ("fixed", 0.0)
    assert resolve_stop_policy("medium", "dark") == ("compensated", 70.0)
    assert resolve_stop_policy("low", "light") == ("compensated", 65.0)
    assert resolve_stop_policy("medium", "light", "compensated", 55.0) == ("compensated", 55.0) and resolve_stop_policy("low", "light", "fixed")[0] == "fixed"
