"""Acceptance for the multi-room LLM raw-grid SCAN station."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_scan import CELLS, SETUP_END, build_scan_rig, scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 30)


def rows_of(case) -> list[str]:
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def stream_of(rows: list[str], tail=()) -> list[int]:
    return [
        len(rows[0]),
        len(rows),
        *(ord(ch) for row in rows for ch in row),
        *tail,
    ]


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = scan_reference(stream)
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
    return build_scan_rig()


def check(text, rows, tail=()):
    stream = stream_of(rows, tail)
    script = Script(stream)
    result = Machine.parse(text).run(
        max_ticks=500_000, controller=script
    )
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    return script


def test_reference_preserves_all_man_markers_and_padding():
    rows = ["+----+", "|@  @|", "+----+"]
    output = scan_reference(stream_of(rows, [7]))
    assert output[17] == ord("@")
    assert output[20] == ord("@")
    assert output[6:16] == [32 + 512] * 10
    assert output[-2:] == [SETUP_END, 7]


def test_generator_is_deterministic_and_server_safe(text):
    assert build_scan_rig() == text
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
    rows = ["+--+", "|@@|", "+--+", "    "]
    check(text, rows, [0, 1, -7, 64, 12345])


def test_scan_tick_bound(text):
    script = check(text, rows_of(max(CASES, key=lambda c: len(rows_of(c)))))
    assert script.last_tick < 400_000

