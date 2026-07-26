"""Physical tests for the room-border DRAW generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_geom import discover_geometry
from littleman.llm_wallgen import WALL_END, build_wallgen_rig, wallgen_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]


def bounds_of(case: dict) -> list[list[int]]:
    rows = program_grid([int(value) for value in case["rounds"][0]["in"]])
    raw = [ord(" ")] * 256
    men = []
    for row, text in enumerate(rows):
        for col, char in enumerate(text):
            raw[row * 16 + col] = ord(char)
            if char == "@":
                men.append(row * 16 + col)
    geometry = discover_geometry(raw, men)
    return [
        [
            man_row * 16 + left,
            man_row * 16 + right,
            top * 16 + left,
            bottom * 16 + left,
        ]
        for (top, left, bottom, right), man in zip(
            geometry.rooms, sorted(men), strict=True
        )
        for man_row in [man // 16]
    ]


class Script:
    def __init__(self, bounds: list[list[int]]):
        self.input = [value for room in bounds for value in room]
        self.expected = [value for room in bounds for value in wallgen_reference(room)]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_wallgen_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_wallgen_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_room_bounds(text, case):
    script = Script(bounds_of(case))
    result = Machine.parse(text).run(max_ticks=2_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_extreme_rectangles(text):
    bounds = [[17, 30, 1, 225], [0, 255, 0, 240]]
    script = Script(bounds)
    result = Machine.parse(text).run(max_ticks=2_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    assert script.output.count(WALL_END) == 2
