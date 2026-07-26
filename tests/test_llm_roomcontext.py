"""Physical gates for indexed LLM room-context packing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import ROOM_END, perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomcontext import (
    build_roomcontext_rig,
    roomcontext_reference,
)
from littleman.llm_roomfind import SETUP_END, roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def fetched_state(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    stream = statebuild_reference(stream)
    world, state = stream[:64], stream[64:]
    return fetchjoin_reference([*world, *maskmap_reference(state)])


def headers(case):
    tokens = fetched_state(case)
    out = []
    index = 0
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 11])
        index += 11
        while tokens[index] != ROOM_END:
            index += 1
            while tokens[index] >= 0:
                index += 2
            index += 2
            count = tokens[index + 1]
            index += 2 + count + 1
        index += 1
    return out


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = roomcontext_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_roomcontext_rig()


def test_inactive_records_are_fixed_width():
    header = [-1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
    assert roomcontext_reference(header) == [0, 0, 0, 0]


def test_generator_is_deterministic_and_server_safe(text):
    assert build_roomcontext_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_public_and_fuzz_headers(text):
    tokens = [
        item
        for case in [*CASES, *FUZZ]
        for item in headers(case)
    ]
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
