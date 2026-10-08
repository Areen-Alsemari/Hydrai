"""
Two-node (gas, wall) real-gas storage vessel with compressor inflow, dispenser draw, leak, PRV and external heat.

State: gas mass m, gas temperature Tg, wall temperature Tw (rho = m / V). Real-gas energy balance with the exact internal energy of
CoolProp hydrogen (no ideal-gas shortcut):

    m cv dTg/dt = Q_wg + mdot_in (h_in - u - rho u_rho) - mdot_out (h - u - rho u_rho)          u_rho = (du/drho)_T
    C_w  dTw/dt = -Q_wg + h_o A_o (T_sun-air - Tw) + Q_ext + Q_fire,       Q_wg = h_i A_i (Tw - Tg)

so slow leaks look isothermal (the wall holds Tg) and fast ones adiabatic (the gas cools as it expands) without a switch. Explicit
integration with automatic substeps (a fraction of the time to empty and of the gas-wall time constant), so a full-bore rupture is
integrated stably under the 1 s recording grid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import PressureClass

BAR = 1.0e5
MAX_DT_PER_SUBSTEP_K = 1.5


@dataclass
class PRV:
    """Spring PRV: pops at its (as-built) set pressure, lifts linearly to full lift at `accumulation` x set, reseats at set x (1 - blowdown)."""
    set_bar: float
    blowdown: float
    accumulation: float
    diameter_mm: float
    cd: float
    stuck_closed: bool = False
    open: bool = False
    lift: float = 0.0
    lift_events: int = 0

    def update(self, P_bar: float) -> None:
        if self.stuck_closed:
            self.open, self.lift = False, 0.0
            return
        if not self.open and P_bar >= self.set_bar:
            self.open = True
            self.lift_events += 1
        elif self.open and P_bar <= self.set_bar * (1.0 - self.blowdown):
            self.open = False
        if self.open:
            self.lift = float(np.clip((P_bar - self.set_bar) / (self.set_bar * (self.accumulation - 1.0)), 0.05, 1.0))
        else:
            self.lift = 0.0

    def mass_rate(self, P_bar: float, T_k: float) -> float:
        if not self.open or self.lift <= 0.0:
            return 0.0
        A = np.pi / 4.0 * (self.diameter_mm * 1e-3) ** 2
        return float(self.cd * self.lift * A * G.choked_mass_flux_fast(P_bar * BAR, T_k))


class Vessel:
    def __init__(self, cls: PressureClass, prv: PRV, mass0_kg: float, Tg0_k: float, Tw0_k: float | None = None,
                 h_gas_wall_mult: float = 1.0, h_outer_mult: float = 1.0):
        self.cls = cls
        self.prv = prv
        self.gas = G.Gas()
        self.V = cls.volume_m3
        self.m = mass0_kg
        self.Tg = Tg0_k
        self.Tw = Tg0_k if Tw0_k is None else Tw0_k
        self.hA_i = R.value("h_gas_wall") * h_gas_wall_mult * cls.area_inner_m2
        self.hA_o = R.value("h_outer") * h_outer_mult * cls.area_outer_m2
        self.Cw = cls.wall_heat_capacity_j_k
        self.t = 0.0
        self.vented_prv_kg = self.leaked_kg = self.dispensed_kg = self.charged_kg = 0.0
        self.min_m = 1e-3
        st = self.gas.state(self.m / self.V, self.Tg)
        self.P_bar = st["P"] / BAR

    @property
    def rho(self) -> float:
        return self.m / self.V

    def step(self, dt: float, T_sunair_k: float, mdot_in: float = 0.0, T_in_k: float = 300.0, mdot_disp: float = 0.0,
             leak_area_m2: float = 0.0, leak_cd: float = 1.0, q_ext_w: float = 0.0, q_fire_w: float = 0.0, max_sub_s: float = 60.0) -> dict:
        """Advance dt seconds. Returns the end-of-step row."""
        remaining = dt
        mdot_leak = mdot_prv = 0.0
        while remaining > 1e-9:
            st = self.gas.state(self.rho, self.Tg)
            P_bar = st["P"] / BAR
            self.prv.update(P_bar)
            mdot_prv = self.prv.mass_rate(P_bar, self.Tg)
            mdot_leak = leak_cd * leak_area_m2 * G.choked_mass_flux_fast(P_bar * BAR, self.Tg) if leak_area_m2 > 0.0 else 0.0
            out = mdot_disp + mdot_leak + mdot_prv
            tau_empty = self.m / out if out > 0 else np.inf
            h = max(min(remaining, max_sub_s, 0.05 * tau_empty), 1e-4)
            # energy and mass
            u, hh, cv, u_rho = st["u"], st["h"], st["cv"], st["u_rho"]
            h_in = self.gas.h_at_PT(st["P"], T_in_k) if mdot_in > 0 else 0.0
            q_wg = self.hA_i * (self.Tw - self.Tg)
            adj = u + self.rho * u_rho
            dTg = (q_wg + mdot_in * (h_in - adj) - out * (hh - adj)) / (self.m * cv)
            dTw = (-q_wg + self.hA_o * (T_sunair_k - self.Tw) + q_ext_w + q_fire_w) / self.Cw
            if abs(dTg) * h > MAX_DT_PER_SUBSTEP_K:        # keep the explicit step accurate when the gas heat capacity is small
                h = max(MAX_DT_PER_SUBSTEP_K / abs(dTg), 1e-4)
            m_new = self.m + (mdot_in - out) * h
            if m_new < self.min_m:                         # emptied within this substep
                scale = (self.m - self.min_m) / max((out - mdot_in) * h, 1e-12)
                h *= min(1.0, scale)
                m_new = self.min_m
            self.Tg += dTg * h
            self.Tw += dTw * h
            self.m = m_new
            self.vented_prv_kg += mdot_prv * h
            self.leaked_kg += mdot_leak * h
            self.dispensed_kg += mdot_disp * h
            self.charged_kg += mdot_in * h
            remaining -= h
            self.t += h
            if self.m <= self.min_m + 1e-12:
                break
        st = self.gas.state(self.rho, self.Tg)
        self.P_bar = st["P"] / BAR
        return {"P_bar": self.P_bar, "Tg_k": self.Tg, "Tw_k": self.Tw, "m_kg": self.m, "mdot_in": mdot_in, "mdot_disp": mdot_disp,
                "mdot_leak": mdot_leak, "mdot_prv": mdot_prv, "prv_open": self.prv.open, "prv_lift": self.prv.lift, "q_wg_w": self.hA_i * (self.Tw - self.Tg)}
