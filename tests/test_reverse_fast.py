"""Tests for the marker-ring reverse-a-list machine."""

import json
import random
from pathlib import Path

from littleman.judge import footprint, judge_case, judge_problem
from littleman.reverse_fast import build_reverse_fast
from littleman.server_compat import validate_layout

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "reverse-a-list" / "reverse_04.man"
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "reverse-a-list.json").read_text()
)
LIMIT = 10**6


def test_generator_is_deterministic():
    assert build_reverse_fast() == build_reverse_fast()


def test_artifact_matches_generator():
    assert ARTIFACT.read_text() == build_reverse_fast()


def test_layout_is_server_loadable():
    # reverse_03.man failed exactly here: its ring-out pipe climbed the
    # column flush against the input room's right wall, which the server
    # counts as a second connection even though it starts and ends
    # elsewhere.  reverse_04.man climbs one column further out.
    validate_layout(build_reverse_fast())


def test_public_cases_pass():
    report = judge_problem(build_reverse_fast(), PROBLEM)
    assert report.cases_passed == report.cases_total == 8


def test_footprint_is_small():
    # the 16x16 predecessor scored 261k locally; keep this one well under it
    assert footprint(build_reverse_fast()) <= 196


def _round(values):
    return {"in": [str(len(values))] + [str(v) for v in values], "out": [
        str(v) for v in reversed(values)
    ]}


def _check(program, lists):
    rounds = [_round(v) for v in lists]
    result = judge_case(program, rounds, max_ticks=200_000)
    assert result.passed, (lists, result.reason)


def test_edge_shapes():
    program = build_reverse_fast()
    cases = [
        [[7]],                                   # n = 1
        [[0]],
        [[LIMIT]], [[-LIMIT]],                   # extreme singletons
        [list(range(1, 17))],                    # n = 16
        [[5] * 16],                              # all equal, full length
        [[1, 2, 3, 2, 1]],                       # palindrome
        [[LIMIT, -LIMIT] * 8],                   # extremes, full length
        [[LIMIT] * 16], [[-LIMIT] * 16],
        [[1], [1, 2], list(range(16))],          # three rounds, growing
        [list(range(16)), [0], [-LIMIT, LIMIT]],  # three rounds, shrinking
    ]
    for lists in cases:
        _check(program, lists)


def test_fuzz_random_lists():
    program = build_reverse_fast()
    rng = random.Random(20260726)
    for _ in range(50):
        rounds = rng.randint(1, 3)
        lists = []
        for _ in range(rounds):
            n = rng.randint(1, 16)
            style = rng.randint(0, 3)
            if style == 0:
                values = [rng.randint(-LIMIT, LIMIT) for _ in range(n)]
            elif style == 1:
                values = [rng.choice([-LIMIT, 0, LIMIT]) for _ in range(n)]
            elif style == 2:
                values = [rng.randint(-3, 3)] * n  # all equal
            else:
                half = [rng.randint(-LIMIT, LIMIT) for _ in range((n + 1) // 2)]
                values = half + half[::-1][n % 2:]  # palindrome
            lists.append(values)
        _check(program, lists)
