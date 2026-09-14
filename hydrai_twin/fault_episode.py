"""
Fault-injection episode generator: same filling -> idle -> discharge
structure as episode.py's normal generator, but a fault (Sec. 10, labels
1-6 plus -1 "unknown") switches on partway through the idle phase and
persists through discharge. Pre-onset, physics and labels are identical to
a normal episode -- this gives each episode a clean "before" segment, which
matters for training a detector on transitions, not just static snapshots.

Design note on severity: Sec. 10's taxonomy table gives a *qualitative*
per-scenario signature (Pressure/Temperature/Boil-off/H2/Strain: Normal /
High / Variable / Abnormal) and, for two scenarios, a *quantitative* staging
sub-table (insulation-degradation health%->heat-leak%; containment-anomaly's
dedicated signature table). Where Sec. 10 gives numbers, they're used
directly (see INSULATION_HEALTH_HEATLEAK_TABLE in constants.py). Where it
only gives a direction ("High", "Variable"), the magnitude/ramp-rate is a
simulation tuning choice, and every such choice is flagged in-line below --
these are not workbook-given numbers.

Labeling choice: the label flips from 0 to the fault_id at the onset tick,
even though the underlying severity then ramps continuously from 0 to 1
over `ramp_duration_s`. Real early-onset ticks are only mildly anomalous
but already labeled positive. This is a simplification (a fuzzy transition
would need soft/graded labels), not a workbook rule.

Scenario 2 vs 3 (insulation vs vacuum degradation): Sec. 10's summary table
gives them an *identical* qualitative signature (High/High/High/Normal/
Normal) -- its columns don't include the vacuum-jacket sensor. The vacuum
sensor (Sec. 9) exists specifically to disambiguate this pair in a way the
taxonomy table's five listed columns can't: insulation degradation raises
heat leak without moving the vacuum reading; vacuum degradation raises both
heat leak AND the vacuum-jacket pressure reading. That distinction is this
generator's own physical reasoning, not stated in Sec. 10 -- flagged here
rather than presented as directly given.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin import leak as leak_mod
from hydrai_twin import materials
from hydrai_twin import sensors
from hydrai_twin.boiloff import SECONDS_PER_DAY, boiloff_rate_kg_s, boiloff_rate_pct_per_day
from hydrai_twin.eos import H2EOS
from hydrai_twin.physics import inner_wall_offset_c, ou_step, strain_ue
from hydrai_twin.schema import build_record

# --- non-workbook simulation tuning (all flagged individually below) -------
DEFAULT_RAMP_DURATION_S = 300.0       # time for severity to go 0 -> 1 after onset
DEFAULT_ONSET_FRAC_OF_IDLE = 0.3      # fault begins 30% of the way through idle
H2_DISPERSION_SCALE_PCT_PER_KGS = 50_000.0  # crude leak-rate -> vent-sensor %vol scaling
SENSOR_FAULT_SPIKE_PROB = 0.15        # per-tick chance of an erratic reading once active
SENSOR_FAULT_TARGET_CHANNEL = "liquid_temp_c"  # Sec. 10 sensor-fault row: "Temperature: Erratic"
DEFAULT_LEAK_SEVERITY = "small"               # default Sec.17.3 rung for fault_id==5 when no variant given
DEFAULT_TARGET_HEALTH_PCT = 40.0              # default Sec.10 "severe" endpoint for fault_id in (2,3)

# NOTE on an unreconciled inconsistency in the source material (flagged, not
# fixed -- whoever builds the anomaly-scoring layer on this dataset should
# pick one of these deliberately rather than inherit the mismatch unnoticed):
# Sec. 7's general 5-tier boil-off ladder gives "severe" = 1.20%/day
# (baseline mode; see constants.BOILOFF_LADDER_PCT_PER_DAY). Sec. 10's
# insulation-degradation-specific staging table, applied here as a
# multiplier on the *normal* rate (0.30%/day baseline * 2.5x at 40% health),
# gives 0.75%/day at its own "severe" endpoint. These are two different
# framings from two different parts of the workbook that were never
# reconciled against each other: one is an independent named tier, the
# other is a multiplier on top of a different named tier. This generator
# uses the Sec.10 multiplier framing (since it's scenario 2/3-specific and
# workbook-cited), NOT the Sec.7 ladder's own "severe" value -- but a
# consumer of this dataset who expects "severe" to mean the same magnitude
# across both framings will be surprised.


def _lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if x1 == x0:
        return y0
    t = max(0.0, min(1.0, (x - x0) / (x1 - x0)))
    return y0 + t * (y1 - y0)


def heat_leak_multiplier(health_pct: float) -> float:
    """Sec. 10 insulation-degradation staging table, piecewise-linear
    interpolation through its three given (health%, heat-leak-mult) points."""
    table = C.INSULATION_HEALTH_HEATLEAK_TABLE  # [(100,1.0),(70,1.5),(40,2.5)]
    if health_pct >= table[0][0]:
        return table[0][1]
    for (h0, m0), (h1, m1) in zip(table, table[1:]):
        if h1 <= health_pct <= h0:
            return _lerp(health_pct, h0, h1, m0, m1)
    return table[-1][1]  # below the lowest tabulated health -> hold at worst tabulated value


@dataclass
class SingleFaultEffects:
    """All channel modifiers for one fault_id at one effective severity
    (0..1). Defaults reproduce plain normal-operation behavior."""
    p_setpoint_bar: float = C.PCV_SETPOINT_BAR
    p_band_hi_bar: float = C.PCV_BAND_BAR[1]
    p_sigma_mult: float = 1.0
    heat_leak_mult: float = 1.0
    boiloff_secondary_mult: float = 1.0   # Sec.10 scenario 4: smaller, consequential-not-causal bump
    vacuum_pa: float = 0.5
    leak_rate_kg_s: float = 0.0
    h2_true_pct: float = 0.0
    strain_scf: float = 1.0


def single_fault_effects(
    fault_id: int,
    severity: float,
    eos: H2EOS,
    p_bar_a_now: float,
    leak_severity: str = DEFAULT_LEAK_SEVERITY,
    target_health_pct: float = DEFAULT_TARGET_HEALTH_PCT,
) -> SingleFaultEffects:
    """severity in [0,1]. See module docstring for what's workbook-cited vs
    simulation tuning in each branch.

    `leak_severity` (fault_id==5) and `target_health_pct` (fault_id in (2,3))
    are the diversity knobs: which Sec.17.3 leak-size rung, and which Sec.10
    health tier ("degraded"=70, "severe"=40), this episode's fault ramps
    toward at full severity. Defaults reproduce the single fixed variant
    this generator used before diversity was added."""
    e = SingleFaultEffects()
    if severity <= 0.0 or fault_id in (0, 1):
        return e  # sensor fault (1) never touches ground-truth physics

    if fault_id in (2, 3):
        # Insulation degradation (2) / vacuum degradation (3): Sec. 10
        # staging table drives heat-leak multiplier (workbook-cited).
        # health ramps 100% -> target_health_pct linearly with severity (the
        # *rate* is a tuning choice; 100/70/40 are Sec. 10's own anchor
        # values -- target_health_pct selects which of the two non-normal
        # anchors, 70 "degraded" or 40 "severe", this episode settles at).
        health = _lerp(severity, 0.0, 1.0, 100.0, target_health_pct)
        e.heat_leak_mult = heat_leak_multiplier(health)
        # Pressure creep as venting fails to keep pace with elevated boil-off
        # -- NOT a Sec.10-given formula, a modeling choice representing
        # "High" pressure/temperature qualitatively, capped below the
        # critical band (Sec.10 says High, not Critical, for these rows).
        e.p_setpoint_bar = C.PCV_SETPOINT_BAR + severity * 0.5 * (C.PRESSURE_HIGH_WARNING_BAR - C.PCV_SETPOINT_BAR)
        e.p_band_hi_bar = C.PCV_BAND_BAR[1] + severity * (C.PRESSURE_HIGH_WARNING_BAR - C.PCV_BAND_BAR[1])
        if fault_id == 3:
            # Vacuum-jacket pressure ramp: the discriminating signal vs. (2).
            # Endpoint (500 Pa) is a tuning choice, not workbook-given --
            # chosen well inside the Sec.9 sensor's 0-1000 Pa range as
            # "clearly degraded, not yet full atmospheric breach".
            e.vacuum_pa = _lerp(severity, 0.0, 1.0, 0.5, 500.0)
        return e

    if fault_id == 4:
        # Abnormal pressure rise: root cause is a valve/PCV fault, not heat
        # leak -- so boil-off's bump here is secondary/consequential
        # (reduced subcooling margin at higher T_sat), smaller than (2)/(3)'s
        # heat-leak-driven bump. Pressure is allowed to climb further (toward
        # the Sec.5 critical band) than (2)/(3), reflecting an impaired vent
        # path rather than merely elevated boil-off gas generation. Both the
        # 0.3 secondary-multiplier and the 0.7 critical-approach fraction are
        # tuning choices, not workbook numbers.
        e.p_setpoint_bar = C.PCV_SETPOINT_BAR + severity * 0.7 * (C.PRESSURE_CRITICAL_BAR - C.PCV_SETPOINT_BAR)
        e.p_band_hi_bar = C.PCV_BAND_BAR[1] + severity * 0.9 * (C.PRESSURE_CRITICAL_BAR - C.PCV_BAND_BAR[1])
        e.boiloff_secondary_mult = 1.0 + severity * 0.3
        return e

    if fault_id == 5:
        # Containment anomaly: Sec. 10's own dedicated signature table
        # (mass loss faster than expected, H2 concentration increasing,
        # pressure/temperature "abnormal" rather than simply "High", strain
        # "potential increase"). Implemented via Sec. 17.5's real leak
        # equation + Sec. 17.3's severity ladder (leak_severity selects which
        # rung -- pinhole/small/small_medium/medium_large/full_bore -- this
        # episode's leak ramps toward; see leak.py), not a made-up mass-loss number.
        area = leak_mod.leak_area_m2(leak_severity) * severity
        sat = eos.saturation_state(p_bar_a_now)
        e.leak_rate_kg_s = leak_mod.leak_mass_flow_kg_s(
            area, p_bar_a_now, sat.vapor_density_kg_m3, sat.t_sat_k
        )
        e.h2_true_pct = min(90.0, e.leak_rate_kg_s * H2_DISPERSION_SCALE_PCT_PER_KGS)
        # "Abnormal" (Sec.10's hedge, distinct from the strictly-"High" rows)
        # modeled as added volatility rather than a clean directional trend.
        e.p_sigma_mult = 1.0 + severity * 4.0
        e.strain_scf = 1.0 + severity * 0.5  # Sec.10: "potential increase", kept modest
        return e

    if fault_id == 6:
        # Structural concern: Sec.10 -- Strain High, P/T/boil-off Variable,
        # H2 Normal. SCF (stress concentration factor) magnitude and the
        # pressure-volatility bump are tuning choices representing a
        # localized stress riser / vibration-driven disturbance, not a
        # workbook-given structural model.
        e.strain_scf = 1.0 + severity * 3.0
        e.p_sigma_mult = 1.0 + severity * 3.0
        return e

    return e


def combine_effects(effects_list: list[SingleFaultEffects]) -> SingleFaultEffects:
    """Combine multiple concurrent single-fault effects for the 'unknown
    anomaly' composite scenario. Setpoint/volatility/vacuum/SCF channels take
    the max across active sub-faults (whichever driver is more extreme
    dominates that channel); heat-leak and strain multipliers combine their
    deviations-from-1 additively; leak rate and H2 concentration sum. This
    combination rule is a simulation design choice (Sec.10 gives no
    composite-fault formula -- 'unknown anomaly' is deliberately meant not
    to match any single named row)."""
    if not effects_list:
        return SingleFaultEffects()
    c = SingleFaultEffects(
        p_setpoint_bar=max(e.p_setpoint_bar for e in effects_list),
        p_band_hi_bar=max(e.p_band_hi_bar for e in effects_list),
        p_sigma_mult=max(e.p_sigma_mult for e in effects_list),
        heat_leak_mult=1.0 + sum(e.heat_leak_mult - 1.0 for e in effects_list),
        boiloff_secondary_mult=1.0 + sum(e.boiloff_secondary_mult - 1.0 for e in effects_list),
        vacuum_pa=max(e.vacuum_pa for e in effects_list),
        leak_rate_kg_s=sum(e.leak_rate_kg_s for e in effects_list),
        h2_true_pct=min(90.0, sum(e.h2_true_pct for e in effects_list)),
        strain_scf=1.0 + sum(e.strain_scf - 1.0 for e in effects_list),
    )
    return c


@dataclass
class FaultEpisodeConfig:
    fault_id: int                                 # 1-6, or -1 for "unknown"
    module_id: str = "M01"
    boiloff_mode: str = C.DEFAULT_BOILOFF_MODE
    dt_s: float = 1.0
    idle_duration_s: float = 900.0                # longer than normal-episode default so
                                                    # there's room for a pre-onset + ramp + settled window
    onset_frac_of_idle: float = DEFAULT_ONSET_FRAC_OF_IDLE
    ramp_duration_s: float = DEFAULT_RAMP_DURATION_S
    discharge_demand: str = "normal"
    discharge_target_fill_pct: float = 40.0
    unknown_sub_fault_ids: tuple[int, ...] | None = None  # only for fault_id == -1

    # --- diversity knobs (dataset-generalization requirements; not tied to
    # a specific workbook section -- see dataset.py's variant matrix for how
    # these get multiplied out across a full dataset) ---
    leak_severity: str = DEFAULT_LEAK_SEVERITY            # fault_id == 5 only
    target_health_pct: float = DEFAULT_TARGET_HEALTH_PCT  # fault_id in (2, 3) only
    max_severity: float = 1.0                             # caps the severity ramp below full;
                                                            # lets fault_id in (4, 6) settle at a
                                                            # mild/moderate magnitude instead of always maxing out
    initial_pressure_bar: float | None = None             # if set, snaps pressure to this value
                                                            # at the onset tick (fault_id == 5 diversity axis)
    fill_target_pct: float = C.TARGET_FILL_PCT            # overrides the filling-phase target,
                                                            # a second fault_id == 5 diversity axis
    variant_tag: str = "default"                          # human-readable variant label, carried into
                                                            # system_context for dataset introspection/splitting

    seed: int | None = None
    start_time: datetime | None = None


class FaultEpisodeGenerator:
    def __init__(self, config: FaultEpisodeConfig):
        self.cfg = config
        self.eos = H2EOS()
        self.rng = np.random.default_rng(self.cfg.seed)
        self._py_rng = random.Random(self.cfg.seed)
        self.episode_id = f"EP-{uuid.uuid4().hex[:10]}"
        self.t0 = self.cfg.start_time or datetime.now(timezone.utc)

        if self.cfg.fault_id == -1:
            self._sub_fault_ids = self.cfg.unknown_sub_fault_ids or tuple(
                self._py_rng.sample([2, 3, 4, 5, 6], 2)
            )
            self._sub_fault_weights = {fid: self._py_rng.uniform(0.4, 0.8) for fid in self._sub_fault_ids}
        else:
            self._sub_fault_ids = ()
            self._sub_fault_weights = {}

        self._p_bar = C.PCV_SETPOINT_BAR
        self._p_theta = 1.0 / 180.0
        self._p_sigma_base = 0.015

        self._outer_wall_c = 10.0
        self._outer_wall_theta = 1.0 / 600.0
        self._outer_wall_sigma = 0.05

        self._ambient_c = float(self.rng.uniform(10.0, 30.0))
        self._ambient_theta = 1.0 / 1800.0
        self._ambient_sigma = 0.02

        self._onset_tick: int | None = None  # set once idle phase starts

    # -- fault severity / effects -------------------------------------------

    def _severity(self, step_idx: int) -> float:
        if self._onset_tick is None or step_idx < self._onset_tick:
            return 0.0
        elapsed = (step_idx - self._onset_tick) * self.cfg.dt_s
        raw = float(np.clip(elapsed / self.cfg.ramp_duration_s, 0.0, 1.0))
        # max_severity caps how far the ramp is allowed to go, so a "mild" or
        # "moderate" variant of a scenario can be generated without the fault
        # always maxing out -- see FaultEpisodeConfig.max_severity.
        return raw * self.cfg.max_severity

    def _effects(self, step_idx: int) -> SingleFaultEffects:
        severity = self._severity(step_idx)
        if self.cfg.fault_id == -1:
            # Unknown-composite sub-faults deliberately keep their own
            # default leak_severity/target_health_pct regardless of this
            # episode's top-level config -- diversity for this scenario is
            # onset timing + which pair is composed, not sub-fault magnitude.
            per_fault = [
                single_fault_effects(fid, severity * self._sub_fault_weights[fid], self.eos, self._p_bar)
                for fid in self._sub_fault_ids
            ]
            return combine_effects(per_fault)
        return single_fault_effects(
            self.cfg.fault_id, severity, self.eos, self._p_bar,
            leak_severity=self.cfg.leak_severity,
            target_health_pct=self.cfg.target_health_pct,
        )

    def _current_label(self, step_idx: int) -> int:
        return self.cfg.fault_id if self._severity(step_idx) > 0.0 else 0

    # -- physics steppers (fault-modulated) ---------------------------------

    def _step_pressure(self, eff: SingleFaultEffects) -> float:
        sigma = self._p_sigma_base * eff.p_sigma_mult
        p = ou_step(self._p_bar, eff.p_setpoint_bar, self._p_theta, sigma, self.cfg.dt_s, self.rng)
        lo = C.PCV_BAND_BAR[0]
        hi = eff.p_band_hi_bar
        self._p_bar = float(np.clip(p, min(lo, hi), max(lo, hi)))
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
        # NOTE: unlike the normal generator, we do NOT clamp to the Sec.6
        # inner-wall *normal* band here -- during an active fault the wall
        # temperature is allowed to leave that band (that's the point of the
        # "High"/"Abnormal" taxonomy entries). We still clamp to the sensor's
        # physical range (Sec.9) since that's an instrument limit, not an
        # operating-envelope one.
        lo, hi = C.SENSOR_SPECS["inner_wall_temp_c"][0], C.SENSOR_SPECS["inner_wall_temp_c"][1]
        return float(np.clip(t_sat_c + offset, lo, hi))

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
        leak_rate_kg_s: float,
        eff: SingleFaultEffects,
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
        strain_thermal_ue, strain_pressure_ue, strain_total_ue = strain_ue(
            inner_wall_k, p_bar, stress_concentration_factor=eff.strain_scf
        )

        h2_conc_pct_true = max(0.0, eff.h2_true_pct + abs(self.rng.normal(0.0, 0.02)))

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
            "vacuum_pressure_pa": eff.vacuum_pa,
            "ambient_temp_c": ambient_c,
        }
        measurements = {name: sensors.measure(name, val, self.rng) for name, val in true_values.items()}

        label = self._current_label(step_idx)
        if self.cfg.fault_id == 1 and label == 1:
            # Sensor fault: ground truth is untouched (physics stays
            # normal); only the measurement layer is corrupted, and only on
            # the channel Sec.10 calls out as "Erratic" for this row.
            if self._py_rng.random() < SENSOR_FAULT_SPIKE_PROB:
                lo, hi = C.SENSOR_SPECS[SENSOR_FAULT_TARGET_CHANNEL][0], C.SENSOR_SPECS[SENSOR_FAULT_TARGET_CHANNEL][1]
                measurements[SENSOR_FAULT_TARGET_CHANNEL] = self._py_rng.uniform(lo, hi)

        timestamp = self.t0 + timedelta(seconds=step_idx * self.cfg.dt_s)

        apparent_boiloff_pct_day = (
            (mdot_bog + leak_rate_kg_s) / mass_kg * SECONDS_PER_DAY * 100.0 if mass_kg > 0 else 0.0
        )

        system_context = {
            "module_id": self.cfg.module_id,
            "n_modules": C.N_MODULES,
            "tank_volume_m3": C.TANK_INTERNAL_VOLUME_M3,
            "scenario": C.FAULT_LABELS[self.cfg.fault_id if self.cfg.fault_id in C.FAULT_LABELS else -1],
            "phase": phase,
            "boiloff_mode": self.cfg.boiloff_mode,
            "fault_severity": self._severity(step_idx),
            "variant_tag": self.cfg.variant_tag,
        }
        if self.cfg.fault_id == -1:
            system_context["unknown_sub_faults"] = list(self._sub_fault_ids)

        simulation_ground_truth = {
            **true_values,
            "mass_kg": mass_kg,
            "t_sat_k": sat.t_sat_k,
            "liquid_density_kg_m3": sat.liquid_density_kg_m3,
            "vapor_density_kg_m3": sat.vapor_density_kg_m3,
            "latent_heat_kj_kg": sat.latent_heat_j_kg / 1e3,
            "boiloff_rate_kg_s": mdot_bog,
            "boiloff_rate_pct_day": boiloff_rate_pct_per_day(self.cfg.boiloff_mode, "normal") * eff.heat_leak_mult * eff.boiloff_secondary_mult,
            "leak_rate_kg_s": leak_rate_kg_s,
            "apparent_boiloff_rate_pct_day": apparent_boiloff_pct_day,
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
            "fault_id": label,
            "fault_name": C.FAULT_LABELS.get(label, "unknown_anomaly"),
            "ai_label": label,
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

        rho0 = self.eos.liquid_density(self._p_bar)
        mass_kg = C.TANK_INTERNAL_VOLUME_M3 * (C.INITIAL_FILL_PCT / 100.0) * rho0

        def fill_pct_of(mass: float) -> float:
            rho = self.eos.liquid_density(self._p_bar)
            return 100.0 * mass / (C.TANK_INTERNAL_VOLUME_M3 * rho)

        # --- Phase 1: filling (identical to normal episodes -- fault has not
        # started yet; Sec.10's taxonomy describes steady-state operating
        # signatures, not filling-transient ones, so onset is deferred to idle) ---
        fill_flow = C.FILL_FLOW_NORMAL_KG_S
        fill_pct = fill_pct_of(mass_kg)
        eff0 = SingleFaultEffects()
        while fill_pct < self.cfg.fill_target_pct:
            self._step_pressure(eff0)
            mdot_in = float(np.clip(self.rng.normal(fill_flow, 0.03), *C.FILL_FLOW_RANGE_KG_S))
            mdot_bog = boiloff_rate_kg_s(mass_kg, self.cfg.boiloff_mode, "normal")
            mass_kg += (mdot_in - mdot_bog) * dt
            fill_pct = fill_pct_of(mass_kg)
            records.append(self._record(step_idx, "filling", mass_kg, fill_pct, mdot_in, 0.0, mdot_bog, 0.0, eff0))
            step_idx += 1

        # --- Phase 2: idle -- fault onset occurs partway through this phase ---
        idle_ticks = int(self.cfg.idle_duration_s / dt)
        self._onset_tick = step_idx + int(idle_ticks * self.cfg.onset_frac_of_idle)
        for _ in range(idle_ticks):
            if step_idx == self._onset_tick and self.cfg.initial_pressure_bar is not None:
                # Snap to the configured starting condition right at onset
                # (rather than at t=0, where the OU process's mean-reversion
                # would mostly erase it by the time the fault begins) --
                # realizes "vary initial tank pressure ... at onset".
                self._p_bar = float(np.clip(self.cfg.initial_pressure_bar, *C.PCV_BAND_BAR))
            eff = self._effects(step_idx)
            self._step_pressure(eff)
            mdot_bog = boiloff_rate_kg_s(mass_kg, self.cfg.boiloff_mode, "normal") * eff.heat_leak_mult * eff.boiloff_secondary_mult
            mass_kg -= (mdot_bog + eff.leak_rate_kg_s) * dt
            fill_pct = fill_pct_of(mass_kg)
            records.append(self._record(step_idx, "idle", mass_kg, fill_pct, 0.0, 0.0, mdot_bog, eff.leak_rate_kg_s, eff))
            step_idx += 1

        # --- Phase 3: discharge -- fault continues at its fully-ramped state ---
        discharge_flow = C.DISCHARGE_DEMAND_KG_S[self.cfg.discharge_demand]
        while fill_pct > self.cfg.discharge_target_fill_pct and mass_kg > 0:
            eff = self._effects(step_idx)
            self._step_pressure(eff)
            mdot_out = float(max(0.0, self.rng.normal(discharge_flow, 0.02)))
            mdot_bog = boiloff_rate_kg_s(mass_kg, self.cfg.boiloff_mode, "normal") * eff.heat_leak_mult * eff.boiloff_secondary_mult
            mass_kg -= (mdot_out + mdot_bog + eff.leak_rate_kg_s) * dt
            fill_pct = fill_pct_of(mass_kg)
            records.append(self._record(step_idx, "discharge", mass_kg, fill_pct, 0.0, mdot_out, mdot_bog, eff.leak_rate_kg_s, eff))
            step_idx += 1

        return records


def generate_fault_episode(**kwargs: Any) -> list[dict[str, Any]]:
    cfg = FaultEpisodeConfig(**kwargs)
    return FaultEpisodeGenerator(cfg).generate()
