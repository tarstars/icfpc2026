"""Physical parity for all raw-world comparison request kinds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_cmpfetch import (
    KINDS,
    build_compare_fetch_rig,
    compare_fetch_reference,
)
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 20)
ADDRESSES = [0, 1, 3, 15, 16, 17, 63, 64, 127, 128, 254, 255]
REQUESTS = [kind * 256 + addr for kind in range(KINDS) for addr in ADDRESSES]


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def world_of(rows):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    raw = scan_reference(source)
    return pack_reference(raw)[:64]


class Script:
    def __init__(self, world, requests):
        self.input = [*world, *requests]
        self.expected = compare_fetch_reference(world, requests)
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
    return build_compare_fetch_rig()


def check(text, rows, requests=REQUESTS, max_ticks=2_000_000):
    script = Script(world_of(rows), requests)
    result = Machine.parse(text).run(max_ticks=max_ticks, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    return script


def test_generator_is_deterministic_and_server_safe(text):
    assert build_compare_fetch_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_all_comparisons(text, case):
    check(text, rows_of(case))


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_all_comparisons(text, case):
    check(text, rows_of(case))


def test_full_canvas_sweep_and_ring_restoration(text):
    requests = [
        *range(256),
        *(kind * 256 + addr for kind in range(1, KINDS) for addr in ADDRESSES),
    ]
    script = check(text, rows_of(CASES[5]), requests, max_ticks=8_000_000)
    assert script.last_tick < 8_000_000
