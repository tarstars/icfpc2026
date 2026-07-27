"""Parity gates for the normalized-ring LLM runtime architecture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_ring_exec import parse_state_stream, run_ring_case
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 50)


def state_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    source.extend(int(round_["in"][0]) for round_ in case["rounds"][1:])
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return statebuild_reference(stream)


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_ring_runtime_matches_every_frame(case):
    expected = [round_["frames"][0] for round_ in case["rounds"]]
    assert run_ring_case(state_stream(case)) == expected


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_state_parser_preserves_counts_and_tail(case):
    raw, rooms, pipes, tail = parse_state_stream(state_stream(case))
    assert len(raw) == 256
    assert len(rooms) == sum(
        chr(int(value)) == "@" for value in case["rounds"][0]["in"][2:]
    )
    assert sum(len(pipe.cells) for pipe in pipes) <= 20
    assert tail == [int(round_["in"][0]) for round_ in case["rounds"][1:]]
