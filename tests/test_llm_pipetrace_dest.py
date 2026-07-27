"""Physical parity for destination-annotated LLM pipe traces."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import ROOM_END, perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import (
    PIPE_DEST,
    PIPE_END,
    build_pipetrace_rig,
    pipetrace_dest_reference,
)
from littleman.llm_roomfind import SETUP_END, roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 10)


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def stream_of(rows):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    packed = pack_reference(scan_reference(source))
    rooms = roomfind_reference(packed)
    return pipestarts_reference(perimeter_reference(rooms))


def destinations(tokens):
    result = []
    index = 64
    while tokens[index] != SETUP_END:
        index += 5
        while tokens[index] != ROOM_END:
            index += 1
            while tokens[index] != PIPE_DEST:
                index += 1
            result.append(tokens[index + 1])
            assert tokens[index + 2] == PIPE_END
            index += 3
        index += 1
    return result


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = pipetrace_dest_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipetrace_rig(annotate_dest=True)


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipetrace_rig(annotate_dest=True) == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_destination_wall_addresses_are_exact(text, case):
    rows = rows_of(case)
    stream = stream_of(rows)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected

    machine = Machine.parse("\n".join(rows))
    actual = destinations(script.output)
    expected = []
    for pipe in machine.pipes:
        tail_row, tail_col = pipe.cells[-1]
        candidates = [
            (row, col)
            for row in range(16)
            for col in range(16)
            if pipe.dest.on_border(row, col)
            if abs(row - tail_row) + abs(col - tail_col) == 1
        ]
        assert len(candidates) == 1
        expected.append(candidates[0][0] * 16 + candidates[0][1])
    assert actual == expected
