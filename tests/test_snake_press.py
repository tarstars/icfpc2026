"""Gates for the geometry-pressed Snake machine (`snake_01.man`).

The rooms come from `littleman.snake` unchanged; only placement and pipe
routing differ. So the interesting assertions are geometric and binding
level, plus an end-to-end oracle check that the re-route did not change
what the machine computes.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.ir_export import machine_ir
from littleman.judge import footprint, normalize_case
from littleman.snake import simulate
from littleman.snake_press import MIN_RING_CELLS, build_pressed_snake, ring_capacity

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions/snake/snake_01.man"
LIVE = ROOT / "submissions/snake/snake_00.man"
PROBLEM = ROOT / "data/small/problems/snake.json"


def _problem():
    return json.loads(PROBLEM.read_text())


def _binding_signature(text: str) -> dict:
    """Every `s`/`r` cell keyed by (room shape, offset in room), valued by
    the shape-pair of the pipe it binds to.

    Room *indices* and absolute coordinates both change when the layout
    changes, so identity is expressed through shapes: no two rooms in this
    machine share a (kind, height, width), and no two pipes in it share a
    (source shape, dest shape).
    """
    ir = machine_ir(text)
    rooms = ir["rooms"]
    shape = {
        i: (r["kind"], r["bottom"] - r["top"], r["right"] - r["left"])
        for i, r in enumerate(rooms)
    }
    assert len(set(shape.values())) == len(rooms), "room shapes not unique"
    pipe_shape = {
        i: (shape.get(p["source"]), shape.get(p["dest"]))
        for i, p in enumerate(ir["pipes"])
    }
    assert len(set(pipe_shape.values())) == len(ir["pipes"]), "pipes not unique"

    signature = {}
    for cell, entry in ir["resolution"].items():
        row, col = (int(v) for v in cell.split(","))
        owner = next(
            i
            for i, rm in enumerate(rooms)
            if rm["top"] < row < rm["bottom"] and rm["left"] < col < rm["right"]
        )
        offset = (row - rooms[owner]["top"], col - rooms[owner]["left"])
        signature[(shape[owner], offset)] = (entry["op"], pipe_shape[entry["pipe"]])
    return signature


def _annotate(rounds):
    """Attach the oracle's frames to each round, so `judge_case` gates the
    machine round by round instead of only at the end."""
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


def test_generator_is_deterministic_and_reproduces_the_artifact():
    text = build_pressed_snake()
    assert build_pressed_snake() == text
    assert ARTIFACT.read_text() == text


def test_layout_gates():
    text = ARTIFACT.read_text()
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_bounding_box_is_smaller_than_the_live_artifact():
    text = ARTIFACT.read_text()
    rows = text.split("\n")
    cells = [
        (r, c)
        for r, line in enumerate(rows)
        for c, ch in enumerate(line)
        if ch != " "
    ]
    width = max(c for _, c in cells) - min(c for _, c in cells) + 1
    height = max(r for r, _ in cells) - min(r for r, _ in cells) + 1
    assert max(width, height) < 223
    assert footprint(text) < footprint(LIVE.read_text())


def test_ring_capacity_invariant():
    """snake.py: "budget >= 70 cells of pipe"; the mode-9 dead sweep puts
    about 2x60 values in the ring at once, so we demand a lot more."""
    text = ARTIFACT.read_text()
    assert ring_capacity(text) >= MIN_RING_CELLS


def test_every_pipe_binding_matches_the_live_machine():
    """A changed `s`/`r` binding is a silently wrong machine."""
    assert _binding_signature(ARTIFACT.read_text()) == _binding_signature(
        LIVE.read_text()
    )


def test_room_internals_are_byte_identical_to_snake_00():
    """Same multiset of room bodies, in the same shapes."""
    def bodies(text):
        rows = text.split("\n")
        out = []
        from littleman.sim import Machine

        for room in Machine.parse(text).rooms:
            out.append(
                tuple(
                    "".join(
                        (rows[r] + " " * 400)[c]
                        for c in range(room.left, room.right + 1)
                    )
                    for r in range(room.top, room.bottom + 1)
                )
            )
        return sorted(out)

    assert bodies(ARTIFACT.read_text()) == bodies(LIVE.read_text())


@pytest.mark.parametrize("index", range(5))
def test_public_case(index):
    case = _problem()["publicTestData"][index]
    result = server_compat.judge_case(
        ARTIFACT.read_text(), normalize_case(case), max_ticks=3_000_000
    )
    assert result.passed, result


def test_all_public_cases():
    report = server_compat.judge_problem(ARTIFACT.read_text(), _problem())
    assert report.cases_passed == report.cases_total == 5


def test_random_games_against_the_reference_oracle():
    """20 random games, judged frame by frame against `snake.simulate`."""
    from test_snake import random_game

    text = ARTIFACT.read_text()
    rng = random.Random(20260726)
    for _ in range(20):
        rounds = _annotate(random_game(rng))
        result = server_compat.judge_case(text, rounds, max_ticks=3_000_000)
        assert result.passed, (result, rounds)
