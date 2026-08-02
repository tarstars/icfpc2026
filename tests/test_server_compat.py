"""Regression tests for known contest-server compatibility differences."""

import json
from pathlib import Path

import pytest

from littleman.server_compat import (
    ServerCompatibilityError,
    find_shared_walls,
    judge_problem,
    parse_server_compatible,
    validate_layout,
)

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS = ROOT / "data" / "small" / "problems"
SUBMISSIONS = ROOT / "submissions"
TRIANGLES = SUBMISSIONS / "triangle"

KNOWN_SERVER_REJECTIONS = [
    ("reverse-a-list/reverse_02.man", "shorter than 2 cells"),
    ("reverse-a-list/reverse_03.man", "against its wall"),
    ("sort/sort_05.man", "shorter than 2 cells"),
    ("triangle/triangle_03.man", "share 3 wall cell"),
]

FIXED_SUCCESSORS = [
    "reverse-a-list/reverse_01.man",
    "sort/sort_06.man",
    "triangle/triangle_04.man",
]


def test_rejects_locally_parseable_shared_wall_layout():
    source = (TRIANGLES / "triangle_03.man").read_text()

    conflicts = find_shared_walls(source)

    assert len(conflicts) == 1
    assert conflicts[0].cells == ((5, 4), (6, 4), (7, 4))
    with pytest.raises(ServerCompatibilityError, match="share 3 wall cell"):
        validate_layout(source)


@pytest.mark.parametrize(
    ("relative_path", "message"),
    KNOWN_SERVER_REJECTIONS,
    ids=lambda value: Path(value).name if value.endswith(".man") else value,
)
def test_parser_like_gate_rejects_every_preserved_loader_failure(
    relative_path: str, message: str
) -> None:
    source = (SUBMISSIONS / relative_path).read_text()

    for validator in (parse_server_compatible, validate_layout):
        with pytest.raises(ServerCompatibilityError, match=message):
            validator(source)


@pytest.mark.parametrize("relative_path", FIXED_SUCCESSORS, ids=lambda p: Path(p).name)
def test_parser_like_gate_accepts_fixed_successors(relative_path: str) -> None:
    source = (SUBMISSIONS / relative_path).read_text()

    machine = parse_server_compatible(source)

    assert machine.rooms
    assert machine.pipes


def test_accepts_final_wall_step_and_drains_output():
    source = (TRIANGLES / "triangle_04.man").read_text()
    problem = json.loads((PROBLEMS / "triangle.json").read_text())

    validate_layout(source)
    report = judge_problem(source, problem)

    assert report.cases_passed == report.cases_total == 6
    assert report.case_ticks == [13] * 6
    assert report.score == 832
