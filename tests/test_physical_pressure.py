"""Validation, valve, conservation and liquid-full tests for the physically
driven pressure model (ullage.py, valves.py, physical_tank.py).

Source-backed expectations come from the verification register
(VALVE_VENT_SOURCE_VERIFICATION.md): K-site Table 1 (S16), and the workbook's
Sec. 7 boil-off ladder. Everything valve-related uses PLACEHOLDER parameters,
so those tests check behavior (hysteresis, conservation, relative scaling),
not engineering numbers.
"""

import math

import pytest

from hydrai_twin import constants as C
from hydrai_twin import placeholders as PH
from hydrai_twin.physical_tank import PhysicalTank, PhysicalTankConfig, calibrated_healthy_flux_w_m2
from hydrai_twin.ullage import TankThermo, liquid_full_pressure_bar_a, stratification_ratio
from hydrai_twin.valves import PCV, PRV, vent_flow_kg_s

DAY = 86400.0

# K-site (S16) Table 1: (flux W/m2, fill, mid tank pressure kPa, homogeneous kPa/hr, measured kPa/hr)
KSITE = [
    (0.35, 0.83, 124.5, 0.198, 0.223),
    (2.0, 0.29, 165.5, 2.73, 3.82),
    (2.0, 0.49, 152.0, 1.86, 2.72),
    (2.0, 0.83, 165.5, 1.46, 3.47),
    (3.5, 0.29, 193.0, 4.83, 8.21),
    (3.5, 0.49, 193.0, 3.71, 6.07),
    (3.5, 0.83, 193.0, 2.63, 8.14),
]


# --- validation against sourced data ---------------------------------------

@pytest.mark.parametrize("q,fill,p_kpa,hsp,_measured", KSITE)
def test_core_matches_ksite_homogeneous_column(q, fill, p_kpa, hsp, _measured):
    t = TankThermo(4.89, fill, p_kpa / 100.0)
    p0 = t.p_pa
    t.step(60.0, q * 14.0)
    rate_kpa_hr = (t.p_pa - p0) / 60.0 * 3600.0 / 1e3
    assert abs(rate_kpa_hr / hsp - 1.0) < 0.10


@pytest.mark.parametrize("q,fill,p_kpa,hsp,measured", KSITE)
def test_stratification_ratio_reproduces_ksite_measured_over_homogeneous(q, fill, p_kpa, hsp, measured):
    assert abs(stratification_ratio(q, fill) - measured / hsp) < 0.05


def test_stratification_ratio_grows_with_flux():
    ratios = [stratification_ratio(f, 0.83) for f in (0.35, 1.0, 2.0, 3.0, 3.5)]
    assert ratios == sorted(ratios)


def test_boiloff_tiers_are_calibrated_separately_not_blended():
    base = calibrated_healthy_flux_w_m2(PhysicalTankConfig(boiloff_mode="baseline"))
    target = calibrated_healthy_flux_w_m2(PhysicalTankConfig(boiloff_mode="target"))
    assert abs(base / target - 3.0) < 0.03          # 0.30 vs 0.10 %/day


# --- conservation ------------------------------------------------------------

def test_closed_tank_conserves_mass_and_energy():
    t = TankThermo(10.0, 0.85, 1.2)
    m0, u0 = t.m, t.U
    q, dt, n = 9.2, 600.0, 144   # one day
    for _ in range(n):
        t.step(dt, q)
    assert t.m == m0
    assert t.U - u0 == pytest.approx(q * dt * n, rel=1e-9)


def test_total_mass_bookkeeping_with_venting():
    pt = PhysicalTank(PhysicalTankConfig())
    pt.run(40 * DAY, record_every_s=3600)
    assert pt.total_mass0_kg - pt.tank.m == pytest.approx(pt.vented_kg, rel=1e-9)


def test_energy_bookkeeping_with_venting_across_liquid_full():
    # blocked PCV + high flux at 90% fill passes through liquid-full and PRV relief of liquid
    pt = PhysicalTank(PhysicalTankConfig(fill_frac=0.90), pcv=PCV(fault="stuck_closed"))
    u0, expected = pt.tank.U, 0.0
    saw_liquid = False
    while pt.t_s < 6 * DAY and pt.ended_reason is None:
        h_vent = pt.tank.h_vent
        row = pt.step(300.0, 5.0)
        saw_liquid |= row["vent_is_liquid"]
        expected += (row["q_w"] - (row["vent_pcv_kg_s"] + row["vent_prv_kg_s"]) * h_vent) * row["dt_s"]
        if pt.t_s > 4 * DAY and saw_liquid:
            break
    assert saw_liquid
    assert pt.tank.U - u0 == pytest.approx(expected, rel=1e-9)


