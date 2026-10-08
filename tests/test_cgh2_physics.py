import math

import numpy as np
import pytest

from hydrai_twin.cgh2 import demand as D
from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import make_class
from hydrai_twin.cgh2.dashboard import CGH2Dashboard
from hydrai_twin.cgh2.episode import CGH2EpisodeConfig, CGH2EpisodeGenerator, generate_cgh2_episode
from hydrai_twin.cgh2.profile import make_profile
from hydrai_twin.cgh2.vessel import PRV, Vessel
from hydrai_twin.channels import first_static_alarm_s

DAY = 86400.0
CLS = make_class("medium")


def vessel(P=300.0, T=300.0, blocked=False, cls=CLS, blow=0.07, h_gw=1.0):
    prv = PRV(cls.mawp_bar, blow, 1.10, 6.0, 0.8, stuck_closed=blocked)
    return Vessel(cls, prv, float(G.rho_PT(P, T)) * cls.volume_m3, T, T, h_gas_wall_mult=h_gw)


def gt(r, key, layer="slow"):
    return np.array([x["simulation_ground_truth"][key] for x in getattr(r, layer)])


# --- vessel physics -----------------------------------------------------------------------------------------------------------

def test_vessel_conserves_mass_and_reproduces_the_isochoric_pressure_sensitivity():
    v = vessel()
    P0, m0 = v.P_bar, v.m
    v.Tg = v.Tw = 310.0                                                   # heat 10 K at constant mass
    row = v.step(1.0, 310.0)
    assert v.m == pytest.approx(m0, rel=1e-9) and row["P_bar"] - P0 == pytest.approx(10.0 * G.dPdT_rho_bar_per_K(300.0, 305.0), rel=0.03)


def test_slow_leak_is_isothermal_and_fast_leak_is_adiabatic():
    slow, fast = vessel(), vessel()
    for _ in range(60):
        slow.step(60.0, 300.0, leak_area_m2=math.pi / 4 * (0.1e-3) ** 2, leak_cd=1.0)
    for _ in range(20):
        fast.step(1.0, 300.0, leak_area_m2=math.pi / 4 * (20e-3) ** 2, leak_cd=1.0)
    assert abs(slow.Tg - 300.0) < 0.5                                     # 0.5 kg/h: the wall holds the gas, isothermal
    assert fast.Tg < 300.0 - 15.0 and fast.m < 0.7 * 204                  # gas cools as it expands: adiabatic (and loses a lot of inventory in 20 s)


def test_isolated_discharge_cools_the_gas_and_charging_heats_it():
    cool, heat = vessel(h_gw=1e-6), vessel(h_gw=1e-6)
    for _ in range(100):
        cool.step(1.0, 300.0, mdot_disp=0.05)
        heat.step(1.0, 300.0, mdot_in=0.05, T_in_k=330.0)
    assert cool.Tg < 300.0 - 0.3 and heat.Tg > 300.0 + 0.3


def test_prv_pops_at_set_lifts_to_accumulation_and_reseats_after_the_blowdown():
    v = vessel(P=329.0)
    prv = v.prv
    prv.update(329.0); assert not prv.open
    prv.update(330.5); assert prv.open and prv.lift_events == 1
    prv.update(0.5 * (330.0 + 363.0)); assert 0.4 < prv.lift < 0.6
    prv.update(364.0); assert prv.lift == 1.0                              # full lift at 110 % accumulation
    prv.update(320.0); assert prv.open                                     # still open: reseat is at 7 % below set = 306.9
    prv.update(306.0); assert not prv.open and prv.lift == 0.0
    stuck = PRV(330.0, 0.07, 1.10, 6.0, 0.8, stuck_closed=True)
    stuck.update(400.0); assert not stuck.open and stuck.mass_rate(400.0, 300.0) == 0.0


def test_stuck_compressor_reaches_alarms_then_relief_and_blocked_relief_fails():
    def run(blocked):
        v = vessel(blocked=blocked); t = 0.0; hit = {}
        while t < 4 * DAY and "fail" not in hit and not (not blocked and "lift" in hit):
            row = v.step(30.0, 300.0, 20 / 3600.0, 315.0); t += 30.0
            for k, lim in (("PAH", CLS.pah_bar), ("PAHH", CLS.pahh_bar)):
                hit.setdefault(k, t) if row["P_bar"] >= lim else None
            if row["prv_open"]:
                hit.setdefault("lift", t)
            if row["P_bar"] > 1.5 * CLS.mawp_bar:
                hit["fail"] = t
        return hit
    ok, bad = run(False), run(True)
    assert ok["PAH"] < ok["PAHH"] < ok["lift"] and ok["PAH"] == pytest.approx(0.12 * 3600, rel=0.3)
    assert "fail" in bad and bad["fail"] / 3600 == pytest.approx(4.3, rel=0.2)


