"""
Small shared physics primitives used by both the normal-operation generator
(episode.py) and the fault-injection generator (fault_episode.py), so the
two don't diverge on math that should behave identically pre-fault.
"""

from __future__ import annotations

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin import materials


def ou_step(x: float, mean: float, theta: float, sigma: float, dt: float, rng: np.random.Generator) -> float:
    """One Euler-Maruyama step of an Ornstein-Uhlenbeck mean-reverting process."""
    return x + theta * (mean - x) * dt + sigma * np.sqrt(dt) * rng.normal()


def strain_ue(
    inner_wall_k: float,
    p_bar_a: float,
    radius_m: float = C.TANK_INTERNAL_RADIUS_M,
    thickness_m: float = C.WALL_THICKNESS_M,
    stress_concentration_factor: float = 1.0,
) -> tuple[float, float, float]:
    """(thermal_ue, pressure_ue, total_ue_clipped_to_sensor_range).

    thermal component: dL/L(T) (Sec. 4.2, corrected) referenced to 293 K,
    converted to microstrain.
    pressure component: thin-wall hoop stress sigma = P*R/t (Sec. 17.1's
    UG-27 form) divided by E(T) (Sec. 4.3).
    `stress_concentration_factor` (SCF) is NOT a workbook value -- it's a
    multiplier on the pressure-induced strain used only by the structural-
    concern fault scenario to represent a localized stress riser (e.g. a
    weld defect or fatigue crack tip). SCF=1.0 (default) reproduces the
    plain thin-wall result used everywhere else.
    """
    dll = materials.thermal_expansion_dl_l(inner_wall_k)
    strain_thermal_ue = dll * 1e6
    e_pa = materials.youngs_modulus_gpa(inner_wall_k) * 1e9
    sigma_hoop_pa = (p_bar_a * 1e5) * radius_m / thickness_m * stress_concentration_factor
    strain_pressure_ue = (sigma_hoop_pa / e_pa) * 1e6
    total = strain_thermal_ue + strain_pressure_ue
    lo, hi = C.SENSOR_SPECS["strain_ue"][0], C.SENSOR_SPECS["strain_ue"][1]
    return strain_thermal_ue, strain_pressure_ue, float(np.clip(total, lo, hi))


def inner_wall_offset_c(rng: np.random.Generator, mean_c: float = 1.0, sigma_c: float = 0.5) -> float:
    """Small positive offset: inner wall runs slightly warmer than the bulk
    saturated liquid it contains."""
    return abs(rng.normal(mean_c, sigma_c))
