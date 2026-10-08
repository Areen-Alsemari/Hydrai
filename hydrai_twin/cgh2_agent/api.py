"""The agent as a function and a small JSON API (standard library only) for a team's own dashboard.

    from hydrai_twin.cgh2_agent.api import AgentAPI
    api = AgentAPI()
    api.assess("M01__leak-0.25mm", tick=4800)         # state, tier, class, leak estimate, forecast, bilingual text, tool trace of the latest decision

    python scripts/cgh2_agent_api.py --port 8800
    GET  /tools                              tool specs (name, description, version, cost, inputs)
    GET  /episodes                           episodes the API can replay
    GET  /assess?episode=NAME&tick=N         the agent's picture at tick N (causal: nothing after N is used)
    GET  /decisions?episode=NAME             every decision with its trace
    POST /approve  {"episode":..., "decision":K, "approve":true|false}    simulated / real operator answer (recorded, never actuates)

The policy-mode orchestrator is deterministic: the same episode and tick always return the same answer.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np

from hydrai_twin.cgh2_agent.replay import _state_timeline
from hydrai_twin.cgh2_agent.session import AgentSession, get_units
from hydrai_twin.cgh2_agent.tools import REGISTRY, load_all_tools


class AgentAPI:
    def __init__(self, dataset: str = "output/cgh2/medium"):
        load_all_tools()
        self.dataset = dataset
        self._runs: dict[str, tuple[AgentSession, dict[str, Any]]] = {}
        self.answers: dict[tuple[str, int], bool] = {}

    def tools(self) -> list[dict[str, str]]:
        return [t.spec() for t in REGISTRY.values()]

    def episodes(self) -> list[str]:
        _, units = get_units(self.dataset)
        return [k for k, u in units.items() if u.entry["role"] == "dev"]

    def _run(self, episode: str):
        if episode not in self._runs:
            s = AgentSession(episode, self.dataset)
            self._runs[episode] = (s, s.run())
        return self._runs[episode]

    def assess(self, episode: str, tick: int) -> dict[str, Any]:
        s, out = self._run(episode)
        u = s.unit
        tick = int(min(max(tick, 0), u.n - 1))
        st = _state_timeline(out, u)(tick)
        past = [d for d in out["decisions"] if d.i <= tick and d.t_s >= (out["events"][0]["t_watch_s"] if out["events"] else 1e18)]
        # the latest decision that belongs to the event active at `tick` (none while MONITOR)
        d = past[-1] if past and st["tier"] != "none" else None
        m2 = s.ctx.monitor("T2_inventory_leak")
        return {"episode": episode, "tick": tick, "t_s": float(u.t[tick]), "state": st["state"], "tier": st["tier"],
                "score": round(float(1 - s.P[tick, 0]), 4), "thresholds": s.orch.thr, "static_alarm": bool(u.static[tick]),
                "compensated_inventory_kg": round(float(m2["In"][tick] * u.raw.inv_ref_kg), 2), "decision": d.to_json() if d else None,
                "approved": self.answers.get((episode, out["decisions"].index(d))) if d else None}

    def decisions(self, episode: str) -> list[dict[str, Any]]:
        _, out = self._run(episode)
        return [d.to_json() for d in out["decisions"]]

    def approve(self, episode: str, decision: int, approve: bool) -> dict[str, Any]:
        self.answers[(episode, int(decision))] = bool(approve)
        return {"episode": episode, "decision": int(decision), "approved": bool(approve), "note": "recorded; the agent never actuates"}


def make_handler(api: AgentAPI):
    class H(BaseHTTPRequestHandler):
        def _send(self, obj: Any, code: int = 200) -> None:
            body = json.dumps(obj, default=float).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                if u.path == "/tools":
                    return self._send(api.tools())
                if u.path == "/episodes":
                    return self._send(api.episodes())
                if u.path == "/assess":
                    return self._send(api.assess(q["episode"], int(q["tick"])))
                if u.path == "/decisions":
                    return self._send(api.decisions(q["episode"]))
                return self._send({"error": "unknown path", "paths": ["/tools", "/episodes", "/assess", "/decisions", "POST /approve"]}, 404)
            except Exception as e:                                 # report, do not crash the dashboard's connection
                return self._send({"error": str(e)}, 400)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            if urlparse(self.path).path == "/approve":
                return self._send(api.approve(body["episode"], body["decision"], body["approve"]))
            return self._send({"error": "unknown path"}, 404)

        def log_message(self, *a):
            pass
    return H


def serve(port: int = 8800, host: str = "127.0.0.1") -> None:
    ThreadingHTTPServer((host, port), make_handler(AgentAPI())).serve_forever()
