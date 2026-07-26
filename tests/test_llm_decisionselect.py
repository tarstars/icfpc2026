"""Physical gates for prepared indexed candidate selection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_decisionselect import (
    build_decisionselect_rig,
    decisionselect_reference,
)
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_indexcopy import indexcopy_reference
from littleman.llm_indexdecision import indexdecision_reference
from littleman.llm_decisionprep import decisionprep_reference
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packedcandidate import (
    missing_pipe_context,
    pack_pipe_context,
    pack_room_context,
)
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipeapply import OP_RECV, OP_SEND
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import stateindex_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASE = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
][0]


def indexed_state():
    source = [int(value) for value in CASE["rounds"][0]["in"]]
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
            item for request in requests for item in decisionselect_reference(request)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_decisionselect_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_decisionselect_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_inactive_send_and_receive(text):
    state = indexed_state()
    inactive = decisionprep_reference(
        indexdecision_reference(indexcopy_reference(state), 0)
    )
    send_context = pack_room_context(OP_SEND, -1, 0, 16, 0, 16, 34)
    send_pipe = pack_pipe_context(-1, 51, 68, 85)
    recv_context = pack_room_context(OP_RECV, -1, 4, 12, 52, 212, 102)
    recv_pipe = pack_pipe_context(-1, 17, 187, 3 * 16 + 4)
    requests = [
        inactive,
        [
            1,
            OP_SEND,
            1,
            -7,
            send_context,
            send_pipe,
            send_context,
            missing_pipe_context(),
            *state,
        ],
        [
            1,
            OP_RECV,
            2,
            99,
            recv_context,
            recv_pipe,
            recv_context,
            missing_pipe_context(),
            *state,
        ],
    ]
    script = Script(requests)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