# --- valve behavior ----------------------------------------------------------

def test_pcv_hysteresis():
    v = PCV()
    for p, expect in [(1.45, False), (1.50, True), (1.46, True), (1.44, True), (1.43, False), (1.46, False)]:
        v.update(p)
        assert v.is_open is expect, (p, v.is_open)


def test_pcv_faults():
    stuck_c, stuck_o = PCV(fault="stuck_closed"), PCV(fault="stuck_open")
    for p in (1.0, 1.6, 3.0):
        stuck_c.update(p); stuck_o.update(p)
        assert stuck_c.is_open is False and stuck_o.is_open is True
    with pytest.raises(ValueError):
        PCV(fault="jammed")


def test_blocked_vent_passes_less_than_open_vent():
    tank = TankThermo(10.0, 0.85, 1.5)
    ok, blocked = PCV(), PCV(fault="blocked")
    ok.is_open = blocked.is_open = True
    assert 0 < blocked.flow_kg_s(tank) < 0.1 * ok.flow_kg_s(tank)


def test_prv_lift_reseat_and_proportional_opening():
    v = PRV()
    for p, expect in [(5.99, False), (6.0, True), (5.8, True), (5.71, True), (5.69, False)]:
        v.update(p)
        assert v.is_open is expect, (p, v.is_open)
    v.is_open = True
    assert v.open_fraction(6.0) == pytest.approx(0.0)
    assert v.open_fraction(6.3) == pytest.approx(0.5)
    assert v.open_fraction(6.6) == pytest.approx(1.0)
    assert v.open_fraction(7.5) == 1.0


def _liquid_full_tank():
    t = TankThermo(10.0, 0.95, 1.2)
    for _ in range(60):
        t.step(600.0, 2000.0)
        if t.liquid_full:
            return t
    raise AssertionError("tank never went liquid-full")


def test_vent_flow_is_far_larger_for_liquid_than_vapor_at_same_area_and_pressure():
    liq = _liquid_full_tank()
    vap = TankThermo(10.0, 0.75, liq.p_bar_a)
    assert liq.liquid_full and not vap.liquid_full
    assert vent_flow_kg_s(1e-4, 0.62, 0.62, liq) > 5.0 * vent_flow_kg_s(1e-4, 0.62, 0.62, vap)


# --- healthy operation -------------------------------------------------------

@pytest.mark.parametrize("mode,days", [("baseline", 90), ("target", 240)])
def test_steady_boiloff_emerges_at_the_calibrated_sec7_rate(mode, days):
    cfg = PhysicalTankConfig(boiloff_mode=mode)
    pt = PhysicalTank(cfg)
    m_liq0 = pt.tank.m_l
    rows = pt.run(days * DAY, record_every_s=120)
    edges, prev = [], False
    for r in rows:
        if r["pcv_open"] and not prev:
            edges.append(r["t_s"])
        prev = r["pcv_open"]
    assert len(edges) >= 8
    t0, t1 = edges[1], edges[-1]
    vented = sum(r["vent_pcv_kg_s"] * 120.0 for r in rows if t0 <= r["t_s"] < t1)
    kg_per_day = vented / ((t1 - t0) / DAY)
    expected = C.BOILOFF_LADDER_PCT_PER_DAY[mode]["normal"] / 100.0 * m_liq0
    assert kg_per_day == pytest.approx(expected, rel=0.05)


def test_healthy_pressure_stays_in_band_and_never_reaches_liquid_full_or_prv():
    pt = PhysicalTank(PhysicalTankConfig())
    rows = pt.run(60 * DAY, record_every_s=300)
    lo, hi = PCV().close_bar_a, PCV().open_bar_a
    assert all(lo - 0.02 <= r["p_bar_a"] <= hi + 0.02 or r["p_bar_a"] < lo for r in rows)
    assert max(r["p_bar_a"] for r in rows) < hi + 0.05
    assert pt.liquid_full_events == 0 and pt.prv_lift_events == 0


