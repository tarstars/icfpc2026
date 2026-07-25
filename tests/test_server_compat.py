"""Regression tests for known contest-server compatibility differences."""

import json
from pathlib import Path

import pytest

from littleman.server_compat import (
    ServerCompatibilityError,
    find_shared_walls,
    judge_problem,
    validate_layout,
)

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS = ROOT / "data" / "small" / "problems"
TRIANGLES = ROOT / "submissions" / "triangle"


def test_rejects_locally_parseable_shared_wall_layout():
    source = (TRIANGLES / "triangle_03.man").read_text()

    conflicts = find_shared_walls(source)

    assert len(conflicts) == 1
    assert conflicts[0].cells == ((5, 4), (6, 4), (7, 4))
    with pytest.raises(ServerCompatibilityError, match="share 3 wall cell"):
        validate_layout(source)


def test_accepts_final_wall_step_and_drains_output():
    source = (TRIANGLES / "triangle_04.man").read_text()
    problem = json.loads((PROBLEMS / "triangle.json").read_text())

    validate_layout(source)
    report = judge_problem(source, problem)

    assert report.cases_passed == report.cases_total == 6
    assert report.case_ticks == [13] * 6
    assert report.score == 832
