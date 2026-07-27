"""Release gates for the lane-swapped Sort candidate."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine
from littleman.tarstars_sort_next import build_tarstars_sort_next

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "sort" / "tarstars_sort_09.man"
PROBLEM = REPO / "data" / "small" / "problems" / "sort-numbers.json"
SHA256 = "533ea6e62a91a089632fb7be6d148a9513016d9f6f58b9a9b0f4ba30ba86f701"


def _rounds(lists: list[list[int]]) -> list[dict]:
    return [{"in": [len(values), *values], "out": sorted(values)} for values in lists]


def _run(lists: list[list[int]]):
    return judge_case(build_tarstars_sort_next(), _rounds(lists))


def test_generator_reproduces_artifact_and_is_deterministic():
    text = build_tarstars_sort_next()
    assert text == build_tarstars_sort_next() == ARTIFACT.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SHA256


def test_geometry_preserves_capacity():
    text = build_tarstars_sort_next()
    rows = text.splitlines()
    assert len(rows) == max(map(len, rows)) == 18
    machine = Machine.parse(text)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [2, 2, 7, 17]
    validate_layout(text)


def test_public_cases_and_exact_score():
    report = judge_problem(build_tarstars_sort_next(), json.loads(PROBLEM.read_text()))
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.case_ticks == [733, 601, 823, 529, 925, 2153, 5191]
    assert report.footprint == 324
    assert report.score == 507_060.0


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
