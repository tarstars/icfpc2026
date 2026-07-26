"""Physical gates for one-room indexed decision extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_components import CLASS_RECV, CLASS_SEND
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_indexcopy import indexcopy_reference
from littleman.llm_indexdecision import (
    build_indexdecision_rig,
    indexdecision_reference,
)
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import PIPE_VALUES, statebuild_reference
from littleman.llm_stateindex import INDEX_SPLIT, stateindex_reference
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


def with_sentinel_payload(tokens):
    result = list(tokens)
    split = result.index(INDEX_SPLIT)
    try:
        values = result.index(PIPE_VALUES, split + 1)
    except ValueError:
        return result
    assert result[values + 1] == 0
    result[values + 1] = 3
    result[values + 2 : values + 2] = [-4900, -5100, -1000]
    return result


def with_active_record(tokens, room_no, cls):
    result = list(tokens)
    start = room_no * 12
    if result[start] == -1000:
        raise ValueError("requested room is absent")
    result[start + 10] = cls * 16
    return result


class Script:
    def __init__(self, requests, room_no):
        self.input = [item for request in requests for item in request]
        self.expected = [
            item
            for request in requests
            for item in indexdecision_reference(request, room_no)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.mark.parametrize("room_no", range(3))
def test_physical_public_fuzz_and_payload_sentinels(room_no):
    text = build_indexdecision_rig(room_no)
    assert build_indexdecision_rig(room_no) == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    states = [indexed_state(case) for case in [*CASES, *FUZZ]]
    states.append(
        with_sentinel_payload(next(state for state in states if -3600 in state))
    )
    room_start = room_no * 12
    room_state = next(
        state
        for state in states
        if len(state) > room_start and state[room_start] != -1000
    )
    states.extend(
        (
            with_active_record(room_state, room_no, CLASS_SEND),
            with_active_record(room_state, room_no, CLASS_RECV),
        )
    )
    requests = [indexcopy_reference(state) for state in states]
    script = Script(requests, room_no)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_reference_rejects_disagreeing_copies():
    state = indexed_state(CASES[0])
    request = indexcopy_reference(state)
    request[len(state) + 2] += 1
    with pytest.raises(ValueError, match="copies disagree"):
        indexdecision_reference(request, 0)
