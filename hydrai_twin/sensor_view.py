"""
The instrument view: what each dashboard tag reads, given the true state.

Built on the split error model (sensors.py: per-unit bias + slow drift + small noise, as multiples of the
instrument's accuracy A). On top of that this module adds, per channel:

  * SAMPLING PERIOD (reference configuration, = Sec. 9 sampling rates): the generator grid stays 1 s. A channel that
    samples every p >= 1 s takes a fresh reading every p seconds and HOLDS it in between (so a 5 s outer-wall tag
    shows 5 identical 1 s rows). A channel faster than the grid (flows and strain 0.1 s, H2 0.2 s) is AGGREGATED, not
    dropped: the 1 s value is the mean of n = 1/p native samples, so its white noise is sigma/sqrt(n). Slow and fast
    layers share the same cached reading at the same instant.
  * H2 detector (default "lfl"): a 0-100 %LFL detector, +/-5 %LFL, 100 %LFL = 4 %vol, T90 10-15 s (first-order lag).
    "spec" keeps the workbook Sec. 9 model (0-100 %vol, +/-2 %vol FS) with the zero-referenced offset workaround.
  * Vacuum gauge (default "log_gauge"): Pirani-class, error = 20% of the reading + an absolute floor, range
    0.1 Pa - 1e5 Pa. UNVERIFIED. "spec" keeps the Sec. 9 linear 0-1000 Pa, 1% FS gauge (Q6 stays open).
  * Level (default "dp"): differential-pressure gauge, 0.5% FS. It is scaled at one reference density, so when the
    saturated liquid/vapor density changes with pressure the reading is biased ("ideal" = the true level).
  * Valve states (default OFF): pcv_state / prv_state as discrete inputs open / closed / unknown. A real historian
    side channel often does not expose them; they appear only when `valve_states=True`.

Every value not from Sec. 9 is an UNVERIFIED placeholder (placeholders.py: h2_*, vacuum_gauge_*, level_dp_*).
`enabled=False` makes the generator use the previous per-record measurement (no periods, no modes).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin import placeholders as PH
from hydrai_twin.sensors import SensorErrorSplit, accuracy_abs

DEFAULT_PERIODS_S: dict[str, float] = {tag: 1.0 / spec[5] for tag, spec in C.SENSOR_SPECS.items()}   # Sec. 9 sampling column
GRID_S = 1.0
VALVE_STATE_CHANNELS = ("pcv_state", "prv_state")
H2_TAG, VAC_TAG, LEVEL_TAG = "h2_concentration_pct", "vacuum_pressure_pa", "liquid_level_pct"


@dataclass(frozen=True)
class SensorViewConfig:
    enabled: bool = True
    periods_s: dict = field(default_factory=lambda: dict(DEFAULT_PERIODS_S))
    h2_mode: str = "lfl"                 # "lfl" | "spec"
    vacuum_mode: str = "log_gauge"       # "log_gauge" | "spec"
    level_mode: str = "dp"               # "dp" | "ideal"
    valve_states: bool = False

    def __post_init__(self) -> None:
        if self.h2_mode not in ("lfl", "spec"):
            raise ValueError("h2_mode must be 'lfl' or 'spec'")
        if self.vacuum_mode not in ("log_gauge", "spec"):
            raise ValueError("vacuum_mode must be 'log_gauge' or 'spec'")
        if self.level_mode not in ("dp", "ideal"):
            raise ValueError("level_mode must be 'dp' or 'ideal'")

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "periods_s": dict(self.periods_s), "grid_s": GRID_S, "h2_mode": self.h2_mode,
                "vacuum_mode": self.vacuum_mode, "level_mode": self.level_mode, "valve_states": self.valve_states,
                "aggregation": "channels faster than the 1 s grid are averaged over 1/period native samples; slower channels hold the last reading",
                "level": "reference configuration; non-Sec.9 modes are UNVERIFIED placeholders"}

    def measurement_units(self) -> dict[str, str]:
        u = {t: C.SENSOR_SPECS[t][2] for t in C.SENSOR_SPECS}
        if self.enabled and self.h2_mode == "lfl":
            u[H2_TAG] = "%LFL"
        return u

    def measurement_ranges(self) -> dict[str, tuple[float, float]]:
        r = {t: (C.SENSOR_SPECS[t][0], C.SENSOR_SPECS[t][1]) for t in C.SENSOR_SPECS}
        if self.enabled and self.h2_mode == "lfl":
            r[H2_TAG] = (0.0, 100.0)
        if self.enabled and self.vacuum_mode == "log_gauge":
            r[VAC_TAG] = (PH.value("vacuum_gauge_min_pa"), PH.value("vacuum_gauge_max_pa"))
        return r

    def log_scale_channels(self) -> set[str]:
        return {VAC_TAG} if (self.enabled and self.vacuum_mode == "log_gauge") else set()

    def accuracy_in_measurement_units(self, tag: str, reference: float | None = None) -> float:
        """Stated accuracy A (the 2-sigma bound on total error) of a channel in this view, in the measurement unit."""
        if self.enabled and tag == H2_TAG and self.h2_mode == "lfl":
            return PH.value("h2_detector_accuracy_lfl")
        if self.enabled and tag == VAC_TAG and self.vacuum_mode == "log_gauge":
            x = max(0.0, float(reference if reference is not None else 1.0))
            return PH.value("vacuum_gauge_rel_accuracy") * x + PH.value("vacuum_gauge_floor_pa")
        return accuracy_abs(tag)

    def obs_sigma_fn(self) -> Callable[[str, np.ndarray], np.ndarray | float]:
        """sigma (= A/2) for the observability test, in GROUND-TRUTH units (H2 in %vol, vacuum in Pa)."""
        def fn(tag: str, ref: np.ndarray):
            if self.enabled and tag == H2_TAG and self.h2_mode == "lfl":
                return 0.5 * PH.value("h2_detector_accuracy_lfl") * PH.value("h2_lfl_vol_pct") / 100.0
            if self.enabled and tag == VAC_TAG and self.vacuum_mode == "log_gauge":
                return 0.5 * (PH.value("vacuum_gauge_rel_accuracy") * np.maximum(ref, 0.0) + PH.value("vacuum_gauge_floor_pa"))
            return 0.5 * accuracy_abs(tag)
        return fn


class SensorView:
    """Stateful reader for one episode. `unit_u[tag]` is the unit's bias draw in [-1, 1] (module profile),
    `drift_units[tag]` the drift series in multiples of A on the grid `env_t`."""

    def __init__(self, cfg: SensorViewConfig, split: SensorErrorSplit, unit_u: dict[str, float],
                 drift_units: dict[str, np.ndarray], env_t: np.ndarray, rng: np.random.Generator):
        self.cfg, self.split, self.unit_u, self.drift_units, self.env_t, self.rng = cfg, split, unit_u, drift_units, env_t, rng
        self._ranges = cfg.measurement_ranges()
        self._last_t: dict[str, float] = {}
        self._value: dict[str, float] = {}
        self._h2_y: float | None = None
        self._h2_t = 0.0
        self._h2_tau = PH.value("h2_detector_t90_s") / 2.3
        self._lfl_per_vol = 100.0 / PH.value("h2_lfl_vol_pct")
        self._rho_ref: tuple[float, float] | None = None

    # -- helpers --------------------------------------------------------------

    def _rho_reference(self) -> tuple[float, float]:
        if self._rho_ref is None:
            import CoolProp.CoolProp as CP
            from hydrai_twin.eos import FLUID
            p = PH.value("level_dp_reference_pressure_bar_a") * 1e5
            self._rho_ref = (CP.PropsSI("D", "P", p, "Q", 0, FLUID), CP.PropsSI("D", "P", p, "Q", 1, FLUID))
        return self._rho_ref

    def _period(self, tag: str) -> float:
        return float(self.cfg.periods_s.get(tag, DEFAULT_PERIODS_S[tag]))

    def _true_in_measurement_units(self, tag: str, true_value: float, t: float, extras: dict[str, Any]) -> float:
        if tag == H2_TAG and self.cfg.h2_mode == "lfl":
            if self._h2_y is None:
                self._h2_y = true_value
            dt = max(0.0, t - self._h2_t)
            self._h2_y += (true_value - self._h2_y) * (1.0 - math.exp(-dt / self._h2_tau))
            self._h2_t = t
            return self._h2_y * self._lfl_per_vol
        if tag == LEVEL_TAG and self.cfg.level_mode == "dp":
            rf, rg = extras.get("rho_f"), extras.get("rho_g")
            if rf is not None and rg is not None and rf > rg:
                rfr, rgr = self._rho_reference()
                return max(0.0, true_value * (rf - rg) / (rfr - rgr))
        return true_value

    def _drift(self, tag: str, t: float) -> float:
        return float(np.interp(t, self.env_t, self.drift_units[tag]))

    def _read_one(self, tag: str, true_value: float, t: float, extras: dict[str, Any]) -> float:
        x = self._true_in_measurement_units(tag, true_value, t, extras)
        period = self._period(tag)
        window = max(period, GRID_S)
        last = self._last_t.get(tag)
        if last is not None and t - last < window - 1e-6:
            return self._value[tag]                                    # hold (slow tag) / already read this instant
        n = max(1, int(round(GRID_S / period))) if period < GRID_S else 1
        a = self.cfg.accuracy_in_measurement_units(tag, x)
        err = (self.unit_u[tag] * self.split.get(tag, "bias_frac") + self._drift(tag, t)
               + self.rng.normal(0.0, self.split.get(tag, "noise_sigma_frac") / math.sqrt(n)))
        lo, hi = self._ranges[tag]
        v = float(np.clip(x + a * err, lo, hi))
        self._last_t[tag], self._value[tag] = t, v
        return v

    # -- public ---------------------------------------------------------------

    def read(self, t: float, true_values: dict[str, float], extras: dict[str, Any] | None = None) -> dict[str, Any]:
        extras = extras or {}
        out: dict[str, Any] = {tag: self._read_one(tag, v, t, extras) for tag, v in true_values.items()}
        if self.cfg.valve_states:
            out["pcv_state"] = "open" if extras.get("pcv_open") else "closed"
            out["prv_state"] = "open" if extras.get("prv_open") else "closed"
        return out
