"""
CGH2 dashboard: tag list, periods and static alarm limits (reference configuration, not a verified Saudi system).

Reuses AlarmLimit / TagSpec from hydrai_twin.channels (read-only) so the LH2 static-alarm scorers work unchanged. Alarm limits are
PROVISIONAL: PAH = 1.02 x MOP and PAHH = 1.05 x MOP (Addendum 1, CALC), gas temperature 85 / 100 C (JUDGE), hydrogen 25 / 50 %LFL
(INL, V1). No alarm is defined for flows, strain, outer-wall temperature, ambient temperature, compressor status or valve states:
a fault that shows only there has "no alarm defined".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from hydrai_twin.channels import AlarmLimit, TagSpec
from hydrai_twin.cgh2 import registry as R
from hydrai_twin.cgh2.config import PressureClass, make_class
from hydrai_twin.cgh2.sensor_view import CONT, DISCRETE, PERIODS_S, CGH2ViewConfig, ranges

REFERENCE_LABEL = "reference configuration, not a verified Saudi system"
PROVISIONAL_NOTE = ("PROVISIONAL: static-alarm limits are PAH 1.02 x MOP, PAHH 1.05 x MOP (Addendum 1), gas temperature 85/100 C (JUDGE) and "
                    "hydrogen 25/50 %LFL (INL); no real Saudi alarm settings are public")
REFERENCE_PATH = Path(__file__).resolve().parent.parent.parent / "dashboard_tags_cgh2.json"
ALIASES = {"ullage_pressure": "pressure_bar_a", "gas_temp": "gas_temp_c", "outer_wall_temp": "outer_wall_temp_c", "h2_ambient_detector": "h2_concentration_pct",
           "fill_flow": "mass_flow_fill_kg_s", "discharge_flow": "mass_flow_discharge_kg_s", "strain": "strain_ue", "ambient_temp": "ambient_temp_c"}
LFL_PER_VOL = 100.0 / 4.0


@dataclass
class CGH2Dashboard:
    pressure_class: str
    tags: list[TagSpec]
    alarms: list[AlarmLimit]
    status: str = REFERENCE_LABEL
    note: str = ""
    valve_states_available: bool = True
    alarm_load: dict[str, Any] = field(default_factory=dict)
    historian_defaults: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def reference(cls, pressure_class: str = "medium", valve_states: bool = True, h2_mode: str = "lfl") -> "CGH2Dashboard":
        raw = json.loads(REFERENCE_PATH.read_text())
        pc: PressureClass = make_class(pressure_class)
        view = CGH2ViewConfig(h2_mode="lfl")            # limits are defined in %LFL; with_h2_mode converts them below
        rng = ranges(view, pc.transmitter_range_bar)
        names = {"pressure_bar_a": "GH2-PT-101", "gas_temp_c": "GH2-TT-101", "outer_wall_temp_c": "GH2-TT-102", "h2_concentration_pct": "GH2-AT-101",
                 "mass_flow_fill_kg_s": "GH2-FT-101", "mass_flow_discharge_kg_s": "GH2-FT-102", "strain_ue": "GH2-SE-101", "ambient_temp_c": "GH2-TT-901"}
        units = view.units()
        src = {t["channel"]: t.get("source", "") for t in raw["tags"]}
        srcmap = {"pressure_bar_a": "ullage_pressure", "gas_temp_c": "gas_temp_c", "outer_wall_temp_c": "outer_wall_temp_c",
                  "h2_concentration_pct": "h2_ambient_detector", "mass_flow_fill_kg_s": "fill_flow", "mass_flow_discharge_kg_s": "discharge_flow",
                  "strain_ue": "strain", "ambient_temp_c": "ambient_temp"}
        tags = [TagSpec(names[c], c, PERIODS_S[c], units[c], rng[c], "", src.get(srcmap[c], ""), "") for c in CONT]
        alarms = [
            AlarmLimit("pressure_bar_a", "high", pc.pah_bar, "warning", name="PAH", basis="1.02 x MOP (Addendum 1, CALC)"),
            AlarmLimit("pressure_bar_a", "high", pc.pahh_bar, "critical", name="PAHH", basis="1.05 x MOP (Addendum 1, CALC)"),
            AlarmLimit("gas_temp_c", "high", R.value("gas_temp_alarm_c")[0], "warning", name="TAH", basis="JUDGE"),
            AlarmLimit("gas_temp_c", "high", R.value("gas_temp_alarm_c")[1], "critical", name="TAHH", basis="JUDGE"),
            AlarmLimit("h2_concentration_pct", "high", R.value("h2_alarm_lfl"), "warning", name="AAH", basis="INL (V1); ISO 26142 (V2)"),
            AlarmLimit("h2_concentration_pct", "high", R.value("h2_trip_lfl"), "critical", name="AAHH", basis="INL (V1)"),
        ]
        d = cls(pressure_class, tags, alarms, raw["_meta"]["status"], raw["_meta"]["name"], valve_states, raw.get("alarm_load", {}), raw.get("historian_defaults", {}))
        return d.with_h2_mode(h2_mode)

    def with_h2_mode(self, mode: str) -> "CGH2Dashboard":
        target = "%LFL" if mode == "lfl" else "%vol"
        tag = self.tag_for("h2_concentration_pct")
        if tag is None or tag.unit == target:
            return self
        f = LFL_PER_VOL if target == "%LFL" else 1.0 / LFL_PER_VOL
        return replace(self, tags=[replace(t, unit=target) if t.channel == "h2_concentration_pct" else t for t in self.tags],
                       alarms=[replace(a, limit=a.limit * f) if a.channel == "h2_concentration_pct" else a for a in self.alarms])

    def tag_for(self, channel: str) -> TagSpec | None:
        return next((t for t in self.tags if t.channel == channel), None)

    def tag_names(self) -> dict[str, str]:
        return {t.channel: t.name for t in self.tags}

    def periods_s(self) -> dict[str, float]:
        return {t.channel: float(t.period_s) for t in self.tags}

    def alarms_for(self, channel: str) -> list[AlarmLimit]:
        return [a for a in self.alarms if a.channel == channel]

    def mask(self, valve_states: bool | None = None) -> frozenset[str]:
        ch = {t.channel for t in self.tags}
        if self.valve_states_available if valve_states is None else valve_states:
            ch |= set(DISCRETE)
        return frozenset(ch)

    def channels_without_alarm(self) -> list[str]:
        have = {a.channel for a in self.alarms}
        return [t.channel for t in self.tags if t.channel not in have] + list(DISCRETE)

    def to_dict(self) -> dict[str, Any]:
        return {"system": "cgh2", "pressure_class": self.pressure_class, "status": self.status, "note": self.note, "level": "reference",
                "valve_states_available": self.valve_states_available, "alarm_load": self.alarm_load, "historian_defaults": self.historian_defaults,
                "tags": [{"name": t.name, "channel": t.channel, "period_s": t.period_s, "unit": t.unit, "range": list(t.range) if t.range else None,
                          "source": t.source} for t in self.tags],
                "alarms": [{"channel": a.channel, "direction": a.direction, "limit": a.limit, "level": a.level, "on_delay_samples": a.on_delay_samples,
                            "name": a.name, "basis": a.basis} for a in self.alarms],
                "provisional": PROVISIONAL_NOTE}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CGH2Dashboard":
        tags = [TagSpec(t["name"], t["channel"], float(t["period_s"]), t.get("unit", ""), tuple(t["range"]) if t.get("range") else None, "", t.get("source", ""), "")
                for t in d["tags"]]
        alarms = [AlarmLimit(a["channel"], a["direction"], float(a["limit"]), a.get("level", "warning"), int(a.get("on_delay_samples", 1)), a.get("name", ""), a.get("basis", ""))
                  for a in d["alarms"]]
        return cls(d["pressure_class"], tags, alarms, d.get("status", REFERENCE_LABEL), d.get("note", ""), d.get("valve_states_available", True),
                   d.get("alarm_load", {}), d.get("historian_defaults", {}))
