"""LLM mode (DEMO ONLY, never part of a benchmark number).

The language model only talks to the operator: it answers questions in Arabic or English by calling the SAME tools through function calling, at temperature 0.
It cannot invent numbers: a checker extracts every number in the answer and requires each to match a number in the tool outputs it received (to the precision
shown); on any mismatch, or if no model is available, the answer falls back to the deterministic template text of the decision (T13 / the tools' own text).
The model does not decide anything; detection and diagnosis are done by the deterministic policy orchestrator. We make NO claim that the language model improved
detection or diagnosis.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from hydrai_twin.cgh2_agent.tools import REGISTRY, CallLog, load_all_tools

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
NUM = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")
MODEL = os.environ.get("HYDRAI_LLM_MODEL", "claude-sonnet-5-5")

SYSTEM = ("You are the HYDRAI hydrogen-storage assistant. Answer the operator's question in the language of the question (Arabic or English). Use ONLY the tools: call "
          "them to get facts. Every number you state must be copied from a tool output (same precision). If the tools do not give the answer, say so. Never recommend "
          "an action that is not in the T13 procedure output. Be brief.")


def numbers_in(text: str) -> list[float]:
    t = text.translate(AR_DIGITS)
    out = []
    for m in NUM.findall(t):
        try:
            out.append(float(m.replace(",", ".")))
        except ValueError:
            pass
    return out


def flatten_numbers(obj: Any, acc: list[float] | None = None) -> list[float]:
    acc = [] if acc is None else acc
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, (int, float)):
        acc.append(float(obj))
    elif isinstance(obj, str):
        acc.extend(numbers_in(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            flatten_numbers(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            flatten_numbers(v, acc)
    return acc


def check_numbers(answer: str, tool_outputs: list[dict[str, Any]]) -> tuple[bool, list[float]]:
    """True if every number in `answer` equals a number in the tool outputs, either exactly or rounded to 0, 1 or 2 decimals (rounding for readability is fine,
    any other value is an invented number); returns the offenders."""
    pool = flatten_numbers(tool_outputs)
    bad = [x for x in numbers_in(answer) if not any(abs(x - y) < 1e-9 or any(abs(x - round(y, d)) < 1e-9 for d in (0, 1, 2)) for y in pool)]
    return (len(bad) == 0), bad


def tool_schemas(names: list[str] | None = None) -> list[dict[str, Any]]:
    load_all_tools()
    out = []
    for n, t in REGISTRY.items():
        if names and n not in names or n in ("T1_data_integrity",):
            continue
        out.append({"name": n, "description": t.description, "input_schema": {"type": "object", "properties": {"hypothesis": {"type": "string", "description": "for T9: leak or heating"}, "cls": {"type": "integer", "description": "for T13: class id"},
                                                                                                       "severity": {"type": "string", "description": "for T13: watch, alert or critical"}}, "required": []}})
    return out


def answer(question: str, session, tick: int, lang: str = "en", client=None, fallback_text: str | None = None) -> dict[str, Any]:
    """Answer an operator question at `tick`. `client`: an Anthropic-style client (messages.create with tools); None -> template fallback."""
    load_all_tools()
    log = CallLog()
    ctx = session.ctx
    ctx.monitor("T1_data_integrity")
    fb = fallback_text or ""
    if client is None:
        return {"answer": fb, "source": "template (no language model available)", "checked": True, "tool_calls": 0}
    messages = [{"role": "user", "content": question}]
    for _ in range(6):
        resp = client.messages.create(model=MODEL, max_tokens=700, temperature=0, system=SYSTEM, tools=tool_schemas(), messages=messages)
        uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
        if not uses:
            text = "".join(getattr(b, "text", "") for b in resp.content)
            ok, bad = check_numbers(text, [c["result"] for c in log.calls])
            if ok:
                return {"answer": text, "source": "language model (numbers verified against tool outputs)", "checked": True, "tool_calls": len(log.calls), "trace": log.calls}
            return {"answer": fb, "source": f"template (the language model's numbers {bad} were not in any tool output)", "checked": False, "tool_calls": len(log.calls), "trace": log.calls}
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in uses:
            kw = {k: v for k, v in (b.input or {}).items() if k in ("hypothesis", "cls", "severity")}
            r = log.run(REGISTRY[b.name], ctx, tick, "operator question", **kw)
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(r.to_json(), default=float)})
        messages.append({"role": "user", "content": results})
    return {"answer": fb, "source": "template (tool loop did not converge)", "checked": False, "tool_calls": len(log.calls), "trace": log.calls}
