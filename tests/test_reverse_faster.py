"""Tests for the double-extraction marker-ring reverse machine."""

import json
import random
from pathlib import Path

from littleman.judge import footprint, judge_case, judge_problem
from littleman.reverse_faster import build_reverse_faster
from littleman.server_compat import validate_layout

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "reverse-a-list" / "reverse_05.man"
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "reverse-a-list.json").read_text()
)


def test_generator_is_deterministic():
    assert build_reverse_faster() == build_reverse_faster()


def test_artifact_matches_generator():
    assert ARTIFACT.read_text() == build_reverse_faster()


def test_layout_is_server_loadable():
    # v1 died here: the ring-out's final westward bend arrow sat flush
    # against the pump's left wall and parsed as a phantom pump->relay
    # pipe that let heads bypass the ring.  Jog row is now below the
    # relay with the I room moved to the SW corner.
    validate_layout(build_reverse_faster())


def test_public_cases_pass():
    report = judge_problem(build_reverse_faster(), PROBLEM)
    assert report.cases_passed == report.cases_total == 8


def test_beats_reverse_04_locally():
    from littleman.reverse_fast import build_reverse_fast

    old = judge_problem(build_reverse_fast(), PROBLEM)
    new = judge_problem(build_reverse_faster(), PROBLEM)
    assert new.score < old.score * 0.7  # measured: 74390.6 vs 120912.4


def _round(values):
    return {
        "in": [str(len(values))] + [str(v) for v in values],
        "out": [str(v) for v in reversed(values)],
    }


def test_edge_shapes_and_fuzz():
    program = build_reverse_faster()
    cases = [
        [[7]],
        [[1, 2]],
        [[3, 1, 4]],
        [list(range(16))],
        [[-1000000, 1000000] * 8],
        [[5] * 16],
        [[9], [8, 7], [1] * 15],
        [[7], [7], [7]],  # three singleton rounds
    ]
    random.seed(11)
    for _ in range(50):
        cases.append(
            [
                [random.randint(-(10**6), 10**6)
                 for _ in range(random.randint(1, 16))]
                for _ in range(random.randint(1, 3))
            ]
        )
    for lists in cases:
        res = judge_case(program, [_round(v) for v in lists], max_ticks=200_000)
        assert res.passed, (lists, res.reason)
