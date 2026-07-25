"""Tests for Sort's in-band remaining-count token variant."""

import json
import random
from pathlib import Path

from littleman.alexey_sort_ring3 import build_sort_count_token
from littleman.judge import footprint, judge_case, judge_problem
from littleman.server_compat import validate_layout


ROOT = Path(__file__).resolve().parent.parent
PROBLEM = ROOT / "data" / "small" / "problems" / "sort-numbers.json"
ARTIFACT = ROOT / "submissions" / "sort" / "sort_05.man"


def _rounds(lists):
    return [{"in": [len(values)] + values, "out": sorted(values)} for values in lists]


def _run(lists):
    return judge_case(build_sort_count_token(), _rounds(lists))


def test_artifact_matches_generator_and_fits_18_square():
    source = build_sort_count_token()
    assert ARTIFACT.read_text() == source
    assert footprint(source) == 18**2
    validate_layout(source)


def test_public_score_improves_sort_03_by_more_than_five_percent():
    problem = json.loads(PROBLEM.read_text())
    report = judge_problem(build_sort_count_token(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.case_ticks == [1038, 854, 1080, 758, 1388, 3302, 8390]
    assert report.score == 778_062.8571428572
    assert report.score < 928_440.4285714285 * 0.95


def test_worst_case_shapes():
    full = list(range(-8, 8))
    cases = [
        [[5]],
        [[0] * 16, [0] * 16],
        [list(range(16, 0, -1))] * 3,
        [list(range(16))] * 3,
        [[10000, -10000] * 8],
        [[-10000] * 8 + [10000] * 8],
        [full, full[::-1], [7], full, [1, 1]],
        [[1], [2], [3], [4], [5], [6]],
    ]
    for lists in cases:
        result = _run(lists)
        assert result.passed, (lists, result.reason)


def test_randomized_sweep():
    rng = random.Random(20260724)
    for trial in range(300):
        list_count = rng.randint(2, 6)
        lists = []
        for _ in range(list_count):
            n = 16 if trial % 3 == 0 else rng.randint(1, 16)
            magnitude = rng.choice([10000, 100, 3])
            lists.append([rng.randint(-magnitude, magnitude) for _ in range(n)])
        result = _run(lists)
        assert result.passed, (trial, lists, result.reason)
