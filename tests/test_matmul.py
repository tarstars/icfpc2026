"""Matrix Multiply generated-machine tests."""

import json
import random
from pathlib import Path

from littleman.judge import judge_case, judge_problem
from littleman.matmul import build_matmul
from littleman.matmul_ring import build_matmul_ring, build_matmul_ring_compact
from littleman.sim import Machine

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"


def test_program_loads():
    Machine.parse(build_matmul())


def test_passes_public_cases():
    problem = json.loads((PROBLEMS / "matmul.json").read_text())
    report = judge_problem(build_matmul(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results


def test_ring_program_loads_with_full_matrix_capacity():
    machine = Machine.parse(build_matmul_ring())
    capacities = sorted(len(pipe.cells) for pipe in machine.pipes)
    assert capacities[-2:] == [276, 350]


def test_ring_passes_public_cases():
    problem = json.loads((PROBLEMS / "matmul.json").read_text())
    report = judge_problem(build_matmul_ring(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.footprint == 80_656


def test_compact_ring_program_loads_with_full_matrix_capacity():
    machine = Machine.parse(build_matmul_ring_compact())
    capacities = sorted(len(pipe.cells) for pipe in machine.pipes)
    assert capacities[-2:] == [268, 334]


def test_compact_ring_passes_public_cases():
    problem = json.loads((PROBLEMS / "matmul.json").read_text())
    report = judge_problem(build_matmul_ring_compact(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.footprint == 33_489


def _matmul_round(n, m, k, a, b):
    output = [
        sum(a[row * m + inner] * b[inner * k + col] for inner in range(m))
        for row in range(n)
        for col in range(k)
    ]
    return {"in": [n, m, k, *a, *b], "out": output}


def test_compact_ring_deterministic_adversarial_cases():
    rng = random.Random(20260724)
    dimensions = [
        (2, 16, 2),
        (2, 2, 16),
        (16, 2, 2),
        (3, 5, 4),
        (6, 6, 6),
    ]
    rounds = []
    for index, (n, m, k) in enumerate(dimensions):
        if index == 0:
            a = [(-99 if i % 2 else 99) for i in range(n * m)]
            b = [(99 if i % 3 else -99) for i in range(m * k)]
        else:
            a = [rng.randint(-99, 99) for _ in range(n * m)]
            b = [rng.randint(-99, 99) for _ in range(m * k)]
        rounds.append(_matmul_round(n, m, k, a, b))

    text = build_matmul_ring_compact()
    for round_data in rounds:
        result = judge_case(text, [round_data])
        assert result.passed, (round_data, result)
