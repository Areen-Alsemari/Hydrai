"""
Instrument view of the CGH2 dashboard: what each tag reads, built on the SAME bias + drift + noise split as the LH2 twin (the
reading is  true + A(true) x (u x bias_frac + drift + noise), with A the instrument's accuracy in measurement units; A can depend on the
reading, as for a flow meter specified as % of reading + zero stability).

Per channel:
  * sampling period (Sec. 9 rates, as the LH2 reference dashboard): 1 s tags read every second, 5 s / 10 s tags hold the last reading,
    channels faster than the 1 s grid (flows and strain 0.1 s, H2 0.2 s) are AGGREGATED (noise / sqrt(n)), not dropped;
  * pressure 0.25 % FS of the class transmitter range; gas temperature +/-0.5 C PLUS a bulk-gradient term (sigma ~1 K at hold, 5-10 K
    right after a compressor charge decaying over the gas-wall time constant; JUDGE) because one probe cannot see the bulk mean;
  * flows: default "datasheet" mode = 0.5 % of reading + 0.009 kg/min zero stability; flow_mode="spec" = 1 % FS; a Coriolis meter
    delay of 2-9 s (first-order) is a healthy property of each unit;
  * H2 detector default "lfl": 0-100 %LFL, +/-5 %LFL, T90 15 s first-order lag; "spec": 0-100 %vol, +/-2 % FS;
  * strain 1 % FS, ambient +/-0.3 C, outer wall +/-0.5 C;
  * discrete inputs (default ON for CGH2; switch for the ablation): compressor_status, inlet_valve, discharge_valve, prv_state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hydrai_twin.cgh2 import registry as R
from hydrai_twin.sensors import SensorErrorSplit

CONT = ("pressure_bar_a", "gas_temp_c", "outer_wall_temp_c", "h2_concentration_pct", "mass_flow_fill_kg_s", "mass_flow_discharge_kg_s",
        "strain_ue", "ambient_temp_c")
DISCRETE = ("compressor_status", "inlet_valve", "discharge_valve", "prv_state")
ALL = CONT + DISCRETE
PERIODS_S = {"pressure_bar_a": 1.0, "gas_temp_c": 1.0, "outer_wall_temp_c": 5.0, "h2_concentration_pct": 0.2,
             "mass_flow_fill_kg_s": 0.1, "mass_flow_discharge_kg_s": 0.1, "strain_ue": 0.1, "ambient_temp_c": 10.0}
STRAIN_RANGE = (-5000.0, 5000.0)
GRID_S = 1.0
KG_MIN = 1.0 / 60.0


@dataclass(frozen=True)
class CGH2ViewConfig:
    enabled: bool = True
    periods_s: dict = field(default_factory=lambda: dict(PERIODS_S))
    h2_mode: str = "lfl"                  # "lfl" | "spec"
    flow_mode: str = "datasheet"          # "datasheet" | "spec"
    valve_states: bool = True             # discrete inputs on the dashboard (compressor status, valves, PRV): ON for CGH2
    gradient: bool = True                 # bulk gas-temperature gradient term

    def __post_init__(self) -> None:
        if self.h2_mode not in ("lfl", "spec"):
            raise ValueError("h2_mode must be 'lfl' or 'spec'")
        if self.flow_mode not in ("datasheet", "spec"):
            raise ValueError("flow_mode must be 'datasheet' or 'spec'")

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "periods_s": dict(self.periods_s), "grid_s": GRID_S, "h2_mode": self.h2_mode,
                "flow_mode": self.flow_mode, "valve_states_and_compressor_status": self.valve_states, "gas_temp_gradient": self.gradient,
                "aggregation": "channels faster than the 1 s grid are averaged over 1/period native samples; slower channels hold the last reading"}

    def units(self) -> dict[str, str]:
        return {"pressure_bar_a": "bar(a)", "gas_temp_c": "C", "outer_wall_temp_c": "C",
                "h2_concentration_pct": "%LFL" if self.h2_mode == "lfl" else "%vol", "mass_flow_fill_kg_s": "kg/s",
                "mass_flow_discharge_kg_s": "kg/s", "strain_ue": "ue", "ambient_temp_c": "C"}


def ranges(cfg: CGH2ViewConfig, p_range_bar: float) -> dict[str, tuple[float, float]]:
    return {"pressure_bar_a": (0.0, p_range_bar), "gas_temp_c": tuple(R.value("gas_temp_range_c")),
            "outer_wall_temp_c": tuple(R.value("outer_wall_temp_range_c")),
            "h2_concentration_pct": (0.0, 100.0), "mass_flow_fill_kg_s": (0.0, R.value("fill_meter_range_kg_min")[1] * KG_MIN),
            "mass_flow_discharge_kg_s": (0.0, R.value("discharge_meter_range_kg_min")[1] * KG_MIN),
            "strain_ue": STRAIN_RANGE, "ambient_temp_c": (-20.0, 60.0)}


def accuracy(tag: str, cfg: CGH2ViewConfig, p_range_bar: float, reading: float = 0.0) -> float:
    """Stated accuracy A (2-sigma bound on total instrument error), in the channel's measurement unit."""
    if tag == "pressure_bar_a":
        return R.value("pressure_accuracy_pct_fs") / 100.0 * p_range_bar
    if tag == "gas_temp_c":
        return R.value("gas_temp_accuracy_c")
    if tag == "outer_wall_temp_c":
        return R.value("outer_wall_accuracy_c")
    if tag == "ambient_temp_c":
        return R.value("ambient_accuracy_c")
    if tag == "strain_ue":
        return R.value("strain_accuracy_pct_fs") / 100.0 * (STRAIN_RANGE[1] - STRAIN_RANGE[0])
    if tag == "h2_concentration_pct":
        return R.value("h2_detector_accuracy_lfl") if cfg.h2_mode == "lfl" else 2.0
    if tag in ("mass_flow_fill_kg_s", "mass_flow_discharge_kg_s"):
        if cfg.flow_mode == "spec":
            fs = ranges(cfg, p_range_bar)[tag][1]
            return R.value("flow_spec_pct_fs") / 100.0 * fs
        return R.value("flow_datasheet_pct_reading") / 100.0 * abs(reading) + R.value("flow_datasheet_zero_kg_min") * KG_MIN
    raise KeyError(tag)


