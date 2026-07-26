"""Exact semantic gates for the normalized pipe-action pass."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipeaction import parse_fetched_state
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_ring_exec import RingExecutor, parse_state_stream
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_tick_assemble import full_statecycle_reference

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 50)


def initial_state(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return statebuild_reference(stream)


def snapshot(world, state):
    _raw, rooms, pipes, tail = parse_state_stream([*world, *state])
    assert not tail
    return (
        [(room.ctrl, room.addr, room.B, room.A, room.old) for room in rooms],
        [(pipe.mask, list(pipe.values)) for pipe in pipes],
    )


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_one_tick_matches_complete_ring_executor(case):
    initial = initial_state(case)
    world, state = initial[:64], initial[64:]
    expected = RingExecutor(initial)
    expected.step()
    actual = full_statecycle_reference(world, state)
    assert snapshot(world, actual) == (
        [(room.ctrl, room.addr, room.B, room.A, room.old) for room in expected.rooms],
        [(pipe.mask, list(pipe.values)) for pipe in expected.pipes],
    )


@pytest.mark.parametrize("case", [*CASES, *FUZZ[:20]], ids=lambda case: case["name"])
def test_repeated_ticks_preserve_fifo_mask_invariant(case):
    initial = initial_state(case)
    world, state = initial[:64], initial[64:]
    expected = RingExecutor(initial)
    for _ in range(50):
        if expected.halted():
            break
        expected.step()
        state = full_statecycle_reference(world, state)
        assert snapshot(world, state) == (
            [
                (room.ctrl, room.addr, room.B, room.A, room.old)
                for room in expected.rooms
            ],
            [(pipe.mask, list(pipe.values)) for pipe in expected.pipes],
        )

        fetched = fetchjoin_reference([*world, *state])
        _rooms, pipes = parse_fetched_state(fetched)
        for pipe in pipes:
            assert len(pipe.values) == sum(bool(pipe.mask & bit) for bit in pipe.bits)