def test_hydrogen_at_300_bar_is_less_dense_than_ideal_gas_Z_above_1():
    ideal = 300e5 * 2.01588e-3 / (8.314462618 * 300.0)
    z = ideal / float(G.rho_PT(300.0, 300.0))
    assert 1.15 < z < 1.22                                                  # compressibility factor of hydrogen at 300 bar, 300 K


# --- episodes: healthy behaviour ------------------------------------------------------------------------------------------------

def test_healthy_medium_runs_have_zero_static_alarms_with_all_alarms_active():
    """Step 5b: diurnal swing, post-fill cooling and demand cycles must not alarm (PAH/PAHH, TAH and H2 active)."""
    d = CGH2Dashboard.reference("medium")
    for mi, mod in enumerate(("M01", "M03", "M05")):
        for pat in ("refuelling", "industrial"):
            r = generate_cgh2_episode(fault_id=0, seed=300 + mi, module_id=mod, profile=make_profile(mod, 20260401), days=14.0, demand_pattern=pat)
            a = first_static_alarm_s(r.slow, d)
            assert a["any"] is None, (mod, pat, a["by_channel"])
            m = r.meta
            assert m["prv_lift_events"] == 0 and m["ended_reason"] is None and abs(m["mass_residual_kg"]) < 1e-6
            assert m["stop_mode"] == "compensated" and m["compensation_ref_temp_c"] == 60.0
            P = gt(r, "pressure_bar_a")
            assert P.max() < CLS.pah_bar and P.min() > 0.5 * CLS.mop_bar


def test_compensated_stop_starts_and_stops_on_the_compensated_pressure_and_never_exceeds_mop_at_the_reference_temperature():
    r = generate_cgh2_episode(fault_id=0, seed=21, days=14.0)
    rho = gt(r, "mass_kg") / CLS.volume_m3
    Pc = np.asarray(G.pressure_bar(rho, 333.15))                                  # pressure the same gas would have at 60 C
    on = gt(r, "compressor_on").astype(bool)
    starts = np.flatnonzero(on[1:] & ~on[:-1]) + 1; stops = np.flatnonzero(~on[1:] & on[:-1]) + 1
    assert len(starts) >= 5 and np.all(Pc[starts] < 0.86 * 300) and np.all(np.abs(Pc[stops] - 300.0) < 3.0)
    assert gt(r, "pressure_bar_a").max() < CLS.pah_bar - 3.0                       # real margin below PAH


def test_dark_vessel_alarms_with_a_fixed_stop_and_is_held_by_the_compensated_stop():
    d = CGH2Dashboard.reference("medium")
    alarms = {"fixed": 0, "auto": 0}
    for mi, mod in enumerate(("M01", "M02", "M04", "M05")):
        for stop in alarms:
            r = generate_cgh2_episode(fault_id=0, seed=700 + mi, module_id=mod, profile=make_profile(mod, 20260401), days=14.0, solar="dark", stop_mode=stop)
            alarms[stop] += first_static_alarm_s(r.slow, d)["any"] is not None
            if stop == "auto":
                assert r.meta["stop_mode"] == "compensated" and r.meta["compensation_ref_temp_c"] == 70.0
    assert alarms["fixed"] >= 2 and alarms["auto"] == 0


def test_low_class_needs_the_compensated_stop_and_stays_quiet_with_it():
    d = CGH2Dashboard.reference("low")
    r = generate_cgh2_episode(fault_id=0, seed=11, days=14.0, pressure_class="low")
    assert r.meta["stop_mode"] == "compensated" and first_static_alarm_s(r.slow, d)["any"] is None
    assert r.meta["demand_kg_per_day"] < 12.0                               # demand follows the 39 kg store
    fixed = generate_cgh2_episode(fault_id=0, seed=11, days=14.0, pressure_class="low", stop_mode="fixed")
    assert first_static_alarm_s(fixed.slow, d)["any"] is not None           # a fixed stop at MOP alarms: 2 % of 50 bar is 1 bar


def test_compressor_starts_below_85_percent_of_mop_and_stops_at_mop():
    r = generate_cgh2_episode(fault_id=0, seed=21, days=14.0, stop_mode="fixed")                   # the literal instruction: stop at MOP
    on = gt(r, "compressor_on").astype(bool); P = gt(r, "pressure_bar_a")
    starts = np.flatnonzero(on[1:] & ~on[:-1]) + 1; stops = np.flatnonzero(~on[1:] & on[:-1]) + 1
    assert len(starts) >= 5 and len(stops) >= 5
    assert np.all(P[starts] < 0.86 * 300) and np.all(P[starts] > 0.75 * 300)
    assert np.all(np.abs(P[stops] - 300.0) < 3.0)
    assert r.meta["compressor_stop_events"] == len(stops) or abs(r.meta["compressor_stop_events"] - len(stops)) <= 1


