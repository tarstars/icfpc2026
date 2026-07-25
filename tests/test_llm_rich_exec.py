"""The physical geometry protocol is sufficient for exact LLM execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm import program_grid
from littleman.llm_fuzz import llm_corpus
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_reference
from littleman.llm_rich_exec import parse_rich_stream, run_rich_case
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 50)


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def rich_stream(case):
    rows = rows_of(case)
    ticks = [int(round_["in"][0]) for round_ in case["rounds"][1:]]
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows)), *ticks]
    packed = pack_reference(scan_reference(source))
    rooms = roomfind_reference(packed)
    perimeters = perimeter_reference(rooms)
    starts = pipestarts_reference(perimeters)
    return pipetrace_reference(starts)


def expected_frames(case):
    return [round_["frames"][0] for round_ in case["rounds"]]


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_rich_executor_is_frame_exact(case):
    assert run_rich_case(rich_stream(case)) == expected_frames(case)


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_rich_geometry_matches_parser(case):
    rows = rows_of(case)
    raw, rooms, pipes, tail = parse_rich_stream(rich_stream(case))
    machine = Machine.parse("\n".join(rows))
    assert [room.man_addr for room in rooms] == [
        man.r * 16 + man.c for man in machine.men
    ]
    assert [pipe.cells for pipe in pipes] == [
        [row * 16 + col for row, col in pipe.cells] for pipe in machine.pipes
    ]
    assert tail == [int(round_["in"][0]) for round_ in case["rounds"][1:]]
    assert len(raw) == 256
