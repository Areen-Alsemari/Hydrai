"""Generate the replay JSON lines that do not exist yet (the five healthy modules for the fleet screen and one containment case), into THIS folder only.
Same code path as scripts/cgh2_agent_replay.py (frozen agent, leave-one-module-out parameters); existing replays under output/cgh2_agent_demo/ are only read.   python make_replays.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from hydrai_twin.cgh2_agent import replay
from hydrai_twin.cgh2_agent.session import AgentSession

NEW = ["M02__normal-refuelling0", "M03__normal-refuelling0", "M04__normal-refuelling0", "M05__normal-refuelling0", "M06__normal-refuelling0", "M01__containment-leak-3.5mm"]

if __name__ == "__main__":
    for name in NEW:
        out = HERE / "replays" / f"{name}.ticks.jsonl"
        if out.exists():
            continue
        data = replay.build(AgentSession(name), 5)
        with open(out, "w") as f:
            for line in replay.stream_lines(data, sleep=False):
                f.write(line + "\n")
        print(name, len(data["ticks"]), "ticks", len(data["decisions"]), "decisions", flush=True)