def obs_sigma_fn(cfg: CGH2ViewConfig, p_range_bar: float):
    """sigma (= A/2 as the conservative total-error scale, as in the LH2 twin) per channel in GROUND-TRUTH units, for the
    observability test. H2: gt is %vol. Gas temperature includes the 1 K bulk-gradient term."""
    def fn(tag: str, ref: np.ndarray):
        if tag == "h2_concentration_pct":
            return 0.5 * accuracy(tag, cfg, p_range_bar) * (R.value("h2_lfl_vol_pct") / 100.0 if cfg.h2_mode == "lfl" else 1.0)
        if tag == "gas_temp_c":
            return math.hypot(0.5 * accuracy(tag, cfg, p_range_bar), R.value("gas_temp_gradient_hold_sigma_k") if cfg.gradient else 0.0)
        if tag in ("mass_flow_fill_kg_s", "mass_flow_discharge_kg_s"):
            return 0.5 * accuracy(tag, cfg, p_range_bar, 0.0) + 0.5 * R.value("flow_datasheet_pct_reading") / 100.0 * np.abs(ref) * (cfg.flow_mode == "datasheet")
        return 0.5 * accuracy(tag, cfg, p_range_bar)
    return fn


class CGH2SensorView:
    """Stateful reader for one episode. `unit_u[tag]` in [-1, 1] is the unit's bias draw, `drift_units[tag]` the drift series in
    multiples of A on the grid `env_t`, `delay_s` the Coriolis delays {fill, discharge}."""

    def __init__(self, cfg: CGH2ViewConfig, split: SensorErrorSplit, p_range_bar: float, unit_u: dict[str, float],
                 drift_units: dict[str, np.ndarray], env_t: np.ndarray, rng: np.random.Generator, delay_s: dict[str, float],
                 gradient_rng: np.random.Generator):
        self.cfg, self.split, self.p_range = cfg, split, p_range_bar
        self.unit_u, self.drift_units, self.env_t, self.rng, self.delay_s = unit_u, drift_units, env_t, rng, delay_s
        self._grng = gradient_rng
        self._ranges = ranges(cfg, p_range_bar)
        self._last_t: dict[str, float] = {}
        self._value: dict[str, float] = {}
        self._lag: dict[str, float] = {}
        self._lag_t: dict[str, float] = {}
        self._h2_tau = R.value("h2_detector_t90_s") / 2.3
        self._lfl_per_vol = 100.0 / R.value("h2_lfl_vol_pct")
        self._grad_hold = 0.0                   # slow random bulk-gradient (OU), K
        self._grad_t = 0.0

    def _drift(self, tag: str, t: float) -> float:
        return float(np.interp(t, self.env_t, self.drift_units[tag]))

    def _lagged(self, key: str, x: float, t: float, tau: float) -> float:
        if key not in self._lag:
            self._lag[key], self._lag_t[key] = x, t
            return x
        dt = max(0.0, t - self._lag_t[key])
        self._lag[key] += (x - self._lag[key]) * (1.0 - math.exp(-dt / max(tau, 1e-6)))
        self._lag_t[key] = t
        return self._lag[key]

    def hold_gradient(self, t: float) -> float:
        """Slow random bulk gradient (sigma 1 K, correlation 600 s), exact OU step since the last call."""
        dt = max(0.0, t - self._grad_t)
        if dt > 0:
            a = math.exp(-dt / 600.0)
            sd = R.value("gas_temp_gradient_hold_sigma_k")
            self._grad_hold = a * self._grad_hold + sd * math.sqrt(1.0 - a * a) * self._grng.normal()
            self._grad_t = t
        return self._grad_hold

    def lagged_flow(self, tag: str, x: float, t: float) -> float:
        """The meter's delayed view of the true flow (deterministic given the flow history): also the noise-free reference."""
        return self._lagged(tag, x, t, self.delay_s["fill" if tag == "mass_flow_fill_kg_s" else "discharge"])

    def _input(self, tag: str, true: float, t: float, extras: dict[str, Any]) -> float:
        if tag == "h2_concentration_pct" and self.cfg.h2_mode == "lfl":
            return self._lagged("h2", true, t, self._h2_tau) * self._lfl_per_vol
        if tag == "h2_concentration_pct":
            return self._lagged("h2", true, t, self._h2_tau)
        if tag in ("mass_flow_fill_kg_s", "mass_flow_discharge_kg_s"):
            return self.lagged_flow(tag, true, t)
        if tag == "gas_temp_c" and self.cfg.gradient:
            return true + extras.get("gradient_k", 0.0) + self.hold_gradient(t)
        return true

    def _read_one(self, tag: str, true: float, t: float, extras: dict[str, Any]) -> float:
        x = self._input(tag, true, t, extras)
        period = float(self.cfg.periods_s.get(tag, PERIODS_S[tag]))
        window = max(period, GRID_S)
        last = self._last_t.get(tag)
        if last is not None and t - last < window - 1e-6:
            return self._value[tag]
        n = max(1, int(round(GRID_S / period))) if period < GRID_S else 1
        A = accuracy(tag, self.cfg, self.p_range, x)
        err = (self.unit_u[tag] * self.split.bias_frac + self._drift(tag, t)
               + self.rng.normal(0.0, self.split.noise_sigma_frac / math.sqrt(n)))
        lo, hi = self._ranges[tag]
        v = float(np.clip(x + A * err, lo, hi))
        self._last_t[tag], self._value[tag] = t, v
        return v

    def read(self, t: float, true_values: dict[str, float], extras: dict[str, Any] | None = None) -> dict[str, Any]:
        extras = extras or {}
        out: dict[str, Any] = {tag: self._read_one(tag, true_values[tag], t, extras) for tag in CONT}
        if self.cfg.valve_states:
            out["compressor_status"] = "run" if extras.get("compressor_on") else "stop"
            out["inlet_valve"] = "open" if extras.get("inlet_open") else "closed"
            out["discharge_valve"] = "open" if extras.get("discharge_open") else "closed"
            out["prv_state"] = "open" if extras.get("prv_open") else "closed"
        return out


def ou_drift_unit(frac: float, tau_s: float, t_s: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Drift in multiples of A: exact OU, 2-sigma = frac, clipped at +/-frac."""
    sd = 0.5 * frac
    out = np.empty(len(t_s))
    x = rng.normal(0.0, sd)
    xi = rng.normal(0.0, 1.0, len(t_s))
    out[0] = x
    for k in range(1, len(t_s)):
        a = math.exp(-(t_s[k] - t_s[k - 1]) / tau_s)
        x = a * x + sd * math.sqrt(1.0 - a * a) * xi[k]
        out[k] = x
    return np.clip(out, -frac, frac)
