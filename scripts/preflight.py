#!/usr/bin/env python
"""Pre-submission gate for a .man candidate.

Runs every check that has historically caught a bad submission, in one place:

* the layout parses at all;
* no two rooms share a wall cell (the server rejects those; our parser does not);
* no pipe is shorter than two cells (the server rejects those at load time and
  our judge still reports a clean pass -- this silently invalidated `sort_05`
  and `reverse_02`);
* the public cases pass under the server-compatible judge;
* footprint, average ticks and local score;
* sha256 and byte size, so the submitted artifact is identifiable afterwards.

Usage:  uv run python scripts/preflight.py <file.man> <problem-slug>
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

from littleman import server_compat
from littleman.judge import footprint
from littleman.sim import LoadError, Machine


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    path, slug = pathlib.Path(argv[1]), argv[2]
    text = path.read_text()
    problem = json.loads(
        pathlib.Path(f"data/small/problems/{slug}.json").read_text()
    )

    rows = text.split("\n")
    occupied = [
        (r, c) for r, line in enumerate(rows) for c, ch in enumerate(line) if ch != " "
    ]
    width = max(c for _, c in occupied) - min(c for _, c in occupied) + 1
    height = max(r for r, _ in occupied) - min(r for r, _ in occupied) + 1

    print(f"artifact : {path}")
    print(f"problem  : {slug}  (scoring {problem.get('scoring')})")
    print(f"size     : {width}x{height}  footprint {footprint(text):,}")
    print(f"sha256   : {hashlib.sha256(text.encode()).hexdigest()}")
    print(f"bytes    : {len(text.encode())}")

    ok = True
    try:
        machine = Machine.parse(text)
        print(f"parse    : OK  ({len(machine.rooms)} rooms, {len(machine.pipes)} pipes,"
              f" {len(machine.men)} men)")
    except LoadError as exc:
        print(f"parse    : FAIL  {exc}")
        return 1

    try:
        server_compat.validate_layout(text)
        print("walls    : OK  (no room shares a wall cell)")
    except server_compat.ServerCompatibilityError as exc:
        print(f"walls    : FAIL  {exc}")
        ok = False

    lengths = sorted(len(p.cells) for p in machine.pipes)
    if lengths and min(lengths) < 2:
        print(f"pipes    : FAIL  one-cell pipe present; lengths {lengths}")
        ok = False
    else:
        print(f"pipes    : OK  lengths {lengths}")

    report = server_compat.judge_problem(text, problem)
    passed = report.cases_passed == report.cases_total
    print(f"cases    : {'OK' if passed else 'FAIL'}  "
          f"{report.cases_passed}/{report.cases_total}")
    for case, result in zip(problem["publicTestData"], report.case_results):
        mark = "pass" if result.passed else f"FAIL ({result.reason})"
        print(f"           {case['name'][:34]:36s} {mark:24s} ticks={result.ticks}")
    if not passed:
        ok = False
    elif report.case_ticks:
        avg = sum(report.case_ticks) / len(report.case_ticks)
        print(f"score    : avgTicks {avg:,.3f}  local score {report.score:,.2f}")

    print()
    print("VERDICT  :", "READY TO SUBMIT" if ok else "NOT SUBMITTABLE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