def test_healthy_cycle_period_scales_with_heat_leak():
    def period(mode):
        rows = PhysicalTank(PhysicalTankConfig(boiloff_mode=mode)).run(120 * DAY, record_every_s=120)
        edges, prev = [], False
        for r in rows:
            if r["pcv_open"] and not prev:
                edges.append(r["t_s"])
            prev = r["pcv_open"]
        gaps = [(b - a) / DAY for a, b in zip(edges[1:], edges[2:])]
        return sum(gaps) / len(gaps)
    p_base, p_target = period("baseline"), period("target")
    assert 0.8 < p_base < 2.0
    assert 2.5 < p_target / p_base < 3.5


# --- faults on a physical timescale -----------------------------------------

def _time_to(pt, pressure_bar, flux=None, horizon_days=400):
    rows = pt.run(horizon_days * DAY, flux_fn=(lambda t: flux) if flux is not None else None,
                  record_every_s=3600, stop_when=lambda r: r["p_bar_a"] >= pressure_bar)
    return rows[-1]["t_s"] if rows and rows[-1]["p_bar_a"] >= pressure_bar else None


def test_stuck_closed_pcv_pressure_keeps_rising_on_a_days_scale():
    t15 = _time_to(PhysicalTank(PhysicalTankConfig(), pcv=PCV(fault="stuck_closed")), 1.5)
    t20 = _time_to(PhysicalTank(PhysicalTankConfig(), pcv=PCV(fault="stuck_closed")), 2.0)
    assert 4 * DAY < t15 < 9 * DAY      # K-site-scale: ~0.2 kPa/hr at the healthy flux
    assert t20 > t15 + 5 * DAY          # the workbook's 2.0 bar warning takes weeks, not minutes


def test_time_to_first_opening_scales_inversely_with_flux():
    base = calibrated_healthy_flux_w_m2(PhysicalTankConfig())

    def first_open(mult):
        pt = PhysicalTank(PhysicalTankConfig())
        rows = pt.run(60 * DAY, flux_fn=lambda t: base * mult, record_every_s=600, stop_when=lambda r: r["pcv_open"])
        return rows[-1]["t_s"]
    ratio = first_open(1.0) / first_open(2.5)
    assert 2.0 < ratio < 3.0


# --- liquid-full boundary ----------------------------------------------------

def test_liquid_full_pressure_matches_reported_values_and_straddles_mawp():
    # (fill, reported bar abs). The reported figures depend on the unstated starting pressure,
    # so the check is that each lies inside my independent range over p0 = 1.013-1.5 bar.
    for fill, reported in [(0.75, 8.9), (0.85, 5.75), (0.90, 4.1), (0.95, 2.65)]:
        lo = liquid_full_pressure_bar_a(fill, 1.013)
        hi = liquid_full_pressure_bar_a(fill, 1.5)
        assert lo <= reported <= hi, (fill, lo, reported, hi)
    # the hazard: the workbook's 85% nominal fill goes liquid-full BELOW MAWP; 75% does not
    assert liquid_full_pressure_bar_a(0.75, 1.2) > C.PRESSURE_MAWP_BAR > liquid_full_pressure_bar_a(0.85, 1.2)
    p = [liquid_full_pressure_bar_a(f, 1.2) for f in (0.75, 0.85, 0.90, 0.95)]
    assert p == sorted(p, reverse=True)


def test_simulation_goes_liquid_full_at_the_predicted_pressure():
    pt = PhysicalTank(PhysicalTankConfig(fill_frac=0.85), pcv=PCV(fault="stuck_closed"))
    predicted = liquid_full_pressure_bar_a(0.85, pt.tank.p_bar_a)
    while not pt.tank.liquid_full and pt.t_s < 30 * DAY:
        pt.step(60.0, 20.0)
    assert pt.tank.liquid_full
    assert pt.tank.p_bar_a == pytest.approx(predicted, rel=0.03)
    assert pt.tank.p_bar_a < C.PRESSURE_MAWP_BAR


