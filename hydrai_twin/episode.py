"""
Normal-operation episode generator: filling -> idle -> discharge.

Scope note: this is phase 1 (label 0, "Normal", Sec. 10) only. Fault
scenarios (labels 1-6 + unknown) are a separate generator layered on top of
the same physics core, not yet built.

Simulation model (deliberately a reduced-order model, not CFD/FEA -- this is
a digital twin producing plausible ground truth for an anomaly-detection
dataset, not a thermal design tool):

- The tank is assumed to sit at liquid/vapor saturation equilibrium at the
  current ullage pressure (Sec. 5/6: normal operation keeps LH2 in the
  -253..-250 C band, which is exactly the saturation range at 1.0-1.5
  bar(a) -- confirmed against CoolProp in eos.py). All liquid/vapor
  properties (T_sat, densities, latent heat) come from H2EOS (Sec. 4.5),
  never a fixed/ideal-gas shortcut.
- Ullage pressure is modeled as an Ornstein-Uhlenbeck process mean-reverting
  to the Sec. 5 "Normal pressure" (1.2 bar(a)) and clamped to the Sec. 5
  "Normal operating range" (1.0-1.5 bar(a)). This stands in for the
  continuous PCV micro-regulation described in Sec. 17.2 (a full valve
  on/off simulation is deferred to the fault-injection generator, which
  needs the 2.0 bar(a) threshold-triggered behavior for the "abnormal
  pressure rise" scenario).
- Inner wall temperature tracks T_sat with a small positive offset (wall is
  slightly warmer than the bulk liquid), clamped to the Sec. 6 inner-wall
  normal band.
- Outer wall and ambient temperature are independent OU processes within
  their Sec. 6 normal bands -- decoupled from the inner state by the
  vacuum+MLI insulation (Sec. 1), consistent with Sec. 10's fault logic
  (only insulation/vacuum *degradation* scenarios couple them).
- Mass balance is exactly Sec. 7: dM/dt = mdot_in - mdot_out - mdot_BOG,
  with mdot_BOG from boiloff.py's "normal" stage at the selected two-tier
  mode.
- Fill fraction is computed from real liquid density at the *current*
  pressure (via H2EOS), not a fixed nominal density -- so a pressure swing
  visibly moves the fill-level reading even at constant mass, same as a
  real level sensor referenced to volume.
- Strain ground truth combines (a) thermal-contraction strain from the
  corrected dL/L(T) (Sec. 4.2) evaluated at the inner wall temperature, and
  (b) pressure-induced hoop strain from thin-wall theory (sigma = P*R/t,
  Sec. 17.1's UG-27 formula) divided by E(T) (Sec. 4.3). Component (a) is
  referenced to the 293 K as-fabricated state, which is why it's a large
  negative baseline (~-2800 to -3000 ue) rather than a small perturbation --
  this is a modeling choice about the strain gauge's zero reference, not a
  workbook-given convention, and it's exactly why Sec. 9 gives the strain
  sensor a wide +/-5000 ue range.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin import materials
from hydrai_twin import sensors
from hydrai_twin.boiloff import boiloff_rate_kg_s, boiloff_rate_pct_per_day
from hydrai_twin.eos import H2EOS
from hydrai_twin.physics import inner_wall_offset_c, ou_step, strain_ue
from hydrai_twin.schema import build_record


@dataclass
class NormalEpisodeConfig:
    module_id: str = "M01"
    boiloff_mode: str = C.DEFAULT_BOILOFF_MODE   # "baseline" (default) or "target"
    dt_s: float = 1.0
    idle_duration_s: float = 600.0
    discharge_demand: str = "normal"             # key into C.DISCHARGE_DEMAND_KG_S
    discharge_target_fill_pct: float = 40.0
    seed: int | None = None
    start_time: datetime | None = None


class NormalEpisodeGenerator:
    def __init__(self, config: NormalEpisodeConfig | None = None):
        self.cfg = config or NormalEpisodeConfig()
        self.eos = H2EOS()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.episode_id = f"EP-{uuid.uuid4().hex[:10]}"
        self.t0 = self.cfg.start_time or datetime.now(timezone.utc)

        # Pressure process tuning (Sec. 5 band/setpoint; theta/sigma are sim
        # tuning, not workbook values -- chosen so the process explores the
        # full 1.0-1.5 bar(a) band over a period of minutes, not seconds).
        self._p_bar = C.PCV_SETPOINT_BAR
        self._p_theta = 1.0 / 180.0   # ~3 min mean-reversion time constant
        self._p_sigma = 0.015         # bar / sqrt(s)

        # Outer wall / ambient OU processes, independent of inner state.
        self._outer_wall_c = 10.0
        self._outer_wall_theta = 1.0 / 600.0
        self._outer_wall_sigma = 0.05

        self._ambient_c = float(self.rng.uniform(10.0, 30.0))  # per-episode "weather"
        self._ambient_theta = 1.0 / 1800.0
        self._ambient_sigma = 0.02

        # Vacuum jacket: healthy, near-static placeholder (Sec. 10 vacuum-
        # degradation scenario, which would drive this up, is future work).
        self._vacuum_pa = 0.5

    # -- physics helpers ----------------------------------------------------

    def _step_pressure(self) -> float:
        p = ou_step(self._p_bar, C.PCV_SETPOINT_BAR, self._p_theta, self._p_sigma, self.cfg.dt_s, self.rng)
        self._p_bar = float(np.clip(p, *C.PCV_BAND_BAR))
        return self._p_bar

    def _step_outer_wall_c(self) -> float:
        v = ou_step(self._outer_wall_c, self._ambient_c * 0.3, self._outer_wall_theta,
                    self._outer_wall_sigma, self.cfg.dt_s, self.rng)
        self._outer_wall_c = float(np.clip(v, *C.TEMP_OUTER_WALL_NORMAL_C))
        return self._outer_wall_c

    def _step_ambient_c(self) -> float:
        v = ou_step(self._ambient_c, self._ambient_c, self._ambient_theta,
                    self._ambient_sigma, self.cfg.dt_s, self.rng)
        self._ambient_c = float(np.clip(v, *C.TEMP_AMBIENT_NORMAL_C))
        return self._ambient_c

    def _inner_wall_c(self, t_sat_c: float) -> float:
        offset = inner_wall_offset_c(self.rng)
        return float(np.clip(t_sat_c + offset, *C.TEMP_INNER_WALL_NORMAL_C))

    def _strain_ue(self, inner_wall_k: float, p_bar_a: float) -> tuple[float, float, float]:
        return strain_ue(inner_wall_k, p_bar_a)

    # -- record assembly ------------------------------------------------

    def _record(
        self,
        step_idx: int,
        phase: str,
        mass_kg: float,
        fill_pct: float,
        mdot_in: float,
        mdot_out: float,
        mdot_bog: float,
    ) -> dict[str, Any]:
        p_bar = self._p_bar
        sat = self.eos.saturation_state(p_bar)
        inner_wall_c = self._inner_wall_c(sat.t_sat_c)
        inner_wall_k = inner_wall_c + 273.15
        outer_wall_c = self._step_outer_wall_c()
        ambient_c = self._step_ambient_c()

        k_val = materials.thermal_conductivity_w_mk(inner_wall_k)
        cp_val = materials.specific_heat_j_kgk(inner_wall_k)
        dll_val = materials.thermal_expansion_dl_l(inner_wall_k)
        e_val = materials.youngs_modulus_gpa(inner_wall_k)
        strain_thermal_ue, strain_pressure_ue, strain_total_ue = self._strain_ue(inner_wall_k, p_bar)

        h2_conc_pct_true = abs(self.rng.normal(0.0, 0.02))  # Sec. 10: ~0% normal

        true_values = {
            "pressure_bar_a": p_bar,
            "liquid_temp_c": sat.t_sat_c,
            "inner_wall_temp_c": inner_wall_c,
            "outer_wall_temp_c": outer_wall_c,
            "h2_concentration_pct": h2_conc_pct_true,
            "liquid_level_pct": fill_pct,
            "mass_flow_fill_kg_s": mdot_in,
            "mass_flow_discharge_kg_s": mdot_out,
            "strain_ue": strain_total_ue,
            "vacuum_pressure_pa": self._vacuum_pa,
            "ambient_temp_c": ambient_c,
        }
        measurements = {name: sensors.measure(name, val, self.rng) for name, val in true_values.items()}

        timestamp = self.t0 + timedelta(seconds=step_idx * self.cfg.dt_s)

        system_context = {
            "module_id": self.cfg.module_id,
            "n_modules": C.N_MODULES,
            "tank_volume_m3": C.TANK_INTERNAL_VOLUME_M3,
            "scenario": "normal",
            "phase": phase,
            "boiloff_mode": self.cfg.boiloff_mode,
            "fault_severity": 0.0,
            "variant_tag": "default",
        }

        simulation_ground_truth = {
            **true_values,
            "mass_kg": mass_kg,
            "t_sat_k": sat.t_sat_k,
            "liquid_density_kg_m3": sat.liquid_density_kg_m3,
            "vapor_density_kg_m3": sat.vapor_density_kg_m3,
            "latent_heat_kj_kg": sat.latent_heat_j_kg / 1e3,
            "boiloff_rate_kg_s": mdot_bog,
            "boiloff_rate_pct_day": boiloff_rate_pct_per_day(self.cfg.boiloff_mode, "normal"),
            "material_inner_wall": {
                "t_k": inner_wall_k,
                "k_w_mk": k_val,
                "cp_j_kgk": cp_val,
                "dl_l": dll_val,
                "e_gpa": e_val,
            },
            "strain_thermal_ue": strain_thermal_ue,
            "strain_pressure_ue": strain_pressure_ue,
        }

        labels = {
            "fault_id": 0,
            "fault_name": C.FAULT_LABELS[0],
            "ai_label": 0,
        }

        return build_record(
            episode_id=self.episode_id,
            timestamp_iso=timestamp.isoformat().replace("+00:00", "Z"),
            system_context=system_context,
            measurements=measurements,
            simulation_ground_truth=simulation_ground_truth,
            labels=labels,
        )

    # -- phases ---------------------------------------------------------

    def generate(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        step_idx = 0
        dt = self.cfg.dt_s

        p0 = self._p_bar
        rho0 = self.eos.liquid_density(p0)
        mass_kg = C.TANK_INTERNAL_VOLUME_M3 * (C.INITIAL_FILL_PCT / 100.0) * rho0

        def fill_pct_of(mass: float) -> float:
            rho = self.eos.liquid_density(self._p_bar)
            return 100.0 * mass / (C.TANK_INTERNAL_VOLUME_M3 * rho)

        # --- Phase 1: filling (Sec. 8: 10% -> 85% target fill) ---
        fill_flow = C.FILL_FLOW_NORMAL_KG_S
        fill_pct = fill_pct_of(mass_kg)
        while fill_pct < C.TARGET_FILL_PCT:
            self._step_pressure()
            mdot_in = float(np.clip(self.rng.normal(fill_flow, 0.03), *C.FILL_FLOW_RANGE_KG_S))
            mdot_bog = boiloff_rate_kg_s(mass_kg, self.cfg.boiloff_mode, "normal")
            mass_kg += (mdot_in - mdot_bog) * dt
            fill_pct = fill_pct_of(mass_kg)
            records.append(self._record(step_idx, "filling", mass_kg, fill_pct, mdot_in, 0.0, mdot_bog))
            step_idx += 1

        # --- Phase 2: idle / holding (boil-off only) ---
        idle_ticks = int(self.cfg.idle_duration_s / dt)
        for _ in range(idle_ticks):
            self._step_pressure()
            mdot_bog = boiloff_rate_kg_s(mass_kg, self.cfg.boiloff_mode, "normal")
            mass_kg -= mdot_bog * dt
            fill_pct = fill_pct_of(mass_kg)
            records.append(self._record(step_idx, "idle", mass_kg, fill_pct, 0.0, 0.0, mdot_bog))
            step_idx += 1

        # --- Phase 3: discharge (Sec. 8 demand table) ---
        discharge_flow = C.DISCHARGE_DEMAND_KG_S[self.cfg.discharge_demand]
        while fill_pct > self.cfg.discharge_target_fill_pct:
            self._step_pressure()
            mdot_out = float(max(0.0, self.rng.normal(discharge_flow, 0.02)))
            mdot_bog = boiloff_rate_kg_s(mass_kg, self.cfg.boiloff_mode, "normal")
            mass_kg -= (mdot_out + mdot_bog) * dt
            fill_pct = fill_pct_of(mass_kg)
            records.append(self._record(step_idx, "discharge", mass_kg, fill_pct, 0.0, mdot_out, mdot_bog))
            step_idx += 1

        return records


def generate_normal_episode(**kwargs: Any) -> list[dict[str, Any]]:
    cfg = NormalEpisodeConfig(**kwargs)
    return NormalEpisodeGenerator(cfg).generate()
