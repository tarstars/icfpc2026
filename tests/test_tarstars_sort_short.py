"""Release gates for the 18-square Sort geometry."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine
from littleman.tarstars_sort_short import build_tarstars_sort_short

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "sort" / "tarstars_sort_08.man"
PROBLEM = REPO / "data" / "small" / "problems" / "sort-numbers.json"
SHA256 = "5a48e23f67359625fa9bb7e0e04ff546015df1cce86222f658551681bbf4a171"


def _rounds(lists: list[list[int]]) -> list[dict]:
    return [{"in": [len(values), *values], "out": sorted(values)} for values in lists]


def _run(lists: list[list[int]]):
    return judge_case(build_tarstars_sort_short(), _rounds(lists))


def test_generator_reproduces_artifact_and_is_deterministic():
    text = build_tarstars_sort_short()
    assert text == build_tarstars_sort_short() == ARTIFACT.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SHA256


def test_geometry_preserves_the_capacity_floor():
    text = build_tarstars_sort_short()
    rows = text.splitlines()
    assert len(rows) == max(map(len, rows)) == 18
    machine = Machine.parse(text)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [2, 2, 7, 17]
    validate_layout(text)


def test_public_cases_and_exact_score():
    report = judge_problem(build_tarstars_sort_short(), json.loads(PROBLEM.read_text()))
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.case_ticks == [755, 617, 772, 544, 928, 2137, 5282]
    assert report.footprint == 324
    assert report.score == 510_762.8571428571


def test_directed_maximum_rounds():
    full = list(range(-8, 8))
    cases = [
        [[0] * 16, [0] * 16],
        [list(range(16, 0, -1))] * 6,
        [list(range(16))] * 6,
        [[10000, -10000] * 8],
        [[-10000] * 8 + [10000] * 8],
        [full, full[::-1], [7], full, [1, 1]],
        [[1], [2], [3], [4], [5], [6]],
    ]
    for lists in cases:
        result = _run(lists)
        assert result.passed, (lists, result.reason)


def test_seeded_constraint_sweep():
    rng = random.Random(20260727)
    for trial in range(300):
        lists = []
        for _ in range(rng.randint(2, 6)):
            n = 16 if trial % 3 == 0 else rng.randint(1, 16)
            magnitude = rng.choice([3, 100, 10_000])
            lists.append([rng.randint(-magnitude, magnitude) for _ in range(n)])
        result = _run(lists)
        assert result.passed, (trial, lists, result.reason)
