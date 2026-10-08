"""
Pressure classes of the CGH2 twin (register Sec. 3 as relayed; the register file was not available, values tagged REG-UNREAD / JUDGE
in registry.py):  low MOP 50 bar, medium MOP 300 bar (PRIMARY), high MOP 350 bar. 700 bar is illustrative only and never in the main
dataset.

Per class: MAWP = PRV set = 1.10 x MOP (JUDGE); PAH = 1.02 x MOP, PAHH = 1.05 x MOP (Addendum 1); compressor starts at 85 % of MOP and
stops at MOP; transmitter range, compressor flow. Vessel: 10 m3, 1.2 m inside diameter, wall from Barlow at MAWP with a 250 MPa allowable
(JUDGE), so the shell heat capacity, and hence the hours-scale gas-wall and shell-ambient time constants, FOLLOW from the class pressure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2 import gas as G

CLASS_NAMES = ("low", "medium", "high")
PRIMARY = "medium"


@dataclass(frozen=True)
class PressureClass:
    name: str
    mop_bar: float
    mawp_bar: float
    pah_bar: float
    pahh_bar: float
    comp_start_bar: float
    comp_stop_bar: float
    transmitter_range_bar: float
    compressor_kg_h: float
    volume_m3: float
    inner_diameter_m: float
    length_m: float
    wall_thickness_m: float
    area_inner_m2: float
    area_outer_m2: float
    wall_mass_kg: float
    wall_heat_capacity_j_k: float

    # -- derived time constants (CALC) ------------------------------------------
    def gas_heat_capacity_j_k(self, p_bar: float | None = None, T_k: float = 300.0) -> float:
        p = self.comp_stop_bar if p_bar is None else p_bar
        g = G.Gas()
        rho = float(G.rho_PT(p, T_k))
        return rho * self.volume_m3 * g.state(rho, T_k)["cv"]

    def tau_gas_wall_s(self, p_bar: float | None = None, T_k: float = 300.0) -> float:
        cg, cw = self.gas_heat_capacity_j_k(p_bar, T_k), self.wall_heat_capacity_j_k
        return (cg * cw / (cg + cw)) / (R.value("h_gas_wall") * self.area_inner_m2)

    def tau_wall_ambient_s(self) -> float:
        return self.wall_heat_capacity_j_k / (R.value("h_outer") * self.area_outer_m2)

    @property
    def hoop_strain_ue_per_bar(self) -> float:
        """Thin-wall hoop strain per bar, microstrain (Poisson 0.3, closed ends)."""
        return 1e6 * (1.0e5 * self.inner_diameter_m / (2.0 * self.wall_thickness_m * R.value("steel_E_gpa") * 1e9)) * (1.0 - 0.3 / 2.0)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["tau_gas_wall_s"] = self.tau_gas_wall_s()
        d["tau_wall_ambient_s"] = self.tau_wall_ambient_s()
        d["hoop_strain_ue_per_bar"] = self.hoop_strain_ue_per_bar
        return d


def make_class(name: str, volume_scale: float = 1.0, wall_scale: float = 1.0) -> PressureClass:
    if name not in CLASS_NAMES:
        raise ValueError(f"pressure class must be one of {CLASS_NAMES}")
    mop = float(R.value(f"mop_bar_{name}"))
    mawp = R.value("mawp_over_mop") * mop
    V = R.value("vessel_volume_m3") * volume_scale
    D = R.value("vessel_inner_diameter_m")
    L = V / (math.pi / 4.0 * D * D)
    t = wall_scale * (mawp * 1e5) * D / (2.0 * R.value("vessel_allowable_stress_mpa") * 1e6)
    a_in = math.pi * D * L + 2.0 * math.pi / 4.0 * D * D
    d_out = D + 2.0 * t
    a_out = math.pi * d_out * L + 2.0 * math.pi / 4.0 * d_out * d_out
    mass = R.value("steel_density") * (math.pi / 4.0 * (d_out ** 2 - D ** 2) * L + 2.0 * math.pi / 4.0 * D * D * t)
    return PressureClass(
        name=name, mop_bar=mop, mawp_bar=mawp, pah_bar=R.value("pah_over_mop") * mop, pahh_bar=R.value("pahh_over_mop") * mop,
        comp_start_bar=R.value("compressor_start_frac_mop") * mop, comp_stop_bar=R.value("compressor_stop_frac_mop") * mop,
        transmitter_range_bar=float(R.value(f"transmitter_range_bar_{name}")), compressor_kg_h=float(R.value(f"compressor_flow_kg_h_{name}")),
        volume_m3=V, inner_diameter_m=D, length_m=L, wall_thickness_m=t, area_inner_m2=a_in, area_outer_m2=a_out,
        wall_mass_kg=mass, wall_heat_capacity_j_k=mass * R.value("steel_cp"))


def resolve_stop_policy(pressure_class: str, solar: str, stop_mode: str = "auto", ref_temp_c: float | None = None) -> tuple[str, float]:
    """(mode, compensation reference temperature in C). "auto": a temperature-COMPENSATED stop (MOP is the rating at the reference gas temperature:
    60 C medium/high, 65 C low class, 70 C dark-vessel stress case); the FIXED stop at MOP (stop_mode="fixed") leaves almost no margin
    below PAH = 1.02 x MOP and alarmed in healthy runs of the generated set. Explicit modes win."""
    if stop_mode == "fixed":
        return "fixed", 0.0
    if stop_mode == "compensated":
        return "compensated", float(ref_temp_c if ref_temp_c is not None else R.value("compensated_ref_temp_c_dark"))
    if pressure_class == "low":
        return "compensated", float(ref_temp_c if ref_temp_c is not None else R.value("compensated_ref_temp_c_dark_low" if solar == "dark" else "compensated_ref_temp_c_low"))
    if solar == "dark":
        return "compensated", float(ref_temp_c if ref_temp_c is not None else R.value("compensated_ref_temp_c_dark"))
    return "compensated", float(ref_temp_c if ref_temp_c is not None else R.value("compensated_ref_temp_c_default"))
