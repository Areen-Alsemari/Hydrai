"""
Real-gas hydrogen for the CGH2 twin: CoolProp fluid "Hydrogen" (normal hydrogen, Leachman 2009; NOT ParaHydrogen).

  * state from (rho, T): P, u, h, cv, (du/drho)_T  -- the two-node vessel model integrates T, so no (rho,u) inversion is needed
  * rho(P, T) and inventory (kg) = rho x V        -- vectorised, for derived features (fast path: Abel-Noble, see below)
  * dP/dT at constant density
  * choked (sonic-throat) mass flux through an orifice of unit area, Cd = 1, from the real-gas isentropic expansion

Abel-Noble fast path: P = rho R T / (1 - b rho). Allowed for derived features only if it agrees with CoolProp within 1 % below 350 bar;
`abel_noble_max_error` measures that and tests/test_cgh2_gas.py enforces it. The physics itself always uses CoolProp.
"""

from __future__ import annotations

from functools import lru_cache

import CoolProp.CoolProp as CP
import numpy as np

FLUID = "Hydrogen"
R_SPECIFIC = 8.314462618 / 2.01588e-3           # J/(kg K)
AN_B = 7.69e-3                                    # m^3/kg, Abel-Noble covolume for hydrogen (literature value used widely in H2 tank codes)
BAR = 1.0e5


class Gas:
    """A reusable CoolProp state (one per thread/process)."""
    def __init__(self) -> None:
        self._s = CP.AbstractState("HEOS", FLUID)

    def state(self, rho: float, T: float) -> dict[str, float]:
        s = self._s
        s.update(CP.DmassT_INPUTS, rho, T)
        return {"P": s.p(), "u": s.umass(), "h": s.hmass(), "cv": s.cvmass(),
                "u_rho": s.first_partial_deriv(CP.iUmass, CP.iDmass, CP.iT), "cp": s.cpmass(), "a": s.speed_sound()}

    def pressure_bar_at(self, rho: float, T: float) -> float:
        """P (bar) at density rho and temperature T, on the persistent state (fast; for the time loop)."""
        self._s.update(CP.DmassT_INPUTS, rho, T)
        return self._s.p() / BAR

    def h_at_PT(self, P: float, T: float) -> float:
        s = self._s
        s.update(CP.PT_INPUTS, P, T)
        return s.hmass()

    def rho_PT(self, P: float, T: float) -> float:
        s = self._s
        s.update(CP.PT_INPUTS, P, T)
        return s.rhomass()


def _vec(fn, a, b):
    """Call a 1-D-only vectorised PropsSI on arrays of any shape."""
    a, b = np.broadcast_arrays(np.asarray(a, dtype=float), np.asarray(b, dtype=float))
    out = fn(a.ravel(), b.ravel()) if a.ndim > 0 else fn(a.reshape(1), b.reshape(1))
    return np.asarray(out).reshape(a.shape) if a.ndim > 0 else float(out[0])


def rho_PT(P_bar, T_K):
    """CoolProp density (kg/m^3); scalars or arrays of any shape."""
    return _vec(lambda p, t: CP.PropsSI("D", "P", p * BAR, "T", t, FLUID), P_bar, T_K)


def pressure_bar(rho, T_K):
    return _vec(lambda d, t: CP.PropsSI("P", "D", d, "T", t, FLUID) / BAR, rho, T_K)


def inventory_kg(P_bar, T_K, volume_m3: float):
    return rho_PT(P_bar, T_K) * volume_m3


def dPdT_rho_bar_per_K(P_bar: float, T_K: float) -> float:
    """(dP/dT) at constant density, bar/K."""
    rho = float(rho_PT(P_bar, T_K))
    return float(CP.PropsSI("d(P)/d(T)|D", "D", rho, "T", T_K, FLUID)) / BAR


# -- Abel-Noble --------------------------------------------------------------

def abel_noble_rho(P_bar, T_K):
    P = np.asarray(P_bar) * BAR
    return P / (R_SPECIFIC * np.asarray(T_K) + AN_B * P)


def abel_noble_pressure_bar(rho, T_K):
    rho = np.asarray(rho)
    return rho * R_SPECIFIC * np.asarray(T_K) / (1.0 - AN_B * rho) / BAR


def abel_noble_max_error(p_max_bar: float = 350.0, T_lo: float = 233.15, T_hi: float = 353.15) -> float:
    """Max relative density error of Abel-Noble vs CoolProp over 1 .. p_max bar, T_lo..T_hi."""
    P = np.linspace(1.0, p_max_bar, 60)
    T = np.linspace(T_lo, T_hi, 25)
    PP, TT = np.meshgrid(P, T)
    ref = rho_PT(PP, TT)
    return float(np.max(np.abs(abel_noble_rho(PP, TT) / ref - 1.0)))


# -- choked flow -------------------------------------------------------------

def choked_mass_flux(P0_pa: float, T0_k: float, gas: Gas | None = None) -> float:
    """Mass flux (kg/s/m^2) at the sonic throat for stagnation (P0, T0), real-gas isentropic expansion, Cd = 1.
    Throat pressure P* solves h0 - h(P*, s0) = a(P*, s0)^2 / 2."""
    s = (gas or Gas())._s
    s.update(CP.PT_INPUTS, P0_pa, T0_k)
    h0, s0 = s.hmass(), s.smass()

    def f(P):
        s.update(CP.PSmass_INPUTS, P, s0)
        return h0 - s.hmass() - 0.5 * s.speed_sound() ** 2

    lo, hi = 0.3 * P0_pa, 0.999 * P0_pa            # f(lo) > 0 (flow still subsonic-accelerating), f(hi) < 0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9 * P0_pa:
            break
    P = 0.5 * (lo + hi)
    s.update(CP.PSmass_INPUTS, P, s0)
    return s.rhomass() * s.speed_sound()


def ideal_choked_mass_flux(P0_pa: float, T0_k: float, gamma: float = 1.41) -> float:
    return P0_pa * np.sqrt(gamma / (R_SPECIFIC * T0_k)) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))


@lru_cache(maxsize=1)
def _flux_table():
    """G(P0, T0) on a grid (P 0.5 .. 500 bar, T 200 .. 400 K) for fast interpolation inside the time loop."""
    from scipy.interpolate import RegularGridInterpolator
    P = np.concatenate([np.linspace(0.5, 20, 12), np.geomspace(25, 500, 52)]) * BAR
    T = np.linspace(200.0, 400.0, 11)
    g = Gas()
    G = np.array([[choked_mass_flux(p, t, g) for t in T] for p in P])
    return RegularGridInterpolator((P, T), G, bounds_error=False, fill_value=None)


def choked_mass_flux_fast(P0_pa, T0_k):
    """Interpolated choked_mass_flux (kg/s/m^2); scalar or arrays. Within ~0.3 % of the direct solve (tested)."""
    out = _flux_table()(np.stack(np.broadcast_arrays(np.asarray(P0_pa, float), np.asarray(T0_k, float)), axis=-1))
    return float(np.squeeze(out)) if np.size(out) == 1 else out


def leak_mass_rate_kg_s(diameter_mm: float, P_bar: float, T_K: float, cd: float = 1.0) -> float:
    A = np.pi / 4.0 * (diameter_mm * 1e-3) ** 2
    return float(cd * A * choked_mass_flux(P_bar * BAR, T_K))
