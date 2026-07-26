"""Physical parity for classified raw-world op fetch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_opfetch import build_opfetch_rig, opfetch_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)
REQUESTS = list(range(256))


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def world_of(rows):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    return pack_reference(scan_reference(source))[:64]


class Script:
    def __init__(self, world):
        self.input = [*world, *REQUESTS]
        self.expected = opfetch_reference(world, REQUESTS)
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
    return build_opfetch_rig()


def check(text, rows):
    world = world_of(rows)
    script = Script(world)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    return script


def test_generator_is_deterministic_and_server_safe(text):
    assert build_opfetch_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_all_addresses(text, case):
    check(text, rows_of(case))


@pytest.mark.parametrize("case", FUZZ[:5], ids=lambda case: case["name"])
def test_pipe_fuzz_all_addresses(text, case):
    check(text, rows_of(case))
