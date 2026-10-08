"""
Per-module as-built/installed variation.

The workbook (Sec.1/2) specifies ONE canonical module and says M01-M06 are
identical in design. Real units are never identical, and a dataset where
every module is physically the same makes a "held-out module" split test
nothing but unseen noise draws. This module adds explicit, bounded,
reproducible differences between modules so that holding one out is a real
generalization test.

EVERY range below is a simulation assumption, NOT a workbook value -- the
workbook gives no tolerances or installation data. They are chosen to be
small, physically plausible, and to stay inside the workbook's own normal
operating envelopes (Sec.5/6/8) and sensor accuracy specs (Sec.9). Adjust
them in VARIATION_HALF_RANGE; `scale=0` reproduces the identical-modules
twin exactly (NOMINAL_PROFILE), `scale=1` is the default spread.

What varies, and the reasoning:
  insulation_leak_mult   as-built MLI/vacuum quality: scales the healthy
                         boil-off rate (Sec.7 normal stage) -- unit-to-unit
                         scatter in as-built heat leak is normal.
  tank_volume_m3         fabrication tolerance on the Sec.2 10 m3 volume.
  wall_thickness_m       plate/forming tolerance on the Sec.2 10 mm wall
                         (affects the hoop-strain ground truth).
  pcv_setpoint_offset_bar  where this module's PCV regulates inside the
                         Sec.5 normal band (1.0-1.5 bar(a)); offset is kept
                         small enough that the setpoint stays inside it.
  pressure_noise_mult    valve/regulator dynamics: how jittery pressure is.
  ambient_offset_c       site/orientation (sun exposure, shelter): shifts
                         the ambient and outer-wall temperature level.
  fill_flow_mult / discharge_flow_mult  piping/pump differences: nominal
                         Sec.8 flows scaled (still clipped to Sec.8 ranges).
  vacuum_baseline_pa     healthy jacket pressure differs unit to unit
                         (outgassing / leak-up history).
  sensor_bias            fixed calibration offset per sensor, up to
                         +/-0.5x the Sec.9 stated accuracy (so a biased
                         sensor is still within spec). Sec.9 gives accuracy
                         only; the handoff Sec.12 lists "bias" and
                         "calibration error" as sensor effects to model.

A monitor does not know a module's profile: nothing here is exposed to the
ML features (see ml/features.py), only ever to the physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hydrai_twin import constants as C
from hydrai_twin.seeding import stable_seed
from hydrai_twin.sensors import accuracy_abs

# half-widths of the uniform spread around the nominal value (scale=1)
VARIATION_HALF_RANGE = {
    "insulation_leak_mult": 0.20,
    "tank_volume_m3": 0.02 * C.TANK_INTERNAL_VOLUME_M3,
    "wall_thickness_m": 0.05 * C.WALL_THICKNESS_M,
    "pcv_setpoint_offset_bar": 0.10,
    "pressure_noise_mult": 0.25,
    "ambient_offset_c": 6.0,
    "fill_flow_mult": 0.20,
    "discharge_flow_mult": 0.20,
    "vacuum_baseline_pa": 0.85,   # around 1.15 Pa -> 0.3 .. 2.0 Pa
}
_NOMINAL = {
    "insulation_leak_mult": 1.0,
    "tank_volume_m3": C.TANK_INTERNAL_VOLUME_M3,
    "wall_thickness_m": C.WALL_THICKNESS_M,
    "pcv_setpoint_offset_bar": 0.0,
    "pressure_noise_mult": 1.0,
    "ambient_offset_c": 0.0,
    "fill_flow_mult": 1.0,
    "discharge_flow_mult": 1.0,
    "vacuum_baseline_pa": 0.5,    # the identical-modules twin's healthy value
}
_VACUUM_CENTER_PA = 1.15
SENSOR_BIAS_FRACTION_OF_ACCURACY = 0.5


@dataclass(frozen=True)
class ModuleProfile:
    module_id: str = "nominal"
    insulation_leak_mult: float = 1.0
    tank_volume_m3: float = C.TANK_INTERNAL_VOLUME_M3
    wall_thickness_m: float = C.WALL_THICKNESS_M
    pcv_setpoint_offset_bar: float = 0.0
    pressure_noise_mult: float = 1.0
    ambient_offset_c: float = 0.0
    fill_flow_mult: float = 1.0
    discharge_flow_mult: float = 1.0
    vacuum_baseline_pa: float = 0.5
    sensor_bias: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["sensor_bias"] = dict(self.sensor_bias)
        return d


NOMINAL_PROFILE = ModuleProfile()


def make_profile(module_id: str, base_seed: int, scale: float = 1.0) -> ModuleProfile:
    """Deterministic profile for `module_id` given `base_seed`. scale=0 ->
    identical to NOMINAL_PROFILE (apart from module_id)."""
    rng = np.random.default_rng(stable_seed(base_seed, module_id, "module-profile"))
    vals = {}
    for name, half in VARIATION_HALF_RANGE.items():
        center = _VACUUM_CENTER_PA if name == "vacuum_baseline_pa" else _NOMINAL[name]
        nominal = _NOMINAL[name]
        draw = center + half * rng.uniform(-1.0, 1.0)
        vals[name] = nominal + scale * (draw - nominal)
    bias = {
        s: scale * SENSOR_BIAS_FRACTION_OF_ACCURACY * accuracy_abs(s) * float(rng.uniform(-1.0, 1.0))
        for s in C.SENSOR_SPECS
    }
    return ModuleProfile(module_id=module_id, sensor_bias=bias, **vals)
