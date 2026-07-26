"""End-to-end physical composition through LLM pipe-cell tracing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_geometry_assemble import build_geometry_pipeline
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
SELECTED = [CASES[0], CASES[1], CASES[5], CASES[8]]


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def stream_of(rows, tail=(1, 7)):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows)), *tail]
    return pack_reference(scan_reference(source))


def expected_of(stream):
    rooms = roomfind_reference(stream)
    perimeters = perimeter_reference(rooms)
    starts = pipestarts_reference(perimeters)
    return pipetrace_reference(starts)


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = expected_of(stream)
        self.output = []
        self.last_tick = 0

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, tick):
        self.output.append(value)
        self.last_tick = tick
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_geometry_pipeline()


def test_composed_layout_is_deterministic_and_server_safe(text):
    assert build_geometry_pipeline() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    lines = text.splitlines()
    assert len(lines) < 2_500
    assert max(map(len, lines)) < 500


@pytest.mark.parametrize("case", SELECTED, ids=lambda case: case["name"])
def test_composed_geometry_pipeline(text, case):
    stream = stream_of(rows_of(case))
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    assert script.last_tick < 50_000_000
