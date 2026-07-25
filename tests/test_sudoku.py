"""Sudoku Auditor generated-machine and adversarial tests."""

from __future__ import annotations

import json
import random
from pathlib import Path

from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine
from littleman.sudoku import build_sudoku, build_sudoku_two_row

REPO = Path(__file__).resolve().parent.parent
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "sudoku-validity.json").read_text()
)
BASELINE_ARTIFACT = REPO / "submissions" / "sudoku-validity" / "sudoku_00.man"
TWO_ROW_ARTIFACT = REPO / "submissions" / "sudoku-validity" / "sudoku_01.man"


def _verdict_rounds(cells):
    rows = [set() for _ in range(9)]
    columns = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    rounds = []
    for row, column, value in cells:
        box = 3 * (row // 3) + column // 3
        valid = (
            value not in rows[row]
            and value not in columns[column]
            and value not in boxes[box]
        )
        rounds.append({"in": [row, column, value], "out": [int(valid)]})
        if not valid:
            break
        rows[row].add(value)
        columns[column].add(value)
        boxes[box].add(value)
    return rounds


def test_sudoku_program_loads():
    machine = Machine.parse(build_sudoku())
    ring_capacities = [
        len(pipe.cells) for pipe in machine.pipes if len(pipe.cells) == 41
    ]
    assert ring_capacities == [41] * 12


def test_sudoku_artifacts_reproduce_and_two_row_layout_is_server_safe():
    baseline = build_sudoku()
    two_row = build_sudoku_two_row()
    assert baseline == BASELINE_ARTIFACT.read_text()
    assert two_row == TWO_ROW_ARTIFACT.read_text()

    lines = two_row.rstrip("\n").splitlines()
    assert max(map(len, lines)) == 286
    assert len(lines) == 285

    machine = Machine.parse(two_row)
    assert len(machine.rooms) == 20
    assert len(machine.pipes) == 33
    assert sorted(len(pipe.cells) for pipe in machine.pipes).count(41) == 12
    validate_layout(two_row)


def test_sudoku_passes_public_cases():
    report = judge_problem(build_sudoku(), PROBLEM)
    assert report.cases_passed == report.cases_total == 6, report.case_results


def test_sudoku_two_row_passes_public_cases():
    report = judge_problem(build_sudoku_two_row(), PROBLEM)
    assert report.cases_passed == report.cases_total == 6, report.case_results


def _assert_deterministic_valid_prefixes_and_forced_duplicates(text):
    solved = [
        (row, column, (row * 3 + row // 3 + column) % 9 + 1)
        for row in range(9)
        for column in range(9)
    ]
    for seed in range(8):
        rng = random.Random(20260724 + seed)
        shuffled = solved[:]
        rng.shuffle(shuffled)
        prefix = shuffled[: 12 + seed]
        used = {(row, column) for row, column, _ in prefix}
        source_row, _, duplicate_value = prefix[0]
        duplicate_cell = next(
            (source_row, column, duplicate_value)
            for column in range(9)
            if (source_row, column) not in used
        )
        rounds = _verdict_rounds([*prefix, duplicate_cell])
        result = judge_case(text, rounds)
        assert result.passed, (seed, rounds, result)

    for cells in (
        [(0, 0, 4), (8, 0, 4)],
        [(0, 0, 7), (2, 2, 7)],
        [(3, 3, 5), (5, 4, 5)],
    ):
        result = judge_case(text, _verdict_rounds(cells))
        assert result.passed, (cells, result)


def test_sudoku_deterministic_valid_prefixes_and_forced_duplicates():
    _assert_deterministic_valid_prefixes_and_forced_duplicates(build_sudoku())


def test_sudoku_two_row_deterministic_valid_prefixes_and_forced_duplicates():
    _assert_deterministic_valid_prefixes_and_forced_duplicates(build_sudoku_two_row())
