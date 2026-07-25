"""Benchmark exact checked-in Littleman candidates with the canonical judge."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from littleman.alexey_pipecheck import PipeLengthError
from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.server_compat import (
    ServerCompatibilityError,
    judge_problem,
    validate_layout,
)
from littleman.sim import LoadError, Machine

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBLEM_DIR = REPO_ROOT / "data" / "small" / "problems"


def occupied_bounds(text: str) -> tuple[int, int]:
    """Return trimmed occupied width and height."""
    occupied = [
        (row, col)
        for row, line in enumerate(text.splitlines())
        for col, char in enumerate(line)
        if char != " "
    ]
    if not occupied:
        return 0, 0
    rows = [row for row, _ in occupied]
    cols = [col for _, col in occupied]
    return max(cols) - min(cols) + 1, max(rows) - min(rows) + 1


def benchmark_candidate(path: Path, problem: dict[str, Any]) -> dict[str, Any]:
    """Measure the exact bytes at *path*; never invoke a generator."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    machine = Machine.parse(text)
    validate_layout(text)
    check_pipe_lengths(text)
    report = judge_problem(text, problem)
    width, height = occupied_bounds(text)
    case_names = [
        case.get("name") or f"case {index + 1}"
        for index, case in enumerate(problem["publicTestData"])
    ]
    cases = [
        {
            "name": name,
            "passed": result.passed,
            "ticks": result.ticks,
            "reason": result.reason,
        }
        for name, result in zip(case_names, report.case_results, strict=True)
    ]
    average_ticks = (
        sum(report.case_ticks) / len(report.case_ticks)
        if report.cases_passed == report.cases_total and report.case_ticks
        else None
    )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "width": width,
        "height": height,
        "maxDimension": max(width, height),
        "footprint": report.footprint,
        "rooms": len(machine.rooms),
        "men": len(machine.men),
        "pipes": len(machine.pipes),
        "pipeLengths": sorted(len(pipe.cells) for pipe in machine.pipes),
        "casesPassed": report.cases_passed,
        "casesTotal": report.cases_total,
        "cases": cases,
        "averageTicks": average_ticks,
        "score": report.score if report.score != float("inf") else None,
    }


def compare(candidate: dict[str, Any], parent: dict[str, Any]) -> dict[str, float]:
    """Return positive percentages for improvements over *parent*."""

    def improvement(key: str) -> float:
        before = parent[key]
        after = candidate[key]
        if before is None or after is None or before == 0:
            raise ValueError(
                f"cannot compare {key}: parent={before}, candidate={after}"
            )
        return 100.0 * (before - after) / before

    return {
        "maxDimensionPercent": improvement("maxDimension"),
        "footprintPercent": improvement("footprint"),
        "averageTicksPercent": improvement("averageTicks"),
        "scorePercent": improvement("score"),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark exact .man files with littleman.judge."
    )
    parser.add_argument("problem", help="problem slug or path to problem JSON")
    parser.add_argument("candidates", nargs="+", type=Path)
    parser.add_argument(
        "--parent",
        type=Path,
        help="benchmark this exact file and compare every candidate against it",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="also write the deterministic JSON result to this path",
    )
    return parser


def _load_problem(value: str) -> tuple[Path, dict[str, Any]]:
    path = Path(value)
    if not path.exists():
        path = DEFAULT_PROBLEM_DIR / f"{value}.json"
    return path, json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        problem_path, problem = _load_problem(args.problem)
        parent = benchmark_candidate(args.parent, problem) if args.parent else None
        candidates = []
        failed = False
        for path in args.candidates:
            result = benchmark_candidate(path, problem)
            if parent is not None:
                result["comparisonWithParent"] = compare(result, parent)
            candidates.append(result)
            failed |= result["casesPassed"] != result["casesTotal"]
        document = {
            "schemaVersion": 1,
            "problem": {
                "path": str(problem_path),
                "sha256": hashlib.sha256(problem_path.read_bytes()).hexdigest(),
                "id": problem.get("id"),
                "slug": problem.get("slug"),
                "scoring": problem.get("scoring"),
            },
            "parent": parent,
            "candidates": candidates,
        }
        output = json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        print(output)
        if args.json_output:
            args.json_output.write_text(output + "\n")
        return 1 if failed else 0
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        LoadError,
        PipeLengthError,
        ServerCompatibilityError,
        ValueError,
    ) as error:
        print(f"benchmark_candidates: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
