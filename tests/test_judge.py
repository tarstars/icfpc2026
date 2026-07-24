"""Judge harness: run a program against problem test cases, score it."""

import json
from pathlib import Path

from littleman.judge import footprint, judge_case, judge_problem

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"

TRIANGLE = """\
+-+ +-+
|I| |O|
+-+ +-+
 v   ^
 v   ^
+-------+
|@rM1+*v|
|Hs/W2M<|
+-------+
"""

ECHO = """\
+-+ +-+
|I| |O|
+-+ +-+
 v   ^
 v   ^
+------+
|>@rsv |
|^   < |
+------+
"""


def test_footprint_is_square_of_max_dimension():
    assert footprint(TRIANGLE) == 81  # 9 x 9


def test_triangle_passes_all_public_cases():
    problem = json.loads((PROBLEMS / "triangle.json").read_text())
    report = judge_problem(TRIANGLE, problem)
    assert report.cases_passed == report.cases_total == 6
    assert report.score > 0
    assert all(t > 0 for t in report.case_ticks)


def test_footprint_scoring_ignores_ticks():
    problem = {
        "publicTestData": [{"rounds": [{"in": ["1"], "out": ["1"]}]}],
        "scoring": "footprint",
    }
    report = judge_problem(ECHO, problem)
    assert report.cases_passed == report.cases_total == 1
    assert report.score == report.footprint


def test_echo_passes_multi_round_case():
    rounds = [{"in": ["1"], "out": ["1"]}, {"in": ["2"], "out": ["2"]}]
    result = judge_case(ECHO, rounds)
    assert result.passed
    # round 2 input is withheld until round 1 output arrives, so the second
    # output must come at least a full pipe round-trip later
    assert result.ticks > 8


def test_wrong_output_fails_immediately():
    rounds = [{"in": ["5"], "out": ["99"]}]
    result = judge_case(ECHO, rounds)
    assert not result.passed
    assert result.reason == "wrong-output"


def test_missing_output_fails_when_program_ends():
    halts = TRIANGLE  # triangle outputs one value then halts
    rounds = [{"in": ["3"], "out": ["6", "6"]}]
    result = judge_case(halts, rounds)
    assert not result.passed
