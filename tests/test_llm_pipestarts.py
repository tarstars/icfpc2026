"""Physical parity for outgoing pipe-start filtering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import (
    ROOM_END,
    perimeter_reference,
    unpack_candidate,
)
from littleman.llm_pipestarts import build_pipestarts_rig, pipestarts_reference
from littleman.llm_roomfind import SETUP_END, roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 20)


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def stream_of(rows, tail=()):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows)), *tail]
    packed = pack_reference(scan_reference(source))
    return perimeter_reference(roomfind_reference(packed))


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = pipestarts_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipestarts_rig()


def check(text, rows, tail=()):
    stream = stream_of(rows, tail)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    return script.output


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipestarts_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_starts(text, case):
    output = check(text, rows_of(case), [1, 7])
    machine = Machine.parse("\n".join(rows_of(case)))
    actual = []
    index = 64
    while output[index] != SETUP_END:
        index += 5
        while output[index] != ROOM_END:
            actual.append(unpack_candidate(output[index])[1])
            index += 1
        index += 1
    assert actual == [row * 16 + col for pipe in machine.pipes for row, col in pipe.cells[:1]]


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_starts(text, case):
    check(text, rows_of(case))
