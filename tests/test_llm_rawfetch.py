"""Physical parity for random access to the packed raw LLM canvas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import WORDS, pack_reference
from littleman.llm_rawfetch import (
    build_raw_fetch_rig,
    raw_fetch_reference,
    rig_stream,
    unpack_raw_world,
)
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 20)
REQUESTS = [0, 1, 3, 4, 15, 16, 17, 63, 64, 127, 128, 254, 255]
COMPARE_REQUESTS = [256 + addr for addr in REQUESTS]


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def raw_of(rows):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    return scan_reference(source)[:256]


def world_of(rows):
    return pack_reference([*raw_of(rows), -1])[:WORDS]


class Script:
    def __init__(self, stream, expected):
        self.input = list(stream)
        self.expected = expected
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
    return build_raw_fetch_rig()


def check(text, rows, requests=REQUESTS):
    world = world_of(rows)
    expected = raw_fetch_reference(world, requests)
    script = Script(rig_stream(world, requests), expected)
    result = Machine.parse(text).run(max_ticks=500_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == expected
    assert unpack_raw_world(world) == raw_of(rows)
    return script


def test_generator_is_deterministic_and_server_safe(text):
    assert build_raw_fetch_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    machine = Machine.parse(text)
    assert len(machine.rooms) == 4
    assert len(machine.men) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_raw_fetch(text, case):
    check(text, rows_of(case), [*REQUESTS, *COMPARE_REQUESTS])


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_raw_fetch(text, case):
    check(text, rows_of(case))


def test_repeated_and_reverse_requests_restore_ring(text):
    rows = rows_of(CASES[0])
    check(text, rows, [255, 0, 255, 17, 17, 3, 2, 1, 0])


def test_compare_requests_return_zero_only_for_vertical_wall(text):
    rows = rows_of(CASES[0])
    raw = raw_of(rows)
    requests = [256 + addr for addr in range(256)]
    script = check(text, rows, requests)
    assert script.output == [cell - ord("|") for cell in raw]


def test_tick_bound(text):
    script = check(text, rows_of(CASES[-1]), list(range(256)))
    assert script.last_tick < 1_000_000
