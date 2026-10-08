"""
Lumped two-phase LH2 tank on the real hydrogen EOS (CoolProp HEOS Leachman,
see eos.py). Pressure is a CONSEQUENCE of mass and energy, not a random
process:

    dm/dt = mdot_in - mdot_liq_out - mdot_vent
    dU/dt = Q + mdot_in*h_in - mdot_liq_out*h_f - mdot_vent*h_g

(handoff Sec. 11.1 mass balance, Sec. 11.3 energy balance). At each step the
state (m, U) at fixed volume V is flashed on (rho=m/V, u=U/m) to give
pressure, temperature and quality.

Model assumptions (all deliberate, each checkable):
  * Homogeneous: liquid and vapor share one saturation state. Validated
    against K-site's own homogeneous column (NASA TM-105411 Table 1,
    tests/test_physical_pressure.py): within about +/-6% on all seven rows.
  * Wall thermal mass neglected. At 20-25 K, 304 stainless cp is ~13-20 J/kg-K
    (materials.py, corrected NIST fit), so a ~2,000 kg inner shell stores
    ~30-40 kJ/K against ~5.8 MJ/K for the liquid: well under 1%.
  * Liquid-full is an explicit state (`liquid_full`). Heated at fixed volume
    with no venting, the liquid expands until it fills the tank (85% fill at
    about 5.5-5.9 bar(a), 90% at ~3.8-4.2, 95% at ~2.4-2.7, 75% at ~8.7-9.0,
    depending on starting pressure). Beyond that the single-phase compressed
    liquid's pressure responds very steeply to heat; this comes straight from
    the real EOS, not from an added fudge. Venting then removes LIQUID, which
    is why valves.py switches to a liquid-flow equation. The tank is not
    modeled past the dry (all-vapor) side; that still raises.
  * Stratification is NOT modeled physically. Real ground tanks pressurize
    faster than the homogeneous model (K-site measured/homogeneous = 1.13 at
    the twin's healthy flux, 1.4-3.1 at 2-3.5 W/m^2). `stratification_ratio`
    returns that measured ratio and can be applied as an empirical multiplier
    on heat input (mode "empirical"); default is "off". This is an
    energy-inconsistent fudge (the extra heat is not conserved), so it is
    off by default and flagged as an open modeling choice. The K-site table
    only measured 0.35 W/m^2 at 83% fill; that value is reused at other fills.
"""

from __future__ import annotations

import numpy as np
import CoolProp.CoolProp as CP

from hydrai_twin.eos import FLUID

# K-site (S16) Table 1, measured / homogeneous quasi-steady pressure rise ratio.
_STRAT_FILLS = [0.29, 0.49, 0.83]
_STRAT_RATIO_FLUX_2P0 = [1.40, 1.46, 2.38]
_STRAT_RATIO_FLUX_3P5 = [1.70, 1.64, 3.10]
_STRAT_RATIO_FLUX_0P35 = 1.13   # measured at 83% fill only


def stratification_ratio(flux_w_m2: float, fill_frac: float) -> float:
    """Measured/homogeneous pressure-rise ratio interpolated from K-site
    Table 1 (clamped outside the measured range)."""
    r2 = float(np.interp(fill_frac, _STRAT_FILLS, _STRAT_RATIO_FLUX_2P0))
    r35 = float(np.interp(fill_frac, _STRAT_FILLS, _STRAT_RATIO_FLUX_3P5))
    return float(np.interp(flux_w_m2, [0.35, 2.0, 3.5], [_STRAT_RATIO_FLUX_0P35, r2, r35]))


class TankOutOfRange(RuntimeError):
    """The tank state left the two-phase / compressed-liquid region this model
    covers (in practice: the liquid has boiled or vented away and the tank is
    dry). A physical end state, not a numerical failure."""


