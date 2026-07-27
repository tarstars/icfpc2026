"""Independent geometry/binding model for the physical LLM setup path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm import program_grid
from littleman.llm_components import LLMPipeline, pack_room
from littleman.llm_fuzz import llm_corpus
from littleman.llm_geom import discover_geometry, finalize
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_corpus(20260726, 50)


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def raw_and_men(rows):
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    raw = scan_reference(source)[:256]
    men = [addr for addr, token in enumerate(raw) if token == ord("@")]
    return raw, men


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_position_first_geometry_matches_parser(case):
    rows = rows_of(case)
    raw, men = raw_and_men(rows)
    got = discover_geometry(raw, men)
    machine = Machine.parse("\n".join(rows))
    assert got.rooms == tuple(
        (room.top, room.left, room.bottom, room.right) for room in machine.rooms
    )
    room_no = {id(room): index for index, room in enumerate(machine.rooms)}
    assert got.pipes == tuple(
        (
            room_no[id(pipe.source)],
            room_no[id(pipe.dest)],
            tuple(row * 16 + col for row, col in pipe.cells),
        )
        for pipe in machine.pipes
    )


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_finalized_streams_match_component_oracle(case):
    raw, men = raw_and_men(rows_of(case))
    got = finalize(raw, men)
    pipeline = LLMPipeline(trace=True)
    pipeline.run_case(case["rounds"])
    trace = pipeline.traces()
    assert list(got.cells) == trace["cell_final_init"]
    assert list(got.exec_words) == trace["cell_final_exec"]
    assert [len(got.pipe_descs), *got.pipe_descs] == trace["pipes_exec"]
    assert list(got.pipe_cells) == trace["pipe_cells"]
    assert [len(got.men), *got.men] == trace["men_exec"]
    assert [
        len(got.geometry.rooms),
        *(pack_room(*room) for room in got.geometry.rooms),
    ] == trace["rooms"]


def test_wall_classification_is_position_first():
    rows = ["+----+", "|@+-H|", "| |  |", "+----+"]
    raw, men = raw_and_men(rows)
    result = finalize(raw, men)
    interior_plus = 1 * 16 + 2
    border_plus = 0
    assert (result.cells[interior_plus] >> 12) & 1 == 0
    assert (result.cells[border_plus] >> 12) & 1 == 1
