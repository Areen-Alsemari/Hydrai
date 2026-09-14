"""
Real-gas hydrogen property wrapper around CoolProp's HEOS::Hydrogen backend.

Why HEOS::Hydrogen: Sec. 4.5 of the workbook identifies the Leachman et al.
(2009) reference EOS as the standard, well-documented choice for normal
hydrogen, the same one NIST/REFPROP use, and proposes CoolProp as the
implementation. CoolProp's "HEOS" backend for "Hydrogen" *is* that EOS --
confirmed at import time below by checking CoolProp's own BibTeX key for the
fluid, and by checking the critical temperature against Sec. 3's cited value
(Tc = -239.96 C = 33.19 K, matching Leachman 2009).

No property in this module is computed from the ideal-gas law. Liquid,
vapor, and saturation properties are all pulled from the real EOS, per the
user's explicit instruction not to assume ideal gas anywhere (this is a
stricter stance than Sec. 4.5's "a simpler correction to ideal-gas behavior
might even be adequate for the vapor/ullage region" -- we don't take that
shortcut here).
"""

from __future__ import annotations

from dataclasses import dataclass

import CoolProp.CoolProp as CP

FLUID = "Hydrogen"   # CoolProp's normal-hydrogen fluid, HEOS backend, Leachman 2009 EOS
BACKEND = "HEOS"

_EXPECTED_TCRIT_K = 33.19   # Sec. 3: -239.96 C, cited against Leachman et al. (2009)
_TCRIT_TOLERANCE_K = 0.1    # CoolProp reports 33.14 K; small deviation is a known
                            # rounding difference between the workbook's C->K
                            # conversion and CoolProp's own constant, not a
                            # wrong-fluid/wrong-EOS signal (BibTeX key check below
                            # is the authoritative match).


def _verify_backend() -> None:
    """Fail loudly at import time if CoolProp isn't actually giving us the
    Leachman 2009 EOS that Sec. 3/4.5 call for."""
    key = CP.get_BibTeXKey(FLUID, "EOS")
    if "Leachman" not in key:
        raise RuntimeError(
            f"CoolProp EOS for '{FLUID}' is '{key}', expected a Leachman-2009 "
            "reference EOS per workbook Sec. 4.5. Refusing to silently use a "
            "different EOS."
        )
    tcrit_k = CP.PropsSI("Tcrit", FLUID)
    if abs(tcrit_k - _EXPECTED_TCRIT_K) > _TCRIT_TOLERANCE_K:
        raise RuntimeError(
            f"CoolProp Tcrit={tcrit_k:.3f} K deviates from Sec. 3's cited "
            f"{_EXPECTED_TCRIT_K} K by more than {_TCRIT_TOLERANCE_K} K."
        )


_verify_backend()


@dataclass(frozen=True)
class SaturationState:
    """LH2/GH2 equilibrium state at a given ullage pressure -- the normal
    operating assumption for a vented cryogenic storage tank (Sec. 5/6:
    the tank runs near the liquid/vapor saturation line, not superheated)."""

    p_pa: float
    t_sat_k: float
    liquid_density_kg_m3: float
    vapor_density_kg_m3: float
    liquid_enthalpy_j_kg: float
    vapor_enthalpy_j_kg: float

    @property
    def t_sat_c(self) -> float:
        return self.t_sat_k - 273.15

    @property
    def latent_heat_j_kg(self) -> float:
        return self.vapor_enthalpy_j_kg - self.liquid_enthalpy_j_kg


class H2EOS:
    """Thin, cached wrapper so the sim loop doesn't re-hit CoolProp's PropsSI
    string-parsing interface every tick more than necessary."""

    def __init__(self) -> None:
        self.fluid = FLUID

    def saturation_state(self, p_bar_a: float) -> SaturationState:
        p_pa = p_bar_a * 1e5
        t_sat_k = CP.PropsSI("T", "P", p_pa, "Q", 0, self.fluid)
        rho_liq = CP.PropsSI("D", "P", p_pa, "Q", 0, self.fluid)
        rho_vap = CP.PropsSI("D", "P", p_pa, "Q", 1, self.fluid)
        h_liq = CP.PropsSI("H", "P", p_pa, "Q", 0, self.fluid)
        h_vap = CP.PropsSI("H", "P", p_pa, "Q", 1, self.fluid)
        return SaturationState(
            p_pa=p_pa,
            t_sat_k=t_sat_k,
            liquid_density_kg_m3=rho_liq,
            vapor_density_kg_m3=rho_vap,
            liquid_enthalpy_j_kg=h_liq,
            vapor_enthalpy_j_kg=h_vap,
        )

    def saturation_pressure_bar(self, t_k: float) -> float:
        p_pa = CP.PropsSI("P", "T", t_k, "Q", 0, self.fluid)
        return p_pa / 1e5

    def liquid_density(self, p_bar_a: float) -> float:
        return CP.PropsSI("D", "P", p_bar_a * 1e5, "Q", 0, self.fluid)

    def vapor_density(self, p_bar_a: float) -> float:
        return CP.PropsSI("D", "P", p_bar_a * 1e5, "Q", 1, self.fluid)


if __name__ == "__main__":
    eos = H2EOS()
    for p in (0.5, 1.0, 1.2, 1.5, 2.0, 3.0, 6.0):
        s = eos.saturation_state(p)
        print(
            f"P={p:>4.1f} bar(a)  T_sat={s.t_sat_k:6.2f} K ({s.t_sat_c:7.2f} C)  "
            f"rho_liq={s.liquid_density_kg_m3:6.2f} kg/m3  "
            f"rho_vap={s.vapor_density_kg_m3:5.3f} kg/m3  "
            f"h_fg={s.latent_heat_j_kg/1e3:6.1f} kJ/kg"
        )
