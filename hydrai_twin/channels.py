"""
Channel mask and dashboard configuration.

The agent will be added to EXISTING dashboards, so a model may only use tags that exist there. No real Saudi LH2
dashboard is publicly documented, so the default is the REFERENCE configuration in `dashboard_tags.json`:
**reference configuration, not a verified Saudi system.** That label travels with the config (`status`) into every
manifest. `dashboard_tags.example.json` keeps the earlier minimal example format, still loadable.

This module separates three things:

  * the twin's full channel set (the 11 Sec. 9 measurements; the inner-wall temperature has no tag on the reference
    dashboard, so a model cannot see it);
  * a ChannelMask: the subset a model is allowed to see (tags on the dashboard; valve states only if switched on);
  * a DashboardConfig: tag name, unit, range, sample period, and the static alarm limits per tag.

STATIC ALARM LIMITS. The reference config gives numeric H / HH only for hydrogen (20 / 40 %LFL, UNVERIFIED). The other
limits are the workbook's own Sec. 5 / 6 warning and critical values, labelled "simulation threshold". Every report that
uses them must call the static-alarm baseline PROVISIONAL (`PROVISIONAL_NOTE`).

UNITS. Channels keep the workbook's units (Sec. 9: liquid temperature in degC). The reference config lists the
liquid-temperature tag in K; the spec wins, so the tag is carried in degC (K = degC + 273.15).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from hydrai_twin import constants as C

REFERENCE_LABEL = "reference configuration, not a verified Saudi system"
PROVISIONAL_NOTE = ("PROVISIONAL: static-alarm limits are the workbook's 'simulation threshold' values (Sec. 5/6; hydrogen 20/40 %LFL "
                    "unverified), not the plant's real alarm settings")
REFERENCE_PATH = Path(__file__).resolve().parent.parent / "dashboard_tags.json"

MEASURED_CHANNELS: tuple[str, ...] = tuple(C.SENSOR_SPECS)
# Discrete inputs; exist only if the plant exposes them to the historian side channel (Q5) and the switch is on.
VALVE_STATE_CHANNELS: tuple[str, ...] = ("pcv_state", "prv_state")
OPTIONAL_CHANNELS: tuple[str, ...] = VALVE_STATE_CHANNELS
ALL_CHANNELS: tuple[str, ...] = MEASURED_CHANNELS + OPTIONAL_CHANNELS

# reference-config channel names -> twin channels (twin names map to themselves)
CHANNEL_ALIASES: dict[str, str] = {
    "ullage_pressure": "pressure_bar_a", "liquid_temp_inner": "liquid_temp_c", "outer_wall_temp": "outer_wall_temp_c",
    "h2_ambient_detector": "h2_concentration_pct", "level": "liquid_level_pct", "fill_flow": "mass_flow_fill_kg_s",
    "discharge_flow": "mass_flow_discharge_kg_s", "strain": "strain_ue", "vacuum_jacket": "vacuum_pressure_pa",
    "ambient_temp": "ambient_temp_c", "inner_wall_temp": "inner_wall_temp_c",
}
VALVE_STATES_CHANNEL = "valve_states"
H2_CH = "h2_concentration_pct"
LFL_PER_VOL = 100.0 / C.H2_FLAMMABILITY_RANGE_VOL_PCT[0]       # 100 %LFL = 4 %vol -> 25 %LFL per %vol


@dataclass(frozen=True)
class AlarmLimit:
    channel: str
    direction: str            # "high" | "low"
    limit: float
    level: str                # "warning" | "critical"
    on_delay_samples: int = 1  # consecutive samples beyond the limit before the alarm raises
    name: str = ""            # e.g. PAH, PAHH, AAH, AAHH
    basis: str = "simulation threshold"

    def breached(self, value: float) -> bool:
        return value > self.limit if self.direction == "high" else value < self.limit


@dataclass(frozen=True)
class TagSpec:
    name: str                       # the dashboard's tag name, e.g. LH2-PT-101
    channel: str                    # which twin channel it carries
    period_s: float = 60.0          # the dashboard's sample period
    unit: str = ""
    range: tuple[float, float] | None = None
    accuracy: str = ""
    source: str = ""                # SPEC | UNV | STD (reference-config provenance)
    technique: str = ""


@dataclass(frozen=True)
class ChannelMask:
    enabled: frozenset[str]

    @classmethod
    def of(cls, channels: Iterable[str]) -> "ChannelMask":
        ch = frozenset(channels)
        unknown = ch - set(ALL_CHANNELS)
        if unknown:
            raise ValueError(f"unknown channels {sorted(unknown)}; known: {list(ALL_CHANNELS)}")
        return cls(ch)

    @classmethod
    def all_measured(cls) -> "ChannelMask":
        return cls.of(MEASURED_CHANNELS)

    def allows(self, channel: str) -> bool:
        return channel in self.enabled

    def apply_to_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Copy of `rec` whose measurements (and quality codes) contain only enabled channels. Ground truth, labels, the
        pre-historian live values and the injected-fault labels are evaluation data and are removed."""
        out = copy.copy(rec)
        out["measurements"] = {k: v for k, v in rec["measurements"].items() if k in self.enabled}
        if "measurement_quality" in rec:
            out["measurement_quality"] = {k: v for k, v in rec["measurement_quality"].items() if k in self.enabled}
        for k in ("simulation_ground_truth", "labels", "measurements_live", "data_faults"):
            out.pop(k, None)
        return out

    def parquet_columns(self, available: Iterable[str]) -> list[str]:
        """Model-visible columns of a slow-layer Parquet file: identifiers, enabled measurement columns and their OPC quality
        codes. No ground-truth (gt__), label (label__), live (live__) or injected-fault (dfault__) column is returned."""
        keep = {"episode_id", "timestamp", "ctx__phase", "ctx__layer", "ctx__t_s"}
        cols = []
        for c in available:
            if c in keep:
                cols.append(c)
            elif c.startswith("meas__") and c[len("meas__"):] in self.enabled:
                cols.append(c)
            elif c.startswith("q__") and c[len("q__"):] in self.enabled:
                cols.append(c)
        return cols


