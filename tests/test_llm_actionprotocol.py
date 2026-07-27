"""Composition gates for the physical LLM action-service protocols."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm_actionprotocol import actionprotocol_reference
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_manmap import manmap_reference
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipeaction import pipeaction_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_recordstrip import recordstrip_reference
from littleman.llm_ring_exec import parse_state_stream
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference

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
def test_composed_protocol_is_exact_for_one_tick(case):
    _world, state = fetched_state(case)
    got, _trace = actionprotocol_reference(state)
    assert got == pipeaction_reference(state)


@pytest.mark.parametrize("case", FUZZ[:20], ids=lambda case: case["name"])
def test_composed_protocol_remains_exact_repeatedly(case):
    world, state = fetched_state(case)
    for _ in range(30):
        got, trace = actionprotocol_reference(state)
        expected = pipeaction_reference(state)
        assert got == expected
        assert all(item.pipe_no in (0, 1) for item in trace)
        runtime = recordstrip_reference(manmap_reference(got))
        _raw, rooms, _pipes, _tail = parse_state_stream([*world, *runtime])
        if any(room.on_border(room.addr) for room in rooms if not room.ctrl & 4):
            break
        if all(room.ctrl & 4 for room in rooms):
            break
        state = fetchjoin_reference([*world, *maskmap_reference(runtime)])
