"""Gates for the lap-reduced Snake machine (`snake_02.man`).

`snake_01` walked the state packet FOUR times round the ring per game
tick; this build does it twice (TICKA merges modes 2+3, DRAW merges 11+12)
without moving a room, so the geometric and binding gates from
`test_snake_press` still apply verbatim and the interesting new gates are
behavioural: the out-of-bounds tick (now detected by TICKB from a -1
coordinate) and ring capacity under maximal growth.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.judge import footprint, normalize_case
from littleman.snake import simulate
from littleman.snake_fast import MIN_RING_CELLS, build_fast_snake, ring_capacity

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions/snake/snake_02.man"
PREV = ROOT / "submissions/snake/snake_01.man"
PROBLEM = ROOT / "data/small/problems/snake.json"

DIRCODE = {(-1, 0): 2, (0, 1): 3, (1, 0): 4, (0, -1): 5}   # (dy, dx) -> code


def _problem():
    return json.loads(PROBLEM.read_text())


def _annotate(rounds):
    """Attach the oracle's frames to each round, so the judge gates round
    by round instead of only at the end."""
    frames = list(simulate(rounds))
    out, over = [], False
    for index, rd in enumerate(rounds):
        values = [int(v) for v in rd["in"]]
        wants = not over and (index == 0 or values[0] in (0, 1))
        got = [frames.pop(0)] if wants and frames else []
        if wants and not got:
            over = True
        out.append({"in": rd["in"], "frames": got})
        if index and values[0] == 0 and not frames:
            over = True
    assert not frames, "oracle produced frames no round claimed"
    return out


def maximal_growth_game(length: int):
    """Adversarial capacity game: a column-major serpentine over the whole
    16x16 board with a fruit dropped on every cell the head is about to
    enter, so the snake eats on every single tick and never stops growing.
    The path never revisits a cell, so the game is loss-free and the body
    reaches exactly ``length``."""
    path = [
        (x, y)
        for x in range(16)
        for y in (range(16) if x % 2 == 0 else range(15, -1, -1))
    ][:length]
    rounds = [{"in": [str(path[0][0]), str(path[0][1])]}]
    facing = 3
    for prev, cur in zip(path, path[1:]):
        code = DIRCODE[(cur[1] - prev[1], cur[0] - prev[0])]
        rounds.append({"in": ["1", str(cur[0]), str(cur[1])]})
        if code != facing:
            rounds.append({"in": [str(code)]})
            facing = code
        rounds.append({"in": ["0"]})
    return rounds


def test_generator_is_deterministic_and_reproduces_the_artifact():
    text = build_fast_snake()
    assert build_fast_snake() == text
    assert ARTIFACT.read_text() == text


def test_layout_gates():
    text = ARTIFACT.read_text()
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_footprint_is_unchanged_and_ring_capacity_holds():
    text = ARTIFACT.read_text()
    assert footprint(text) == footprint(PREV.read_text()) == 23_716
    assert ring_capacity(text) >= MIN_RING_CELLS


@pytest.mark.parametrize("index", range(5))
def test_public_case(index):
    case = _problem()["publicTestData"][index]
    result = server_compat.judge_case(
        ARTIFACT.read_text(), normalize_case(case), max_ticks=3_000_000
    )
    assert result.passed, result


def test_all_public_cases_and_the_tick_win():
    text = ARTIFACT.read_text()
    report = server_compat.judge_problem(text, _problem())
    assert report.cases_passed == report.cases_total == 5
    before = server_compat.judge_problem(PREV.read_text(), _problem())
    assert report.score < before.score / 1.6


def test_random_games_against_the_reference_oracle():
    from test_snake import random_game

    text = ARTIFACT.read_text()
    rng = random.Random(20260726)
    for _ in range(20):
        rounds = _annotate(random_game(rng))
        result = server_compat.judge_case(text, rounds, max_ticks=3_000_000)
        assert result.passed, (result, rounds)


@pytest.mark.parametrize("length", [48, 68])
def test_maximal_growth_does_not_exhaust_the_ring(length):
    """48 is the stated adversarial target; 68 is the empirical ceiling of
    `snake_01` (both builds deadlock at 70), so capacity is unregressed."""
    rounds = maximal_growth_game(length)
    assert sum(row.count("a") for row in simulate(rounds)[-1]) == length
    result = server_compat.judge_case(
        ARTIFACT.read_text(), _annotate(rounds), max_ticks=5_000_000
    )
    assert result.passed, result
