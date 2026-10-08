"""Healthy pressure drift and fault timescales for each healthy boil-off tier (PLACEHOLDER valve parameters throughout).

    python scripts/timescale_tables.py        # both tiers, side by side: default 'baseline' 0.30 %/day and 'target' 0.10 %/day (spec)

Tank at the spec nominal fill (85 %), calibrated healthy wall flux for the tier (Sec. 7), PCV / PRV / pressure-builder from
the placeholder registry. The vacuum-loss rungs use absolute fluxes (heat leak ladder), so they do not depend on the tier.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hydrai_twin import constants as C
from hydrai_twin.physical_tank import PhysicalTank, PhysicalTankConfig, calibrated_healthy_flux_w_m2
from hydrai_twin.valves import PCV

DAY = 86400.0


def fmt(s):
    return "never (in window)" if s is None else (f"{s / DAY:6.1f} d" if s >= 2 * 3600 else f"{s / 3600:6.1f} h")


def first_time(pt, cond, horizon_s, **kw):
    try:
        rows = pt.run(horizon_s, stop_when=cond, record_every_s=3600, **kw)
    except RuntimeError:
        return None
    return rows[-1]["t_s"] if rows and cond(rows[-1]) else None


def tier(mode: str) -> dict:
    cfg = PhysicalTankConfig(boiloff_mode=mode, fill_frac=0.85)
    flux = calibrated_healthy_flux_w_m2(cfg)
    out = {"mode": mode, "pct": C.BOILOFF_LADDER_PCT_PER_DAY[mode]["normal"], "flux": flux}
    pt = PhysicalTank(cfg)
    rows = pt.run(120 * DAY, record_every_s=60)
    edges, prev = [], False
    for r in rows:
        if r["pcv_open"] and not prev:
            edges.append(r["t_s"])
        prev = r["pcv_open"]
    per = [(b - a) / DAY for a, b in zip(edges[1:], edges[2:])]
    out["cycle_d"] = sum(per) / len(per) if per else None
    # healthy rise between PCV close and the next open (steady cycle)
    close_p = min(r["p_bar_a"] for r in rows if r["t_s"] > edges[1]) if len(edges) > 1 else None
    open_p = max(r["p_bar_a"] for r in rows)
    out["band"] = (close_p, open_p)
    out["drift_kpa_h"] = (open_p - close_p) * 100.0 / (out["cycle_d"] * 24.0) if out["cycle_d"] else None
    out["first_open_d"] = edges[0] / DAY if edges else None
    out["vented_kg_60d"] = None
    pt2 = PhysicalTank(cfg)
    pt2.run(60 * DAY, record_every_s=3600)
    out["vented_kg_60d"] = pt2.vented_kg
    out["stuck"] = {}
    for tg in (1.5, 2.0, 3.0):
        p = PhysicalTank(cfg, pcv=PCV(fault="stuck_closed"))
        out["stuck"][tg] = first_time(p, lambda r, g=tg: r["p_bar_a"] >= g, 1500 * DAY)
    out["ins"] = {}
    for mult in (1.5, 2.5, 6.0, 10.0):
        p = PhysicalTank(cfg)
        out["ins"][mult] = first_time(p, lambda r: r["pcv_open"], 120 * DAY, flux_fn=lambda ts, m=mult: flux * m)
    return out


def main():
    res = [tier("baseline"), tier("target")]
    print("PLACEHOLDER valve/vent parameters (PCV opens 1.5 bar(a), 0.069 bar deadband; Q1 open)\n")
    hdr = f"{'':46}{'baseline (DEFAULT) 0.30 %/day':>30}{'target (spec) 0.10 %/day':>24}"
    print(hdr)
    f2 = lambda r, k, fmt_="{:.3f}": fmt_.format(r[k])
    print(f"{'healthy wall flux, W/m2':46}{res[0]['flux']:>30.3f}{res[1]['flux']:>24.3f}")
    print(f"{'first PCV opening after a fill, d':46}{res[0]['first_open_d']:>30.2f}{res[1]['first_open_d']:>24.2f}")
    print(f"{'steady PCV cycle period, d':46}{res[0]['cycle_d']:>30.2f}{res[1]['cycle_d']:>24.2f}")
    print(f"{'healthy pressure band, bar(a)':46}{res[0]['band'][0]:>20.3f}-{res[0]['band'][1]:<9.3f}{res[1]['band'][0]:>14.3f}-{res[1]['band'][1]:<8.3f}")
    print(f"{'healthy pressure drift between openings, kPa/h':46}{res[0]['drift_kpa_h']:>30.3f}{res[1]['drift_kpa_h']:>24.3f}")
    print(f"{'vented in 60 d, kg':46}{res[0]['vented_kg_60d']:>30.1f}{res[1]['vented_kg_60d']:>24.1f}")
    print("\nPCV stuck closed (from 1.2 bar(a) at healthy heat leak): time to reach")
    for tg, lab in ((1.5, "1.5 bar (top of normal band)"), (2.0, "2.0 bar (Sec. 5 warning)"), (3.0, "3.0 bar (Sec. 5 critical)")):
        print(f"   {lab:43}{fmt(res[0]['stuck'][tg]):>30}{fmt(res[1]['stuck'][tg]):>24}")
    print("\nInsulation degradation, heat-flux multiplier: first PCV opening")
    for mult in (1.5, 2.5, 6.0, 10.0):
        print(f"   x{mult:<4}{'':38}{fmt(res[0]['ins'][mult]):>30}{fmt(res[1]['ins'][mult]):>24}")


if __name__ == "__main__":
    main()
