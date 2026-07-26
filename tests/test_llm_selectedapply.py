"""Physical gates for applying one selected indexed pipe record."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_actioncopy import actioncopy_reference
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_indexdecision import _headers_and_pipes
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipeapply import OP_RECV, OP_SEND
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_selectedapply import (
    build_selectedapply_rig,
    selectedapply_reference,
)
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import stateindex_reference
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
    state = fetchjoin_reference([*world, *maskmap_reference(state)])
    return stateindex_reference(state)


class Script:
    def __init__(self, requests):
        self.input = [item for request in requests for item in request]
        self.expected = [
            item for request in requests for item in selectedapply_reference(request)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_selectedapply_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_selectedapply_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_inactive_send_receive_and_second_slot(text):
    states = [indexed_state(case) for case in [*CASES, *FUZZ]]
    no_pipe = next(state for state in states if not _headers_and_pipes(state)[1])
    one_pipe = next(state for state in states if len(_headers_and_pipes(state)[1]) >= 1)
    two_pipe = next(state for state in states if len(_headers_and_pipes(state)[1]) == 2)
    requests = [
        actioncopy_reference([0, 0, 0, 0, 0, *no_pipe]),
        actioncopy_reference([1, OP_SEND, 1, -7, 0, *one_pipe]),
        actioncopy_reference([1, OP_RECV, 2, 99, 0, *one_pipe]),
        actioncopy_reference([1, OP_SEND, 3, 42, 1, *two_pipe]),
    ]
    script = Script(requests)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
