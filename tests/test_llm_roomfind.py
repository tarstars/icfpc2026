"""Physical parity for position-first room discovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_roomfind import build_roomfind_rig, roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 30)


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def stream_of(rows, tail=()):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows)), *tail]
    raw_stream = scan_reference(source)
    return pack_reference(raw_stream)


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = roomfind_reference(stream)
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
    return build_roomfind_rig()


def check(text, rows, tail=()):
    stream = stream_of(rows, tail)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=5_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    return script


def test_generator_is_deterministic_and_server_safe(text):
    assert build_roomfind_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    machine = Machine.parse(text)
    assert len(machine.rooms) == 5
    assert len(machine.men) == 3


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_rooms(text, case):
    check(text, rows_of(case), [1, 7])


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_rooms(text, case):
    check(text, rows_of(case))


def test_relays_runtime_tokens(text):
    check(text, rows_of(CASES[0]), [0, 1, -7, 64, 12345])


def test_tick_and_size_bound(text):
    script = check(text, rows_of(CASES[5]))
    assert script.last_tick < 2_000_000
    lines = text.splitlines()
    assert len(lines) < 2_000
    assert max(map(len, lines)) < 300