class TankThermo:
    def __init__(self, volume_m3: float, liquid_vol_frac: float, p_bar_a: float):
        self.V = volume_m3
        self._as = CP.AbstractState("HEOS", FLUID)
        p = p_bar_a * 1e5
        self._as.update(CP.PQ_INPUTS, p, 0.0)
        rf, uf = self._as.rhomass(), self._as.umass()
        self._as.update(CP.PQ_INPUTS, p, 1.0)
        rg, ug = self._as.rhomass(), self._as.umass()
        m_l = liquid_vol_frac * volume_m3 * rf
        m_v = (1.0 - liquid_vol_frac) * volume_m3 * rg
        self.m = m_l + m_v
        self.U = m_l * uf + m_v * ug
        self._flash()

    def _flash(self) -> None:
        self._as.update(CP.DmassUmass_INPUTS, self.m / self.V, self.U / self.m)
        phase = self._as.phase()
        self.p_pa = self._as.p()
        self.T_k = self._as.T()
        if phase == CP.iphase_twophase:
            self.liquid_full = False
            self.x = self._as.Q()
            self.rho_f = self._as.saturated_liquid_keyed_output(CP.iDmass)
            self.rho_g = self._as.saturated_vapor_keyed_output(CP.iDmass)
            self.h_f = self._as.saturated_liquid_keyed_output(CP.iHmass)
            self.h_g = self._as.saturated_vapor_keyed_output(CP.iHmass)
            self.h_vent = self.h_g              # a vent line draws vapor
            self.m_v = self.x * self.m
            self.m_l = self.m - self.m_v
            self.fill_frac = self.m_l / self.rho_f / self.V
        elif phase == CP.iphase_liquid:
            # compressed single-phase liquid filling the whole tank
            self.liquid_full = True
            self.x = 0.0
            self.rho_f = self.rho_g = self.m / self.V
            self.h_f = self.h_g = self.h_vent = self._as.hmass()   # a vent line draws liquid
            self.m_v = 0.0
            self.m_l = self.m
            self.fill_frac = 1.0
        else:
            raise TankOutOfRange(f"tank left the validity range of this model (phase code {phase}); liquid exhausted (dry tank)")

    def vent_mass_cap_kg(self) -> float:
        """Largest mass that may be removed in one step before the explicit
        scheme becomes unreliable: 20% of the ullage vapor, or 0.1% of the
        total mass when liquid-full (the compressed liquid is very stiff)."""
        return 0.001 * self.m if self.liquid_full else 0.2 * self.m_v

    @property
    def p_bar_a(self) -> float:
        return self.p_pa / 1e5

    @property
    def latent_heat_j_kg(self) -> float:
        return self.h_g - self.h_f

    def step(
        self,
        dt_s: float,
        q_w: float,
        mdot_in: float = 0.0,
        h_in: float = 0.0,
        mdot_liq_out: float = 0.0,
        mdot_vent: float = 0.0,
    ) -> None:
        """Advance one explicit step. Vent removes saturated vapor (h_g);
        liquid withdrawal removes saturated liquid (h_f)."""
        dm = (mdot_in - mdot_liq_out - mdot_vent) * dt_s
        dU = (q_w + mdot_in * h_in - mdot_liq_out * self.h_f - mdot_vent * self.h_vent) * dt_s
        self.m += dm
        self.U += dU
        self._flash()


def liquid_full_pressure_bar_a(fill_frac: float, p0_bar_a: float = 1.2) -> float:
    """Pressure at which a closed, unvented tank filled to `fill_frac` (by
    volume, saturated at `p0_bar_a`) becomes liquid-full: the saturated-liquid
    density has fallen to the tank's fixed mean density."""
    p0 = p0_bar_a * 1e5
    rho_f0 = CP.PropsSI("D", "P", p0, "Q", 0, FLUID)
    rho_g0 = CP.PropsSI("D", "P", p0, "Q", 1, FLUID)
    rho_mean = fill_frac * rho_f0 + (1.0 - fill_frac) * rho_g0
    lo, hi = p0, CP.PropsSI("Pcrit", FLUID) * 0.999
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if CP.PropsSI("D", "P", mid, "Q", 0, FLUID) > rho_mean:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi) / 1e5
