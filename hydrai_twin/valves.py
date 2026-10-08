"""
PCV and PRV models plus vent flow. Every parameter comes from the
placeholder registry (placeholders.py) so unconfirmed values stay flagged.

Vent flow uses the workbook Sec. 17.5 compressible-orifice equations, whose
choked branch was verified against NASA Glenn (S10); the same equations the
leak model uses (leak.py), applied to saturated vapor at the tank state.

Simplifications (flagged, none from a source):
  * PCV is on/off with hysteresis and an instantaneous stroke.
  * PRV opens at its lift pressure and reseats after blowdown; between lift
    and lift+10% the open area scales linearly (S7: certified valves reach
    rated capacity at 10% or less overpressure).
  * Venting is to atmosphere (Q3 asks whether a recovery header exists).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from hydrai_twin import placeholders as PH
from hydrai_twin.leak import leak_mass_flow_kg_s
from hydrai_twin.ullage import TankThermo

PCV_FAULTS = (None, "stuck_closed", "stuck_open", "blocked")


def vent_flow_kg_s(area_m2: float, cd_gas: float, cd_liquid: float, tank: TankThermo) -> float:
    """Flow through an orifice to atmosphere. Gas path: Sec. 17.5 compressible
    equations on saturated vapor. If the tank is liquid-full the device passes
    LIQUID: incompressible orifice flow, mdot = Cd*A*sqrt(2*rho*dP), with
    flashing downstream ignored (flagged simplification)."""
    p_amb = PH.value("ambient_bar_a")
    if tank.liquid_full:
        dp_pa = max(tank.p_pa - p_amb * 1e5, 0.0)
        return cd_liquid * area_m2 * math.sqrt(2.0 * tank.rho_f * dp_pa)
    return leak_mass_flow_kg_s(area_m2, tank.p_bar_a, tank.rho_g, tank.T_k, p_amb, cd_gas)


@dataclass
class PCV:
    open_bar_a: float = field(default_factory=lambda: PH.value("pcv_open_bar_a"))
    deadband_bar: float = field(default_factory=lambda: PH.value("pcv_deadband_bar"))
    area_m2: float = field(default_factory=lambda: math.pi / 4.0 * PH.value("pcv_effective_diameter_m") ** 2)
    cd: float = field(default_factory=lambda: PH.value("pcv_cd"))
    fault: str | None = None
    blocked_area_frac: float = 0.02   # remaining open fraction when the vent line is blocked/iced
    is_open: bool = False

    def __post_init__(self) -> None:
        if self.fault not in PCV_FAULTS:
            raise ValueError(f"unknown PCV fault {self.fault!r}; expected one of {PCV_FAULTS}")

    @property
    def close_bar_a(self) -> float:
        return self.open_bar_a - self.deadband_bar

    def update(self, p_bar_a: float) -> None:
        if self.fault == "stuck_closed":
            self.is_open = False
        elif self.fault == "stuck_open":
            self.is_open = True
        elif not self.is_open and p_bar_a >= self.open_bar_a:
            self.is_open = True
        elif self.is_open and p_bar_a <= self.close_bar_a:
            self.is_open = False

    def flow_kg_s(self, tank: TankThermo) -> float:
        if not self.is_open:
            return 0.0
        area = self.area_m2 * (self.blocked_area_frac if self.fault == "blocked" else 1.0)
        return vent_flow_kg_s(area, self.cd, self.cd, tank)


@dataclass
class PressureBuilder:
    """Pressure-building circuit: while engaged it adds vaporizer heat to the
    ullage. Hysteresis only; capacity is a placeholder (Q1)."""
    open_bar_a: float = field(default_factory=lambda: PH.value("pbr_open_bar_a"))
    close_bar_a: float = field(default_factory=lambda: PH.value("pbr_close_bar_a"))
    heat_w: float = field(default_factory=lambda: PH.value("pbr_heat_w"))
    is_on: bool = False

    def update(self, p_bar_a: float) -> None:
        if not self.is_on and p_bar_a <= self.open_bar_a:
            self.is_on = True
        elif self.is_on and p_bar_a >= self.close_bar_a:
            self.is_on = False


@dataclass
class PRV:
    set_bar_a: float = field(default_factory=lambda: PH.value("prv_set_bar_a"))
    pop_offset_frac: float = 0.0   # per-unit lift tolerance, within +/- prv_pop_tolerance_frac
    blowdown_frac: float = field(default_factory=lambda: PH.value("prv_blowdown_frac"))
    full_lift_overpressure_frac: float = field(default_factory=lambda: PH.value("prv_full_lift_overpressure_frac"))
    area_m2: float = field(default_factory=lambda: PH.value("prv_effective_area_m2"))
    cd: float = field(default_factory=lambda: PH.value("prv_cd"))
    cd_liquid: float = field(default_factory=lambda: PH.value("prv_cd_liquid"))
    is_open: bool = False

    @property
    def lift_bar_a(self) -> float:
        return self.set_bar_a * (1.0 + self.pop_offset_frac)

    @property
    def reseat_bar_a(self) -> float:
        return self.lift_bar_a * (1.0 - self.blowdown_frac)

    def update(self, p_bar_a: float) -> None:
        if not self.is_open and p_bar_a >= self.lift_bar_a:
            self.is_open = True
        elif self.is_open and p_bar_a <= self.reseat_bar_a:
            self.is_open = False

    def open_fraction(self, p_bar_a: float) -> float:
        if not self.is_open:
            return 0.0
        span = self.full_lift_overpressure_frac * self.lift_bar_a
        return min(1.0, max(0.0, (p_bar_a - self.lift_bar_a) / span)) if span > 0 else 1.0

    def flow_kg_s(self, tank: TankThermo) -> float:
        frac = self.open_fraction(tank.p_bar_a)
        if frac <= 0.0:
            # just lifted: a small non-zero opening so the valve can pass flow and bring pressure down
            frac = 0.02 if self.is_open else 0.0
        if frac == 0.0:
            return 0.0
        return vent_flow_kg_s(self.area_m2 * frac, self.cd, self.cd_liquid, tank)
