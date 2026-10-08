"""
CGH2EpisodeGenerator: one storage module of the compressed-gas system over `days` (default 14) at a 1 s recording grid
(dense during dispenser fills and events, 60 s snapshots otherwise: the same two-layer design as the LH2 twin).

Healthy operation: the compressor tops the vessel up between 85 % of MOP and MOP; the dispenser draws gas in fills; the gas and the
shell follow the diurnal ambient and a labelled solar offset. Faults are CAUSES acting on that physics, not painted signatures:

  1 sensor_fault                  measurement layer only (spikes on the gas-temperature probe)
  2 thermal_anomaly               intercooler failure (hot compressor discharge) or abnormal external heat input
  3 small_slow_leak               0.1-1 mm equivalent orifice (stress set 0.03-0.1 mm, labelled expected_miss)
  4 abnormal_pressure_behaviour   compressor overrun, blocked relief (PRV fails to open), fire exposure, discharge valve stuck open
  5 containment_anomaly           2-5 mm leak with detector pickup, or (rare) a 25-100 mm rupture
  6 structural_concern            stress concentration growing with the pressure-cycle count
 -1 unknown_anomaly               two of the causes 2-6 at partial weight

Labels: `ai_label` flips at the TRUE onset; `ai_label_observable` at the first observable deviation, from a paired healthy twin that
shares the weather, demand and sensor draws (hydrai_twin.observability, unchanged definition).
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from hydrai_twin.cgh2 import demand as D
from hydrai_twin.cgh2 import gas as G
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import PRIMARY, PressureClass, make_class, resolve_stop_policy
from hydrai_twin.cgh2.profile import CGH2Profile
from hydrai_twin.cgh2.sensor_view import (CONT, CGH2SensorView, CGH2ViewConfig, accuracy, obs_sigma_fn, ou_drift_unit)
from hydrai_twin.cgh2.vessel import PRV, Vessel
from hydrai_twin.observability import K_CLEAR, K_SENSITIVE, N_CONSECUTIVE, OUTLIER_K, first_deviation_times, observable_time
from hydrai_twin.physical_episode import EpisodeResult
from hydrai_twin.schema import build_record
from hydrai_twin.seeding import stable_seed
from hydrai_twin.sensors import SensorErrorSplit

DAY = 86400.0
SLOW_DT_S = 60.0
FAST_DT_S = 1.0
BURST_TAIL_S = 120.0
BURST_MAX_S = 600.0
SPIKE_PROB = 0.15
CAUSE_FAULTS = (2, 3, 4, 5, 6)

FAULT_LABELS = {0: "normal", 1: "sensor_fault", 2: "thermal_anomaly", 3: "small_slow_leak", 4: "abnormal_pressure_behaviour",
                5: "containment_anomaly", 6: "structural_concern", -1: "unknown_anomaly"}

NOISE_FREE_KEY = {"gas_temp_c": "gas_temp_sensor_nf_c", "mass_flow_fill_kg_s": "mass_flow_fill_nf_kg_s",
                  "mass_flow_discharge_kg_s": "mass_flow_discharge_nf_kg_s", "h2_concentration_pct": "h2_nf_pct"}


@dataclass
class CGH2EpisodeConfig:
    fault_id: int = 0
    module_id: str = "M01"
    pressure_class: str = PRIMARY
    seed: int | None = None
    start_time: datetime | None = None
    days: float = 14.0
    onset_day_range: tuple[float, float] = (3.0, 5.0)
    demand_pattern: str = "refuelling"                  # "refuelling" | "industrial"
    demand_kg_day: float | None = None                  # None -> drawn U(20, 50)
    stop_mode: str = "auto"                             # compressor stop: "auto" | "fixed" at MOP | "compensated" (see config.resolve_stop_policy)
    compensated_ref_temp_c: float | None = None
    solar: str = "light"                                # "light" +10 K | "dark" +27 K sun-air offset at the 1050 W/m2 peak
    profile: CGH2Profile = field(default_factory=CGH2Profile)
    ramp_duration_s: float = 3600.0
    max_severity: float = 1.0
    # cause variants
    thermal_variant: str = "intercooler"                # fault 2: "intercooler" | "external_heat"
    leak_diameter_mm: float = 0.5                       # fault 3 / 5
    leak_cd: float | None = None                        # None -> drawn U(0.6, 1.0)
    expected_miss: bool = False                         # stress set: leak too small to observe
    pressure_variant: str = "compressor_overrun"        # fault 4: compressor_overrun | blocked_relief | fire | stuck_open
    containment_variant: str = "leak"                   # fault 5: "leak" (2-5 mm) | "rupture"
    rupture_diameter_mm: float = 50.0
    unknown_sub_fault_ids: tuple[int, ...] | None = None
    prv_blowdown: str = "nominal"                       # "nominal" 7 % | "conservative" 10 %
    sensor_view: CGH2ViewConfig = field(default_factory=CGH2ViewConfig)
    sensor_split: SensorErrorSplit | None = None
    variant_tag: str = "default"
    compute_observability: bool = True
    scenario_class: str = "standard"
    compressor_enabled: bool = True                     # False = hold test (leak-detectability table): compressor never starts
    # fault 1 variant (slow sensor drift, measurement layer only; OFF by default so every existing episode is unchanged): the named channel's reading gains a bias that
    # ramps linearly from 0 at onset to drift_pct_fs % of the channel's full-scale span at onset + drift_days, then holds
    drift_tag: str | None = None                        # "pressure_bar_a" | "gas_temp_c"
    drift_pct_fs: float = 0.0
    drift_days: float = 5.0
    drift_sign: float = 1.0


class CGH2EpisodeGenerator:
    def __init__(self, cfg: CGH2EpisodeConfig):
        self.cfg = cfg
        if cfg.fault_id not in FAULT_LABELS:
            raise ValueError(f"unknown fault_id {cfg.fault_id}")
        for name, val, ok in (("thermal_variant", cfg.thermal_variant, ("intercooler", "external_heat")),
                              ("pressure_variant", cfg.pressure_variant, ("compressor_overrun", "blocked_relief", "fire", "stuck_open")),
                              ("containment_variant", cfg.containment_variant, ("leak", "rupture")),
                              ("demand_pattern", cfg.demand_pattern, ("refuelling", "industrial")),
                              ("stop_mode", cfg.stop_mode, ("auto", "fixed", "compensated")), ("solar", cfg.solar, ("light", "dark")),
                              ("prv_blowdown", cfg.prv_blowdown, ("nominal", "conservative"))):
            if val not in ok:
                raise ValueError(f"{name} must be one of {ok}")
        self.profile = cfg.profile
        self.seed = cfg.seed if cfg.seed is not None else int(np.random.SeedSequence().entropy % (2 ** 63))
        self.rng = np.random.default_rng(stable_seed(self.seed, "sensor"))
        self._rng_scn = np.random.default_rng(stable_seed(self.seed, "scenario"))
        self._rng_env = np.random.default_rng(stable_seed(self.seed, "env"))
        self._rng_dem = np.random.default_rng(stable_seed(self.seed, "demand"))
        self._rng_drift = np.random.default_rng(stable_seed(self.seed, "sensor-drift"))
        self._rng_grad = np.random.default_rng(stable_seed(self.seed, "gradient"))
        self._py = random.Random(stable_seed(self.seed, "py"))
        self.episode_id = f"CGH2-{cfg.seed:016x}" if cfg.seed is not None else f"CGH2-{uuid.uuid4().hex[:10]}"
        self.t0 = cfg.start_time or datetime(2026, 7, 1, tzinfo=timezone.utc)
        self.cls: PressureClass = make_class(cfg.pressure_class, self.profile.volume_scale, self.profile.wall_scale)
        self.stop_mode, self.comp_ref_c = resolve_stop_policy(cfg.pressure_class, cfg.solar, cfg.stop_mode, cfg.compensated_ref_temp_c)
        self.horizon_s = cfg.days * DAY

        # scenario draws (always drawn, so a healthy twin stays aligned)
        lo, hi = R.value("ambient_episode_mean_range_c")
        self._amb_mean_c = float(self._rng_scn.uniform(lo, hi)) + self.profile.ambient_offset_c
        self._start_weekday = int(self._rng_scn.integers(0, 7))
        self._kg_day = float(self._rng_scn.uniform(*R.value("demand_kg_per_day"))) if cfg.demand_kg_day is None else cfg.demand_kg_day
        self._p0_frac = float(self._rng_scn.uniform(0.88, 0.98))
        self._onset_draw_days = float(self._rng_scn.uniform(*cfg.onset_day_range))
        self._leak_cd = float(self._rng_scn.uniform(*R.value("leak_cd_range"))) if cfg.leak_cd is None else cfg.leak_cd
        self._grad_target_k = float(self._rng_scn.uniform(*R.value("gas_temp_gradient_postfill_k")))
        self._stuck_flow = float(self._rng_scn.uniform(*R.value("stuck_open_discharge_kg_min"))) / 60.0

        if cfg.fault_id == -1:
            self.sub_ids = cfg.unknown_sub_fault_ids or tuple(self._py.sample(list(CAUSE_FAULTS), 2))
            self.weights = {f: self._py.uniform(0.4, 0.8) for f in self.sub_ids}
        else:
            self.sub_ids, self.weights = (), {}

        self._build_environment()
        # demand follows the storage: the 20-50 kg/day of the medium class is scaled by the class's inventory at MOP (a low-pressure store
        # holds ~39 kg in 10 m3 and could not serve it), and no fill may exceed 25 % of that inventory (JUDGE)
        self._cap_kg = float(G.inventory_kg(self.cls.mop_bar, 300.0, self.cls.volume_m3))
        self._cap_scale = min(1.0, self._cap_kg / float(G.inventory_kg(R.value("mop_bar_medium"), 300.0, R.value("vessel_volume_m3"))))
        self._kg_day *= self._cap_scale
        max_fill = 0.25 * self._cap_kg
        self.fills = (D.refuelling_schedule(self._rng_dem, self.horizon_s, self._start_weekday, self._kg_day, self.profile.demand_mult, max_fill)
                      if cfg.demand_pattern == "refuelling" else D.industrial_schedule(self._rng_dem, self.horizon_s, self.profile.demand_mult, max_fill))
        self._fill_i = 0

        blow = R.value("prv_blowdown_nominal" if cfg.prv_blowdown == "nominal" else "prv_blowdown_conservative")
        acc = R.value("prv_accumulation_fire" if (cfg.fault_id == 4 and cfg.pressure_variant == "fire") else "prv_accumulation_single")
        prv = PRV(set_bar=self.cls.mawp_bar * (1.0 + self.profile.prv_set_tol), blowdown=blow, accumulation=acc,
                  diameter_mm=R.value("prv_effective_diameter_mm"), cd=R.value("prv_cd"))
        self.prv = prv
        Ta0 = float(self._env_amb[0]) + 273.15
        # initial inventory: a fraction of MOP at the gas temperature (fixed stop) or at the compensation reference temperature (compensated stop)
        T_init = Ta0 if self.stop_mode == "fixed" else self.comp_ref_c + 273.15
        m0 = float(G.rho_PT(self._p0_frac * self.cls.mop_bar, T_init)) * self.cls.volume_m3
        self.vessel = Vessel(self.cls, prv, m0, Ta0, Ta0, self.profile.h_gas_wall_mult, self.profile.h_outer_mult)
        self.m_start = m0

        self._build_sensors()
        self._ctl_gas = G.Gas()
        self.t = 0.0
        self._t_onset: float | None = None
        self._next_slow = 0.0
        self._next_fast = 0.0
        self._burst_until = -1.0
        self._burst_start: float | None = None
        self._trig_prev = False
        self._comp_on = False
        self._comp_frac = 0.0
        self._comp_stop_events = 0
        self._cycles_since_onset = 0
        self._grad_k = 0.0
        self._rupture_done = False
        self.slow: list[dict] = []
        self.fast: list[dict] = []
        self.ended_reason: str | None = None
        self._comp_events = 0
        self._row: dict = {}

    # -- environment -----------------------------------------------------------

    def _build_environment(self) -> None:
        n = int((self.horizon_s + 7200.0) / SLOW_DT_S) + 2
        self._env_t = np.arange(n) * SLOW_DT_S
        amp = R.value("ambient_diurnal_amplitude_k")
        dev = 0.0
        amb = np.empty(n)
        sol = np.empty(n)
        day_cloud = {}
        rise, setd = R.value("solar_day_length_h")
        peak = R.value("solar_peak_flux_w_m2")
        for k in range(n):
            hour = (self._env_t[k] / 3600.0) % 24.0
            dev = dev * math.exp(-SLOW_DT_S / 21600.0) + 1.0 * math.sqrt(1 - math.exp(-2 * SLOW_DT_S / 21600.0)) * self._rng_env.normal()
            amb[k] = np.clip(self._amb_mean_c + amp * math.sin(2 * math.pi * (hour - 9.0) / 24.0) + dev, -10.0, 55.0)
            d = int(self._env_t[k] // DAY)
            if d not in day_cloud:
                day_cloud[d] = float(self._rng_env.uniform(0.85, 1.0))
            sol[k] = peak * day_cloud[d] * math.sin(math.pi * (hour - rise) / (setd - rise)) if rise < hour < setd else 0.0
        self._env_amb, self._env_solar = amb, sol

    def _amb_c(self) -> float:
        return float(np.interp(self.t, self._env_t, self._env_amb))

    def _solar(self) -> float:
        return float(np.interp(self.t, self._env_t, self._env_solar))

    def _sunair_k(self) -> float:
        off = R.value("solar_offset_dark_k" if self.cfg.solar == "dark" else "solar_offset_light_k") * self.profile.solar_offset_mult
        return self._amb_c() + 273.15 + off * self._solar() / R.value("solar_peak_flux_w_m2")

    # -- sensors ---------------------------------------------------------------

    def _build_sensors(self) -> None:
        cfg = self.cfg
        self._split = cfg.sensor_split or SensorErrorSplit(R.value("sensor_bias_frac"), R.value("sensor_drift_frac"),
                                                           R.value("sensor_noise_sigma_frac"), R.value("sensor_drift_tau_days") * DAY)
        drift = {tag: ou_drift_unit(self._split.drift_frac, self._split.drift_tau_s, self._env_t, self._rng_drift) for tag in CONT}
        unit_u = {tag: float(self.profile.sensor_u.get(tag, 0.0)) for tag in CONT}
        self._view = CGH2SensorView(cfg.sensor_view, self._split, self.cls.transmitter_range_bar, unit_u, drift, self._env_t, self.rng,
                                    {"fill": self.profile.meter_delay_fill_s, "discharge": self.profile.meter_delay_discharge_s}, self._rng_grad)

    # -- causes ----------------------------------------------------------------

    def _ramp(self, t: float, step: bool) -> float:
        if self._t_onset is None or t < self._t_onset:
            return 0.0
        if step:
            return self.cfg.max_severity
        return min(1.0, (t - self._t_onset) / self.cfg.ramp_duration_s) * self.cfg.max_severity

    def _causes(self, t: float) -> dict[str, Any]:
        cfg = self.cfg
        c: dict[str, Any] = dict(sev=0.0, ic_dT=0.0, q_ext_w=0.0, leak_d_mm=0.0, overrun=False, prv_stuck=False, q_fire_w=0.0,
                                 stuck_flow=0.0, scf=1.0)
        if self._t_onset is None or t < self._t_onset or cfg.fault_id in (0, 1):
            return c
        faults = self.sub_ids if cfg.fault_id == -1 else (cfg.fault_id,)
        area_o = self.cls.area_outer_m2
        for fid in faults:
            w = self.weights.get(fid, 1.0)
            if fid == 2:
                s = self._ramp(t, False) * w
                if cfg.thermal_variant == "intercooler":
                    c["ic_dT"] += R.value("intercooler_failure_dT_k") * s
                else:
                    c["q_ext_w"] += R.value("external_heat_flux_w_m2") * area_o * s
                c["sev"] = max(c["sev"], s)
            elif fid == 3 or (fid == 5 and cfg.containment_variant == "leak"):
                s = min(1.0, (t - self._t_onset) / 60.0) * cfg.max_severity * w      # a leak starts abruptly (60 s)
                d = cfg.leak_diameter_mm if fid == 3 else max(cfg.leak_diameter_mm, 2.0) if cfg.leak_diameter_mm < 2.0 else cfg.leak_diameter_mm
                c["leak_d_mm"] = max(c["leak_d_mm"], d * math.sqrt(s))
                c["sev"] = max(c["sev"], s)
            elif fid == 5:                                                              # rupture: a step
                c["leak_d_mm"] = max(c["leak_d_mm"], cfg.rupture_diameter_mm)
                c["sev"] = 1.0
            elif fid == 4:
                v = cfg.pressure_variant
                s = self._ramp(t, True) * w
                if v in ("compressor_overrun", "blocked_relief"):
                    c["overrun"] = True
                if v == "blocked_relief":
                    c["prv_stuck"] = True
                if v == "fire" and t < self._t_onset + R.value("fire_duration_s"):
                    c["q_fire_w"] += R.value("fire_heat_flux_kw_m2") * 1e3 * R.value("fire_exposed_fraction") * area_o * min(1.0, (t - self._t_onset) / 300.0)
                if v == "stuck_open":
                    c["stuck_flow"] += self._stuck_flow * s
                c["sev"] = max(c["sev"], s)
            elif fid == 6:
                s = min(1.0, self._cycles_since_onset / R.value("structural_cycles_to_full_scf")) * cfg.max_severity * w
                c["scf"] += (R.value("strain_scf_max") - 1.0) * s
                c["sev"] = max(c["sev"], s)
        return c

    # -- recording -------------------------------------------------------------

    def _label(self) -> int:
        if self._t_onset is None or self.t < self._t_onset or self.cfg.fault_id == 0:
            return 0
        return self.cfg.fault_id

    def _record(self, layer: str, row: dict, causes: dict) -> dict:
        v, cls = self.vessel, self.cls
        h2_vol = R.value("h2_dispersion_pct_per_g_s") * row["mdot_leak"] * 1e3 + abs(float(self._rng_scn_noise())) * 0.02
        thermal_ue = 1.8 * (v.Tg - v.Tw)
        strain = cls.hoop_strain_ue_per_bar * causes["scf"] * row["P_bar"] + thermal_ue
        amb = self._amb_c()
        view = self._view
        fill_nf = view.lagged_flow("mass_flow_fill_kg_s", row["mdot_in"], self.t)
        disc_nf = view.lagged_flow("mass_flow_discharge_kg_s", row["mdot_disp"], self.t)
        true_values = {"pressure_bar_a": row["P_bar"], "gas_temp_c": v.Tg - 273.15, "outer_wall_temp_c": v.Tw - 273.15,
                       "h2_concentration_pct": min(h2_vol, 100.0), "mass_flow_fill_kg_s": row["mdot_in"], "mass_flow_discharge_kg_s": row["mdot_disp"],
                       "strain_ue": strain, "ambient_temp_c": amb}
        meas = view.read(self.t, true_values, {"gradient_k": self._grad_k, "compressor_on": self._comp_on, "inlet_open": self._comp_on,
                                               "discharge_open": row["mdot_disp"] > 0 or causes["stuck_flow"] > 0, "prv_open": row["prv_open"]})
        label = self._label()
        if self.cfg.fault_id == 1 and label == 1 and self.cfg.drift_tag is None and self._py.random() < SPIKE_PROB:
            lo, hi = R.value("gas_temp_range_c")
            meas["gas_temp_c"] = self._py.uniform(lo, hi)
        if self.cfg.fault_id == 1 and label == 1 and self.cfg.drift_tag is not None and self._t_onset is not None:
            lo_fs, hi_fs = (R.value("gas_temp_range_c") if self.cfg.drift_tag == "gas_temp_c" else (0.0, self.cls.transmitter_range_bar))
            frac = min(1.0, max(0.0, (self.t - self._t_onset) / (self.cfg.drift_days * DAY)))
            meas[self.cfg.drift_tag] = meas[self.cfg.drift_tag] + self.cfg.drift_sign * self.cfg.drift_pct_fs / 100.0 * (hi_fs - lo_fs) * frac
        ctx = {"system": "cgh2", "module_id": self.cfg.module_id, "pressure_class": cls.name, "mop_bar": cls.mop_bar,
               "tank_volume_m3": cls.volume_m3, "scenario": FAULT_LABELS[self.cfg.fault_id], "phase": "operation", "layer": layer,
               "fault_severity": float(causes["sev"]), "variant_tag": self.cfg.variant_tag, "scenario_class": self.cfg.scenario_class,
               "expected_miss": bool(self.cfg.expected_miss), "sample_period_s": SLOW_DT_S if layer == "slow" else FAST_DT_S,
               "demand_pattern": self.cfg.demand_pattern, "compressor_on": self._comp_on, "dispensing": row["mdot_disp"] > 0,
               "physical_model": True, "t_s": self.t}
        if self.cfg.fault_id == -1:
            ctx["unknown_sub_faults"] = list(self.sub_ids)
        gt = {**true_values, "mass_kg": v.m, "gas_temp_k": v.Tg, "wall_temp_k": v.Tw, "gas_temp_sensor_nf_c": v.Tg - 273.15 + self._grad_k,
              "gas_gradient_k": self._grad_k, "mass_flow_fill_nf_kg_s": fill_nf, "mass_flow_discharge_nf_kg_s": disc_nf,
              "h2_nf_pct": min(h2_vol, 100.0), "strain_scf": causes["scf"], "solar_flux_w_m2": self._solar(),
              "mdot_leak_kg_s": row["mdot_leak"], "mdot_prv_kg_s": row["mdot_prv"], "prv_open": row["prv_open"], "compressor_on": self._comp_on,
              "q_wall_gas_w": row["q_wg_w"], "ic_dT_k": causes["ic_dT"], "inventory_kg": v.m}
        labels = {"fault_id": label, "fault_name": FAULT_LABELS.get(label, "unknown_anomaly"), "ai_label": label, "ai_label_observable": 0}
        ts = (self.t0 + timedelta(seconds=self.t)).isoformat().replace("+00:00", "Z")
        return build_record(self.episode_id, ts, ctx, meas, gt, labels)

    def _rng_scn_noise(self) -> float:
        return self.rng.normal(0.0, 1.0)

    def _emit(self, row: dict, causes: dict, force_fast: bool) -> None:
        in_burst = self.t < self._burst_until
        if self.t + 1e-9 >= self._next_slow:
            self.slow.append(self._record("slow", row, causes))
            while self._next_slow <= self.t + 1e-9:
                self._next_slow += SLOW_DT_S
        if (force_fast or in_burst) and self.t + 1e-9 >= self._next_fast:
            self.fast.append(self._record("fast", row, causes))
            while self._next_fast <= self.t + 1e-9:
                self._next_fast += FAST_DT_S

    # -- stepping --------------------------------------------------------------

    def _active_fill(self, t: float, dt: float) -> float:
        """Mean dispenser draw (kg/s) over [t, t+dt]."""
        tot = 0.0
        i = self._fill_i
        while i < len(self.fills) and self.fills[i].t1 <= t:
            i += 1
        self._fill_i = i
        j = i
        while j < len(self.fills) and self.fills[j].t0 < t + dt:
            f = self.fills[j]
            tot += f.rate_kg_s * max(0.0, min(t + dt, f.t1) - max(t, f.t0))
            j += 1
        return tot / dt

    def _next_fill_start(self, t: float) -> float | None:
        for f in self.fills[self._fill_i:]:
            if f.t0 > t + 1e-9:
                return f.t0
        return None

    def _ctl_pressure(self) -> float:
        if self.stop_mode == "fixed":
            return self.vessel.P_bar
        return self._ctl_gas.pressure_bar_at(self.vessel.rho, self.comp_ref_c + 273.15)

    def _advance(self, dt: float, force_fast: bool) -> bool:
        cfg, cls, v = self.cfg, self.cls, self.vessel
        causes = self._causes(self.t)
        self.prv.stuck_closed = causes["prv_stuck"]
        # compressor control (evaluated on its own pressure signal)
        pc = self._ctl_pressure()
        was_on = self._comp_on
        stop_p, start_p = cls.comp_stop_bar, cls.comp_start_bar
        if not self._comp_on and pc < start_p and cfg.compressor_enabled:
            self._comp_on = True
        elif self._comp_on and not causes["overrun"] and (pc >= stop_p or v.P_bar >= cls.pahh_bar):
            self._comp_on = False
            self._comp_stop_events += 1
            if self._t_onset is not None and self.t >= self._t_onset:
                self._cycles_since_onset += 1
        if self._comp_on != was_on:
            self._burst_until = max(self._burst_until, self.t + BURST_TAIL_S)
            self._comp_events += 1
        ramp = max(dt / R.value("compressor_ramp_s"), 1e-6)
        self._comp_frac = min(1.0, self._comp_frac + ramp) if self._comp_on else max(0.0, self._comp_frac - ramp)
        flow = cls.compressor_kg_h / 3600.0 * self.profile.compressor_flow_mult * self._comp_frac
        T_in = self._amb_c() + 273.15 + R.value("compressor_discharge_dT_ambient_k") + causes["ic_dT"]
        mdot_disp = self._active_fill(self.t, dt) + causes["stuck_flow"]
        leak_area = math.pi / 4.0 * (causes["leak_d_mm"] * 1e-3) ** 2
        row = v.step(dt, self._sunair_k(), flow, T_in, mdot_disp, leak_area, self._leak_cd, causes["q_ext_w"], causes["q_fire_w"])
        # gas-temperature gradient (what one probe sees vs the bulk): builds while charging, decays over the gas-wall time constant
        tau_gw = self._tau_gw
        if self._comp_on:
            self._grad_k += (self._grad_target_k - self._grad_k) * (1 - math.exp(-dt / R.value("gas_temp_gradient_rise_tau_s")))
        else:
            self._grad_k *= math.exp(-dt / tau_gw)
        self.t += dt
        row["mdot_in"], row["mdot_disp"] = flow, mdot_disp
        trig = bool(row["prv_open"] or v.P_bar >= cls.pah_bar or (causes["leak_d_mm"] > 0 and self._t_onset is not None and self.t < self._t_onset + BURST_MAX_S))
        if trig and not self._trig_prev:
            self._burst_start = self.t
        if trig and self._burst_start is not None and self.t < self._burst_start + BURST_MAX_S:
            self._burst_until = max(self._burst_until, self.t + BURST_TAIL_S)
        self._trig_prev = trig
        self._row = row
        self._emit(row, self._causes(self.t), force_fast)
        if v.P_bar > 1.5 * cls.mawp_bar:
            self.ended_reason = "vessel overpressure failure (P > 1.5 x MAWP)"
        elif v.Tw > R.value("wall_failure_temp_k"):
            self.ended_reason = "wall over-temperature (steel strength loss)"
        elif v.m <= v.min_m + 1e-6 or v.P_bar < 1.5:
            self.ended_reason = "vessel emptied (inventory exhausted)"
        return self.ended_reason is None

    def _fast_fallback(self, twin: EpisodeResult, per_channel: dict) -> dict:
        """For episodes that end within minutes of onset: the same k-sigma / N-consecutive rule on the 1 s fast rows against the healthy twin's
        60 s truth interpolated to those times (the 60 s grid has no post-onset samples)."""
        tw_t = np.array([r["system_context"]["t_s"] for r in twin.slow])
        sig = obs_sigma_fn(self.cfg.sensor_view, self.cls.transmitter_range_bar)
        rows = [r for r in self.fast if r["system_context"]["t_s"] >= (self._t_onset or 0.0) - 60.0]
        if len(rows) < N_CONSECUTIVE:
            return per_channel
        tf = np.array([r["system_context"]["t_s"] for r in rows])
        out = dict(per_channel)
        for tag in CONT:
            key = NOISE_FREE_KEY.get(tag, tag)
            f = np.array([r["simulation_ground_truth"][key] for r in rows], dtype=float)
            h = np.interp(tf, tw_t, np.array([r["simulation_ground_truth"][key] for r in twin.slow], dtype=float))
            sg = sig(tag, h)
            entry = {}
            for lab, k in (("k3", K_SENSITIVE), ("k10", K_CLEAR)):
                hit = np.convolve((np.abs(f - h) > k * sg).astype(int), np.ones(N_CONSECUTIVE, dtype=int), mode="valid")
                idx = np.flatnonzero(hit >= N_CONSECUTIVE)
                entry[lab] = float(tf[idx[0]]) if len(idx) else None
            out[tag] = entry
        return out

    def generate(self) -> EpisodeResult:
        cfg = self.cfg
        self._tau_gw = self.cls.tau_gas_wall_s()
        if cfg.fault_id != 0:
            self._t_onset = self._onset_draw_days * DAY
        first = {"P_bar": self.vessel.P_bar, "Tg_k": self.vessel.Tg, "Tw_k": self.vessel.Tw, "m_kg": self.vessel.m, "mdot_in": 0.0, "mdot_disp": 0.0,
                 "mdot_leak": 0.0, "mdot_prv": 0.0, "prv_open": False, "prv_lift": 0.0, "q_wg_w": 0.0}
        self._emit(first, self._causes(0.0), True)
        t_end = self.horizon_s
        while self.t < t_end - 1e-9 and self.ended_reason is None:
            dispensing = self._active_fill(self.t, 1.0) > 0
            fast = dispensing or self.t < self._burst_until
            dt = FAST_DT_S if fast else min(SLOW_DT_S, max(self._next_slow - self.t, 1e-3))
            nxt = self._next_fill_start(self.t)
            if nxt is not None and not fast and nxt - self.t < dt:
                dt = max(nxt - self.t, 1e-3)
            if self._t_onset is not None and self.t < self._t_onset and self._t_onset - self.t < dt:
                dt = max(self._t_onset - self.t, 1e-3)
            dt = min(dt, t_end - self.t)
            if not self._advance(dt, dispensing):
                break

        twin_per_channel: dict[str, dict] = {}
        t_obs = t_obs_clear = None
        if cfg.fault_id != 0 and cfg.compute_observability:
            twin = CGH2EpisodeGenerator(replace(cfg, fault_id=0, unknown_sub_fault_ids=None, compute_observability=False,
                                                variant_tag=f"{cfg.variant_tag}~healthy-counterfactual")).generate()
            twin_per_channel = first_deviation_times(self.slow, twin.slow, cfg.fault_id, sigma_fn=obs_sigma_fn(cfg.sensor_view, self.cls.transmitter_range_bar),
                                                     tags=CONT, noise_free_key=NOISE_FREE_KEY, sensor_fault_tag="gas_temp_c")
            if self._t_onset is not None and (self.t - self._t_onset) < 900.0:        # ended within 15 min of onset (rupture): 60 s grid too coarse
                twin_per_channel = self._fast_fallback(twin, twin_per_channel)
            t_obs = observable_time(twin_per_channel, None, "k3")
            t_obs_clear = observable_time(twin_per_channel, None, "k10")
            for rec in self.slow + self.fast:
                seen = t_obs is not None and rec["system_context"]["t_s"] >= t_obs
                rec["labels"]["ai_label_observable"] = cfg.fault_id if seen else 0
        v = self.vessel
        meta = {
            "system": "cgh2", "episode_id": self.episode_id, "seed": cfg.seed, "fault_id": cfg.fault_id, "scenario": FAULT_LABELS[cfg.fault_id],
            "variant_tag": cfg.variant_tag, "scenario_class": cfg.scenario_class, "module_id": cfg.module_id, "pressure_class": self.cls.name,
            "expected_miss": cfg.expected_miss, "demand_pattern": cfg.demand_pattern, "demand_kg_per_day": self._kg_day,
            "stop_mode": self.stop_mode, "compensation_ref_temp_c": (self.comp_ref_c if self.stop_mode == "compensated" else None), "solar": cfg.solar, "onset_s": self._t_onset,
            "first_observable_s": t_obs, "first_observable_clear_s": t_obs_clear,
            "onset_to_first_observable_s": (t_obs - self._t_onset) if (t_obs is not None and self._t_onset is not None) else None,
            "per_channel_deviation_s": twin_per_channel,
            "observability_definition": {"basis": "noise-free ground truth vs paired healthy counterfactual, 60 s grid; sigma = accuracy / 2 (gas temperature incl. 1 K bulk gradient)",
                                         "k_sensitive": K_SENSITIVE, "k_clear": K_CLEAR, "n_consecutive": N_CONSECUTIVE, "sensor_outlier_k": OUTLIER_K,
                                         "note": "ideal-observer bound; a real detector without the healthy twin will detect later"},
            "healthy_exposure_s": (self._t_onset if self._t_onset is not None else self.t),
            "time_onset_to_end_s": (self.t - self._t_onset) if self._t_onset is not None else None,
            "duration_s": self.t, "ended_reason": self.ended_reason, "unknown_sub_faults": list(self.sub_ids),
            "n_slow": len(self.slow), "n_fast": len(self.fast),
            "compressor_stop_events": self._comp_stop_events, "prv_lift_events": self.prv.lift_events, "prv_set_bar_actual": self.prv.set_bar,
            "vented_prv_kg": v.vented_prv_kg, "leaked_kg": v.leaked_kg, "dispensed_kg": v.dispensed_kg, "charged_kg": v.charged_kg,
            "mass_residual_kg": self.m_start + v.charged_kg - v.dispensed_kg - v.leaked_kg - v.vented_prv_kg - v.m,
            "class": self.cls.to_dict(), "meter_delay_s": {"fill": self.profile.meter_delay_fill_s, "discharge": self.profile.meter_delay_discharge_s},
            "sensor_view": cfg.sensor_view.to_dict(), "measurement_units": cfg.sensor_view.units(),
            "sensor_split": self._split.to_dict(), "registry_used": R.used(),
        }
        return EpisodeResult(self.slow, self.fast, meta)


def generate_cgh2_episode(**kwargs: Any) -> EpisodeResult:
    return CGH2EpisodeGenerator(CGH2EpisodeConfig(**kwargs)).generate()
