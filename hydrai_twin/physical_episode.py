"""
PhysicalEpisodeGenerator: episodes built on the physically-driven tank
(physical_tank.py) instead of the legacy random-process pressure. The legacy
generators (episode.py, fault_episode.py) are NOT retired and stay the default.

Episode structure (decision: storage episodes are 14 days at 60 s):
  filling    1 s    heel (10%) -> target fill, cold liquid in (no-vent fill)
  storage   60 s    `storage_days` days; fault onset drawn around days 3-5
  discharge  1 s    liquid withdrawn down to 30% fill

Two output layers from ONE simulation:
  slow : a 60 s snapshot of the WHOLE timeline (Parquet-friendly)
  fast : 1 s rows during operations and during event bursts (valve actuation,
         liquid-full), with a 120 s tail (JSONL)

Scenarios are expressed as CAUSES acting on the physics, not painted-on
signatures (workbook Sec. 10 labels kept):
  1 sensor fault        measurement layer only; ground truth untouched
  2 insulation degr.    heat-flux multiplier ramps up (Sec. 10 anchors 1.5x / 2.5x)
  3 vacuum degradation  added jacket pressure ramps; heat flux from the vacuum
                        ladder (heat_leak.py, placeholder, Q8)
  4 abnormal pressure   PCV stuck closed (icing) or severely blocked vent line
  5 containment anomaly leak area ramps (Sec. 17.3/17.5); vapor leaves the ullage,
                        so pressure FALLS and the PCV vents less (the legacy
                        generator pushed pressure the wrong way)
  6 structural concern  wall stress-concentration factor ramps; pressure untouched
 -1 unknown composite   two of {2,3,4,5,6} acting together at partial weight

Labeling rule (same simplification as the legacy generator): the label flips
at onset although the signature can take hours to days to become detectable.
Valve faults (4) and sensor faults (1) are step changes (severity 1 at onset);
the others ramp over `ramp_duration_s`.

Fill rule (spec, Sec. 2 / 8): healthy and fault episodes fill to 85% nominal and
never above the 90% maximum. Anything above that needs `allow_overfill=True` and is
labeled `scenario_class="overfill_hydraulic_lock"`. (The earlier 55-75% range and the
unverified 75% first-fill cap are no longer used.)

Every valve/regulator/vent parameter is a flagged placeholder
(placeholders.py); `meta["placeholders_used"]` lists them for the manifest.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any

import CoolProp.CoolProp as CP
import numpy as np

from hydrai_twin import constants as C
from hydrai_twin import placeholders as PH
from hydrai_twin import sensors
from hydrai_twin.sensor_view import H2_TAG, SensorView, SensorViewConfig
from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs, drift_series, measure_split, rescale_unit_bias
from hydrai_twin.eos import FLUID
from hydrai_twin.heat_leak import ambient_flux_mult, vacuum_added_flux_w_m2
from hydrai_twin.leak import leak_area_m2
from hydrai_twin.module_profile import ModuleProfile
from hydrai_twin.observability import K_CLEAR, K_SENSITIVE, N_CONSECUTIVE, OUTLIER_K, first_deviation_times, observable_time
from hydrai_twin.physical_tank import PhysicalTank, PhysicalTankConfig
from hydrai_twin.physics import inner_wall_offset_c, ou_step, strain_ue
from hydrai_twin.schema import build_record
from hydrai_twin.seeding import stable_seed
from hydrai_twin.ullage import TankOutOfRange
from hydrai_twin.valves import PCV, PressureBuilder

DAY = 86400.0
SLOW_DT_S = 60.0
FAST_DT_S = 1.0
BURST_TAIL_S = 120.0
BURST_MAX_S = 600.0              # a burst records 1 s rows for at most this long per trigger streak
HEEL_FILL_FRAC = 0.10            # workbook Sec. 8 initial fill
DISCHARGE_END_FILL_FRAC = 0.30
CAUSE_FAULTS = (2, 3, 4, 5, 6)

# Healthy boil-off of the physical generator. ONE-LINE SWITCH: "baseline" = 0.30 %/day (DEFAULT; workbook Sec. 7: real 10 m^3 tanks run
# 0.3-0.6 %/day; at 0.10 a healthy tank barely vents and pressure faults are weak in 14 d episodes); "target" = 0.10 %/day (the
# handoff / workbook Sec. 10 spec value, kept as the spec switch). Recorded in every manifest. Does NOT touch the legacy generators,
# which keep C.DEFAULT_BOILOFF_MODE.
PHYSICAL_DEFAULT_BOILOFF_MODE = "baseline"
SPEC_NOMINAL_FILL = C.NOMINAL_FILL_PCT / 100.0       # Sec. 2 / 8: 85 %
SPEC_MAX_FILL = C.MAX_MODELED_FILL_PCT / 100.0       # Sec. 2 / 8: 90 %  (above this = overfill)


@dataclass
class PhysicalEpisodeConfig:
    fault_id: int = 0                                   # 0 normal, 1-6, -1 composite
    module_id: str = "M01"
    boiloff_mode: str = PHYSICAL_DEFAULT_BOILOFF_MODE
    seed: int | None = None
    start_time: datetime | None = None
    storage_days: float = 14.0
    onset_day_range: tuple[float, float] = (3.0, 5.0)
    fill_target_frac: float | None = None               # None -> spec fill: 85 % nominal, up to the 90 % maximum (see _draw_fill)
    allow_overfill: bool = False
    stratification: str = "off"                         # "off" (main dataset) | "empirical" (robustness variant)
    include_discharge: bool = True
    profile: ModuleProfile = field(default_factory=ModuleProfile)

    # cause variants
    ramp_duration_s: float = 2.0 * DAY
    max_severity: float = 1.0
    insulation_mult_target: float = 2.5                 # fault 2: Sec. 10 severe anchor
    vacuum_target_dp_pa: float = 13.33                  # fault 3: added jacket pressure at full severity
    pcv_fault: str = "stuck_closed"                     # fault 4: "stuck_closed" | "blocked"
    blocked_area_frac: float = 0.002                    # fault 4 "blocked": remaining vent-line area fraction
    leak_severity: str = "small_medium"                 # fault 5: Sec. 17.3 ladder rung
    unknown_sub_fault_ids: tuple[int, ...] | None = None
    variant_tag: str = "default"
    compute_observability: bool = True                  # run the paired healthy counterfactual for observable-deviation labels
    sensor_error_model: str = "split"                   # "split" (bias + drift + small noise) | "legacy_white" (whole accuracy as noise)
    sensor_split: SensorErrorSplit | None = None        # None -> placeholder registry values (Q12)
    sensor_view: SensorViewConfig = field(default_factory=SensorViewConfig)   # sampling periods, H2/vacuum/level instrument modes


@dataclass
class EpisodeResult:
    slow: list[dict[str, Any]]
    fast: list[dict[str, Any]]
    meta: dict[str, Any]


def _h_in_liquid_supply_j_kg() -> float:
    a = CP.AbstractState("HEOS", FLUID)
    a.update(CP.PQ_INPUTS, PH.value("ambient_bar_a") * 1e5, 0.0)
    return a.hmass()


class PhysicalEpisodeGenerator:
    def __init__(self, cfg: PhysicalEpisodeConfig):
        self.cfg = cfg
        if cfg.fault_id not in C.FAULT_LABELS:
            raise ValueError(f"unknown fault_id {cfg.fault_id}")
        if cfg.stratification not in ("off", "empirical"):
            raise ValueError("stratification must be 'off' or 'empirical'")
        if cfg.pcv_fault not in ("stuck_closed", "blocked"):
            raise ValueError("pcv_fault must be 'stuck_closed' or 'blocked'")
        if cfg.sensor_error_model not in ("split", "legacy_white"):
            raise ValueError("sensor_error_model must be 'split' or 'legacy_white'")
        self.profile = cfg.profile
        # Separate streams so the PHYSICS (scenario draws, weather) never depends on how many sensor/noise
        # samples were drawn: a fault run and its healthy counterfactual then share identical pre-onset physics.
        self.seed = cfg.seed if cfg.seed is not None else int(np.random.SeedSequence().entropy % (2**63))
        self.rng = np.random.default_rng(stable_seed(self.seed, "sensor"))        # measurement noise only
        self._rng_scn = np.random.default_rng(stable_seed(self.seed, "scenario"))  # fill, ambient base, onset
        self._rng_env = np.random.default_rng(stable_seed(self.seed, "env"))       # weather series
        self._py = random.Random(stable_seed(self.seed, "py"))                     # composite choice, sensor-fault spikes
        self._rng_drift = np.random.default_rng(stable_seed(self.seed, "sensor-drift"))   # slow sensor drift series
        self.episode_id = f"PEP-{cfg.seed:016x}" if cfg.seed is not None else f"PEP-{uuid.uuid4().hex[:10]}"
        self.t0 = cfg.start_time or datetime(2026, 1, 1, tzinfo=timezone.utc)

        fill = self._draw_fill() if cfg.fill_target_frac is None else cfg.fill_target_frac
        if fill > SPEC_MAX_FILL + 1e-9 and not cfg.allow_overfill:
            raise ValueError(
                f"fill {fill:.2f} is above the spec maximum fill {SPEC_MAX_FILL:.2f} (Sec. 2/8); pass allow_overfill=True to run an "
                "explicit overfill / hydraulic-lock scenario"
            )
        self.fill_target = fill
        self.scenario_class = "overfill_hydraulic_lock" if fill > SPEC_MAX_FILL + 1e-9 else "standard"

        if cfg.fault_id == -1:
            self.sub_ids = cfg.unknown_sub_fault_ids or tuple(self._py.sample(list(CAUSE_FAULTS), 2))
            self.weights = {f: self._py.uniform(0.4, 0.8) for f in self.sub_ids}
        else:
            self.sub_ids, self.weights = (), {}

        tcfg = PhysicalTankConfig(
            volume_m3=self.profile.tank_volume_m3, fill_frac=HEEL_FILL_FRAC, p0_bar_a=1.2,
            boiloff_mode=cfg.boiloff_mode, insulation_leak_mult=self.profile.insulation_leak_mult,
            stratification=cfg.stratification,
        )
        pcv = PCV(
            open_bar_a=PH.value("pcv_open_bar_a") + self.profile.pcv_setpoint_offset_bar,
            deadband_bar=PH.value("pcv_deadband_bar") * self.profile.pressure_noise_mult,
        )
        self.pt = PhysicalTank(tcfg, pcv=pcv, pbr=PressureBuilder())
        self.h_in = _h_in_liquid_supply_j_kg()
        self.fill_flow = C.FILL_FLOW_NORMAL_KG_S * self.profile.fill_flow_mult
        self.discharge_flow = C.DISCHARGE_DEMAND_KG_S["normal"] * self.profile.discharge_flow_mult

        # environment: a deterministic time series on a 60 s grid, independent of the stepping
        self._amb_base = float(np.clip(self._rng_scn.uniform(10.0, 30.0) + self.profile.ambient_offset_c, *C.TEMP_AMBIENT_NORMAL_C))
        self._onset_draw_days = float(self._rng_scn.uniform(*cfg.onset_day_range))   # always drawn so a healthy twin stays aligned
        self._diurnal_amp = PH.value("ambient_diurnal_amplitude_c")
        self._build_environment()
        self._build_sensor_error()
        self._spike_prob = PH.value("sensor_fault_spike_prob")
        self._scf_max = PH.value("strain_scf_max")

        self.t = 0.0
        self._t_storage0: float | None = None
        self._t_onset: float | None = None
        self._next_slow = 0.0
        self._next_fast = 0.0
        self._burst_until = -1.0
        self._burst_start: float | None = None
        self._trig_prev = False
        self._in_kg = self._out_kg = 0.0
        self.slow: list[dict] = []
        self.fast: list[dict] = []
        self.ended_reason: str | None = None

    # -- causes ---------------------------------------------------------------

    def _ramp(self, t: float) -> float:
        if self._t_onset is None or t < self._t_onset:
            return 0.0
        if self.cfg.fault_id in (1, 4):
            return 1.0   # step changes
        return min(1.0, (t - self._t_onset) / self.cfg.ramp_duration_s) * self.cfg.max_severity

    def _causes(self, t: float) -> dict[str, Any]:
        s_all = self._ramp(t)
        c: dict[str, Any] = dict(sev=s_all, ins_mult=1.0, dp_pa=0.0, pcv_fault=None,
                                 blocked_frac=self.cfg.blocked_area_frac, leak_area=0.0, scf=1.0)
        if s_all <= 0.0 or self.cfg.fault_id in (0, 1):
            return c
        faults = self.sub_ids if self.cfg.fault_id == -1 else (self.cfg.fault_id,)
        for fid in faults:
            w = self.weights.get(fid, 1.0)
            s = s_all * w
            if fid == 2:
                c["ins_mult"] += (self.cfg.insulation_mult_target - 1.0) * s
            elif fid == 3:
                c["dp_pa"] += self.cfg.vacuum_target_dp_pa * s
            elif fid == 4:
                if self.cfg.fault_id == -1 and self.cfg.pcv_fault == "blocked":
                    c["pcv_fault"], c["blocked_frac"] = "blocked", self.cfg.blocked_area_frac ** w   # partial weight = partly blocked
                else:
                    c["pcv_fault"], c["blocked_frac"] = self.cfg.pcv_fault, self.cfg.blocked_area_frac
            elif fid == 5:
                c["leak_area"] += leak_area_m2(self.cfg.leak_severity) * s
            elif fid == 6:
                c["scf"] += (self._scf_max - 1.0) * s
        return c

    # -- environment ----------------------------------------------------------

    def _build_environment(self) -> None:
        horizon = 4 * 3600.0 + (self.cfg.storage_days + 0.2) * DAY + 3 * 3600.0
        n = int(horizon / SLOW_DT_S) + 2
        self._env_t = np.arange(n) * SLOW_DT_S
        dev, outer = 0.0, 10.0
        amb = np.empty(n)
        out = np.empty(n)
        for k in range(n):
            diurnal = self._diurnal_amp * math.sin(2.0 * math.pi * (self._env_t[k] / DAY - 0.25))
            dev = ou_step(dev, 0.0, 1.0 / 1800.0, 0.02, SLOW_DT_S, self._rng_env)
            amb[k] = np.clip(self._amb_base + diurnal + dev, *C.TEMP_AMBIENT_NORMAL_C)
            outer = ou_step(outer, amb[k] * 0.3, 1.0 / 600.0, 0.05, SLOW_DT_S, self._rng_env)
            out[k] = np.clip(outer, *C.TEMP_OUTER_WALL_NORMAL_C)
        self._env_amb, self._env_outer = amb, out

    def _draw_fill(self) -> float:
        """Healthy fill follows the spec: 85 % nominal (Sec. 2/8 target), valve closes between 85 and 90 %. Drawn as
        85 % + 5 % x Beta(1, 2.5): mostly near nominal, never above the 90 % maximum. A simulation choice."""
        return float(SPEC_NOMINAL_FILL + (SPEC_MAX_FILL - SPEC_NOMINAL_FILL) * self._rng_scn.beta(1.0, 2.5))

    def _build_sensor_error(self) -> None:
        """Per-unit bias (from the module profile, rescaled into the split's bound), a drift series per channel, and
        (unless disabled) the per-channel instrument view: sampling periods and H2 / vacuum / level instrument modes."""
        self._split = None
        self._view: SensorView | None = None
        self._unit_bias: dict[str, float] = {}
        self._drift: dict[str, np.ndarray] = {}
        if self.cfg.sensor_error_model != "split":
            return
        view_cfg = self.cfg.sensor_view
        split = self.cfg.sensor_split or SensorErrorSplit.from_registry()
        if view_cfg.enabled and view_cfg.h2_mode == "lfl" and self.cfg.sensor_split is None:
            # the realistic %LFL detector has its own +/-5 %LFL accuracy: no zero-referenced workaround needed
            split = replace(split, per_channel={k: v for k, v in split.per_channel.items() if k != H2_TAG})
        self._split = split
        for tag in C.SENSOR_SPECS:
            self._unit_bias[tag] = rescale_unit_bias(self.profile.sensor_bias.get(tag, 0.0), tag, self._split)
            self._drift[tag] = drift_series(tag, self._env_t, self._rng_drift, self._split)
        if view_cfg.enabled:
            from hydrai_twin.module_profile import SENSOR_BIAS_FRACTION_OF_ACCURACY as F
            unit_u = {tag: self.profile.sensor_bias.get(tag, 0.0) / (F * accuracy_abs(tag)) for tag in C.SENSOR_SPECS}
            drift_u = {tag: self._drift[tag] / accuracy_abs(tag) for tag in C.SENSOR_SPECS}
            self._view = SensorView(view_cfg, self._split, unit_u, drift_u, self._env_t, self.rng)

    def _sensor_drift(self, tag: str) -> float:
        return float(np.interp(self.t, self._env_t, self._drift[tag]))

    def _ambient_c(self) -> float:
        return float(np.interp(self.t, self._env_t, self._env_amb))

    @property
    def _outer_c(self) -> float:
        return float(np.interp(self.t, self._env_t, self._env_outer))

    # -- recording ------------------------------------------------------------

    def _record(self, layer: str, phase: str, row: dict, causes: dict, mdot_in: float, mdot_out: float) -> dict:
        tank = self.pt.tank
        p_bar, t_sat = tank.p_bar_a, tank.T_k
        lo_i, hi_i = C.SENSOR_SPECS["inner_wall_temp_c"][0], C.SENSOR_SPECS["inner_wall_temp_c"][1]
        inner_c = float(np.clip(t_sat - 273.15 + inner_wall_offset_c(self.rng), lo_i, hi_i))
        thermal_ue, pressure_ue, strain_total = strain_ue(
            inner_c + 273.15, p_bar, thickness_m=self.profile.wall_thickness_m,
            stress_concentration_factor=causes["scf"])
        h2_nf = float(PH.value("h2_dispersion_pct_per_kg_s") * row["leak_kg_s"])
        h2 = h2_nf + abs(self.rng.normal(0.0, 0.02))
        inner_nf_c = float(np.clip(t_sat - 273.15 + 1.0, lo_i, hi_i))        # mean wall offset, no noise
        strain_nf = strain_ue(inner_nf_c + 273.15, p_bar, thickness_m=self.profile.wall_thickness_m,
                              stress_concentration_factor=causes["scf"])[2]
        jacket = min(self.profile.vacuum_baseline_pa + causes["dp_pa"], PH.value("vacuum_lost_jacket_pa"))
        true_values = {
            "pressure_bar_a": p_bar, "liquid_temp_c": t_sat - 273.15, "inner_wall_temp_c": inner_c,
            "outer_wall_temp_c": self._outer_c, "h2_concentration_pct": min(h2, 90.0),
            "liquid_level_pct": 100.0 * tank.fill_frac, "mass_flow_fill_kg_s": mdot_in,
            "mass_flow_discharge_kg_s": mdot_out, "strain_ue": strain_total,
            "vacuum_pressure_pa": jacket, "ambient_temp_c": self._ambient_c(),
        }
        if self._view is not None:
            meas = self._view.read(self.t, true_values, {"rho_f": tank.rho_f, "rho_g": tank.rho_g,
                                                          "pcv_open": row["pcv_open"], "prv_open": row["prv_open"]})
        elif self._split is None:
            meas = {n: sensors.measure(n, v, self.rng, bias=self.profile.sensor_bias.get(n, 0.0)) for n, v in true_values.items()}
        else:
            meas = {n: measure_split(n, v, self.rng, self._split, self._unit_bias[n], self._sensor_drift(n)) for n, v in true_values.items()}

        label = self._label(causes)
        if self.cfg.fault_id == 1 and label == 1 and self._py.random() < self._spike_prob:
            lo, hi = C.SENSOR_SPECS["liquid_temp_c"][0], C.SENSOR_SPECS["liquid_temp_c"][1]
            meas["liquid_temp_c"] = self._py.uniform(lo, hi)

        ctx = {
            "module_id": self.cfg.module_id, "n_modules": C.N_MODULES, "tank_volume_m3": self.profile.tank_volume_m3,
            "scenario": C.FAULT_LABELS[self.cfg.fault_id], "phase": phase, "boiloff_mode": self.cfg.boiloff_mode,
            "fault_severity": float(causes["sev"]), "variant_tag": self.cfg.variant_tag,
            "scenario_class": self.scenario_class, "layer": layer,
            "sample_period_s": SLOW_DT_S if layer == "slow" else FAST_DT_S,
            "stratification": self.cfg.stratification, "fill_target_pct": 100.0 * self.fill_target,
            "physical_model": True, "t_s": self.t,
        }
        if self.cfg.fault_id == -1:
            ctx["unknown_sub_faults"] = list(self.sub_ids)
        gt = {
            **true_values,
            "mass_kg": tank.m, "liquid_kg": tank.m_l, "t_sat_k": t_sat,
            "pcv_open": row["pcv_open"], "prv_open": row["prv_open"], "liquid_full": row["liquid_full"],
            "pbr_on": row["pbr_on"], "vent_pcv_kg_s": row["vent_pcv_kg_s"], "vent_prv_kg_s": row["vent_prv_kg_s"],
            "leak_kg_s": row["leak_kg_s"], "heat_flux_w_m2": row["flux_w_m2"], "q_pb_w": row["q_pb_w"],
            "insulation_mult": causes["ins_mult"], "strain_scf": causes["scf"],
            "inner_wall_nf_c": inner_nf_c, "h2_nf_pct": min(h2_nf, 90.0), "strain_nf_ue": strain_nf,
        }
        # ai_label = TRUE ONSET label. ai_label_observable is filled in after the run, from the paired
        # healthy counterfactual (first observable deviation); 0 until then.
        labels = {"fault_id": label, "fault_name": C.FAULT_LABELS.get(label, "unknown_anomaly"),
                  "ai_label": label, "ai_label_observable": 0}
        ts = (self.t0 + timedelta(seconds=self.t)).isoformat().replace("+00:00", "Z")
        return build_record(self.episode_id, ts, ctx, meas, gt, labels)

    def _label(self, causes: dict) -> int:
        if self._t_onset is None or self.t < self._t_onset or self.cfg.fault_id == 0:
            return 0
        return self.cfg.fault_id

    def _emit(self, phase: str, row: dict, causes: dict, mdot_in: float, mdot_out: float, force_fast: bool) -> None:
        in_burst = self.t < self._burst_until
        if self.t + 1e-9 >= self._next_slow:
            self.slow.append(self._record("slow", phase, row, causes, mdot_in, mdot_out))
            while self._next_slow <= self.t + 1e-9:
                self._next_slow += SLOW_DT_S
        if (force_fast or in_burst) and self.t + 1e-9 >= self._next_fast:
            self.fast.append(self._record("fast", phase, row, causes, mdot_in, mdot_out))
            while self._next_fast <= self.t + 1e-9:
                self._next_fast += FAST_DT_S

    # -- stepping -------------------------------------------------------------

    def _advance(self, dt: float, phase: str, mdot_in: float = 0.0, mdot_out: float = 0.0, force_fast: bool = False) -> dict | None:
        causes = self._causes(self.t)
        pcv = self.pt.pcv
        if causes["pcv_fault"] != pcv.fault:
            pcv.fault = causes["pcv_fault"]
            pcv.blocked_area_frac = causes["blocked_frac"]
        flux = (self.pt.healthy_flux_w_m2 * causes["ins_mult"] + vacuum_added_flux_w_m2(causes["dp_pa"])) \
            * ambient_flux_mult(self._ambient_c() + 273.15, self.pt.tank.T_k)
        try:
            row = self.pt.step(dt, flux, mdot_in, self.h_in if mdot_in > 0 else 0.0, mdot_out, causes["leak_area"])
        except TankOutOfRange as e:
            self.ended_reason = str(e)
            return None
        self.t += row["dt_s"]
        self._in_kg += mdot_in * row["dt_s"]
        self._out_kg += mdot_out * row["dt_s"]
        trig = bool(row["pcv_open"] or row["prv_open"] or row["liquid_full"])
        if trig and not self._trig_prev:
            self._burst_start = self.t            # a new trigger streak begins
        if trig and self._burst_start is not None and self.t < self._burst_start + BURST_MAX_S:
            self._burst_until = self.t + BURST_TAIL_S
        self._trig_prev = trig
        self._emit(phase, row, self._causes(self.t), mdot_in, mdot_out, force_fast)
        return row

    # -- run -------------------------------------------------------------------

    def generate(self) -> EpisodeResult:
        cfg = self.cfg
        m0 = self.pt.tank.m
        first = self.pt.step(0.0, self.pt.healthy_flux_w_m2)  # initial state row (dt=0)
        self._emit("filling", first, self._causes(0.0), 0.0, 0.0, True)

        # 1. filling (operations, 1 s)
        while self.pt.tank.fill_frac < self.fill_target and self.t < 4 * 3600 and self.ended_reason is None:
            self._advance(FAST_DT_S, "filling", mdot_in=self.fill_flow, force_fast=True)

        # 2. storage (60 s; 1 s during bursts)
        self._t_storage0 = self.t
        if cfg.fault_id != 0:
            self._t_onset = self.t + self._onset_draw_days * DAY
        t_end = self.t + cfg.storage_days * DAY
        while self.t < t_end - 1e-9 and self.ended_reason is None:
            in_burst = self.t < self._burst_until
            dt = FAST_DT_S if in_burst else min(SLOW_DT_S, max(self._next_slow - self.t, 1e-3))
            if self._advance(dt, "storage") is None:
                break

        # 3. discharge (operations, 1 s)
        if cfg.include_discharge and self.ended_reason is None:
            t_stop = self.t + 2 * 3600
            while self.pt.tank.fill_frac > DISCHARGE_END_FILL_FRAC and self.t < t_stop and self.ended_reason is None:
                self._advance(FAST_DT_S, "discharge", mdot_out=self.discharge_flow, force_fast=True)

        tank = self.pt.tank
        per_channel: dict[str, dict[str, float | None]] = {}
        t_obs = t_obs_clear = None
        if cfg.fault_id != 0 and cfg.compute_observability:
            twin = PhysicalEpisodeGenerator(replace(
                cfg, fault_id=0, unknown_sub_fault_ids=None, compute_observability=False,
                variant_tag=f"{cfg.variant_tag}~healthy-counterfactual")).generate()
            sig_fn = self._view.cfg.obs_sigma_fn() if self._view is not None else None
            per_channel = first_deviation_times(self.slow, twin.slow, cfg.fault_id, sigma_fn=sig_fn)
            t_obs = observable_time(per_channel, None, "k3")
            t_obs_clear = observable_time(per_channel, None, "k10")
            for rec in self.slow + self.fast:
                seen = t_obs is not None and rec["system_context"]["t_s"] >= t_obs
                rec["labels"]["ai_label_observable"] = cfg.fault_id if seen else 0
        meta = {
            "episode_id": self.episode_id, "seed": cfg.seed, "fault_id": cfg.fault_id,
            "scenario": C.FAULT_LABELS[cfg.fault_id], "variant_tag": cfg.variant_tag,
            "scenario_class": self.scenario_class, "module_id": cfg.module_id,
            "fill_target_pct": 100.0 * self.fill_target, "stratification": cfg.stratification,
            "onset_s": self._t_onset, "storage_start_s": self._t_storage0,
            "first_observable_s": t_obs, "first_observable_clear_s": t_obs_clear,
            "onset_to_first_observable_s": (t_obs - self._t_onset) if (t_obs is not None and self._t_onset is not None) else None,
            "per_channel_deviation_s": per_channel,
            "observability_definition": {
                "basis": "noise-free ground truth vs paired healthy counterfactual, 60 s grid; sensor sigma = Sec. 9 accuracy / 2",
                "k_sensitive": K_SENSITIVE, "k_clear": K_CLEAR, "n_consecutive": N_CONSECUTIVE, "sensor_outlier_k": OUTLIER_K,
                "note": "ideal-observer bound; a real detector without the healthy twin will detect later",
            },
            "healthy_exposure_s": (self._t_onset if self._t_onset is not None else self.t),
            "time_onset_to_end_s": (self.t - self._t_onset) if self._t_onset is not None else None,
            "duration_s": self.t, "ended_reason": self.ended_reason,
            "unknown_sub_faults": list(self.sub_ids), "n_slow": len(self.slow), "n_fast": len(self.fast),
            "pcv_open_events": self.pt.pcv_open_events, "prv_lift_events": self.pt.prv_lift_events,
            "liquid_full_events": self.pt.liquid_full_events, "liquid_vented_kg": self.pt.liquid_vented_kg,
            "vented_kg": self.pt.vented_kg, "leaked_kg": self.pt.leaked_kg,
            "mass_in_kg": self._in_kg, "mass_liquid_out_kg": self._out_kg,
            "mass_residual_kg": m0 + self._in_kg - self._out_kg - self.pt.vented_kg - self.pt.leaked_kg - tank.m,
            "placeholders_used": PH.used_placeholders(),
            "sensor_error_model": cfg.sensor_error_model,
            "sensor_view": cfg.sensor_view.to_dict(),
            "measurement_units": cfg.sensor_view.measurement_units(),
            "boiloff_mode": cfg.boiloff_mode,
            "boiloff_normal_pct_per_day": C.BOILOFF_LADDER_PCT_PER_DAY[cfg.boiloff_mode]["normal"],
            "fill_rule": f"spec: {100*SPEC_NOMINAL_FILL:.0f}% nominal, {100*SPEC_MAX_FILL:.0f}% maximum; above the maximum = overfill (allow_overfill, labeled)",
            "sensor_error_split": self._split.to_dict() if self._split is not None else None,
            "sensor_unit_bias": dict(self._unit_bias) if self._split is not None else dict(self.profile.sensor_bias),
        }
        return EpisodeResult(self.slow, self.fast, meta)


def generate_physical_episode(**kwargs: Any) -> EpisodeResult:
    return PhysicalEpisodeGenerator(PhysicalEpisodeConfig(**kwargs)).generate()
