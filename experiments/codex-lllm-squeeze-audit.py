"""Bounded judge-driven search for safe blank-line deletions in LLLM 03."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path

from littleman.alexey_squeeze import deletable_cols, deletable_rows
from littleman.server_compat import judge_problem

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "submissions/lllm/lllm_03.man"
PROBLEM = json.loads(
    (REPO / "data/small/problems/little-little-little-man.json").read_text()
)
LINES = SOURCE.read_text().rstrip("\n").splitlines()
WIDTH = max(map(len, LINES))
GRID = tuple(line.ljust(WIDTH) for line in LINES)


def build(rows: tuple[int, ...], columns: tuple[int, ...]) -> str:
    dropped_rows = set(rows)
    dropped_columns = set(columns)
    return (
        "\n".join(
            "".join(
                char
                for column, char in enumerate(line)
                if column not in dropped_columns
            ).rstrip()
            for row, line in enumerate(GRID)
            if row not in dropped_rows
        ).rstrip()
        + "\n"
    )


def evaluate(spec: tuple[str, int]) -> tuple[str, int, bool, object]:
    axis, index = spec
    rows = (index,) if axis == "row" else ()
    columns = (index,) if axis == "column" else ()
    try:
        report = judge_problem(build(rows, columns), PROBLEM, max_ticks=500_000)
    except (AssertionError, RuntimeError, ValueError) as error:
        return axis, index, False, type(error).__name__
    passed = report.cases_passed == report.cases_total
    summary = (
        (
            report.footprint,
            report.case_ticks,
            report.score,
        )
        if passed
        else (report.cases_passed, report.cases_total)
    )
    return axis, index, passed, summary


def evaluate_combo(
    spec: tuple[str, tuple[int, ...], tuple[int, ...]],
) -> dict[str, object]:
    label, rows, columns = spec
    try:
        report = judge_problem(build(rows, columns), PROBLEM, max_ticks=500_000)
    except (AssertionError, RuntimeError, ValueError) as error:
        return {"label": label, "error": type(error).__name__}
    return {
        "label": label,
        "rows": rows,
        "columns": columns,
        "passed": (report.cases_passed, report.cases_total),
        "footprint": report.footprint,
        "ticks": report.case_ticks,
        "score": report.score,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combinations-only", action="store_true")
    args = parser.parse_args()
    rows = deletable_rows(list(GRID))
    columns = deletable_cols(list(GRID))
    combos = [
        ("r310-c23x8", (310,), tuple(range(23, 31))),
        ("r310-c37x5", (310,), tuple(range(37, 42))),
        ("r310-c43", (310,), (43,)),
        ("r310-c74x4", (310,), (74, 75, 76, 78)),
        ("r310-c183x4", (310,), tuple(range(183, 187))),
        ("r310-c214x3", (310,), tuple(range(214, 217))),
        ("r310-c293x4", (310,), tuple(range(293, 297))),
        ("r310-one-each", (310,), (23, 37, 43, 74, 183, 214, 293)),
        (
            "r310-first-four-groups",
            (310,),
            (*range(23, 31), *range(37, 42), 43, 74, 75, 76, 78),
        ),
    ]
    if args.combinations_only:
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            for result in executor.map(evaluate_combo, combos):
                print(json.dumps(result), flush=True)
        return

    specs = [*(("row", row) for row in rows)]
    specs.extend(("column", column) for column in columns)
    print(
        json.dumps(
            {
                "shape": [len(GRID), WIDTH],
                "rows": rows,
                "columnCount": len(columns),
            }
        ),
        flush=True,
    )
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(evaluate, specs))
    passing = [result for result in results if result[2]]
    print(json.dumps({"passing": passing}), flush=True)

    passing_rows = tuple(index for axis, index, *_ in passing if axis == "row")
    combinations = [("rows-only", passing_rows, ())]
    for label, selected_rows, selected_columns in combinations:
        try:
            report = judge_problem(build(selected_rows, selected_columns), PROBLEM)
            result = {
                "label": label,
                "rows": len(selected_rows),
                "columns": len(selected_columns),
                "passed": [report.cases_passed, report.cases_total],
                "footprint": report.footprint,
                "ticks": report.case_ticks,
                "score": report.score,
            }
        except (AssertionError, RuntimeError, ValueError) as error:
            result = {"label": label, "error": repr(error)}
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
