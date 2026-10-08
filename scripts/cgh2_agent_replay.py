"""Replay one CGH2 episode through the HYDRAI orchestrator.

  python scripts/cgh2_agent_replay.py --episode M01__leak-0.25mm --out output/cgh2_agent_demo      # writes <episode>.ticks.jsonl + <episode>.html (no waiting)
  python scripts/cgh2_agent_replay.py --episode M01__leak-0.25mm --stream --speed 3600              # prints JSON ticks to stdout, one simulated hour per second
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2_agent import replay
from hydrai_twin.cgh2_agent.session import AgentSession

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--out", default="output/cgh2_agent_demo")
    ap.add_argument("--stride", type=int, default=5, help="minutes between ticks")
    ap.add_argument("--stream", action="store_true", help="print the JSON ticks to stdout with accelerated playback")
    ap.add_argument("--speed", type=float, default=3600.0, help="simulated seconds per real second when streaming")
    ap.add_argument("--operator", choices=["auto", "reject"], default="auto")
    ap.add_argument("--start-h", type=float, default=None)
    ap.add_argument("--stop-h", type=float, default=None)
    a = ap.parse_args()
    s = AgentSession(a.episode)
    op = (lambda d: (False, 300.0)) if a.operator == "reject" else None
    data = replay.build(s, a.stride, None if a.start_h is None else int(a.start_h * 60), None if a.stop_h is None else int(a.stop_h * 60), operator=op)
    if a.stream:
        for line in replay.stream_lines(data, a.speed, True):
            print(line, flush=True)
    else:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / f"{a.episode}.ticks.jsonl", "w") as f:
            for line in replay.stream_lines(data, sleep=False):
                f.write(line + "\n")
        replay.write_html(data, str(out / f"{a.episode}.html"))
        print(out / f"{a.episode}.ticks.jsonl", out / f"{a.episode}.html", len(data["ticks"]), "ticks", len(data["decisions"]), "decisions")
