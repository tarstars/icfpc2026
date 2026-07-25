#!/usr/bin/env python
"""Classify a running subagent from its transcript metadata.

Implements the triage table of docs/architecture/claude_14_subagent_policy.md.
Reads only metadata (timestamps, tool names, token counts) -- never message
content, which would overflow the supervisor's context.

Usage: uv run python scripts/agent_watch.py <transcript.output> [...]
"""
from __future__ import annotations

import datetime
import json
import sys

CEILING = 64000


def scan(path: str) -> dict:
    tools: dict[str, int] = {}
    maxout = ceilings = turns = 0
    first_ts = last_ts = first_write = None
    for line in open(path, errors="replace"):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        stamp = (entry.get("timestamp") or "")[11:19]
        if stamp:
            first_ts = first_ts or stamp
            last_ts = stamp
        out = (message.get("usage") or {}).get("output_tokens") or 0
        maxout = max(maxout, out)
        ceilings += out >= CEILING
        if entry.get("type") == "assistant":
            turns += 1
        for chunk in message.get("content") or []:
            if isinstance(chunk, dict) and chunk.get("type") == "tool_use":
                name = chunk.get("name", "?")
                tools[name] = tools.get(name, 0) + 1
                if name in ("Write", "Edit", "NotebookEdit") and not first_write:
                    first_write = stamp
    return {
        "tools": tools, "maxout": maxout, "ceilings": ceilings, "turns": turns,
        "first": first_ts, "last": last_ts, "first_write": first_write,
    }


def minutes(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    fmt = "%H:%M:%S"
    delta = datetime.datetime.strptime(b, fmt) - datetime.datetime.strptime(a, fmt)
    return delta.total_seconds() / 60


def verdict(s: dict) -> str:
    writes = sum(s["tools"].get(k, 0) for k in ("Write", "Edit", "NotebookEdit"))
    reads = s["tools"].get("Read", 0)
    age = minutes(s["first"], s["last"]) or 0
    to_write = minutes(s["first"], s["first_write"])
    if s["ceilings"] >= 2:
        return "KILL+RESPAWN: repeated ceiling truncation"
    if s["ceilings"]:
        return "SPLIT HARDER: already truncating (64k turn)"
    if s["maxout"] > 40000:
        return "SPLIT HARDER: approaching the ceiling"
    if not writes and age > 25:
        return "KILL+RESPAWN: no writes after 25 min"
    if not writes and s["maxout"] < 1000 and reads > writes and age > 6:
        return "WRITE NOW: spiral (many reads, tiny outputs, no writes)"
    if not s["tools"] and age > 6:
        return "RECHECK +3: no tool calls; hung or generating"
    if writes:
        return f"HEALTHY: {writes} writes, first at +{to_write:.0f}m" if to_write else "HEALTHY"
    return "EARLY: reading; recheck at +3m"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for path in argv[1:]:
        s = scan(path)
        age = minutes(s["first"], s["last"])
        print(f"{path.split('/')[-1][:20]:22s} turns={s['turns']:3d} "
              f"maxout={s['maxout']:6d} ceil={s['ceilings']} "
              f"tools={s['tools']} age={age:.0f}m" if age is not None else path)
        print(f"  -> {verdict(s)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
