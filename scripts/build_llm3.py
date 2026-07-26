#!/usr/bin/env python
"""Rebuild submissions/llm/llm3_00.man and say exactly where it stalls.

STEP3 changes on disk under us, so this ALWAYS re-reads it, re-assembles,
rewrites the artifact, judges one case, and on failure prints the stall
diagnostic (component, pipe fill, tick, STEP3 stream position + man cell).

    uv run python scripts/build_llm3.py                    # "first steps"
    uv run python scripts/build_llm3.py --case "pileup"
    uv run python scripts/build_llm3.py --all --no-diagnose
"""

from __future__ import annotations

import argparse
import json
import pathlib

from littleman import llm_assemble3 as A
from littleman import server_compat
from littleman.judge import normalize_case
from littleman.sim import Machine

OUT = pathlib.Path("submissions/llm/llm3_00.man")
PROBLEM = pathlib.Path("data/small/problems/little-little-man.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="first steps")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-diagnose", action="store_true")
    ap.add_argument("--ticks", type=int, default=None)
    ap.add_argument("--quiet", type=int, default=150_000)
    args = ap.parse_args()

    spec = A.step3_spec()
    text, anchors = A.assemble(spec)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    src = spec["stub"] or f"llm_step3.{spec.get('builder')}"
    lines = text.split("\n")
    print(f"wrote {OUT}  ({len(lines)}x{max(map(len, lines))},"
          f" {len(text.encode())} bytes)  STEP3 room: {src}")
    machine = Machine.parse(text)
    print(f"  rooms {len(machine.rooms)}  pipes {len(machine.pipes)}"
          f"  men {len(machine.men)}"
          f"  FETCH ring {A.ring_cells(machine, anchors, 'FETCH', 'FETCHRELAY')}"
          f"  scr1 ring {A.ring_cells(machine, anchors, 'STEP3', 'STEP3RELAY')}")
    try:
        server_compat.validate_layout(text)
        print("  server layout: OK")
    except Exception as exc:
        print(f"  server layout: FAIL {exc}")
    for line in A.binding_audit(text, anchors):
        if "NO pipe" in line or int(line.split("margin=")[1].split()[0]) < 2:
            print("  audit", line)

    problem = json.loads(PROBLEM.read_text())
    cap = args.ticks or problem.get("tickCap") or 50_000_000
    cases = problem["publicTestData"]
    todo = cases if args.all else \
        [c for c in cases if c["name"] == args.case]
    if not todo:
        print(f"no case named {args.case!r}")
        return 2
    failed = None
    for case in todo:
        result = server_compat.judge_case(text, normalize_case(case),
                                          max_ticks=cap)
        print(f"case {case['name']!r}: "
              f"{'PASS' if result.passed else 'FAIL'} ticks={result.ticks}"
              f" reason={result.reason}")
        if not result.passed and failed is None:
            failed = case
    if failed is None or args.no_diagnose:
        return 0 if failed is None else 1
    print(f"-- diagnosing {failed['name']!r} (pure sim, stops on"
          f" {args.quiet}-tick quiescence) --")
    rows = A.case_rows(failed)
    res, trace, controller = A.diagnose(
        text, normalize_case(failed), anchors,
        max_ticks=min(cap, 30_000_000), quiet=args.quiet)
    for line in A.stall_report(rows, res, trace, controller, anchors):
        print(line)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
