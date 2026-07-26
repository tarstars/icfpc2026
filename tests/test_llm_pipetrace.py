"""Physical parity for source-to-destination pipe tracing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import (
    PIPE_END,
    build_pipetrace_rig,
    pipetrace_reference,
)
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
    rooms = roomfind_reference(packed)
    return pipestarts_reference(perimeter_reference(rooms))


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = pipetrace_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipetrace_rig()


def check(text, rows, tail=()):
    stream = stream_of(rows, tail)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    return script.output


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipetrace_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_pipe_cells(text, case):
    output = check(text, rows_of(case), [1, 7])
    actual = []
    index = 64
    while output[index] != SETUP_END:
        index += 5
        while output[index] != -2000:
            index += 1
            cells = []
            while output[index] != PIPE_END:
                cells.append(output[index])
                index += 1
            actual.append(cells)
            index += 1
        index += 1
    machine = Machine.parse("\n".join(rows_of(case)))
    assert actual == [[r * 16 + c for r, c in pipe.cells] for pipe in machine.pipes]


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_cells(text, case):
    check(text, rows_of(case))
