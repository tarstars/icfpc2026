"""Acceptance for the LLM raw-cell PACK station."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import (
    CELLS,
    SETUP_END,
    WORDS,
    build_pack_rig,
    pack_reference,
    unpack_words,
)
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 30)


def rows_of(case) -> list[str]:
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def scan_stream(rows: list[str], tail=()) -> list[int]:
    source = [
        len(rows[0]),
        len(rows),
        *(ord(ch) for row in rows for ch in row),
        *tail,
    ]
    return scan_reference(source)


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = pack_reference(stream)
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
    return build_pack_rig()


def check(text, rows, tail=()):
    stream = scan_stream(rows, tail)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=500_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    cells, men = unpack_words(script.output)
    assert cells == stream[:CELLS]
    assert men == [
        addr for addr, token in enumerate(stream[:CELLS]) if token == ord("@")
    ]
    return script


def test_reference_interleaves_all_men_and_relays_signed_tail():
    cells = [32] * CELLS
    cells[0] = cells[17] = cells[255] = ord("@")
    stream = [*cells, -1, 0, -7, 12345]
    output = pack_reference(stream)
    assert [token for token in output if -257 <= token <= -1] == [
        -1,
        -18,
        -256,
        -7,
    ]
    assert output.count(SETUP_END) == 1
    assert unpack_words(output) == (cells, [0, 17, 255])


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pack_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    machine = Machine.parse(text)
    assert len(machine.rooms) == 4
    assert len(machine.men) == 2
    assert min(len(pipe.cells) for pipe in machine.pipes) >= 2


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_programs(text, case):
    check(text, rows_of(case), [1, 7])


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_programs(text, case):
    check(text, rows_of(case))


@pytest.mark.parametrize("size", [(4, 4), (4, 16), (16, 4), (16, 16)])
def test_directed_size_extremes(text, size):
    width, height = size
    rows = [
        "+" + "-" * (width - 2) + "+"
        if y in (0, height - 1)
        else "|" + ("@" if y == 1 else " ") + " " * (width - 3) + "|"
        for y in range(height)
    ]
    check(text, rows)


def test_relays_signed_round_tokens_forever(text):
    check(text, ["+--+", "|@@|", "+--+"], [0, 1, -7, 64, 12345])


def test_pack_tick_and_size_bounds(text):
    script = check(text, rows_of(max(CASES, key=lambda c: len(rows_of(c)))))
    assert script.last_tick < 200_000
    lines = text.splitlines()
    assert len(lines) < 4_000
    assert max(map(len, lines)) < 128
    assert WORDS == 64
