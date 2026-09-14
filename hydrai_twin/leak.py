"""
Leak discharge (mass-flow) model, Sec. 17.5 -- turns an orifice area + tank
state into a kg/s release rate. Transcribed directly from the workbook's
proposed equations (standard compressible-orifice flow, the same math
HyRAM+ itself uses per Sec. 17.5), not re-derived.

Note on ideal-gas terms: Sec. 17.5's own equations use the specific gas
constant R (i.e. classical compressible-orifice/nozzle flow theory, which is
inherently ideal-gas-based -- that's baked into the standard derivation the
workbook cites, not a shortcut taken here). This is a narrower and different
thing from the EOS wrapper in eos.py, which uses CoolProp's real Leachman
EOS for all bulk liquid/vapor state properties (density, saturation, etc.)
per Sec. 4.5 and the user's explicit instruction not to assume ideal gas
there. The two aren't in tension: Sec. 17.5 prescribes ideal-gas orifice
flow theory by name for the release-rate formula specifically; nothing else
in this codebase uses it.
"""

from __future__ import annotations

import math

from hydrai_twin import constants as C

R_UNIVERSAL_J_MOLK = 8.314462618  # physical constant, not workbook-specific


def h2_specific_gas_constant_j_kgk() -> float:
    """R_specific for H2, from Sec. 3's molecular weight (2.016 g/mol)."""
    m_kg_mol = C.H2_MOLECULAR_WEIGHT_G_MOL / 1000.0
    return R_UNIVERSAL_J_MOLK / m_kg_mol


def leak_area_m2(severity: str) -> float:
    """Sec. 17.3 ladder fraction * assumed reference orifice area (flagged
    non-workbook assumption, see constants.REFERENCE_LEAK_ORIFICE_DIAMETER_M)."""
    frac = C.LEAK_SEVERITY_AREA_FRACTION[severity]
    ref_area_m2 = math.pi / 4.0 * C.REFERENCE_LEAK_ORIFICE_DIAMETER_M**2
    return frac * ref_area_m2


def is_choked(p_tank_bar_a: float, p_ambient_bar_a: float = C.STANDARD_ATMOSPHERIC_PRESSURE_BAR) -> bool:
    return (p_ambient_bar_a / p_tank_bar_a) <= C.CHOKE_PRESSURE_RATIO


def leak_mass_flow_kg_s(
    area_m2: float,
    p_tank_bar_a: float,
    rho_tank_kg_m3: float,
    t_tank_k: float,
    p_ambient_bar_a: float = C.STANDARD_ATMOSPHERIC_PRESSURE_BAR,
    cd: float = C.DISCHARGE_COEFFICIENT_CD,
) -> float:
    """Sec. 17.5: choked (sonic) vs unchoked (subsonic) compressible orifice
    flow, selected by the critical pressure ratio r_crit = 0.528 for H2."""
    if area_m2 <= 0.0:
        return 0.0

    gamma = C.H2_GAMMA
    p_tank_pa = p_tank_bar_a * 1e5
    r_ratio = p_ambient_bar_a / p_tank_bar_a

    if r_ratio <= C.CHOKE_PRESSURE_RATIO:
        r_specific = h2_specific_gas_constant_j_kgk()
        mdot = cd * area_m2 * p_tank_pa * math.sqrt(
            (gamma / (r_specific * t_tank_k)) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
        )
    else:
        term = (r_ratio ** (2.0 / gamma)) - (r_ratio ** ((gamma + 1.0) / gamma))
        term = max(term, 0.0)  # guard tiny negative from float error right at r_ratio -> 1
        mdot = cd * area_m2 * math.sqrt(
            2.0 * rho_tank_kg_m3 * p_tank_pa * (gamma / (gamma - 1.0)) * term
        )
    return mdot


if __name__ == "__main__":
    from hydrai_twin.eos import H2EOS

    eos = H2EOS()
    for severity in ("pinhole", "small", "small_medium", "medium_large", "full_bore"):
        area = leak_area_m2(severity)
        p = 1.2
        sat = eos.saturation_state(p)
        mdot = leak_mass_flow_kg_s(area, p, sat.vapor_density_kg_m3, sat.t_sat_k)
        choked = is_choked(p)
        print(f"{severity:14s} area={area*1e6:9.4f} mm2  choked={choked!s:5s}  mdot={mdot*1000:9.4f} g/s")
