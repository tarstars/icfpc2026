"""Physical gates for scanning normalized state for wall contact."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_cycle import cycle_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_wallscan import (
    WALLSCAN_END,
    build_wallscan_rig,
    wallscan_reference,
)
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]


def state_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return statebuild_reference(stream)


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = wallscan_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if value == WALLSCAN_END else None


@pytest.fixture(scope="module")
def text():
    return build_wallscan_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_wallscan_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("index", [0, 1, 3, 4, 8, 11])
@pytest.mark.parametrize("ticks", [0, 1, 3])
def test_physical_wall_scan(text, index, ticks):
    stream = state_stream(CASES[index])
    state = cycle_reference(stream, ticks)
    script = Script(state)
    result = Machine.parse(text).run(max_ticks=10_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
