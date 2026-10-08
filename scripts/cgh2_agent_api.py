"""Start the HYDRAI agent JSON API (see hydrai_twin/cgh2_agent/api.py).   python scripts/cgh2_agent_api.py --port 8800"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydrai_twin.cgh2_agent.api import serve

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    print(f"HYDRAI agent API on http://{a.host}:{a.port}  (GET /tools /episodes /assess /decisions, POST /approve)")
    serve(a.port, a.host)
