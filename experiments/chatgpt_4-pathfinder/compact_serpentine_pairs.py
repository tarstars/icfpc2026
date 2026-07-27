#!/usr/bin/env python3
"""Compact pairs of pure-computation serpentine rows in Pathfinder.

Pathfinder's giant room is mostly an unrolled two-row racetrack:

    > operation... v
    v ........... <

Two consecutive *pure computation* laps can be fused into one operation row
and one return row.  Their instruction streams are concatenated in the same
order, while the two middle rows are deleted.  This removes two rows and the
blank return traversal without moving any pipe-dependent instruction.

Only laps whose bodies contain no receive/send/pipe-count operation and no
turn/branch/halt are considered.  Every group is additionally gated by the
same parser, exact pipe-length, display-shape and nearest-pipe-binding checks
as search_pass_through_rows.py, followed by all public display-frame cases.
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
from dataclasses import asdict, dataclass
from typing import Sequence

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

from littleman import sim  # noqa: E402
from littleman.judge import judge_problem  # noqa: E402
from search_pass_through_rows import (  # noqa: E402
    geometry,
    structural_fingerprint,
    structural_gate,
)

DEFAULT_SOURCE = ROOT / "submissions/pathfinder/pathfinder_02.man"
DEFAULT_PROBLEM = ROOT / "data/small/problems/pathfinder.json"
DEFAULT_OUTPUT = ROOT / "submissions/pathfinder/chatgpt4_pathfinder_04.man"
DEFAULT_RECORD = HERE / "serpentine_result.json"

# These either select a pipe by position, change direction conditionally,
# split/halt, or mark the initial man.  Moving them is not this transformation.
FORBIDDEN_BODY = frozenset("rRsSUq><^vVXdaxHU@Y")


@dataclass(frozen=True)
class MergeSite:
    row: int
    start: int
    end_first: int
    end_second: int
    body_first: str
    body_second: str

    @property
    def deleted_rows(self) -> tuple[int, int]:
        return self.row + 1, self.row + 2

    @property
    def new_end(self) -> int:
        return self.start + 1 + len(self.body_first) + len(self.body_second)


def _grid(text: str) -> list[list[str]]:
    lines = text.rstrip("\n").split("\n")
    width = max(map(len, lines))
    return [list(line.ljust(width)) for line in lines]


def _meaningful_positions(
    grid: list[list[str]], row: int, left: int, right: int
) -> list[int]:
    return [
        col for col in range(left + 1, right)
        if grid[row][col] not in " ."
    ]


def _operation(
    grid: list[list[str]], room: sim.Room, row: int
) -> tuple[int, int, str] | None:
    positions = _meaningful_positions(grid, row, room.left, room.right)
    if len(positions) < 2:
        return None
    start, end = positions[0], positions[-1]
    if grid[row][start] != ">" or grid[row][end] not in "vV":
        return None

    # There must be no unrelated glyph outside the walked segment.
    if any(
        grid[row][col] not in " ."
        for col in range(room.left + 1, start)
    ):
        return None
    if any(
        grid[row][col] not in " ."
        for col in range(end + 1, room.right)
    ):
        return None

    body = "".join(
        ch for ch in grid[row][start + 1 : end]
        if ch not in " ."
    )
    if not body or any(ch in FORBIDDEN_BODY for ch in body):
        return None
    # Keep each horizontal literal self-contained before concatenation.
    if body.count("`") % 2:
        return None
    return start, end, body


def _is_return(
    grid: list[list[str]],
    room: sim.Room,
    row: int,
    start: int,
    end: int,
) -> bool:
    positions = _meaningful_positions(grid, row, room.left, room.right)
    return (
        positions == [start, end]
        and grid[row][start] in "vV"
        and grid[row][end] == "<"
    )


def find_sites(text: str) -> tuple[sim.Room, list[MergeSite]]:
    grid = _grid(text)
    machine = sim.Machine.parse(text)
    rooms = [room for room in machine.rooms if room.kind == "room"]
    main = max(
        rooms,
        key=lambda room: (room.bottom - room.top) * (room.right - room.left),
    )
    pipe_rows = {row for pipe in machine.pipes for row, _ in pipe.cells}
    other_rooms = [room for room in machine.rooms if room is not main]

    raw: list[MergeSite] = []
    for row in range(main.top + 1, main.bottom - 2):
        first = _operation(grid, main, row)
        second = _operation(grid, main, row + 2)
        if first is None or second is None:
            continue
        start1, end1, body1 = first
        start2, end2, body2 = second
        if start1 != start2:
            continue
        if not _is_return(grid, main, row + 1, start1, end1):
            continue
        if not _is_return(grid, main, row + 3, start2, end2):
            continue

        deleted = (row + 1, row + 2)
        if any(r in pipe_rows for r in deleted):
            continue
        # Do not globally delete a row that belongs to another room.  This
        # keeps the transformation local to the giant unrolled room.
        if any(
            other.top <= r <= other.bottom
            for other in other_rooms
            for r in deleted
        ):
            continue

        site = MergeSite(row, start1, end1, end2, body1, body2)
        if site.new_end >= main.right:
            continue
        raw.append(site)

    # Pick a deterministic maximal non-overlapping subset.  A site occupies
    # rows row..row+3; the next one may start at row+4.
    selected: list[MergeSite] = []
    last = -1
    for site in raw:
        if site.row <= last:
            continue
        selected.append(site)
        last = site.row + 3
    return main, selected


def apply_sites(text: str, room: sim.Room, sites: Sequence[MergeSite]) -> str:
    grid = _grid(text)
    for site in sorted(sites, key=lambda item: item.row, reverse=True):
        body = site.body_first + site.body_second
        end = site.new_end

        for col in range(room.left + 1, room.right):
            grid[site.row][col] = " "
            grid[site.row + 3][col] = " "

        grid[site.row][site.start] = ">"
        for offset, ch in enumerate(body, start=site.start + 1):
            grid[site.row][offset] = ch
        grid[site.row][end] = "v"

        grid[site.row + 3][site.start] = "v"
        grid[site.row + 3][end] = "<"

        # Bottom-up application keeps every stored original row index valid.
        del grid[site.row + 2]
        del grid[site.row + 1]

    return "\n".join("".join(row).rstrip() for row in grid) + "\n"


def _judge_worker(
    source_path: str,
    problem_path: str,
    site_dicts: tuple[dict, ...],
) -> dict:
    source = pathlib.Path(source_path).read_text()
    problem = json.loads(pathlib.Path(problem_path).read_text())
    room, all_sites = find_sites(source)
    by_row = {site.row: site for site in all_sites}
    sites = [by_row[item["row"]] for item in site_dicts]
    text = apply_sites(source, room, sites)
    started = time.time()
    try:
        report = judge_problem(text, problem)
        return {
            "site_rows": [site.row for site in sites],
            "rows_saved": 2 * len(sites),
            "passed": report.cases_passed == report.cases_total,
            "cases_passed": report.cases_passed,
            "cases_total": report.cases_total,
            "case_ticks": list(report.case_ticks),
            "case_results": [asdict(item) for item in report.case_results],
            "footprint": report.footprint,
            "score": report.score,
            "seconds": time.time() - started,
            "error": None,
        }
    except Exception as exc:
        return {
            "site_rows": [site.row for site in sites],
            "rows_saved": 2 * len(sites),
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


def _payload(sites: Sequence[MergeSite]) -> tuple[dict, ...]:
    return tuple({"row": site.row} for site in sites)


def _groups(
    sites: Sequence[MergeSite], size: int
) -> list[tuple[MergeSite, ...]]:
    return [
        tuple(sites[start : start + size])
        for start in range(0, len(sites), size)
    ]


def judge_many(
    source: pathlib.Path,
    problem: pathlib.Path,
    groups: Sequence[tuple[MergeSite, ...]],
    workers: int,
) -> list[dict]:
    if workers <= 1:
        return [
            _judge_worker(str(source), str(problem), _payload(group))
            for group in groups
        ]
    results: list[dict] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _judge_worker, str(source), str(problem), _payload(group)
            ): group
            for group in groups
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            rows = result["site_rows"]
            print(
                f"[group] sites={len(rows):2d} rows={min(rows):4d}-{max(rows):4d} "
                f"saved={result['rows_saved']:3d} "
                f"cases={result['cases_passed']}/{result['cases_total']} "
                f"score={result['score']:.3f} seconds={result['seconds']:.1f}",
                flush=True,
            )
    return results


def save(
    source_text: str,
    room: sim.Room,
    sites: Sequence[MergeSite],
    result: dict,
    baseline: dict,
    output: pathlib.Path,
    record: pathlib.Path,
) -> None:
    text = apply_sites(source_text, room, sites)
    output.parent.mkdir(parents=True, exist_ok=True)
    record.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    width, height, box = geometry(text)
    payload = {
        "source": str(DEFAULT_SOURCE.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)),
        "sha256": digest,
        "merge_rows": [site.row for site in sites],
        "sites": [asdict(site) for site in sites],
        "rows_saved": 2 * len(sites),
        "width": width,
        "height": height,
        "box": box,
        "result": result,
        "baseline": baseline,
        "local_factor": baseline["score"] / result["score"],
    }
    record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        f"[best] sites={len(sites)} saved={2 * len(sites)} "
        f"geometry={width}x{height} box={box} "
        f"factor={payload['local_factor']:.6f} sha256={digest}",
        flush=True,
    )


def run(args: argparse.Namespace) -> int:
    source_path = args.source.resolve()
    problem_path = args.problem.resolve()
    source_text = source_path.read_text()
    problem = json.loads(problem_path.read_text())
    room, sites = find_sites(source_text)
    baseline_struct = structural_fingerprint(source_text)

    print(
        f"main room=({room.left},{room.top})..({room.right},{room.bottom}) "
        f"candidate merge sites={len(sites)} rows available={2 * len(sites)}",
        flush=True,
    )
    if not sites:
        return 2

    baseline_report = judge_problem(source_text, problem)
    baseline = {
        "passed": baseline_report.cases_passed == baseline_report.cases_total,
        "cases_passed": baseline_report.cases_passed,
        "cases_total": baseline_report.cases_total,
        "case_ticks": list(baseline_report.case_ticks),
        "footprint": baseline_report.footprint,
        "score": baseline_report.score,
    }
    if not baseline["passed"]:
        print("baseline fails; refusing to search", file=sys.stderr)
        return 3
    print(
        f"baseline={baseline['cases_passed']}/{baseline['cases_total']} "
        f"score={baseline['score']:.3f} geometry={geometry(source_text)}",
        flush=True,
    )

    # Prefer lower sites, matching the proven-safe direction of the earlier
    # row bisection.
    sites = sorted(sites, key=lambda site: site.row, reverse=True)
    groups = _groups(sites, args.sites_per_group)
    safe_groups: list[tuple[MergeSite, ...]] = []
    rejected: list[tuple[MergeSite, ...]] = []
    for group in groups:
        text = apply_sites(source_text, room, group)
        ok, reason = structural_gate(baseline_struct, text)
        if ok:
            safe_groups.append(group)
        else:
            rejected.append(group)
            print(
                f"[structure] reject sites={len(group)} "
                f"{group[-1].row}-{group[0].row}: {reason}",
                flush=True,
            )

    started = time.time()
    tests = 1
    budget = max(0, args.max_tests - tests - args.reserve_tests)
    initial = safe_groups[:budget]
    untested = safe_groups[budget:]
    results = judge_many(source_path, problem_path, initial, args.workers)
    tests += len(results)

    by_row = {site.row: site for site in sites}
    passing_groups = [
        tuple(by_row[row] for row in result["site_rows"])
        for result in results if result["passed"]
    ]
    failing_groups = [
        tuple(by_row[row] for row in result["site_rows"])
        for result in results if not result["passed"]
    ] + rejected + untested

    best_sites: tuple[MergeSite, ...] = ()
    best_result = baseline

    # Try the union of all passing groups first.
    if passing_groups and tests < args.max_tests:
        union_map = {
            site.row: site
            for group in passing_groups
            for site in group
        }
        union = tuple(sorted(union_map.values(), key=lambda site: site.row))
        text = apply_sites(source_text, room, union)
        ok, reason = structural_gate(baseline_struct, text)
        if ok:
            result = _judge_worker(
                str(source_path), str(problem_path), _payload(union)
            )
            tests += 1
            print(
                f"[union] sites={len(union)} saved={2 * len(union)} "
                f"cases={result['cases_passed']}/{result['cases_total']} "
                f"score={result['score']:.3f}",
                flush=True,
            )
            if result["passed"] and result["score"] < best_result["score"]:
                best_sites, best_result = union, result
                save(
                    source_text, room, best_sites, best_result, baseline,
                    args.output.resolve(), args.record.resolve(),
                )
        else:
            print(f"[union] structural reject: {reason}", flush=True)

    # Compose passing groups greedily when their union interacts.
    if 2 * len(best_sites) < args.target_rows:
        accepted = {site.row: site for site in best_sites}
        for group in passing_groups:
            addition = [site for site in group if site.row not in accepted]
            if not addition:
                continue
            if tests >= args.max_tests or time.time() - started >= args.time_limit:
                break
            trial_map = dict(accepted)
            trial_map.update((site.row, site) for site in addition)
            trial = tuple(sorted(trial_map.values(), key=lambda site: site.row))
            text = apply_sites(source_text, room, trial)
            ok, reason = structural_gate(baseline_struct, text)
            if not ok:
                print(f"[greedy] structural reject: {reason}", flush=True)
                continue
            result = _judge_worker(
                str(source_path), str(problem_path), _payload(trial)
            )
            tests += 1
            print(
                f"[greedy] sites={len(trial)} saved={2 * len(trial)} "
                f"cases={result['cases_passed']}/{result['cases_total']} "
                f"score={result['score']:.3f}",
                flush=True,
            )
            if result["passed"] and result["score"] < best_result["score"]:
                accepted = trial_map
                best_sites, best_result = trial, result
                save(
                    source_text, room, best_sites, best_result, baseline,
                    args.output.resolve(), args.record.resolve(),
                )
                if (
                    2 * len(best_sites) >= args.target_rows
                    or baseline["score"] / result["score"] >= args.target_factor
                ):
                    break

        queue = list(failing_groups)
        queue.sort(
            key=lambda group: (len(group), max(site.row for site in group)),
            reverse=True,
        )
        while (
            queue
            and tests < args.max_tests
            and time.time() - started < args.time_limit
            and 2 * len(best_sites) < args.target_rows
        ):
            group = queue.pop(0)
            trial_map = {site.row: site for site in best_sites}
            trial_map.update((site.row, site) for site in group)
            trial = tuple(sorted(trial_map.values(), key=lambda site: site.row))
            text = apply_sites(source_text, room, trial)
            ok, reason = structural_gate(baseline_struct, text)
            result = None
            if ok:
                result = _judge_worker(
                    str(source_path), str(problem_path), _payload(trial)
                )
                tests += 1
                print(
                    f"[split] group={len(group)} total={len(trial)} "
                    f"saved={2 * len(trial)} "
                    f"cases={result['cases_passed']}/{result['cases_total']} "
                    f"score={result['score']:.3f}",
                    flush=True,
                )
            else:
                print(
                    f"[split] structural reject group={len(group)}: {reason}",
                    flush=True,
                )

            if (
                result is not None
                and result["passed"]
                and result["score"] < best_result["score"]
            ):
                best_sites, best_result = trial, result
                save(
                    source_text, room, best_sites, best_result, baseline,
                    args.output.resolve(), args.record.resolve(),
                )
                if baseline["score"] / result["score"] >= args.target_factor:
                    break
                continue
            if len(group) > 1:
                middle = len(group) // 2
                queue = [group[:middle], group[middle:]] + queue

    if not best_sites:
        print(
            f"NO VERIFIED IMPROVEMENT tests={tests} "
            f"seconds={time.time() - started:.1f}",
            flush=True,
        )
        return 1

    factor = baseline["score"] / best_result["score"]
    print(
        f"DONE sites={len(best_sites)} rows_saved={2 * len(best_sites)} "
        f"factor={factor:.6f} tests={tests} "
        f"output={args.output.resolve().relative_to(ROOT)}",
        flush=True,
    )
    print(
        "NEXT: uv run python scripts/preflight.py "
        f"{args.output.resolve().relative_to(ROOT)} pathfinder",
        flush=True,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--problem", type=pathlib.Path, default=DEFAULT_PROBLEM)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--record", type=pathlib.Path, default=DEFAULT_RECORD)
    parser.add_argument("--sites-per-group", type=int, default=4)
    parser.add_argument("--workers", type=int, default=min(3, os.cpu_count() or 1))
    parser.add_argument("--max-tests", type=int, default=36)
    parser.add_argument("--reserve-tests", type=int, default=12)
    parser.add_argument("--time-limit", type=float, default=2400.0)
    parser.add_argument("--target-rows", type=int, default=54)
    parser.add_argument("--target-factor", type=float, default=1.053)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
