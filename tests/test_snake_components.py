"""Component and end-to-end gates for the compact Snake geometry."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
from test_snake import random_game
from test_snake_fast import _annotate, maximal_growth_game

from littleman import alexey_pipecheck, server_compat
from littleman.ir_export import machine_ir
from littleman.judge import footprint, normalize_case
from littleman.rustexec import CompiledMachine
from littleman.sim import Machine
from littleman.snake_components import (
    EXPECTED_COMPACTION,
    build_component_compact_snake,
    compact_snake,
)
from littleman.snake_fast import MIN_RING_CELLS

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "submissions/snake/snake_02.man"
ARTIFACT = ROOT / "submissions/snake/snake_03.man"
PROBLEM = ROOT / "data/small/problems/snake.json"
PUBLIC_TICKS = [9948, 4032, 17160, 16701, 79305]


def _problem():
    return json.loads(PROBLEM.read_text())


def _normalized_room_bodies(text: str) -> tuple:
    """Room glyph matrices after removing room-local empty rows/columns."""

    grid = text.rstrip("\n").split("\n")
    width = max(map(len, grid))
    grid = [row.ljust(width) for row in grid]
    bodies = []
    for room in Machine.parse(text).rooms:
        cells = [
            list(grid[row][room.left + 1 : room.right])
            for row in range(room.top + 1, room.bottom)
        ]
        active_rows = [row for row in cells if any(ch != " " for ch in row)]
        active_cols = [
            col
            for col in range(len(cells[0]) if cells else 0)
            if any(row[col] != " " for row in cells)
        ]
        body = tuple("".join(row[col] for col in active_cols) for row in active_rows)
        bodies.append((room.kind, body))
    return tuple(bodies)


def _binding_contract(text: str) -> tuple:
    """Reading-order r/s bindings expressed only through room/pipe indices."""

    ir = machine_ir(text)
    rooms = ir["rooms"]
    per_room = [[] for _ in rooms]
    for cell, entry in ir["resolution"].items():
        row, col = (int(value) for value in cell.split(","))
        owner = next(
            index
            for index, room in enumerate(rooms)
            if room["top"] < row < room["bottom"] and room["left"] < col < room["right"]
        )
        pipe = ir["pipes"][entry["pipe"]]
        per_room[owner].append((row, col, entry["op"], pipe["source"], pipe["dest"]))
    return tuple(
        tuple((op, source, dest) for _, _, op, source, dest in sorted(entries))
        for entries in per_room
    )


def test_generator_is_deterministic_and_reproduces_artifact():
    text = build_component_compact_snake()
    assert build_component_compact_snake() == text == ARTIFACT.read_text()
    assert compact_snake(BASE.read_text()) == (text, EXPECTED_COMPACTION)


def test_layout_capacity_and_footprint_gates():
    text = ARTIFACT.read_text()
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    assert EXPECTED_COMPACTION.ring_cells >= MIN_RING_CELLS
    assert footprint(text) == 22_500 < footprint(BASE.read_text()) == 23_716


def test_every_named_room_preserves_its_instruction_component():
    assert _normalized_room_bodies(ARTIFACT.read_text()) == _normalized_room_bodies(
        BASE.read_text()
    )


def test_every_receive_and_send_keeps_the_same_pipe_binding():
    assert _binding_contract(ARTIFACT.read_text()) == _binding_contract(
        BASE.read_text()
    )


def test_all_public_cases_and_exact_tick_improvement():
    compiled = CompiledMachine(ARTIFACT.read_text())
    results = [
        compiled.run_rounds(index, normalize_case(case), max_ticks=3_000_000)
        for index, case in enumerate(_problem()["publicTestData"])
    ]
    assert [result.status for result in results] == ["passed"] * 5
    assert [result.judged_ticks for result in results] == PUBLIC_TICKS
    assert footprint(ARTIFACT.read_text()) * sum(PUBLIC_TICKS) / 5 == 572_157_000


def test_random_games_against_reference_oracle():
    compiled = CompiledMachine(ARTIFACT.read_text())
    rng = random.Random(20260726)
    for index in range(20):
        result = compiled.run_rounds(index, _annotate(random_game(rng)), 3_000_000)
        assert result.status == "passed", result


@pytest.mark.parametrize("length", [48, 68])
def test_maximal_growth_preserves_ring_headroom(length):
    result = CompiledMachine(ARTIFACT.read_text()).run_rounds(
        length,
        _annotate(maximal_growth_game(length)),
        5_000_000,
    )
    assert result.status == "passed", result
