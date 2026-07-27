#!/usr/bin/env python3
"""Bounded Pathfinder row-deletion search for the ICFPC 2026 endgame.

The counted Pathfinder machine was already improved by deleting 84 rows whose
only glyphs were spaces and vertical walls.  This search widens that syntactic
family to *pass-through routing rows*: rows containing only spaces, dots,
vertical walls, and vertical direction arrows.  Every proposed deletion is
then gated by:

* parser success and unchanged room/man/pipe counts;
* unchanged display dimensions;
* byte-for-byte pipe-length vector (deletion must not reduce capacity/delay);
* unchanged nearest-pipe binding signatures for every r/R/s/S/U socket;
* all public display-frame cases under the repository judge.

The search is intentionally bounded.  It first tests fixed-size row groups in
parallel, then greedily composes passing groups and recursively splits failures.
It writes the best verified candidate and a JSON record suitable for handoff.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import pathlib
import sys
import time
from dataclasses import asdict
from typing import Iterable, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from littleman import sim  # noqa: E402
from littleman.judge import judge_problem  # noqa: E402
from littleman.room_lab import describe  # noqa: E402

DEFAULT_SOURCE = ROOT / "submissions/pathfinder/pathfinder_02.man"
DEFAULT_PROBLEM = ROOT / "data/small/problems/pathfinder.json"
DEFAULT_OUTPUT = ROOT / "submissions/pathfinder/chatgpt4_pathfinder_03.man"
DEFAULT_RECORD = ROOT / "experiments/chatgpt_4-pathfinder/result.json"

# A global row deletion is plausible only when the row contains no operation
# other than routing that can be redundant on a vertical pass.  Public judging
# remains the semantic authority; this alphabet is merely the search frontier.
DEFAULT_PASSIVE = " |.^vV"


def _lines(text: str) -> list[str]:
    return text.rstrip("\n").split("\n")


def build(text: str, rows: Iterable[int]) -> str:
    removed = set(rows)
    return "\n".join(
        line.rstrip() for index, line in enumerate(_lines(text))
        if index not in removed
    ) + "\n"


def geometry(text: str) -> tuple[int, int, int]:
    occupied = [
        (r, c)
        for r, line in enumerate(text.splitlines())
        for c, ch in enumerate(line)
        if ch != " "
    ]
    if not occupied:
        return 0, 0, 0
    min_r = min(r for r, _ in occupied)
    max_r = max(r for r, _ in occupied)
    min_c = min(c for _, c in occupied)
    max_c = max(c for _, c in occupied)
    width = max_c - min_c + 1
    height = max_r - min_r + 1
    return width, height, max(width, height)


def _signatures(text: str) -> dict[int, tuple]:
    return {index: interface.signature() for index, interface in describe(text).items()}


def structural_fingerprint(text: str) -> dict:
    machine = sim.Machine.parse(text)
    return {
        "rooms": len(machine.rooms),
        "men": len(machine.men),
        "pipes": len(machine.pipes),
        "pipe_lengths": tuple(len(pipe.cells) for pipe in machine.pipes),
        "display_shapes": tuple(
            (room.disp_w, room.disp_h)
            for room in machine.rooms
            if room.kind == "display"
        ),
        "interfaces": _signatures(text),
    }


def structural_gate(
    baseline: dict,
    candidate_text: str,
) -> tuple[bool, str]:
    try:
        candidate = structural_fingerprint(candidate_text)
    except Exception as exc:  # LoadError and defensive parser failures
        return False, f"parse/load: {type(exc).__name__}: {exc}"

    for key in ("rooms", "men", "pipes", "display_shapes"):
        if candidate[key] != baseline[key]:
            return False, f"{key}: {baseline[key]!r} -> {candidate[key]!r}"

    # Pipe length is delay and capacity.  Exact equality is deliberately
    # stricter than merely "not shorter"; a row deletion should move a whole
    # pipe or leave it alone, not silently change timing.
    if candidate["pipe_lengths"] != baseline["pipe_lengths"]:
        changed = [
            (i, before, after)
            for i, (before, after) in enumerate(
                zip(baseline["pipe_lengths"], candidate["pipe_lengths"], strict=True)
            )
            if before != after
        ]
        return False, f"pipe lengths changed: {changed[:8]}"

    if candidate["interfaces"] != baseline["interfaces"]:
        changed = sorted(
            set(baseline["interfaces"]) | set(candidate["interfaces"])
        )
        changed = [
            index for index in changed
            if baseline["interfaces"].get(index) != candidate["interfaces"].get(index)
        ]
        return False, f"nearest-pipe bindings changed in rooms {changed}"

    return True, "ok"


def candidate_rows(text: str, passive: str) -> list[int]:
    lines = _lines(text)
    width = max(map(len, lines))
    grid = [line.ljust(width) for line in lines]
    machine = sim.Machine.parse(text)

    border_rows = {
        row
        for room in machine.rooms
        for row in (room.top, room.bottom)
    }
    pipe_rows = {r for pipe in machine.pipes for r, _ in pipe.cells}
    occupied_rows = [
        r for r, line in enumerate(grid)
        if any(ch != " " for ch in line)
    ]
    low, high = min(occupied_rows), max(occupied_rows)
    allowed = set(passive)

    rows: list[int] = []
    for row in range(low + 1, high):
        if row in border_rows or row in pipe_rows:
            continue
        if not all(ch in allowed for ch in grid[row]):
            continue
        # `|` is also the bitwise-OR instruction.  Since pipe rows were
        # excluded above, every remaining `|` must be a vertical room wall,
        # never an interior operation.
        wall_columns = {
            column
            for room in machine.rooms
            if room.top <= row <= room.bottom
            for column in (room.left, room.right)
        }
        if any(ch == "|" and column not in wall_columns
               for column, ch in enumerate(grid[row])):
            continue
        # A row outside every room is just margin and cannot help the occupied
        # bounding box.  Require at least one real room interior crossing.
        if not any(
            room.kind == "room" and room.top < row < room.bottom
            for room in machine.rooms
        ):
            continue
        rows.append(row)
    return rows


def row_histogram(text: str) -> dict[str, int]:
    lines = _lines(text)
    width = max(map(len, lines))
    grid = [line.ljust(width) for line in lines]
    alphabets = {
        "blank_vertical": set(" |"),
        "vertical_pass": set(DEFAULT_PASSIVE),
        "all_arrows": set(" |.^vV<>"),
    }
    return {
        name: sum(all(ch in chars for ch in row) for row in grid)
        for name, chars in alphabets.items()
    }


def chunks(rows: Sequence[int], size: int) -> list[tuple[int, ...]]:
    return [
        tuple(rows[start : start + size])
        for start in range(0, len(rows), size)
    ]


def _judge_worker(
    source_path: str,
    problem_path: str,
    rows: tuple[int, ...],
) -> dict:
    source = pathlib.Path(source_path).read_text()
    problem = json.loads(pathlib.Path(problem_path).read_text())
    text = build(source, rows)
    started = time.time()
    try:
        report = judge_problem(text, problem)
        return {
            "rows": list(rows),
            "passed": report.cases_passed == report.cases_total,
            "cases_passed": report.cases_passed,
            "cases_total": report.cases_total,
            "case_ticks": list(report.case_ticks),
            "case_results": [
                asdict(result) for result in report.case_results
            ],
            "footprint": report.footprint,
            "score": report.score,
            "seconds": time.time() - started,
            "error": None,
        }
    except Exception as exc:
        return {
            "rows": list(rows),
            "passed": False,
            "cases_passed": 0,
            "cases_total": 0,
            "case_ticks": [],
            "case_results": [],
            "footprint": 0,
            "score": math.inf,
            "seconds": time.time() - started,
            "error": f"{type(exc).__name__}: {exc}",
        }


def judge_many(
    source_path: pathlib.Path,
    problem_path: pathlib.Path,
    groups: Sequence[tuple[int, ...]],
    workers: int,
) -> list[dict]:
    if not groups:
        return []
    if workers <= 1:
        return [
            _judge_worker(str(source_path), str(problem_path), group)
            for group in groups
        ]
    results: list[dict] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        future_to_group = {
            pool.submit(
                _judge_worker,
                str(source_path),
                str(problem_path),
                group,
            ): group
            for group in groups
        }
        for future in concurrent.futures.as_completed(future_to_group):
            result = future.result()
            results.append(result)
            print(
                f"[group] rows={len(result['rows']):3d} "
                f"{min(result['rows']):4d}-{max(result['rows']):4d} "
                f"cases={result['cases_passed']}/{result['cases_total']} "
                f"score={result['score']:.3f} "
                f"seconds={result['seconds']:.1f}",
                flush=True,
            )
    return results


def save_candidate(
    source: str,
    rows: Sequence[int],
    output: pathlib.Path,
    record_path: pathlib.Path,
    result: dict,
    baseline_result: dict,
    source_path: pathlib.Path,
) -> None:
    text = build(source, rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    width, height, box = geometry(text)
    record = {
        "source": str(source_path.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)),
        "sha256": digest,
        "removed_rows": list(rows),
        "removed_count": len(rows),
        "width": width,
        "height": height,
        "box": box,
        "result": result,
        "baseline": baseline_result,
        "local_factor": (
            baseline_result["score"] / result["score"]
            if result["score"] and math.isfinite(result["score"])
            else None
        ),
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        f"[best] wrote {output.relative_to(ROOT)} "
        f"rows={len(rows)} geometry={width}x{height} box={box} "
        f"score={result['score']:.3f} factor={record['local_factor']:.6f} "
        f"sha256={digest}",
        flush=True,
    )


def run(args: argparse.Namespace) -> int:
    source_path = args.source.resolve()
    problem_path = args.problem.resolve()
    output_path = args.output.resolve()
    record_path = args.record.resolve()
    source = source_path.read_text()
    problem = json.loads(problem_path.read_text())
    baseline_struct = structural_fingerprint(source)

    print(f"source={source_path.relative_to(ROOT)}", flush=True)
    print(f"geometry={geometry(source)} histogram={row_histogram(source)}", flush=True)

    rows = candidate_rows(source, args.passive)
    print(
        f"candidate rows={len(rows)} passive={args.passive!r} "
        f"range={rows[0] if rows else '-'}..{rows[-1] if rows else '-'}",
        flush=True,
    )
    if not rows:
        return 2

    # Establish the same local baseline used for every factor below.
    baseline_report = judge_problem(source, problem)
    baseline_result = {
        "rows": [],
        "passed": baseline_report.cases_passed == baseline_report.cases_total,
        "cases_passed": baseline_report.cases_passed,
        "cases_total": baseline_report.cases_total,
        "case_ticks": list(baseline_report.case_ticks),
        "footprint": baseline_report.footprint,
        "score": baseline_report.score,
    }
    print(
        f"baseline={baseline_report.cases_passed}/{baseline_report.cases_total} "
        f"footprint={baseline_report.footprint} score={baseline_report.score:.3f}",
        flush=True,
    )
    if not baseline_result["passed"]:
        print("refusing to search from a failing baseline", file=sys.stderr)
        return 3

    started = time.time()
    tests_used = 1
    best_rows: tuple[int, ...] = ()
    best_result = baseline_result

    initial_groups = chunks(rows, args.chunk_size)
    structurally_safe: list[tuple[int, ...]] = []
    structurally_failed: list[tuple[int, ...]] = []
    for group in initial_groups:
        ok, reason = structural_gate(baseline_struct, build(source, group))
        if ok:
            structurally_safe.append(group)
        else:
            structurally_failed.append(group)
            print(
                f"[structure] reject {group[0]}-{group[-1]} "
                f"rows={len(group)}: {reason}",
                flush=True,
            )

    budget = max(0, args.max_tests - tests_used)
    first_batch = structurally_safe[:budget]
    first_results = judge_many(
        source_path, problem_path, first_batch, args.workers
    )
    tests_used += len(first_results)

    passing = [
        tuple(result["rows"])
        for result in first_results
        if result["passed"]
    ]
    failing = [
        tuple(result["rows"])
        for result in first_results
        if not result["passed"]
    ] + structurally_failed

    # Prefer lower rows: they are less likely to move room ports and socket
    # distances in this machine, and the earlier bisection's poison was in the
    # top-spanning group.
    passing.sort(key=lambda group: min(group), reverse=True)
    failing.sort(key=lambda group: min(group), reverse=True)

    # Fast path: all individually passing groups together.
    if passing and tests_used < args.max_tests:
        union = tuple(sorted({row for group in passing for row in group}))
        ok, reason = structural_gate(baseline_struct, build(source, union))
        if ok:
            union_result = _judge_worker(
                str(source_path), str(problem_path), union
            )
            tests_used += 1
            print(
                f"[union] rows={len(union)} "
                f"cases={union_result['cases_passed']}/{union_result['cases_total']} "
                f"score={union_result['score']:.3f}",
                flush=True,
            )
            if union_result["passed"]:
                best_rows, best_result = union, union_result
                save_candidate(
                    source, best_rows, output_path, record_path, best_result,
                    baseline_result, source_path,
                )
        else:
            print(f"[union] structural reject: {reason}", flush=True)

    # If the union failed, or if it did not reach the target, compose groups
    # greedily.  A passing group is retested against the accumulated candidate;
    # this catches timing interactions between individually safe deletions.
    if len(best_rows) < args.target_rows:
        accepted = set(best_rows)
        for group in passing:
            if time.time() - started >= args.time_limit:
                break
            addition = set(group) - accepted
            if not addition:
                continue
            trial = tuple(sorted(accepted | addition))
            ok, reason = structural_gate(baseline_struct, build(source, trial))
            if not ok:
                print(
                    f"[greedy] structural reject +{len(addition)} "
                    f"{min(addition)}-{max(addition)}: {reason}",
                    flush=True,
                )
                continue
            if tests_used >= args.max_tests:
                break
            result = _judge_worker(
                str(source_path), str(problem_path), trial
            )
            tests_used += 1
            print(
                f"[greedy] total={len(trial)} "
                f"cases={result['cases_passed']}/{result['cases_total']} "
                f"score={result['score']:.3f}",
                flush=True,
            )
            if result["passed"] and result["score"] < best_result["score"]:
                accepted.update(addition)
                best_rows, best_result = trial, result
                save_candidate(
                    source, best_rows, output_path, record_path, best_result,
                    baseline_result, source_path,
                )
                factor = baseline_result["score"] / result["score"]
                if len(best_rows) >= args.target_rows or factor >= args.target_factor:
                    break

        # Recursively split failed groups, largest/lower first.  This also
        # explores initial groups rejected structurally as a whole: a smaller
        # subset may leave every pipe and binding unchanged.
        queue = [
            group for group in failing
            if group
        ]
        queue.sort(key=lambda group: (len(group), min(group)), reverse=True)
        while (
            queue
            and tests_used < args.max_tests
            and time.time() - started < args.time_limit
            and len(best_rows) < args.target_rows
        ):
            group = queue.pop(0)
            trial = tuple(sorted(set(best_rows) | set(group)))
            ok, reason = structural_gate(baseline_struct, build(source, trial))
            if not ok:
                result = None
                print(
                    f"[split] structural reject group={group[0]}-{group[-1]} "
                    f"n={len(group)}: {reason}",
                    flush=True,
                )
            else:
                result = _judge_worker(
                    str(source_path), str(problem_path), trial
                )
                tests_used += 1
                print(
                    f"[split] group={group[0]}-{group[-1]} n={len(group)} "
                    f"total={len(trial)} "
                    f"cases={result['cases_passed']}/{result['cases_total']} "
                    f"score={result['score']:.3f}",
                    flush=True,
                )
            if (
                result is not None
                and result["passed"]
                and result["score"] < best_result["score"]
            ):
                best_rows, best_result = trial, result
                save_candidate(
                    source, best_rows, output_path, record_path, best_result,
                    baseline_result, source_path,
                )
                factor = baseline_result["score"] / result["score"]
                if factor >= args.target_factor:
                    break
                continue
            if len(group) > 1:
                middle = len(group) // 2
                children = [group[:middle], group[middle:]]
                children.sort(key=lambda child: min(child), reverse=True)
                queue = children + queue

    elapsed = time.time() - started
    if not best_rows:
        print(
            f"NO VERIFIED IMPROVEMENT tests={tests_used} seconds={elapsed:.1f}",
            flush=True,
        )
        return 1

    factor = baseline_result["score"] / best_result["score"]
    print(
        f"DONE rows={len(best_rows)} factor={factor:.6f} "
        f"tests={tests_used} seconds={elapsed:.1f} "
        f"output={output_path.relative_to(ROOT)}",
        flush=True,
    )
    print(
        "NEXT: uv run python scripts/preflight.py "
        f"{output_path.relative_to(ROOT)} pathfinder",
        flush=True,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--problem", type=pathlib.Path, default=DEFAULT_PROBLEM)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--record", type=pathlib.Path, default=DEFAULT_RECORD)
    parser.add_argument("--passive", default=DEFAULT_PASSIVE)
    parser.add_argument("--chunk-size", type=int, default=12)
    parser.add_argument("--workers", type=int, default=min(3, os.cpu_count() or 1))
    parser.add_argument("--max-tests", type=int, default=40)
    parser.add_argument("--time-limit", type=float, default=2400.0)
    parser.add_argument("--target-rows", type=int, default=55)
    parser.add_argument("--target-factor", type=float, default=1.053)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
