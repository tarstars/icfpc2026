"""Release gates for the GPT Matrix Multiply and Sudoku candidates."""

from __future__ import annotations

import importlib.util
import json
import random
from pathlib import Path

from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = ROOT / "experiments" / "gpt-submission-candidates"
MATMUL = ROOT / "submissions" / "matmul" / "matmul_08.man"
SUDOKU = ROOT / "submissions" / "sudoku-validity" / "sudoku_05.man"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _matmul_round(n, m, k, a, b):
    output = [
        sum(a[row * m + inner] * b[inner * k + col] for inner in range(m))
        for row in range(n)
        for col in range(k)
    ]
    return {"in": [n, m, k, *a, *b], "out": output}


def test_matmul_08_release_gates():
    text = MATMUL.read_text()
    generator = _load(EXPERIMENTS / "generate_matmul_08.py")
    parent = ROOT / "submissions" / "matmul" / "matmul_07.man"
    assert generator.build(parent.read_text()) == text
    assert text == (EXPERIMENTS / "matmul_08.man").read_text()
    assert (max(map(len, text.splitlines())), len(text.splitlines())) == (99, 98)
    machine = Machine.parse(text)
    assert sorted(len(pipe.cells) for pipe in machine.pipes)[-2:] == [256, 268]
    validate_layout(text)

    problem = json.loads((ROOT / "data/small/problems/matmul.json").read_text())
    assert judge_problem(text, problem).cases_passed == 7

    rng = random.Random(20260726)
    for index, (n, m, k) in enumerate(
        [(2, 16, 2), (2, 2, 16), (16, 2, 2), (3, 5, 4), (6, 6, 6), (16, 16, 16)]
    ):
        if index == 0:
            a = [-99 if item % 2 else 99 for item in range(n * m)]
            b = [99 if item % 3 else -99 for item in range(m * k)]
        else:
            a = [rng.randint(-99, 99) for _ in range(n * m)]
            b = [rng.randint(-99, 99) for _ in range(m * k)]
        assert judge_case(text, [_matmul_round(n, m, k, a, b)]).passed


def _sudoku_rounds(cells):
    rows = [set() for _ in range(9)]
    columns = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    result = []
    for row, column, value in cells:
        box = 3 * (row // 3) + column // 3
        valid = (
            value not in rows[row]
            and value not in columns[column]
            and value not in boxes[box]
        )
        result.append({"in": [row, column, value], "out": [int(valid)]})
        if not valid:
            break
        rows[row].add(value)
        columns[column].add(value)
        boxes[box].add(value)
    return result


def test_sudoku_05_release_gates():
    text = SUDOKU.read_text()
    generator = _load(EXPERIMENTS / "generate_sudoku_05.py")
    assert generator.build() == text
    assert text == (EXPERIMENTS / "sudoku_05_single_ring.man").read_text()
    assert (max(map(len, text.splitlines())), len(text.splitlines())) == (75, 131)
    assert min(len(pipe.cells) for pipe in Machine.parse(text).pipes) == 2
    validate_layout(text)

    problem = json.loads(
        (ROOT / "data/small/problems/sudoku-validity.json").read_text()
    )
    assert judge_problem(text, problem).cases_passed == 6

    solved = [
        (row, column, (row * 3 + row // 3 + column) % 9 + 1)
        for row in range(9)
        for column in range(9)
    ]
    workloads = []
    for seed in range(8):
        rng = random.Random(20260724 + seed)
        shuffled = solved[:]
        rng.shuffle(shuffled)
        prefix = shuffled[: 12 + seed]
        used = {(row, column) for row, column, _ in prefix}
        source_row, _, duplicate = prefix[0]
        extra = next(
            (source_row, column, duplicate)
            for column in range(9)
            if (source_row, column) not in used
        )
        workloads.append([*prefix, extra])
    workloads.extend(
        [
            [(0, 0, 4), (8, 0, 4)],
            [(0, 0, 7), (2, 2, 7)],
            [(3, 3, 5), (5, 4, 5)],
            solved,
            sorted(solved, key=lambda cell: (cell[1], cell[0])),
        ]
    )
    shuffled = solved[:]
    random.Random(20260799).shuffle(shuffled)
    workloads.append(shuffled)
    for kind in ("row", "column", "box"):
        cells = solved[:]
        row, column, _ = cells[-1]
        duplicate = next(
            value
            for other_row, other_column, value in cells[:-1]
            if (kind == "row" and other_row == row)
            or (kind == "column" and other_column == column)
            or (
                kind == "box"
                and 3 * (other_row // 3) + other_column // 3
                == 3 * (row // 3) + column // 3
            )
        )
        cells[-1] = (row, column, duplicate)
        workloads.append(cells)
    assert len(workloads) == 17
    assert all(judge_case(text, _sudoku_rounds(cells)).passed for cells in workloads)
