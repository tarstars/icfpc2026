"""Coordinator-contract tests for indexed LLM pipe actions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm_actionprotocol import actionprotocol_reference
from littleman.llm_components import CLASS_SEND
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_indexaction import (
    indexed_action_reference,
    indexed_candidates_reference,
    indexed_room_action_reference,
)
from littleman.llm_manmap import manmap_reference
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipeaction import parse_fetched_state, serialize_fetched_state
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_recordstrip import recordstrip_reference
from littleman.llm_ring_exec import parse_state_stream
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import (
    stateindex_reference,
    stateunindex_reference,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 50)


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


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_indexed_whole_action_matches_interleaved_oracle(case):
    _world, state = fetched_state(case)
    indexed = stateindex_reference(state)
    expected, expected_trace = actionprotocol_reference(state)
    got, got_trace = indexed_action_reference(indexed)
    assert stateunindex_reference(got) == expected
    assert got_trace == expected_trace


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_sequential_room_stages_match_whole_action(case):
    _world, state = fetched_state(case)
    expected, expected_trace = indexed_action_reference(stateindex_reference(state))
    rooms, _pipes = parse_fetched_state(state)
    got = stateindex_reference(state)
    got_trace = []
    for room_no in range(len(rooms)):
        got, item = indexed_room_action_reference(got, room_no)
        if item is not None:
            got_trace.append(item)
    assert got == expected
    assert got_trace == expected_trace


def test_absent_and_non_action_room_are_identity():
    _world, state = fetched_state(CASES[0])
    indexed = stateindex_reference(state)
    assert indexed_candidates_reference(indexed, 99).active is False
    assert indexed_room_action_reference(indexed, 99) == (indexed, None)
    decision = indexed_candidates_reference(indexed, 0)
    assert decision.active is False
    assert indexed_room_action_reference(indexed, 0) == (indexed, None)


def test_missing_second_pipe_is_fixed_ineligible_slot():
    case = next(case for case in CASES if case["name"] == "countdown relay")
    _world, state = fetched_state(case)
    rooms, pipes = parse_fetched_state(state)
    assert len(pipes) == 1
    rooms[pipes[0].source].record = CLASS_SEND * 16
    state = serialize_fetched_state(rooms, pipes)
    indexed = stateindex_reference(state)
    seen = []
    for room_no in range(3):
        decision = indexed_candidates_reference(indexed, room_no)
        if decision.active:
            seen.append(decision)
    assert seen
    assert all(item.targets[1] == 0 for item in seen)
    assert all(item.eligible[1] == 0 for item in seen)


@pytest.mark.parametrize("case", FUZZ[:20], ids=lambda case: case["name"])
def test_decision_slot_matches_action_trace_over_time(case):
    world, state = fetched_state(case)
    for _tick in range(30):
        indexed = stateindex_reference(state)
        decisions = []
        for room_no in range(3):
            decision = indexed_candidates_reference(indexed, room_no)
            if decision.active:
                decisions.append((room_no, decision.selected))
            indexed, _item = indexed_room_action_reference(indexed, room_no)
        expected, trace = actionprotocol_reference(state)
        assert decisions == [(item.room_no, item.pipe_no) for item in trace]
        assert stateunindex_reference(indexed) == expected
        runtime = recordstrip_reference(manmap_reference(expected))
        _raw, rooms, _pipes, _tail = parse_state_stream([*world, *runtime])
        if any(room.on_border(room.addr) for room in rooms if not room.ctrl & 4):
            break
        if all(room.ctrl & 4 for room in rooms):
            break
        state = fetchjoin_reference([*world, *maskmap_reference(runtime)])