def spec_alarm_limits() -> list[AlarmLimit]:
    """The workbook's Sec. 5/6 warning and critical values ('simulation threshold'), per twin channel. Used where the
    reference config gives no numeric limit. PAHH is the Sec. 5 critical 3.0 bar(a), below the PRV set pressure."""
    return [
        AlarmLimit("pressure_bar_a", "low", C.PRESSURE_LOW_WARNING_BAR, "warning", name="PAL"),
        AlarmLimit("pressure_bar_a", "high", C.PRESSURE_HIGH_WARNING_BAR, "warning", name="PAH"),
        AlarmLimit("pressure_bar_a", "high", C.PRESSURE_CRITICAL_BAR, "critical", name="PAHH"),
        AlarmLimit("liquid_temp_c", "high", C.TEMP_LH2_WARNING_C, "warning", name="TAH"),
        AlarmLimit("liquid_temp_c", "high", C.TEMP_LH2_CRITICAL_C, "critical", name="TAHH"),
        AlarmLimit("inner_wall_temp_c", "high", C.TEMP_INNER_WALL_WARNING_C, "warning", name="TAH"),
        AlarmLimit("inner_wall_temp_c", "high", C.TEMP_INNER_WALL_CRITICAL_C, "critical", name="TAHH"),
        AlarmLimit("outer_wall_temp_c", "high", C.TEMP_OUTER_WALL_WARNING_C, "warning", name="TAH"),
        AlarmLimit("outer_wall_temp_c", "high", C.TEMP_OUTER_WALL_CRITICAL_C, "critical", name="TAHH"),
        AlarmLimit("ambient_temp_c", "high", C.TEMP_AMBIENT_WARNING_C, "warning", name="TAH"),
        AlarmLimit("ambient_temp_c", "high", C.TEMP_AMBIENT_CRITICAL_C, "critical", name="TAHH"),
    ]


def _num(x: Any) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


