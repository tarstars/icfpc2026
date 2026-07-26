"""Physical parity for the mutable-ring LLM state normalizer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import (
    HEAD_BIT,
    build_statebuild_rig,
    statebuild_reference,
)
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def rich_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    source.extend(int(round_["in"][0]) for round_ in case["rounds"][1:])
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    return pipetrace_reference(stream)


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = statebuild_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_statebuild_rig()


def check(text, case):
    stream = rich_stream(case)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=2_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_generator_is_deterministic_and_server_safe(text):
    assert build_statebuild_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_streams(text, case):
    check(text, case)


@pytest.mark.parametrize("case", FUZZ[:10], ids=lambda case: case["name"])
def test_pipe_fuzz_streams(text, case):
    check(text, case)


def test_descending_bits_leave_a_tail_barrier():
    source = rich_stream(CASES[2])
    state = statebuild_reference(source)
    start = next(i for i, value in enumerate(state[64:]) if value > 255) + 64
    first_cell, first_bit = state[start + 1 : start + 3]
    assert 0 <= first_cell < 256
    assert first_bit == HEAD_BIT
