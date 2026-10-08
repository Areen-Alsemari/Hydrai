"""
Heat-leak pieces that sit outside the tank thermodynamics: the vacuum ladder
(added jacket pressure -> added wall heat flux) and the ambient scaling.

The vacuum ladder is a PLACEHOLDER interpolation (question Q8), anchored on:
  * 13.33 Pa  -> 52.2 W/m^2  (S20, nitrogen-cooled MLI blanket, V1)
  * 101325 Pa -> 1274 W/m^2  (S21, hydrogen tank with vacuum failed, flow-limited, likely low)
and linear in pressure below 13.33 Pa (free-molecular gas conduction is
proportional to pressure). Between the anchors it is log-log. The anchors are
sourced; the shape between them is mine. Sumner & Maloy (S24) could not be
reproduced and are not used.
"""

from __future__ import annotations

import math

from hydrai_twin import placeholders as PH


def vacuum_added_flux_w_m2(dp_pa: float) -> float:
    """Wall heat flux ADDED by `dp_pa` of extra jacket pressure."""
    if dp_pa <= 0.0:
        return 0.0
    dp_soft = PH.value("vacuum_ladder_soft_dp_pa")
    q_soft = PH.value("vacuum_flux_soft_w_m2")
    dp_lost = PH.value("vacuum_lost_jacket_pa")
    q_lost = PH.value("vacuum_flux_lost_w_m2")
    if dp_pa <= dp_soft:
        return q_soft * dp_pa / dp_soft
    slope = math.log(q_lost / q_soft) / math.log(dp_lost / dp_soft)
    return q_soft * (min(dp_pa, dp_lost) / dp_soft) ** slope


def ambient_flux_mult(t_amb_k: float, t_cold_k: float, t_ref_k: float = 293.15) -> float:
    """Radiation-law (T^4) scaling of the heat leak with ambient temperature,
    relative to the 293.15 K reference the healthy flux is calibrated at."""
    return (t_amb_k**4 - t_cold_k**4) / (t_ref_k**4 - t_cold_k**4)
