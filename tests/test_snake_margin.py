"""Release gates for the 194-cell state-ring Snake variant."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest
from test_snake import random_game
from test_snake_components import _binding_contract, _normalized_room_bodies
from test_snake_fast import _annotate, maximal_growth_game

from littleman import alexey_pipecheck, server_compat
from littleman.judge import footprint, normalize_case
from littleman.rustexec import CompiledMachine
from littleman.sim import Machine
from littleman.snake_fast import ring_capacity
from littleman.snake_margin import (
    EXPECTED_REPORTED_RING_CELLS,
    EXPECTED_STATE_RING_CELLS,
    ROUTE_ENDPOINTS,
    TARGET_ROUTE_CELLS,
    build_margin_snake,
    state_ring_capacity,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "submissions/snake/snake_03.man"
ARTIFACT = ROOT / "submissions/snake/snake_04.man"
PROBLEM = ROOT / "data/small/problems/snake.json"
PUBLIC_TICKS = [9872, 3996, 17052, 16581, 78693]


def _problem():
    return json.loads(PROBLEM.read_text())


def test_generator_is_deterministic_and_reproduces_artifact():
    text = build_margin_snake()
    assert build_margin_snake() == text == ARTIFACT.read_text()
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "7694030a224b158c9649010dbf87168e730e2a85e00baa05cdb994f97e59304b"
    )


def test_geometry_capacity_and_layout_gates():
    text = ARTIFACT.read_text()
    lines = text.splitlines()
    assert (len(lines), max(map(len, lines))) == (129, 150)
    assert footprint(text) == footprint(BASE.read_text()) == 22_500
    assert ring_capacity(text) == EXPECTED_REPORTED_RING_CELLS == 203
    assert state_ring_capacity(BASE.read_text()) == 198
    assert state_ring_capacity(text) == EXPECTED_STATE_RING_CELLS == 194
    pipe = next(
        pipe
        for pipe in Machine.parse(text).pipes
        if (pipe.cells[0], pipe.cells[-1]) == ROUTE_ENDPOINTS
    )
    assert len(pipe.cells) == TARGET_ROUTE_CELLS == 85
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_components_and_pipe_bindings_are_unchanged():
    candidate = ARTIFACT.read_text()
    baseline = BASE.read_text()
    assert _normalized_room_bodies(candidate) == _normalized_room_bodies(baseline)
    assert _binding_contract(candidate) == _binding_contract(baseline)


def test_all_public_cases_and_exact_tick_reduction():
    compiled = CompiledMachine(ARTIFACT.read_text())
    results = [
        compiled.run_rounds(index, normalize_case(case), max_ticks=3_000_000)
        for index, case in enumerate(_problem()["publicTestData"])
    ]
    assert [result.status for result in results] == ["passed"] * 5
    assert [result.judged_ticks for result in results] == PUBLIC_TICKS
    assert footprint(ARTIFACT.read_text()) * sum(PUBLIC_TICKS) / 5 == 567_873_000


def test_random_games_against_reference_oracle():
    compiled = CompiledMachine(ARTIFACT.read_text())
    rng = random.Random(20260727)
    for index in range(40):
        result = compiled.run_rounds(
            index,
            _annotate(random_game(rng)),
            max_ticks=3_000_000,
        )
        assert result.status == "passed", result


@pytest.mark.parametrize("length", [48, 68])
def test_maximal_growth_retains_the_measured_capacity_margin(length):
    result = CompiledMachine(ARTIFACT.read_text()).run_rounds(
        length,
        _annotate(maximal_growth_game(length)),
        max_ticks=5_000_000,
    )
    assert result.status == "passed", result
