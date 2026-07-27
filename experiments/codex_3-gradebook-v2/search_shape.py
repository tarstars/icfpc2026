#!/usr/bin/env python
"""Try verified one-column shaves of the live codex_3 Grade Book artifact.

The live machine is 379x315, so one width column is immediately worth about
0.53% at unchanged ticks. This driver considers only sparse occupied columns.
It slides non-arrow instructions along the same already-walked straight run,
vacates a column, deletes it, and then applies the repository's strongest
available proof gates:

* the box must shrink;
* no ordered pipe length may decrease;
* nearest-pipe bindings and every room boundary contract must be unchanged;
* the full public problem must still pass;
* the first codex_3 randomized and 256-transition stress suites must pass.

Usage:

    uv run python experiments/codex_3-gradebook-v2/search_shape.py

A winner is written to ``submissions/gradebook/codex3_gradebook_07.man``. The
script never submits it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
from typing import Any

from littleman import room_compact, room_shrink, server_compat
from littleman.judge import judge_problem
from littleman.sim import Machine

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVE_PATH = ROOT / "submissions" / "gradebook" / "codex3_gradebook_06.man"
FOLD_PATH = ROOT / "submissions" / "gradebook" / "codex3_gradebook_07.man"
PROBLEM_PATH = ROOT / "data" / "small" / "problems" / "gradebook.json"
SUPPORT_PATH = (
    ROOT / "experiments" / "codex_3-gradebook-v2" / "search_extra_folds.py"
)
DEFAULT_OUTPUT = ROOT / "submissions" / "gradebook" / "codex3_gradebook_07.man"
DEFAULT_REPORT = ROOT / "experiments" / "codex_3-gradebook-v2" / "shape-result.json"


def _load_support():
    name = "codex3_gradebook_v2_support"
    spec = importlib.util.spec_from_file_location(name, SUPPORT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load support module: {SUPPORT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ordered_pipe_lengths(text: str) -> tuple[int, ...]:
    return tuple(len(pipe.cells) for pipe in Machine.parse(text).pipes)


def _counts(text: str) -> tuple[int, int, int]:
    machine = Machine.parse(text)
    return len(machine.rooms), len(machine.pipes), len(machine.men)


def _candidate_from_column(text: str, cases, column: int) -> tuple[str | None, str]:
    slides = room_compact.slides_toward(text, cases, target_col=column)
    occupancy = room_compact.column_occupancy(text)
    needed = occupancy[column]
    if len(slides) < needed:
        return None, f"only {len(slides)} legal slides for {needed} glyphs"

    moved = room_compact.apply_slides(text, slides)
    after_move = room_compact.column_occupancy(moved)
    if column >= len(after_move) or after_move[column] != 0:
        return None, f"column still holds {after_move[column]} glyphs"
    return room_shrink.drop_column(moved, column), "vacated"


def _ordered_capacity_ok(before: str, after: str) -> tuple[bool, str]:
    try:
        old = _ordered_pipe_lengths(before)
        new = _ordered_pipe_lengths(after)
    except Exception as exc:
        return False, f"parse failed: {type(exc).__name__}: {exc}"
    if len(old) != len(new):
        return False, f"pipe count {len(old)} -> {len(new)}"
    shortened = [
        (index, old_length, new_length)
        for index, (old_length, new_length) in enumerate(zip(old, new, strict=True))
        if new_length < old_length
    ]
    if shortened:
        return False, f"ordered pipes shortened: {shortened}"
    return True, "no ordered pipe shortened"


def search(
    *,
    source: pathlib.Path,
    max_occupancy: int,
    max_attempts: int,
    random_start: int,
    random_count: int,
) -> tuple[str | None, dict[str, Any]]:
    support = _load_support()
    problem = json.loads(PROBLEM_PATH.read_text())
    cases = problem["publicTestData"]
    before = source.read_text()
    before_structure = support._structure(before)
    before_report = judge_problem(before, problem)
    if before_report.cases_passed != before_report.cases_total:
        raise RuntimeError(f"source {source} fails its own public gate")

    occupancy = room_compact.column_occupancy(before)
    columns = [
        (count, column)
        for column, count in enumerate(occupancy)
        if 0 < count <= max_occupancy
    ]
    columns.sort()
    attempts = []
    passing = []

    for count, column in columns[:max_attempts]:
        row: dict[str, Any] = {"column": column, "occupancy": count}
        candidate, reason = _candidate_from_column(before, cases, column)
        row["construction"] = reason
        if candidate is None:
            row["accepted"] = False
            attempts.append(row)
            continue

        row["dimensions"] = list(support._dimensions(candidate))
        row["counts"] = list(_counts(candidate))
        capacity_ok, capacity_reason = _ordered_capacity_ok(before, candidate)
        row["capacity"] = capacity_reason
        if not capacity_ok:
            row["accepted"] = False
            attempts.append(row)
            continue

        try:
            server_compat.validate_layout(candidate)
        except Exception as exc:
            row["layout"] = f"{type(exc).__name__}: {exc}"
            row["accepted"] = False
            attempts.append(row)
            continue
        row["layout"] = "ok"

        verdict = room_shrink.verify(before, candidate, cases)
        row["contract"] = {
            "ok": verdict.ok,
            "reason": verdict.reason,
            "box_before": verdict.box_before,
            "box_after": verdict.box_after,
        }
        if not verdict.ok:
            row["accepted"] = False
            attempts.append(row)
            continue

        report = judge_problem(candidate, problem)
        row["public"] = {
            "passed": report.cases_passed,
            "total": report.cases_total,
            "ticks": list(report.case_ticks),
            "score": report.score,
        }
        if report.cases_passed != report.cases_total:
            row["accepted"] = False
            attempts.append(row)
            continue

        stress = support._stress(
            candidate,
            random_start=random_start,
            random_count=random_count,
        )
        row["stress"] = stress
        if not stress["passed"]:
            row["accepted"] = False
            attempts.append(row)
            continue

        digest = hashlib.sha256(candidate.encode()).hexdigest()
        row["sha256"] = digest
        row["accepted"] = True
        attempts.append(row)
        passing.append((float(report.score), column, digest, candidate, row))

    passing.sort(key=lambda item: (item[0], item[1], item[2]))
    winner = passing[0] if passing else None
    result = {
        "source": str(source.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "source_structure": {
            "dimensions": list(before_structure.dimensions),
            "footprint": before_structure.footprint,
            "counts": list(_counts(before)),
            "pipe_lengths": list(_ordered_pipe_lengths(before)),
            "public_ticks": list(before_report.case_ticks),
            "public_score": before_report.score,
        },
        "parameters": {
            "max_occupancy": max_occupancy,
            "max_attempts": max_attempts,
            "random_start": random_start,
            "random_count": random_count,
        },
        "candidate_columns": len(columns),
        "attempts": attempts,
        "winner": winner[4] if winner else None,
    }
    return (winner[3] if winner else None), result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=None,
        help="defaults to fold-search output when present, otherwise live _06",
    )
    parser.add_argument("--max-occupancy", type=int, default=6)
    parser.add_argument("--max-attempts", type=int, default=32)
    parser.add_argument("--random-start", type=int, default=100)
    parser.add_argument("--random-count", type=int, default=24)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    if min(args.max_occupancy, args.max_attempts, args.random_count) < 1:
        parser.error("occupancy, attempts, and random-count must be positive")
    source = args.source or (FOLD_PATH if FOLD_PATH.exists() else LIVE_PATH)

    winner, report = search(
        source=source,
        max_occupancy=args.max_occupancy,
        max_attempts=args.max_attempts,
        random_start=args.random_start,
        random_count=args.random_count,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if winner is None:
        print("no verified sparse-column shave found")
        print(f"report: {args.report}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(winner)
    selected = report["winner"]
    print(f"winner column : {selected['column']}")
    print(f"dimensions    : {selected['dimensions']}")
    print(f"public score  : {selected['public']['score']:,.2f}")
    print(f"sha256        : {selected['sha256']}")
    print(f"candidate     : {args.output}")
    print(f"report        : {args.report}")
    print()
    print("DECISIVE NEXT GATES:")
    print(f"uv run python scripts/subdb.py compare {args.output.relative_to(ROOT)} gradebook")
    print(f"uv run python scripts/wasm_judge.py {args.output.relative_to(ROOT)} gradebook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