@dataclass
class DashboardConfig:
    tags: list[TagSpec]
    alarms: list[AlarmLimit]
    level: str = "reference"          # "reference" (not verified) | "user_supplied" (the plant's real list)
    note: str = ""
    status: str = REFERENCE_LABEL
    historian_defaults: dict[str, Any] = field(default_factory=dict)
    alarm_load: dict[str, Any] = field(default_factory=dict)
    valve_states_available: bool = False     # the dashboard exposes valve states to the historian side channel (switch)

    # -- views ----------------------------------------------------------------

    def mask(self, valve_states: bool | None = None) -> ChannelMask:
        ch = {t.channel for t in self.tags if t.channel in MEASURED_CHANNELS}
        if self.valve_states_available if valve_states is None else valve_states:
            ch |= set(VALVE_STATE_CHANNELS)
        return ChannelMask.of(ch)

    def tag_for(self, channel: str) -> TagSpec | None:
        return next((t for t in self.tags if t.channel == channel), None)

    def tag_names(self) -> dict[str, str]:
        return {t.channel: t.name for t in self.tags if t.channel in MEASURED_CHANNELS}

    def periods_s(self) -> dict[str, float]:
        return {t.channel: float(t.period_s) for t in self.tags if t.channel in MEASURED_CHANNELS}

    def alarms_for(self, channel: str) -> list[AlarmLimit]:
        return [a for a in self.alarms if a.channel == channel]

    def with_h2_mode(self, mode: str) -> "DashboardConfig":
        """Hydrogen tag in %LFL (realistic detector) or %vol (Sec. 9 spec mode); the H / HH limits convert (100 %LFL = 4 %vol).
        Idempotent: converts only if the tag is not already in the target unit."""
        if mode not in ("lfl", "spec"):
            raise ValueError("h2 mode must be 'lfl' or 'spec'")
        tag = self.tag_for(H2_CH)
        target = "%LFL" if mode == "lfl" else "%vol"
        if tag is None or tag.unit == target:
            return self
        factor = LFL_PER_VOL if target == "%LFL" else 1.0 / LFL_PER_VOL
        tags = [replace(t, unit=target) if t.channel == H2_CH else t for t in self.tags]
        alarms = [replace(a, limit=a.limit * factor) if a.channel == H2_CH else a for a in self.alarms]
        return replace(self, tags=tags, alarms=alarms)

    # -- construction ---------------------------------------------------------

    @classmethod
    def reference(cls) -> "DashboardConfig":
        """The packaged reference configuration (dashboard_tags.json): not a verified Saudi system."""
        return cls.from_json(REFERENCE_PATH)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DashboardConfig":
        meta = d.get("_meta", {})
        tags: list[TagSpec] = []
        alarms: list[AlarmLimit] = []
        valves = False
        for t in d["tags"]:
            raw_ch = t.get("channel", t.get("name", t.get("tag")))
            if raw_ch == VALVE_STATES_CHANNEL or t.get("type") == "discrete_input":
                valves = True
                continue
            ch = CHANNEL_ALIASES.get(raw_ch, raw_ch)
            if ch not in MEASURED_CHANNELS:
                raise ValueError(f"tag {t} maps to unknown channel {raw_ch!r}")
            rng = tuple(t["range"]) if t.get("range") else None
            period = float(t.get("sample_period_s", t.get("period_s", 60.0)))
            unit = t.get("unit", C.SENSOR_SPECS[ch][2])
            if ch == "liquid_temp_c" and unit == "K":
                unit = "C"        # spec wins (Sec. 9 is in degC); see module docstring
            tags.append(TagSpec(t.get("tag", t.get("name", ch)), ch, period, unit, rng,
                                t.get("accuracy", t.get("accuracy_default", "")), t.get("source", ""),
                                t.get("technique", t.get("gauge", ""))))
            for nm, v in (t.get("alarms") or {}).items():
                x = _num(v)
                if x is not None and nm in ("H", "HH"):                   # numeric H / HH (hydrogen, %LFL)
                    alarms.append(AlarmLimit(ch, "high", x, "warning" if nm == "H" else "critical", name="AAH" if nm == "H" else "AAHH",
                                             basis="reference configuration (UNVERIFIED)"))
        if d.get("alarms"):                                               # explicit alarm list (round-trip / user supplied)
            for a in d["alarms"]:
                alarms.append(AlarmLimit(CHANNEL_ALIASES.get(a["channel"], a["channel"]), a["direction"], float(a["limit"]),
                                         a.get("level", "warning"), int(a.get("on_delay_samples", 1)), a.get("name", ""),
                                         a.get("basis", "user supplied")))
        else:                                                             # spec simulation thresholds where no numeric limit is given
            have = {a.channel for a in alarms}
            on_tags = {t.channel for t in tags}
            alarms += [a for a in spec_alarm_limits() if a.channel in on_tags and a.channel not in have]
        is_ref = "_meta" in d
        cfg = cls(tags, alarms, d.get("level", "reference" if is_ref else "user_supplied"),
                  meta.get("name", d.get("note", "")),
                  meta.get("status", d.get("status", REFERENCE_LABEL if is_ref else "user supplied")),
                  d.get("historian_defaults", {}), d.get("alarm_load", {}), valves)
        bad_alarm = [a.channel for a in alarms if a.channel not in {t.channel for t in tags}]
        if bad_alarm:
            raise ValueError(f"alarms reference channels with no tag: {bad_alarm}")
        return cfg

    @classmethod
    def from_json(cls, path: Path | str) -> "DashboardConfig":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def to_dict(self) -> dict[str, Any]:
        """Round-trippable through from_dict (explicit-alarm format)."""
        tags = [{"name": t.name, "channel": t.channel, "period_s": t.period_s, "unit": t.unit,
                 "range": list(t.range) if t.range else None, "accuracy": t.accuracy, "source": t.source, "technique": t.technique}
                for t in self.tags]
        if self.valve_states_available:
            tags.append({"name": "valve_states", "channel": VALVE_STATES_CHANNEL, "type": "discrete_input"})
        return {
            "level": self.level, "note": self.note, "status": self.status,
            "historian_defaults": self.historian_defaults, "alarm_load": self.alarm_load, "tags": tags,
            "alarms": [{"channel": a.channel, "direction": a.direction, "limit": a.limit, "level": a.level,
                        "on_delay_samples": a.on_delay_samples, "name": a.name, "basis": a.basis} for a in self.alarms],
        }


