"""Validation for the 15x15 Reverse geometry."""

import json
import random
from pathlib import Path

from littleman.alexey_reverse3 import build_reverse3
from littleman.judge import footprint, judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine


ROOT = Path(__file__).resolve().parent.parent
PROBLEM = ROOT / "data" / "small" / "problems" / "reverse-a-list.json"
ARTIFACT = ROOT / "submissions" / "reverse-a-list" / "reverse_02.man"
LIMIT = 10**6


def _run(lists):
    rounds = [{"in": [len(values)] + values, "out": values[::-1]} for values in lists]
    return judge_case(build_reverse3(), rounds, max_ticks=200_000)


def test_artifact_geometry_capacity_and_public_score():
    source = build_reverse3()
    assert ARTIFACT.read_text() == source
    assert footprint(source) == 15**2
    validate_layout(source)
    ring_in = max(Machine.parse(source).pipes, key=lambda pipe: len(pipe.cells))
    assert len(ring_in.cells) == 17

    problem = json.loads(PROBLEM.read_text())
    report = judge_problem(source, problem)
    assert report.cases_passed == report.cases_total == 8, report.case_results
    assert report.case_ticks == [331, 515, 563, 969, 429, 165, 1801, 4521]
    assert report.score == 261_393.75
    assert report.score < 297_536 * 0.95


def test_worst_case_shapes():
    full = list(range(-8, 8))
    cases = [
        [[7]],
        [[1], [2], [3]],
        [list(range(16))],
        [list(range(16))] * 3,
        [[0] * 16],
        [[LIMIT, -LIMIT] * 8],
        [[-LIMIT] * 16],
        [full, [3], full],
        [[1, 2], list(range(16)), [5]],
        [list(range(16, 0, -1)), [0], [9, 9]],
    ]
    for lists in cases:
        result = _run(lists)
        assert result.passed, (lists, result.reason)


def test_randomized_sweep():
    rng = random.Random(20260724)
    for trial in range(250):
        lists = []
        for _ in range(rng.randint(1, 3)):
            n = 16 if trial % 3 == 0 else rng.randint(1, 16)
            magnitude = rng.choice([LIMIT, 1000, 2])
            lists.append([rng.randint(-magnitude, magnitude) for _ in range(n)])
        result = _run(lists)
        assert result.passed, (trial, lists, result.reason)
