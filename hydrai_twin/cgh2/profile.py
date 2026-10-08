"""As-built variation between CGH2 modules (the six modules are independent units, as in the LH2 twin). Ranges are simulation
assumptions (JUDGE) except the PRV set tolerance (+/-3 %, ASME VIII-1 UG-126(d), V2)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.sensor_view import CONT
from hydrai_twin.seeding import stable_seed

HALF_RANGE = {
    "volume_scale": 0.02, "wall_scale": 0.05, "h_gas_wall_mult": 0.15, "h_outer_mult": 0.15, "ambient_offset_c": 6.0,
    "solar_offset_mult": 0.20, "compressor_flow_mult": 0.10, "demand_mult": 0.20,
}


@dataclass(frozen=True)
class CGH2Profile:
    module_id: str = "nominal"
    volume_scale: float = 1.0
    wall_scale: float = 1.0
    prv_set_tol: float = 0.0               # fraction of the set pressure, within +/-3 %
    h_gas_wall_mult: float = 1.0
    h_outer_mult: float = 1.0
    ambient_offset_c: float = 0.0
    solar_offset_mult: float = 1.0
    compressor_flow_mult: float = 1.0
    demand_mult: float = 1.0
    meter_delay_fill_s: float = 5.0
    meter_delay_discharge_s: float = 5.0
    sensor_u: dict = field(default_factory=dict)       # per-channel bias draw in [-1, 1]

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["sensor_u"] = dict(self.sensor_u)
        return d


def make_profile(module_id: str, base_seed: int, scale: float = 1.0) -> CGH2Profile:
    rng = np.random.default_rng(stable_seed(base_seed, module_id, "cgh2-module-profile"))
    v = {k: 1.0 + scale * h * rng.uniform(-1, 1) if k not in ("ambient_offset_c",) else scale * h * rng.uniform(-1, 1) for k, h in HALF_RANGE.items()}
    dmin, dmax = R.value("flow_meter_delay_s")
    return CGH2Profile(
        module_id=module_id, prv_set_tol=scale * R.value("prv_set_tolerance") * rng.uniform(-1, 1),
        meter_delay_fill_s=float(rng.uniform(dmin, dmax)), meter_delay_discharge_s=float(rng.uniform(dmin, dmax)),
        sensor_u={t: scale * float(rng.uniform(-1, 1)) for t in CONT}, **v)
