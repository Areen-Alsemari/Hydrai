"""Demonstrate the physically-driven pressure model: validation against the
K-site homogeneous column, healthy venting cycle, and how valve/insulation/
vacuum faults actually unfold on a physical timescale.

Everything here uses PLACEHOLDER valve parameters (see placeholders.py); the
printed footer lists them. Run: python scripts/demo_physical_pressure.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import placeholders as PH
from hydrai_twin.physical_tank import PhysicalTank, PhysicalTankConfig, calibrated_healthy_flux_w_m2
from hydrai_twin.ullage import TankThermo, stratification_ratio
from hydrai_twin.valves import PCV

DAY = 86400.0


def fmt_t(s):
    if s is None:
        return "never (in window)"
    return f"{s/3600:7.1f} h ({s/DAY:5.2f} d)" if s >= 3600 else f"{s:7.0f} s"


def first_time(pt, cond, horizon_s, **run_kw):
    try:
        rows = pt.run(horizon_s, stop_when=cond, record_every_s=3600, **run_kw)
    except RuntimeError as e:  # tank left the two-phase region (e.g. went liquid-full)
        print(f"      (model stopped at t={pt.t_s/DAY:.1f} d, p={pt.tank.p_bar_a:.2f} bar(a): {e})")
        return None, []
    return rows[-1]["t_s"] if rows and cond(rows[-1]) else None, rows


def main():
    cfg = PhysicalTankConfig()
    base_flux = calibrated_healthy_flux_w_m2(cfg)
    print(f"healthy wall flux (calibrated to Sec.7 baseline 0.30 %/day): {base_flux:.3f} W/m2  = {base_flux*cfg.area_m2:.1f} W\n")

    print("== 1. Core vs K-site homogeneous column (NASA TM-105411 Table 1) ==")
    rows = [(0.35, .83, 124.5, 0.198), (2.0, .29, 165.5, 2.73), (2.0, .49, 152, 1.86), (2.0, .83, 165.5, 1.46),
            (3.5, .29, 193, 4.83), (3.5, .49, 193, 3.71), (3.5, .83, 193, 2.63)]
    for q, f, p, hsp in rows:
        t = TankThermo(4.89, f, p / 100)
        p0 = t.p_pa
        t.step(60.0, q * 14.0)
        rate = (t.p_pa - p0) / 60.0 * 3600 / 1e3
        print(f"   q={q:4.2f} W/m2 fill={f*100:3.0f}%  K-site {hsp:5.3f}  model {rate:5.3f} kPa/hr  ({rate/hsp-1:+.0%})")

    print("\n== 2. Healthy operation, 60 days ==")
    pt = PhysicalTank(cfg)
    rows = pt.run(60 * DAY, record_every_s=60)
    edges, prev = [], False
    for r in rows:
        if r["pcv_open"] and not prev:
            edges.append(r["t_s"])
        prev = r["pcv_open"]
    per = [(b - a) / DAY for a, b in zip(edges[1:], edges[2:])]
    print(f"   PCV openings: {len(edges)}; steady cycle period {sum(per)/len(per):.2f} d; pressure {min(r['p_bar_a'] for r in rows):.3f}-{max(r['p_bar_a'] for r in rows):.3f} bar(a)")
    print(f"   vented {pt.vented_kg:.1f} kg in 60 d (first 4-5 d vent nothing: pressure still rising to the PCV setpoint)")

    print("\n== 3. PCV stuck closed (healthy heat leak): when does pressure reach each level? ==")
    for target, label in ((1.5, "top of normal band"), (2.0, "workbook warning 2.0"), (3.0, "workbook critical 3.0"), (6.0, "PRV set / MAWP 6.0")):
        pt = PhysicalTank(cfg, pcv=PCV(fault="stuck_closed"))
        t, _ = first_time(pt, lambda r, tg=target: r["p_bar_a"] >= tg, 2000 * DAY)
        print(f"   to {target:3.1f} bar(a) ({label:22s}): {fmt_t(t)}" + (f"   [liquid-full first at {pt.liquid_full_events} event(s)]" if target >= 6.0 else ""))

    print("\n== 3b. Blocked PCV at 5 W/m2: what is the PRV passing when it lifts? (fill level matters) ==")
    for fill in (0.75, 0.85, 0.90):
        pt = PhysicalTank(PhysicalTankConfig(fill_frac=fill), pcv=PCV(fault="stuck_closed"))
        rows = pt.run(30 * DAY, flux_fn=lambda ts: 5.0, record_every_s=300)
        lf = next((r for r in rows if r["liquid_full"]), None)
        pl = next((r for r in rows if r["prv_open"]), None)
        print(f"   fill {fill:.0%}: liquid-full "
              + (f"at {lf['t_s']/3600:6.1f} h, {lf['p_bar_a']:.2f} bar" if lf else "never            ")
              + f" | first PRV lift {pl['t_s']/3600:6.1f} h" if pl else "   (no lift)")
        print(f"            liquid-full events {pt.liquid_full_events}, PRV lifts {pt.prv_lift_events}, "
              f"LIQUID vented {pt.liquid_vented_kg:.1f} kg of {pt.vented_kg:.0f} kg total"
              + (f", tank dry after {pt.t_s/3600:.0f} h" if pt.ended_reason else ""))

    print("\n== 4. Insulation degradation: heat-flux multiplier vs time to first PCV opening (PCV healthy) ==")
    for mult in (1.0, 1.5, 2.5, 6.0, 10.0):
        pt = PhysicalTank(cfg)
        t, _ = first_time(pt, lambda r: r["pcv_open"], 60 * DAY, flux_fn=lambda ts, m=mult: base_flux * m)
        print(f"   x{mult:4.1f} ({base_flux*mult:5.2f} W/m2): first PCV opening after {fmt_t(t)}")

    print("\n== 5. Stratification factor sensitivity (time 1.2 -> 1.5 bar) ==")
    for flux in (base_flux, 2.0, 3.5):
        out = []
        for mode in ("off", "empirical"):
            pt = PhysicalTank(PhysicalTankConfig(stratification=mode), pcv=PCV(fault="stuck_closed"))
            t, _ = first_time(pt, lambda r: r["p_bar_a"] >= 1.5, 60 * DAY, flux_fn=lambda ts, f=flux: f)
            out.append(t)
        print(f"   flux {flux:5.2f} W/m2 (K-site ratio {stratification_ratio(flux, 0.85):.2f}):  homogeneous {fmt_t(out[0])} | empirical {fmt_t(out[1])}")

    print("\n== 6. Vacuum ladder (PCV and PRV working) ==")
    for name in ("vacuum_flux_soft_w_m2", "vacuum_flux_lost_w_m2", "vacuum_flux_lost_high_w_m2"):
        flux = PH.value(name)
        pt = PhysicalTank(cfg)
        rows = pt.run(12 * 3600, flux_fn=lambda ts, f=flux: f, record_every_s=30)
        pmax = max(r["p_bar_a"] for r in rows)
        lifted = next((r["t_s"] for r in rows if r["prv_open"]), None)
        lfull = next((r["t_s"] for r in rows if r["liquid_full"]), None)
        peak_vent = max(r["vent_pcv_kg_s"] + r["vent_prv_kg_s"] for r in rows)
        end = (f"tank dry at {pt.t_s/3600:.1f} h" if pt.ended_reason else f"{rows[-1]['liquid_kg']:.0f} kg liquid left after 12 h")
        print(f"   {name:22s} {flux:7.1f} W/m2 = {flux*cfg.area_m2/1e3:6.1f} kW: peak {pmax:5.2f} bar(a), PRV lift {fmt_t(lifted)}, "
              f"liquid-full {fmt_t(lfull)}, peak vent {peak_vent:.3f} kg/s ({peak_vent*60:.1f} kg/min), liquid vented {pt.liquid_vented_kg:.1f} kg; {end}")

    print("\nPLACEHOLDERS USED (confirm or replace via ENGINEER_QUESTIONS_VALVE_VENT.md):")
    for p in PH.used_placeholders():
        print(f"   [{p['level']:11s}] {p['name']:32s} {p['value']:<10.4g} {p['unit']:8s} {p['question']}")


if __name__ == "__main__":
    main()
