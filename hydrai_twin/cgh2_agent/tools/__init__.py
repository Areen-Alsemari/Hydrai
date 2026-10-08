"""Tool interface and registry.

Every tool has: name, description, version, a cost class, a `monitor(ctx)` that returns CAUSAL per-tick series (the always-on cheap evidence, equivalent to
running the tool on every tick because it only looks backwards) and a `call(ctx, i, **kw)` for on-demand investigation at tick i that returns a
ToolResult: structured evidence (verdict, score or estimate with interval, supporting series, plain-language fields). Calls are logged (CallLog).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class ToolResult:
    tool: str
    verdict: str                                  # short machine-readable verdict, e.g. "leak_suspected"
    score: float | None = None
    estimate: dict[str, Any] = field(default_factory=dict)     # named estimates, each {value, lo, hi, unit}
    series: dict[str, list] = field(default_factory=dict)      # supporting series (downsampled, JSON-able)
    text_en: str = ""
    text_ar: str = ""
    fields: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"tool": self.tool, "verdict": self.verdict, "score": self.score, "estimate": self.estimate, "series": self.series,
                "text_en": self.text_en, "text_ar": self.text_ar, "fields": self.fields}


class Ctx:
    """Everything a tool may read for one unit: the dashboard-visible Unit, the fitted parameters, the per-unit commissioning baseline, and shared caches
    (cleaned series from T1, other tools' monitor outputs). Tools never read `unit.truth`."""
    def __init__(self, unit, fit, baseline=None, options=None):
        self.unit, self.fit, self.baseline = unit, fit, (baseline or {})
        self.opt = {"e2": "comm+first2d", "e3": True, "valve_states": True, **(options or {})}
        self.mon: dict[str, dict[str, np.ndarray]] = {}
        self.cache: dict[str, Any] = {}

    def monitor(self, tool_name: str) -> dict[str, np.ndarray]:
        if tool_name not in self.mon:
            self.mon[tool_name] = REGISTRY[tool_name].monitor(self)
        return self.mon[tool_name]


class Tool:
    name = "tool"
    description = ""
    version = "1.0"
    cost = "cheap"                                # cheap (monitor, vectorised) | medium | expensive (twin simulation)
    inputs = "dashboard-visible tag window + context"

    def monitor(self, ctx) -> dict[str, np.ndarray]:
        return {}

    def call(self, ctx, i: int, **kw) -> ToolResult:
        raise NotImplementedError

    def spec(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description, "version": self.version, "cost": self.cost, "inputs": self.inputs}


class CallLog:
    """Ordered log of tool calls for one decision (the reasoning trace)."""
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, tool: Tool, ctx, i: int, why: str, **kw) -> ToolResult:
        unit = ctx.unit
        t0 = time.perf_counter()
        res = tool.call(ctx, i, **kw)
        dt = time.perf_counter() - t0
        self.calls.append({"order": len(self.calls) + 1, "tool": tool.name, "version": tool.version, "t_s": float(unit.t[i]), "why": why,
                           "args": {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(type(v).__name__)) for k, v in kw.items()},
                           "runtime_ms": round(1000 * dt, 2), "result": res.to_json()})
        return res

    def total_runtime_ms(self) -> float:
        return sum(c["runtime_ms"] for c in self.calls)


REGISTRY: dict[str, Tool] = {}


def register(tool):
    """Class decorator: registers one instance under its name and returns the class."""
    inst = tool() if isinstance(tool, type) else tool
    REGISTRY[inst.name] = inst
    return tool


def load_all_tools() -> dict[str, Tool]:
    """Import every tool module (registering it) and return the registry."""
    import importlib
    for mod in ("t1_data_integrity", "t2_inventory_leak", "t3_thermal_state", "t4_pressure_behaviour", "t5_sensor_integrity", "t6_structural", "t9_twin_verifier", "t11_hold_test_planner",
                "t10_forecast_consequence", "t12_alarm_context", "t13_procedures"):
        importlib.import_module(f"hydrai_twin.cgh2_agent.tools.{mod}")
    return REGISTRY
