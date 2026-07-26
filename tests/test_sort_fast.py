"""Tests for the tight-loop shrinking-ring sort (``sort_07``)."""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

from littleman.judge import judge_case
from littleman.sort_fast import build_sort_tight, selection_traversals

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "sort" / "sort_07.man"
SHA256 = "eb3d9c1f42c064597c5231ff3b314a45848296b77f366fa668020c43faa74661"

# Both this program and the live sort_06 deadlock above 20 values per list:
# the ring pipe plus relay cannot hold n values and the count token.
MAX_N = 20


def _run(program, lists, max_ticks=200_000):
    rounds = [
        {"in": [str(len(v))] + [str(x) for x in v],
         "out": [str(x) for x in sorted(v)]}
        for v in lists
    ]
    return judge_case(program, rounds, max_ticks=max_ticks)


def test_generator_reproduces_artifact_byte_for_byte():
    text = build_sort_tight()
    assert text == ARTIFACT.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SHA256


def test_generator_is_deterministic():
    assert build_sort_tight() == build_sort_tight()


def test_public_cases_and_score():
    import json

    problem = json.loads(
        (REPO / "data" / "small" / "problems" / "sort-numbers.json").read_text()
    )
    from littleman.judge import judge_problem

    report = judge_problem(build_sort_tight(), problem)
    assert report.cases_passed == report.cases_total == 7
    assert report.footprint == 361
    # The live sort_06 scores 867,277 here; stay comfortably better.
    assert report.score < 600_000


def test_edge_cases():
    program = build_sort_tight()
    for lst in ([5], [1], [0, 0], [7] * 5, [-1], list(range(MAX_N)),
                list(range(MAX_N, 0, -1)), [2**40, -(2**40), 0],
                [-5, -5, 3, 3, 0, 0]):
        assert _run(program, [lst]).passed, lst


def test_fuzz_against_sorted():
    program = build_sort_tight()
    rng = random.Random(20260726)
    lists = []
    for _ in range(50):
        n = rng.randint(1, MAX_N)
        lo = rng.choice([-3, -100, -(10**9), -(2**40)])
        lists.append([rng.randint(lo, -lo) for _ in range(n)])
    for lst in lists:
        assert _run(program, [lst]).passed, lst


def test_multi_round_rounds():
    program = build_sort_tight()
    rng = random.Random(7)
    for _ in range(8):
        lists = [
            [rng.randint(-999, 999) for _ in range(rng.randint(1, MAX_N))]
            for _ in range(rng.randint(1, 5))
        ]
        assert _run(program, lists, max_ticks=400_000).passed


def test_traversal_model():
    assert selection_traversals(1) == 1
    assert selection_traversals(16) == 136
