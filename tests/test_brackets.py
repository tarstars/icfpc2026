"""Brackets packed-stack machine."""

import json
from pathlib import Path

import pytest

from littleman.brackets import build_brackets
from littleman.judge import judge_problem
from littleman.sim import Machine

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"


def test_passes_all_public_cases():
    problem = json.loads((PROBLEMS / "brackets.json").read_text())
    report = judge_problem(build_brackets(), problem)
    assert report.cases_passed == report.cases_total == 9


@pytest.mark.parametrize(
    "codes,expected",
    [
        ([2, 40, 41], 0),          # ()
        ([0], 0),                   # empty
        ([2, 40, 93], 2),           # (]
        ([1, 41], 1),               # )
        ([3, 40, 91, 123], 4),      # ([{ unclosed
        ([4, 40, 91, 41, 93], 3),   # ([)] interleaved
        ([64] + [40] * 32 + [41] * 32, 0),  # depth exactly 32
        ([2, 123, 125], 0),         # {}
    ],
)
def test_hand_cases(codes, expected):
    m = Machine.parse(build_brackets())
    res = m.run(inputs=codes, max_ticks=100000)
    assert res.output == [expected]
