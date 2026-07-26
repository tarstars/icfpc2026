"""Physical gates for restoring source-grouped LLM state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_actioncoordinator import actioncoordinator_reference
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import stateindex_reference, stateunindex_reference
from littleman.llm_stateunindex import (
    build_stateunindex_rig,
    stateunindex_pipeline_reference,
)
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def indexed_state(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    stream = statebuild_reference(stream)
    world, state = stream[:64], stream[64:]
    fetched = fetchjoin_reference([*world, *maskmap_reference(state)])
    return stateindex_reference(fetched)


class Script:
    def __init__(self, requests):
        self.input = [item for request in requests for item in request]
        self.expected = [
            item
            for request in requests
            for item in stateunindex_pipeline_reference(request)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_stateunindex_rig()


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_reference_pipeline_is_exact_inverse(case):
    indexed = indexed_state(case)
    assert stateunindex_pipeline_reference(indexed) == stateunindex_reference(indexed)


def test_generator_is_deterministic_and_server_safe(text):
    assert build_stateunindex_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_room_and_pipe_cardinalities(text):
    requests = [indexed_state(CASES[index]) for index in (0, 1, 3, 5)]
    script = Script(requests)
    result = Machine.parse(text).run(max_ticks=10_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_physical_updated_action_state_and_repeated_requests(text):
    requests = [
        actioncoordinator_reference(indexed_state(case))
        for case in [CASES[3], CASES[5], *FUZZ[:4]]
    ]
    script = Script(requests)
    result = Machine.parse(text).run(max_ticks=10_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
