"""
Physically-driven tank: heat leak -> vapor -> pressure -> PCV/PRV -> vent flow,
built from ullage.py (mass/energy on the real EOS) and valves.py (PCV/PRV).

First increment of the pressure-model rebuild. It is NOT yet wired into the
episode generators, the sensor layer, or the dataset; the legacy random-
process pressure model remains the default everywhere else until the cutover
is decided.

Heat leak is calibrated, not imposed as a boil-off number: the healthy wall
flux is chosen so that steady venting reproduces the workbook Sec. 7 normal-
stage boil-off for the selected two-tier mode (baseline 0.30 %/day or target
0.10 %/day). Boil-off then EMERGES from the vent flow, and tests check that
it does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from hydrai_twin import constants as C
from hydrai_twin import placeholders as PH
from hydrai_twin.ullage import TankOutOfRange, TankThermo, stratification_ratio
from hydrai_twin.valves import PCV, PRV, PressureBuilder, vent_flow_kg_s

SECONDS_PER_DAY = 86400.0


@dataclass
class PhysicalTankConfig:
    volume_m3: float = C.TANK_INTERNAL_VOLUME_M3
    area_m2: float = C.INNER_SURFACE_AREA_M2
    fill_frac: float = 0.85
    p0_bar_a: float = 1.2
    calibration_fill_frac: float = 0.85    # heat leak is calibrated to the Sec. 7 boil-off at THIS fill (nominal ~603 kg), independent of the starting fill
    boiloff_mode: str = C.DEFAULT_BOILOFF_MODE
    insulation_leak_mult: float = 1.0      # per-module as-built heat-leak scatter (module_profile.py)
    stratification: str = "off"            # "off" | "empirical" (see ullage.py)


def calibrated_healthy_flux_w_m2(cfg: PhysicalTankConfig) -> float:
    """Wall heat flux whose steady venting equals the Sec. 7 normal-stage
    boil-off (percent of liquid mass per day) at the nominal fill/pressure."""
    th = TankThermo(cfg.volume_m3, cfg.calibration_fill_frac, cfg.p0_bar_a)
    pct = C.BOILOFF_LADDER_PCT_PER_DAY[cfg.boiloff_mode]["normal"]
    q_w = pct / 100.0 * th.m_l / SECONDS_PER_DAY * th.latent_heat_j_kg
    return q_w / cfg.area_m2


class PhysicalTank:
    def __init__(
        self,
        cfg: PhysicalTankConfig | None = None,
        pcv: PCV | None = None,
        prv: PRV | None = None,
        pbr: PressureBuilder | None = None,
    ):
        self.cfg = cfg or PhysicalTankConfig()
        if self.cfg.stratification not in ("off", "empirical"):
            raise ValueError("stratification must be 'off' or 'empirical'")
        self.tank = TankThermo(self.cfg.volume_m3, self.cfg.fill_frac, self.cfg.p0_bar_a)
        self.pcv = pcv or PCV()
        self.prv = prv or PRV()
        self.pbr = pbr                      # optional pressure-building circuit (None = absent)
        self.leaked_kg = 0.0
        # Placeholders that govern behavior whether or not a valve ever opens must
        # be recorded as used at construction, not only when first read mid-run.
        PH.value("ambient_bar_a")
        PH.value("first_fill_max_fraction")
        self.healthy_flux_w_m2 = calibrated_healthy_flux_w_m2(self.cfg) * self.cfg.insulation_leak_mult
        self.t_s = 0.0
        self.vented_pcv_kg = 0.0
        self.vented_prv_kg = 0.0
        self.pcv_open_events = 0
        self.prv_lift_events = 0
        self._last_dp_bar = 0.0
        self.total_mass0_kg = self.tank.m
        self.liquid_full_events = 0
        self.liquid_vented_kg = 0.0           # mass of LIQUID passed by PCV/PRV while the tank was liquid-full
        self.ended_reason: str | None = None   # set if the run stopped because the tank ran dry

    def step(
        self,
        dt_s: float,
        flux_w_m2: float | None = None,
        mdot_in: float = 0.0,
        h_in: float = 0.0,
        mdot_liq_out: float = 0.0,
        leak_area_m2: float = 0.0,
    ) -> dict:
        flux = self.healthy_flux_w_m2 if flux_w_m2 is None else flux_w_m2
        q_w = flux * self.cfg.area_m2
        if self.cfg.stratification == "empirical":
            q_w *= stratification_ratio(flux, self.tank.fill_frac)

        q_pb = 0.0
        if self.pbr is not None:
            self.pbr.update(self.tank.p_bar_a)
            q_pb = self.pbr.heat_w if self.pbr.is_on else 0.0
            q_w += q_pb
        was_pcv, was_prv = self.pcv.is_open, self.prv.is_open
        p = self.tank.p_bar_a
        self.pcv.update(p)
        self.prv.update(p)
        self.pcv_open_events += int(self.pcv.is_open and not was_pcv)
        self.prv_lift_events += int(self.prv.is_open and not was_prv)

        m_pcv = self.pcv.flow_kg_s(self.tank)
        m_prv = self.prv.flow_kg_s(self.tank)
        m_leak = vent_flow_kg_s(leak_area_m2, 0.62, 0.62, self.tank) if leak_area_m2 > 0.0 else 0.0
        mdot_vent = m_pcv + m_prv + m_leak
        vent_is_liquid = self.tank.liquid_full and mdot_vent > 0.0   # state at the START of the step
        if mdot_vent > 0.0:
            dt_s = min(dt_s, max(self.tank.vent_mass_cap_kg() / mdot_vent, 1e-3))

        p_before = self.tank.p_bar_a
        was_full = self.tank.liquid_full
        self.tank.step(dt_s, q_w, mdot_in, h_in, mdot_liq_out, mdot_vent)
        self.liquid_full_events += int(self.tank.liquid_full and not was_full)
        self._last_dp_bar = self.tank.p_bar_a - p_before
        self.t_s += dt_s
        self.vented_pcv_kg += m_pcv * dt_s
        self.vented_prv_kg += m_prv * dt_s
        self.leaked_kg += m_leak * dt_s
        if vent_is_liquid:
            self.liquid_vented_kg += mdot_vent * dt_s
        return {
            "t_s": self.t_s, "dt_s": dt_s, "p_bar_a": self.tank.p_bar_a, "t_sat_k": self.tank.T_k,
            "fill_pct": 100.0 * self.tank.fill_frac, "liquid_kg": self.tank.m_l,
            "flux_w_m2": flux, "q_w": q_w,
            "pcv_open": self.pcv.is_open, "prv_open": self.prv.is_open,
            "liquid_full": self.tank.liquid_full,
            "fill_above_first_fill_cap": self.cfg.fill_frac > PH.value("first_fill_max_fraction"),
            "vent_pcv_kg_s": m_pcv, "vent_prv_kg_s": m_prv, "vent_is_liquid": vent_is_liquid,
            "leak_kg_s": m_leak, "pbr_on": bool(self.pbr is not None and self.pbr.is_on), "q_pb_w": q_pb,
        }

    def run(
        self,
        duration_s: float,
        flux_fn: Callable[[float], float] | None = None,
        record_every_s: float = 300.0,
        dt_min_s: float = 0.5,
        dt_max_s: float = 60.0,
        dp_target_bar: float = 0.002,
        stop_when: Callable[[dict], bool] | None = None,
    ) -> list[dict]:
        """Integrate with adaptive time steps (smaller when pressure moves
        fast), recording a row every `record_every_s`. `flux_fn(t_s)` gives the
        wall heat flux (W/m^2); default is the calibrated healthy flux."""
        rows: list[dict] = []
        t_end = self.t_s + duration_s
        next_rec = self.t_s
        dt = dt_max_s
        while self.t_s < t_end:
            flux = flux_fn(self.t_s) if flux_fn is not None else None
            try:
                row = self.step(min(dt, t_end - self.t_s), flux)
            except TankOutOfRange as e:
                self.ended_reason = str(e)
                break
            if self.t_s >= next_rec:
                rows.append(row)
                next_rec += record_every_s
            if stop_when is not None and stop_when(row):
                rows.append(row)
                break
            dp = abs(self._last_dp_bar)
            target = dt_max_s if dp < 1e-12 else row["dt_s"] * dp_target_bar / dp
            dt = min(max(target, dt_min_s), dt_max_s, 2.0 * row["dt_s"] if row["dt_s"] > 0 else dt_max_s)
        return rows

    @property
    def vented_kg(self) -> float:
        return self.vented_pcv_kg + self.vented_prv_kg
