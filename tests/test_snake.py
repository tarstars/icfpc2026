"""Tests for the Snake problem: reference simulator vs. public test data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.snake import DIRS, render, simulate

PROBLEM = Path(__file__).resolve().parents[1] / "data/small/problems/snake.json"


def _problem():
    return json.loads(PROBLEM.read_text())


def _cases():
    return _problem()["publicTestData"]


def _expected_frames(case):
    return [frame for rd in case["rounds"] for frame in rd["frames"]]


@pytest.mark.parametrize("index", range(5))
def test_reference_reproduces_public_frames(index):
    case = _cases()[index]
    assert simulate(case["rounds"]) == _expected_frames(case)


def test_public_data_shape():
    problem = _problem()
    assert problem["slug"] == "snake"
    assert problem["scoring"] == "footprint-tick"
    assert problem["io"]["display"] == {"width": 16, "height": 16}
    assert len(_cases()) == 5


def test_render_colors():
    frame = render([(1, 0), (2, 0)], (5, 5), over=False)
    assert frame[0] == "0aa0000000000000"  # green snake on row 0
    assert frame[1] == "0" * 16
    assert frame[5][5] == "9"  # red fruit
    dead = render([(1, 0)], None, over=True)
    assert dead[0][1] == "9"  # dead snake turns red


def test_direction_codes():
    assert DIRS == {2: (0, -1), 3: (1, 0), 4: (0, 1), 5: (-1, 0)}


def test_loss_frame_shows_pre_tick_body():
    """Case 'game over at the wall': last frame is the unmoved body in red."""
    case = next(c for c in _cases() if c["name"] == "game over at the wall")
    frames = simulate(case["rounds"])
    last, prev = frames[-1], frames[-2]
    assert last != prev
    assert set("".join(last)) <= {"0", "9"}
    # same occupied cells as the previous frame, only recoloured
    assert [
        [ch != "0" for ch in row] for row in last
    ] == [[ch != "0" for ch in row] for row in prev]


def test_tail_vacated_cell_is_legal():
    """A 3-cell snake turning into the cell its tail just left is legal."""
    rounds = [
        {"in": ["1", "1"]},  # head at (1,1) moving right
        {"in": ["1", "2", "1"]},  # fruit at (2,1)
        {"in": ["0"]},  # eat -> body [(1,1),(2,1)]
        {"in": ["1", "3", "1"]},
        {"in": ["0"]},  # eat -> body [(1,1),(2,1),(3,1)]
        {"in": ["4"]},  # down
        {"in": ["0"]},  # head (3,2)
        {"in": ["5"]},  # left
        {"in": ["0"]},  # head (2,2)
        {"in": ["2"]},  # up
        {"in": ["0"]},  # head (2,1): the cell the tail is vacating
    ]
    frames = simulate(rounds)
    assert set("".join(frames[-1])) == {"0", "a"}  # still alive


# --- validated controller building blocks ---------------------------------

from littleman import alexey_pipecheck, server_compat  # noqa: E402
from littleman.sim import Machine  # noqa: E402
from littleman.snake import Box, build_row_pass_rig, cell_code  # noqa: E402


def test_cell_code_is_one_based_and_collision_free():
    codes = {cell_code(x, y) for y in range(16) for x in range(16)}
    assert len(codes) == 256
    assert min(codes) == 1 and max(codes) == 256  # 0 and negatives stay free


def test_box_rejects_conflicting_cells():
    box = Box().put(1, 1, ">rs")
    box.put(1, 1, ">")  # identical overwrite is fine
    with pytest.raises(ValueError):
        box.put(1, 2, "X")


def _run_row_pass(values):
    return Machine.parse(build_row_pass_rig()).run(inputs=list(values), max_ticks=3000)


@pytest.mark.parametrize(
    "values,expected",
    [
        ([0, 5, 7, 8, -1], [0, 5, 7, 8, -1, -3]),  # dr=0: row unchanged
        ([-1, 5, -1], [-1, 4, -1, -3]),  # dr=-1, empty body
        ([1, 14, 200, 1, -1], [1, 15, 200, 1, -1, -3]),  # last legal row
        ([1, 15, 7, -1], [1, 16, -9]),  # row 16: out of bounds
        ([-1, 0, 3, -1], [-1, -1, -9]),  # row -1: out of bounds
    ],
)
def test_row_pass_moves_checks_bounds_and_relays(values, expected):
    result = _run_row_pass(values)
    assert result.error is None
    assert result.output == expected


def test_row_pass_layout_passes_server_gates():
    text = build_row_pass_rig()
    server_compat.validate_layout(text)  # no rooms sharing wall cells
    alexey_pipecheck.check(text)  # no pipe shorter than 2 cells


# --- station-cycle protocol model -----------------------------------------

import random  # noqa: E402

from littleman.snake import DIRS, CycleModel, run_model, simulate  # noqa: E402


@pytest.mark.parametrize("index", range(5))
def test_cycle_model_matches_oracle_on_public_cases(index):
    rounds = _cases()[index]["rounds"]
    assert run_model(rounds) == simulate(rounds)


def random_game(rng):
    """A random legal-per-the-guarantees game (may or may not end in a loss)."""
    rounds = [{"in": [str(rng.randrange(16)), str(rng.randrange(16))]}]
    body = [(int(rounds[0]["in"][0]), int(rounds[0]["in"][1]))]
    direction, fruit, over = 3, None, False
    can_turn = True
    for _ in range(rng.randrange(1, 98)):
        if over or len(rounds) >= 99:
            break
        roll = rng.random()
        if roll < 0.15 and fruit is None:
            empty = [
                (x, y) for y in range(16) for x in range(16) if (x, y) not in body
            ]
            fruit = rng.choice(empty)
            rounds.append({"in": ["1", str(fruit[0]), str(fruit[1])]})
            continue
        if roll < 0.45 and can_turn:
            opposite = {2: 4, 4: 2, 3: 5, 5: 3}
            choices = [c for c in (2, 3, 4, 5) if c not in (direction, opposite[direction])]
            direction = rng.choice(choices)
            rounds.append({"in": [str(direction)]})
            can_turn = False
            continue
        rounds.append({"in": ["0"]})
        can_turn = True
        dx, dy = DIRS[direction]
        hx, hy = body[-1]
        nx, ny = hx + dx, hy + dy
        if not (0 <= nx < 16 and 0 <= ny < 16):
            over = True
        elif fruit is not None and (nx, ny) == fruit:
            body.append((nx, ny))
            fruit = None
        elif (nx, ny) in body[1:]:
            over = True
        else:
            body.pop(0)
            body.append((nx, ny))
    return rounds


def test_cycle_model_matches_oracle_on_random_games():
    rng = random.Random(20260725)
    for _ in range(300):
        rounds = random_game(rng)
        assert run_model(rounds) == simulate(rounds)


def test_cycle_model_packet_shapes():
    """Every packet in a model trace is well-formed for the ring stations."""
    rng = random.Random(7)
    for _ in range(40):
        model = CycleModel(
            [int(v) for rd in random_game(rng) for v in rd["in"]]
        )
        model.run()
        for _, before, after in model.trace:
            for packet in (before, after):
                mode = packet[0]
                assert 1 <= mode <= 12
                if mode in (10, 11):
                    assert packet[-3] == -1  # MARK then two trailers
                    assert 1 <= packet[-2] <= 256 and 0 <= packet[-1] <= 15
                else:
                    assert packet[-1] == -1
                    body = packet[6:-1] if mode not in (4, 5) else []
                    assert all(1 <= b <= 256 for b in body)


# --- littleman stations and the full machine ------------------------------

from pathlib import Path as _Path  # noqa: E402

from littleman import alexey_pipecheck as _pipecheck  # noqa: E402
from littleman import server_compat as _compat  # noqa: E402
from littleman.snake import (  # noqa: E402
    build_draw,
    build_in_rig,
    build_snake,
    build_station_rig,
    build_ticka,
    build_tickb,
    build_tickc,
    encode_token,
    pixel_token,
)

ARTIFACT = _Path(__file__).resolve().parents[1] / "submissions/snake/snake_00.man"


def _echo(station_rows, packet, ticks=30000):
    machine = Machine.parse(build_station_rig(station_rows))
    result = machine.run(inputs=list(packet), max_ticks=ticks)
    assert result.error is None
    return result.output


def test_tickc_acts_and_relays():
    rows = build_tickc()
    assert _echo(rows, [8, 0, 5, 1, 6, 0, 103, 102, 101, -1]) == [
        11, 12, 0, 5, 1, 6, 0, 103, 102, -1, 101, 0]
    for relay in ([1, 0, 5, 1, 6, 0, 103, -1],
                  [10, 1, 0, 5, 1, 6, 88, 103, -1, 88, 9],
                  [12, 0, 5, 1, 6, 0, 103, -1]):
        assert _echo(rows, relay) == relay


def test_ticka_bounds_and_builders():
    rows = build_ticka()
    assert _echo(rows, [5, 8, 4, -1]) == [10, 1, 0, 8, 1, 4, 0, 133, -1, 133, 10]
    assert _echo(rows, [4, 7, 3, 0, 5, 1, 6, 0, 103, -1]) == [
        10, 1, 0, 5, 1, 6, 116, 103, -1, 116, 9]
    legal = [2, 0, 5, 1, 6, 0, 103, -1] + [3, 0, 5, 1, 6, 0, 103, -1]
    assert _echo(rows, legal) == [3, 0, 5, 1, 6, 0, 103, -1] + [
        6, 0, 5, 1, 7, 0, 103, -1]
    dead = [2, -1, 0, 1, 6, 0, 5, -1] + [3, -1, 0, 1, 6, 0, 5, -1]
    assert _echo(rows, dead) == [3, -1, 0, 1, 6, 0, 5, -1] + [
        9, -1, 0, 1, 6, 0, 5, -1]


def test_tickb_scan_verdicts():
    rows = build_tickb()
    for body, verdict_packet in (
        ([87, 86], [8, 0, 5, 1, 7, 0, 88, 87, 86, -1]),  # legal
        ([87, 86, 88], [8, 0, 5, 1, 7, 0, 88, 87, 86, 88, -1]),  # tail hit ok
        ([87, 88, 89], [9, 0, 5, 1, 7, 0, 87, 88, 89, -1]),  # collision
    ):
        seq = [6, 0, 5, 1, 7, 0, *body, -1] + [7, 0, 5, 1, 7, 0, *body, -1]
        assert _echo(rows, seq, 40000) == [7, 0, 5, 1, 7, 0, *body, -1] + verdict_packet
    eat = [6, 0, 5, 1, 7, 88, 87, -1] + [7, 0, 5, 1, 7, 88, 87, -1]
    assert _echo(rows, eat, 40000) == [7, 0, 5, 1, 7, 88, 87, -1] + [
        10, 1, 0, 5, 1, 7, 0, 88, 87, -1, 88, 10]


def test_draw_tokens():
    rows = build_draw()
    out = _echo(rows, [10, 1, 0, 5, 1, 6, 88, 103, -1, 88, 9])
    assert out == [1, 0, 5, 1, 6, 88, 103, -1,
                   encode_token(pixel_token(88, 9)), encode_token(-1)]
    out = _echo(rows, [12, 0, 5, 1, 6, 0, 103, 102, -1])
    assert out == [1, 0, 5, 1, 6, 0, 103, 102, -1,
                   encode_token(pixel_token(103, 10)), encode_token(-1)]


def test_in_station_dispatch():
    text = build_in_rig()

    def run(seq):
        result = Machine.parse(text).run(inputs=seq, max_ticks=80000)
        assert result.error is None
        return result.output

    def word(v):
        return v + 1000

    pro = [5, 8, 4, -1]
    assert run([word(4), word(8)]) == pro
    base = [1, 0, 8, 1, 4, 0, 133, -1]
    assert run([word(4), word(8)] + base + [word(0)]) == pro + [
        2, 0, 8, 1, 4, 0, 133, -1]
    assert run([word(4), word(8)] + base + [word(1), word(3), word(7)]) == pro + [
        4, 7, 3, 0, 8, 1, 4, 0, 133, -1]
    assert run([word(4), word(8)] + base + [word(2)]) == pro + [
        1, -1, 8, 0, 4, 0, 133, -1]


def test_machine_gates_and_artifact():
    text = build_snake()
    _compat.validate_layout(text)
    _pipecheck.check(text)
    assert ARTIFACT.read_text() == text  # generator reproduces the artifact


def test_machine_passes_public_case_fast():
    """One full judged case (the shortest) as a regression smoke test."""
    text = ARTIFACT.read_text()
    problem = _problem()
    case = next(c for c in problem["publicTestData"]
                if c["name"] == "game over at the wall")
    from littleman.judge import normalize_case

    result = _compat.judge_case(text, normalize_case(case), max_ticks=3000000)
    assert result.passed, result


def test_machine_passes_all_public_cases():
    text = ARTIFACT.read_text()
    report = _compat.judge_problem(text, _problem())
    assert report.cases_passed == report.cases_total == 5
