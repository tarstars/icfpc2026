"""Streaming-max machine (practice problem)."""

import json
from pathlib import Path

from littleman.judge import judge_problem
from littleman.max_element import build_max_element
from littleman.sim import Machine

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"


def test_passes_all_public_cases():
    problem = json.loads((PROBLEMS / "max-element.json").read_text())
    report = judge_problem(build_max_element(), problem)
    assert report.cases_passed == report.cases_total == 10


def test_halts_after_single_output():
    m = Machine.parse(build_max_element())
    res = m.run(inputs=[4, -7, -2, -9, -1], max_ticks=2000)
    assert res.status == "halted"
    assert res.output == [-1]
