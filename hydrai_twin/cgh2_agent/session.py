"""AgentSession: everything needed to run the orchestrator on one episode of the dataset with LEAVE-ONE-MODULE-OUT parameters (the tool fit, commissioning baseline,
fusion model and thresholds of the fold that did not see this episode's module)."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np

from hydrai_twin.cgh2_agent import fusion as F
from hydrai_twin.cgh2_agent.agent import Orchestrator
from hydrai_twin.cgh2_agent.features import feature_matrix
from hydrai_twin.cgh2_agent.loader import load_all
from hydrai_twin.cgh2_agent.tools import Ctx, load_all_tools

_UNITS: dict[str, Any] = {}


def get_units(dataset: str = "output/cgh2/medium", roles: tuple[str, ...] = ("dev", "commissioning")):
    key = dataset + "|" + ",".join(roles)
    if key not in _UNITS:
        _UNITS[key] = load_all(dataset, roles)
    return _UNITS[key]


class AgentSession:
    def __init__(self, episode: str, dataset: str = "output/cgh2/medium", fold_tag: str | None = None, enabled_tools: set[str] | None = None, meta_tag: str | None = None, use_static: bool = True, roles: tuple[str, ...] = ("dev", "commissioning")):
        load_all_tools()
        self.manifest, units = get_units(dataset, roles)
        self.unit = units[episode]
        tag = fold_tag or self.unit.entry["module_id"]
        with open(F.CACHE / f"fit_{tag}.pkl", "rb") as f:
            fb = pickle.load(f)
        pre = f"{meta_tag}_" if meta_tag else ""
        with open(F.CACHE / f"meta_{pre}{tag}.pkl", "rb") as f:
            self.meta = pickle.load(f)
        self.ctx = Ctx(self.unit, fb["fit"], fb["baseline"])
        cached = F.CACHE / f"probs_{pre}{episode}.npy"
        fu = F.FUnit(self.unit.entry, self.unit.t, feature_matrix(self.ctx))
        self.P = np.load(cached) if (cached.exists() and fold_tag is None) else F.probs(self.meta["model"], fu)
        self.P_fast = F.raw_probs(self.meta["model"], fu)
        self.orch = Orchestrator(self.meta["thr"], enabled_tools=enabled_tools, use_static=use_static)

    def run(self, **kw) -> dict[str, Any]:
        return self.orch.run(self.ctx, self.P, P_fast=self.P_fast, **kw)


def slim_decision(d) -> dict:
    """Compact, picklable record of a Decision (the full trace is kept only for the first decision of an event)."""
    return {"t_s": d.t_s, "i": d.i, "tier": d.tier, "cls": d.cls, "open_set": d.open_set, "score": d.score, "posterior": d.posterior, "hard": d.hard_evidence, "approved": d.approved,
            "leak": d.leak_estimate, "released_kg": d.released_kg, "forecast": d.forecast, "runtime_ms": d.runtime_ms, "n_calls": len(d.trace),
            "calls": [{"tool": c["tool"], "runtime_ms": c["runtime_ms"], "verdict": c["result"]["verdict"]} for c in d.trace], "text_en": d.text_en}
