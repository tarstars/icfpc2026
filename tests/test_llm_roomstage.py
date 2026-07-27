"""End-to-end reference gates for one indexed LLM room stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_components import CLASS_RECV, CLASS_SEND
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_indexaction import indexed_room_action_reference
from littleman.llm_manmap import manmap_reference
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_recordstrip import recordstrip_reference
from littleman.llm_ring_exec import parse_state_stream
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_roomstage import build_roomstage_rig, roomstage_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import stateindex_reference, stateunindex_reference
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
    return world, fetchjoin_reference([*world, *maskmap_reference(state)])


class Script:
    def __init__(self, requests, room_no):
        self.input = [item for request in requests for item in request]
        self.expected = [
            item for request in requests for item in roomstage_reference(request, room_no)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_stage_matches_frozen_room_action(case):
    _world, state = fetched_state(case)
    indexed = stateindex_reference(state)
    for room_no in range(3):
        expected, _trace = indexed_room_action_reference(indexed, room_no)
        assert roomstage_reference(indexed, room_no) == expected
        indexed = expected


@pytest.mark.parametrize("case", FUZZ[:10], ids=lambda case: case["name"])
def test_stage_matches_over_runtime_actions(case):
    world, state = fetched_state(case)
    for _tick in range(20):
        indexed = stateindex_reference(state)
        for room_no in range(3):
            expected, _trace = indexed_room_action_reference(indexed, room_no)
            got = roomstage_reference(indexed, room_no)
            assert got == expected
            indexed = got
        normalized = stateunindex_reference(indexed)
        runtime = recordstrip_reference(manmap_reference(normalized))
        _raw, rooms, _pipes, _tail = parse_state_stream([*world, *runtime])
        if any(room.on_border(room.addr) for room in rooms if not room.ctrl & 4):
            break
        if all(room.ctrl & 4 for room in rooms):
            break
        state = fetchjoin_reference([*world, *maskmap_reference(runtime)])


@pytest.mark.parametrize("room_no", range(3))
def test_physical_stage_inactive_send_and_receive(room_no):
    text = build_roomstage_rig(room_no)
    assert build_roomstage_rig(room_no) == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    states = [stateindex_reference(fetched_state(case)[1]) for case in [*CASES, *FUZZ]]
    start = room_no * 12
    inactive = next(
        state for state in states if len(state) > start and state[start] != -1000
    )
    requests = [inactive]
    for cls in (CLASS_SEND, CLASS_RECV):
        for state in states:
            start = room_no * 12
            if len(state) <= start or state[start] == -1000:
                continue
            candidate = list(state)
            candidate[start + 10] = cls * 16
            try:
                roomstage_reference(candidate, room_no)
            except ValueError:
                continue
            requests.append(candidate)
            break
    assert len(requests) >= 2
    script = Script(requests, room_no)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
