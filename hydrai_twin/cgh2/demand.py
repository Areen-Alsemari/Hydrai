"""
Demand on one module: the dispenser draws gas from the storage vessel.

  pattern 1 "refuelling": Poisson fills, bimodal daily intensity (07-09 and 17-19, NREL 2023, V1), weekend factor 0.9 (V1) applied to
      Friday/Saturday (the Saudi weekend; JUDGE), light-duty fills of mean ~2.9 kg at ~0.85 kg/min (NREL, V1; spread JUDGE, clipped
      1-6 kg), rare bus fills 20-40 kg at 3.5 kg/min (30 kg in <=10 min, V1); daily total 20-50 kg per module (instruction).
  pattern 2 "industrial": a cyclic buffer, one draw of 8-15 kg every 3-5 h (JUDGE).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hydrai_twin.cgh2 import registry as R

DAY = 86400.0


@dataclass(frozen=True)
class Fill:
    t0: float
    mass_kg: float
    rate_kg_s: float

    @property
    def t1(self) -> float:
        return self.t0 + self.mass_kg / self.rate_kg_s


def hourly_intensity() -> np.ndarray:
    """Fraction of a day's fills in each hour (sums to 1): bimodal peaks 07-09 and 17-19 over a low floor."""
    h = np.arange(24) + 0.5
    f = np.full(24, 0.15)
    for lo, hi in R.value("demand_peak_hours"):
        c, w = 0.5 * (lo + hi), 0.5 * (hi - lo)
        f += np.exp(-0.5 * ((h - c) / max(w, 0.5)) ** 2)
    return f / f.sum()


def _no_overlap(fills: list[Fill], gap_s: float = 60.0) -> list[Fill]:
    out: list[Fill] = []
    for f in sorted(fills, key=lambda x: x.t0):
        t0 = f.t0 if not out else max(f.t0, out[-1].t1 + gap_s)
        out.append(Fill(t0, f.mass_kg, f.rate_kg_s))
    return out


def refuelling_schedule(rng: np.random.Generator, horizon_s: float, start_weekday: int, kg_per_day: float, demand_mult: float = 1.0,
                        max_fill_kg: float | None = None) -> list[Fill]:
    mean_light = R.value("fill_mean_kg")
    lo, hi = R.value("fill_size_clip_kg")
    p_bus = R.value("bus_fill_probability")
    bus_lo, bus_hi = R.value("bus_fill_kg")
    if max_fill_kg is not None and bus_lo > max_fill_kg:
        p_bus = 0.0                                            # a store too small for a bus fill serves light-duty vehicles only
    if max_fill_kg is not None:
        hi = min(hi, max_fill_kg)
    mean_mass = (1 - p_bus) * mean_light + p_bus * 0.5 * (bus_lo + bus_hi)
    pdf = hourly_intensity()
    fills: list[Fill] = []
    n_days = int(np.ceil(horizon_s / DAY))
    for d in range(n_days):
        weekday = (start_weekday + d) % 7
        factor = R.value("demand_weekend_factor") if weekday in (4, 5) else 1.0           # Friday, Saturday
        n = rng.poisson(kg_per_day * demand_mult * factor / mean_mass)
        for _ in range(n):
            hour = rng.choice(24, p=pdf)
            t0 = d * DAY + hour * 3600.0 + rng.uniform(0, 3600.0)
            if rng.random() < p_bus:
                m, rate = rng.uniform(bus_lo, bus_hi), R.value("bus_fill_rate_kg_min") / 60.0
            else:
                m = float(np.clip(rng.lognormal(np.log(mean_light) - 0.5 * 0.35 ** 2, 0.35), lo, hi))
                rate = R.value("fill_rate_kg_min") / 60.0 * rng.uniform(0.85, 1.15)
            if t0 < horizon_s:
                fills.append(Fill(t0, float(m), float(rate)))
    return _no_overlap(fills)


def industrial_schedule(rng: np.random.Generator, horizon_s: float, demand_mult: float = 1.0, max_fill_kg: float | None = None) -> list[Fill]:
    period = rng.uniform(3.0, 5.0) * 3600.0
    t = rng.uniform(0.0, period)
    fills = []
    while t < horizon_s:
        m = rng.uniform(8.0, 15.0) * demand_mult
        fills.append(Fill(float(t + rng.normal(0, 0.1 * period)), float(m if max_fill_kg is None else min(m, max_fill_kg)), float(rng.uniform(0.5, 0.8) / 60.0)))
        t += period
    return _no_overlap([f for f in fills if 0 <= f.t0 < horizon_s])
