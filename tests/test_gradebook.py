"""Grade Book generated-machine tests."""

import json
from pathlib import Path

from littleman.gradebook import build_gradebook
from littleman.judge import judge_problem
from littleman.sim import Machine

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"
SUBMISSIONS = Path(__file__).resolve().parent.parent / "submissions" / "gradebook"


def test_program_loads():
    Machine.parse(build_gradebook())


def test_preserved_candidate_matches_generator():
    assert (SUBMISSIONS / "gradebook_00.man").read_text() == build_gradebook()


def test_passes_public_cases():
    problem = json.loads((PROBLEMS / "gradebook.json").read_text())
    report = judge_problem(build_gradebook(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results
