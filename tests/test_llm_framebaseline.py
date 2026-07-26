"""Physical gates for previous-frame address refresh."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_framebaseline import (
    build_framebaseline_rig,
    framebaseline_reference,
)
from littleman.llm_machine import normalize_input_reference
from littleman.llm_ring_exec import parse_state_stream
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = framebaseline_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text() -> str:
    return build_framebaseline_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_framebaseline_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_refreshes_old_to_current_and_preserves_everything_else(text, case):
    raw = [int(value) for value in case["rounds"][0]["in"]]
    tokens = normalize_input_reference([*raw, 7, 11])
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=2_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    _raw, rooms, _pipes, tail = parse_state_stream(script.output)
    assert all(room.old == room.addr for room in rooms)
    assert tail == [7, 11]