def _values(r: dict[str, Any], source: str) -> dict[str, Any]:
    return r.get("measurements_live", r["measurements"]) if source == "live" else r["measurements"]


def static_alarm_flags(
    slow_rows: list[dict[str, Any]],
    dashboard: DashboardConfig,
    level: str | None = None,
    source: str = "live",
) -> list[bool]:
    """Per-sample 'a static alarm is active' flag (any tag, any limit of `level`). Static alarms act on the LIVE DCS value
    (`measurements_live` when the historian layer is on, else `measurements`). An alarm is active from the sample where
    `on_delay_samples` consecutive samples are beyond the limit, and stays active while the value stays beyond it. Missing
    samples clear the run."""
    n = len(slow_rows)
    flags = [False] * n
    for ch in {a.channel for a in dashboard.alarms}:
        for lim in dashboard.alarms_for(ch):
            if level is not None and lim.level != level:
                continue
            run = 0
            for i, r in enumerate(slow_rows):
                v = _values(r, source).get(ch)
                run = run + 1 if (v is not None and lim.breached(v)) else 0
                if run >= lim.on_delay_samples:
                    flags[i] = True
    return flags


def first_static_alarm_s(
    slow_rows: list[dict[str, Any]],
    dashboard: DashboardConfig,
    level: str | None = None,
    source: str = "live",
) -> dict[str, Any]:
    """First static-alarm time (seconds since episode start) per tag and overall. `level` restricts to 'warning' or
    'critical' (None = any). Returns {'any': t|None, 'by_channel': {channel: t|None}}."""
    by_channel: dict[str, float | None] = {}
    for ch in sorted({a.channel for a in dashboard.alarms}):
        best: float | None = None
        for lim in dashboard.alarms_for(ch):
            if level is not None and lim.level != level:
                continue
            run = 0
            for r in slow_rows:
                v = _values(r, source).get(ch)
                run = run + 1 if (v is not None and lim.breached(v)) else 0
                if run >= lim.on_delay_samples:
                    t = float(r["system_context"]["t_s"])
                    best = t if best is None else min(best, t)
                    break
        by_channel[ch] = best
    times = [t for t in by_channel.values() if t is not None]
    return {"any": min(times) if times else None, "by_channel": by_channel}