def test_pressure_response_is_steeper_once_liquid_full_and_matches_the_eos():
    import CoolProp.CoolProp as CP

    def eos_slope_pa_per_j(m, u_total, volume=10.0, d=20.0):
        rho, u = m / volume, u_total / m
        hi = CP.PropsSI("P", "Dmass", rho, "Umass", u + d, "Hydrogen")
        lo = CP.PropsSI("P", "Dmass", rho, "Umass", u - d, "Hydrogen")
        return (hi - lo) / (2 * d * m)

    t = TankThermo(10.0, 0.85, 1.2)
    q, dt = 522.0, 60.0
    hist = []
    while not t.liquid_full:
        hist.append((t.m, t.U, t.p_pa))
        t.step(dt, q)
    # two-phase side: last 5 steps before the transition
    sim_two = (hist[-1][2] - hist[-6][2]) / (5 * q * dt)
    m5, u5, _ = hist[-3]
    assert sim_two == pytest.approx(eos_slope_pa_per_j(m5, u5), rel=0.05)
    # liquid-full side: the next 3 steps
    p0 = t.p_pa
    for _ in range(3):
        t.step(dt, q)
    sim_liq = (t.p_pa - p0) / (3 * q * dt)
    assert sim_liq == pytest.approx(eos_slope_pa_per_j(t.m, t.U), rel=0.10)
    assert sim_liq > 10.0 * sim_two      # ~14x at this state (real-EOS value, not a tuned factor)


def test_prv_passes_liquid_at_90_percent_fill_and_pressure_recovers():
    pt = PhysicalTank(PhysicalTankConfig(fill_frac=0.90), pcv=PCV(fault="stuck_closed"))
    rows = pt.run(8 * DAY, flux_fn=lambda t: 5.0, record_every_s=300)
    assert pt.liquid_full_events >= 1 and pt.liquid_vented_kg > 5.0
    assert pt.prv_lift_events >= 1
    assert max(r["p_bar_a"] for r in rows) < 1.15 * pt.prv.lift_bar_a      # relief holds the accumulation
    first_full = next(i for i, r in enumerate(rows) if r["liquid_full"])
    assert any(not r["liquid_full"] for r in rows[first_full:])             # leaves liquid-full again


def test_75_percent_fill_relieves_vapor_never_liquid():
    pt = PhysicalTank(PhysicalTankConfig(fill_frac=0.75), pcv=PCV(fault="stuck_closed"))
    pt.run(8 * DAY, flux_fn=lambda t: 5.0, record_every_s=600)
    assert pt.prv_lift_events >= 1
    assert pt.liquid_full_events == 0 and pt.liquid_vented_kg == 0.0


def test_running_dry_ends_the_run_cleanly_instead_of_raising():
    pt = PhysicalTank(PhysicalTankConfig(fill_frac=0.75), pcv=PCV(fault="stuck_closed"))
    pt.run(60 * DAY, flux_fn=lambda t: 50.0, record_every_s=3600)
    assert pt.ended_reason is not None and "dry" in pt.ended_reason


def test_unknown_stratification_mode_is_rejected():
    with pytest.raises(ValueError):
        PhysicalTank(PhysicalTankConfig(stratification="magic"))


# --- placeholder flagging ----------------------------------------------------

def test_every_registry_entry_is_documented_and_placeholders_name_a_question():
    assert PH.REGISTRY
    for p in PH.REGISTRY.values():
        assert p.basis.strip()
        assert p.level in ("placeholder", "literature")
        assert p.question is not None and p.question.startswith("Q")


def test_first_fill_cap_is_a_flagged_unverified_placeholder_and_rows_report_it():
    entry = PH.REGISTRY["first_fill_max_fraction"]
    assert entry.level == "placeholder" and entry.question == "Q9b" and entry.value == 0.75
    assert "UNVERIFIED" in entry.basis and "FIRST fill" in entry.basis
    assert "max_fill_fraction" not in PH.REGISTRY      # old name must not linger
    assert PhysicalTank(PhysicalTankConfig(fill_frac=0.85)).step(60.0)["fill_above_first_fill_cap"] is True
    assert PhysicalTank(PhysicalTankConfig(fill_frac=0.75)).step(60.0)["fill_above_first_fill_cap"] is False


def test_used_placeholders_are_recorded_for_the_manifest():
    PH.reset_usage()
    PhysicalTank(PhysicalTankConfig()).step(60.0)
    names = {p["name"] for p in PH.used_placeholders()}
    assert {"pcv_open_bar_a", "pcv_deadband_bar", "prv_set_bar_a", "ambient_bar_a"} <= names
    assert all(p["question"] for p in PH.used_placeholders())