def test_gas_temperature_has_a_diurnal_swing_and_post_charge_cooling():
    r = generate_cgh2_episode(fault_id=0, seed=22, days=14.0)
    T, Tw = gt(r, "gas_temp_c"), gt(r, "outer_wall_temp_c")
    assert T.max() - T.min() > 10.0 and Tw.max() - Tw.min() > 5.0
    hours = (gt(r, "ambient_temp_c") * 0 + np.array([x["system_context"]["t_s"] for x in r.slow]) / 3600.0) % 24
    day = (hours > 12) & (hours < 17); night = (hours > 2) & (hours < 7)
    assert Tw[day].mean() > Tw[night].mean() + 3.0                             # shell follows ambient and the solar offset
    g = gt(r, "gas_gradient_k")
    assert g.max() > 4.0 and g.max() <= 10.5                                   # 5-10 K builds while charging ...
    on = gt(r, "compressor_on").astype(bool)
    stop = np.flatnonzero(~on[1:] & on[:-1])[0] + 1
    assert g[min(stop + 120, len(g) - 1)] < 0.5 * g[stop]                       # ... and decays over the gas-wall time constant after the stop


def test_demand_schedules_follow_the_register_and_addendum():
    rng = np.random.default_rng(3)
    f = D.refuelling_schedule(rng, 56 * DAY, 0, 35.0)
    kg_day = sum(x.mass_kg for x in f) / 56
    assert 25.0 < kg_day < 50.0
    light = [x for x in f if x.mass_kg < 10]
    assert np.mean([x.mass_kg for x in light]) == pytest.approx(2.9, rel=0.2) and np.mean([x.rate_kg_s * 60 for x in light]) == pytest.approx(0.85, rel=0.1)
    assert all(a.t1 <= b.t0 for a, b in zip(f, f[1:]))                          # fills never overlap
    hour = np.array([int((x.t0 % DAY) // 3600) for x in f])
    assert np.mean(np.isin(hour, (7, 8, 17, 18))) > 0.45 and np.mean(np.isin(hour, (10, 11, 12, 13))) < 0.10      # bimodal 07-09 / 17-19
    wk = np.array([int(x.t0 // DAY) % 7 for x in f])
    ratio = np.mean([np.sum(wk == d) for d in (4, 5)]) / np.mean([np.sum(wk == d) for d in (0, 1, 2, 3, 6)])
    assert 0.7 < ratio < 1.1                                                    # weekend factor 0.9
    big = [x for x in f if x.mass_kg >= 20]
    assert all(20 <= x.mass_kg <= 40 and (x.t1 - x.t0) <= 12 * 60 for x in big)
    assert all((x.t1 - x.t0) <= 10 * 60 for x in big if x.mass_kg <= 30)         # bus fills: 30 kg in <= 10 min
    ind = D.industrial_schedule(np.random.default_rng(4), 14 * DAY)
    assert 40 < sum(x.mass_kg for x in ind) / 14 < 90 and all(a.t1 <= b.t0 for a, b in zip(ind, ind[1:]))
    assert not [x for x in D.refuelling_schedule(np.random.default_rng(5), 14 * DAY, 0, 35.0, max_fill_kg=9.0) if x.mass_kg > 9.0]


def test_deterministic_and_paired_twin_shares_the_world_before_onset():
    a = generate_cgh2_episode(fault_id=0, seed=9, days=5.0, onset_day_range=(2.0, 3.0), compute_observability=False)
    b = generate_cgh2_episode(fault_id=3, seed=9, days=5.0, onset_day_range=(2.0, 3.0), leak_diameter_mm=0.5, compute_observability=False)
    on = b.meta["onset_s"]
    pre = [(x, y) for x, y in zip(a.slow, b.slow) if x["system_context"]["t_s"] < on]
    assert len(pre) > 2000
    assert all(x["measurements"] == y["measurements"] and x["simulation_ground_truth"]["pressure_bar_a"] == y["simulation_ground_truth"]["pressure_bar_a"] for x, y in pre)
    assert generate_cgh2_episode(fault_id=0, seed=9, days=2.0).slow == generate_cgh2_episode(fault_id=0, seed=9, days=2.0).slow
    assert a.slow != generate_cgh2_episode(fault_id=0, seed=10, days=5.0, onset_day_range=(2.0, 3.0), compute_observability=False).slow
