"""Judge a machine on the organizers' own WASM engine, not our simulator.

Written 2026-07-27 after our judge reported 0/8 "bad-op" on a teammate's
Reverse machine that the organizers' engine runs correctly. The op was
`Y` (split): it is a real, current instruction, documented in
`claude/official-sim/NOTES.md` and returned by the engine's own
`validOps()`, but `src/littleman/sim.py` never implemented it and
`docs/language-reference.md` predates it. Any machine using `Y` is
therefore invisible to `scripts/preflight.py` — it fails with `bad-op` at
whatever tick the first split would have happened.

So this is the fallback authority for `Y`-using candidates. It is slower
than `fastsim` (a Node subprocess and an ~80 ms WASM boot per case), which
is why it is not the default judge — use `preflight.py` for everything
that does not touch `Y`.

Per `NOTES.md`, public cases are INDEPENDENT runs; the site's editor
chains them with ` / ` inside one machine, and for stateful programs the
chained outputs differ from the per-case `out` lists. We therefore run one
case per engine session.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent / "claude" / "official-sim" / "harness.mjs"
NODE = "node"


def run_case(program: str, rounds: list[dict], max_ticks: int) -> dict:
    """One case = one engine session, rounds released as the engine matches."""
    request = {
        "program": program,
        "input": [[int(v) for v in rd.get("in", [])] for rd in rounds],
        "expected": [[int(v) for v in rd.get("out", [])] for rd in rounds],
        "maxTicks": max_ticks,
        "stopOnSettle": True,
    }
    proc = subprocess.run([NODE, str(HARNESS)], input=json.dumps(request),
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        return {"ok": False, "reason": f"harness rc={proc.returncode}: "
                                       f"{proc.stderr.strip()[:200]}"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "reason": f"unparsable: {proc.stdout[:200]}"}


def geometry(text: str) -> tuple[int, int]:
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return max((len(line) for line in lines), default=0), len(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact")
    parser.add_argument("problem", help="slug, e.g. reverse-a-list")
    parser.add_argument("--max-ticks", type=int, default=1_000_000)
    args = parser.parse_args()

    text = pathlib.Path(args.artifact).read_text()
    spec = json.loads(
        (HERE.parent / "data" / "small" / "problems"
         / f"{args.problem}.json").read_text())
    cases = spec["publicTestData"]

    width, height = geometry(text)
    box = max(width, height)
    print(f"artifact : {args.artifact}")
    print(f"engine   : organizers' WASM (claude/official-sim) -- authority for `Y`")
    print(f"size     : {width}x{height}  box {box}  footprint {box * box}")

    passed = 0
    ticks_total = 0
    for index, case in enumerate(cases):
        rounds = case.get("rounds") or [{"in": case.get("in", []),
                                         "out": case.get("out", [])}]
        result = run_case(text, rounds, args.max_ticks)
        # the engine reports success as `outputSettled`: every expected value
        # of every round matched. `fatal` and `reason` are null on success.
        ok = bool(result.get("outputSettled"))
        ticks = int(result.get("ticks") or 0)
        fatal = result.get("fatal") or {}
        reason = result.get("reason") or fatal.get("reason") or result.get(
            "status") or ""
        passed += ok
        ticks_total += ticks
        print(f"  case {index}: {'pass' if ok else 'FAIL':4} ticks={ticks:>9,} "
              f"{reason if not ok else ''}")

    average = ticks_total / len(cases) if cases else 0
    print(f"cases    : {passed}/{len(cases)}")
    print(f"score    : avgTicks {average:,.3f}  local score "
          f"{box * box * average:,.2f}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
