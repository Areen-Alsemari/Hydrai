"""MODELLED operator, not a human study.

A simulated operator who has only the dashboard and looks at it every `period` minutes (15 or 60). At a look he sees the current raw values and flags the unit when

  * pressure: the raw pressure is below the expected envelope by more than X. The envelope the operator expects is the compressor's working band, so its floor is the
    compressor start pressure (85 % of MOP); X is a fraction of MOP;
  * temperature: the raw gas temperature is above the ambient temperature by more than Y kelvin (a hot vessel relative to its surroundings);
  * (expert variant) instead of the raw pressure he reads the TEMPERATURE-COMPENSATED INVENTORY (real-gas density from the raw pressure and temperature) and flags when it is
    below the inventory at the compressor start pressure at the compensation reference temperature by more than Z (fraction of the class inventory).

X, Y and Z are set on HEALTHY dev data only, each rule at the same budget of 1 false alarm per week (alarm events merged within 1 h, as for every other detector), and are
never touched again: no fault data and no unseen / OOD data are used to set them. A look is a single glance: no averaging beyond what the displayed raw value already is.
Everything is a modelling assumption of how an attentive operator reads a trend screen; it is not evidence about real operators.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from hydrai_twin.cgh2_agent.tools.common import inventory
from ml.cgh2_baselines import MAX_ON_FRACTION
from ml.classical_baselines import count_events

WEEK_S = 7 * 86400.0
PERIODS = (15, 60)
BUDGET_PER_WEEK = 1.0
KINDS = ("pressure", "temperature", "inventory")


def stats(unit) -> dict[str, np.ndarray]:
    """Per-tick deficits the operator's rules look at (all 'larger = more alarming')."""
    cls = unit.cls
    P, T, Ta = unit.raw.x["P"], unit.raw.x["T"], unit.raw.x["Ta"]
    mop = cls["mop_bar"]
    ref = unit.entry.get("compensation_ref_temp_c") or 60.0
    I = inventory(P, T, cls["volume_m3"])
    I_lo = float(inventory(np.array([cls["comp_start_bar"]]), np.array([ref]), cls["volume_m3"])[0])
    return {"pressure": (cls["comp_start_bar"] - P) / mop, "temperature": T - Ta, "inventory": (I_lo - I) / unit.raw.inv_ref_kg}


def look_ticks(unit, period_min: int) -> np.ndarray:
    return (np.round(unit.t / 60.0).astype(int) % period_min == 0) & (unit.t > 86400.0)


def calibrate(healthy_units: list, period_min: int) -> dict[str, float]:
    """Smallest threshold per rule such that the healthy dev units raise at most BUDGET_PER_WEEK alarm events per week at this look period (bisection on the event count)."""
    out = {}
    weeks = sum((u.t[-1] - 86400.0) / WEEK_S for u in healthy_units)
    data = []
    for u in healthy_units:
        data.append((u.t, stats(u), look_ticks(u, period_min)))
    for k in KINDS:
        series = [(t, np.where(m, s[k], -np.inf)) for t, s, m in data]
        vals = np.concatenate([v[np.isfinite(v)] for _, v in series])
        # same guard as every other detector: a statistic that is always above its threshold merges into one event per episode and passes any event budget, so the
        # rule may be on for at most MAX_ON_FRACTION of the looks and the search starts above that floor
        lo, hi = float(np.quantile(vals, 1.0 - MAX_ON_FRACTION)), float(np.max(vals))
        budget = BUDGET_PER_WEEK * weeks
        if sum(count_events(t, v > lo) for t, v in series) <= budget:
            out[k] = lo
            continue
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if sum(count_events(t, v > mid) for t, v in series) <= budget:
                hi = mid
            else:
                lo = mid
        out[k] = hi
    return out


def flags(unit, thr: dict[str, float], period_min: int, expert: bool = False) -> np.ndarray:
    s, m = stats(unit), look_ticks(unit, period_min)
    low = s["inventory" if expert else "pressure"] > thr["inventory" if expert else "pressure"]
    return m & (low | (s["temperature"] > thr["temperature"]))


def flags_pressure_only(unit, thr: dict[str, float], period_min: int) -> np.ndarray:
    s, m = stats(unit), look_ticks(unit, period_min)
    return m & (s["pressure"] > thr["pressure"])


def thresholds_cached() -> dict[int, dict[str, float]]:
    """Thresholds per look period, set ONCE on healthy dev units and cached (output/cgh2_cache/agent/operator_thresholds.json); never refitted on anything else."""
    import json

    from hydrai_twin.cgh2_agent import fusion as F
    from hydrai_twin.cgh2_agent.session import get_units
    path = F.CACHE / "operator_thresholds.json"
    if path.exists():
        return {int(k): v for k, v in json.loads(path.read_text()).items()}
    _, units = get_units()
    healthy = [u for u in units.values() if u.entry["role"] == "dev" and u.entry["fault_id"] == 0 and u.entry["scenario_class"] == "standard" and "dark" not in u.entry["variant_tag"]]
    out = {p: calibrate(healthy, p) for p in PERIODS}
    path.write_text(json.dumps(out, indent=1))
    return out
