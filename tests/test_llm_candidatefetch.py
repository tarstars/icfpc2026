"""Physical parity for robust pipe-start candidate comparison."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_candidatefetch import (
    build_candidate_fetch_rig,
    candidate_fetch_reference,
)
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import ROOM_END, perimeter_reference
from littleman.llm_perimeter import pack_candidate
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


def world_candidates(rows):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    packed = pack_reference(scan_reference(source))
    stream = perimeter_reference(roomfind_reference(packed))
    candidates = []
    index = 64
    while stream[index] != SETUP_END:
        index += 5
        while stream[index] != ROOM_END:
            candidates.append(stream[index])
            index += 1
        index += 1
    return packed[:64], candidates


class Script:
    def __init__(self, world, candidates):
        self.input = [*world, *candidates]
        self.expected = candidate_fetch_reference(world, candidates)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_candidate_fetch_rig()


def check(text, rows):
    world, candidates = world_candidates(rows)
    script = Script(world, candidates)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_generator_is_deterministic_and_server_safe(text):
    assert build_candidate_fetch_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_body_comparisons(text):
    rows = rows_of(CASES[1])
    world, _ = world_candidates(rows)
    candidates = [pack_candidate(1, addr) for addr in range(0, 256, 4)]
    candidates += [pack_candidate(6, addr) for addr in range(0, 256, 4)]
    script = Script(world, candidates)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.status == "passed"
    assert script.output == script.expected


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_candidates(text, case):
    check(text, rows_of(case))


@pytest.mark.parametrize("case", FUZZ, ids=lambda case: case["name"])
def test_pipe_fuzz_candidates(text, case):
    check(text, rows_of(case))
