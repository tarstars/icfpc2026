"""reverse_06: 14x14 double-extraction ring machine for reverse-a-list."""

from __future__ import annotations

import json
import random
from pathlib import Path

from littleman.alexey_reverse6 import build_reverse6
from littleman.judge import judge_case
from littleman.server_compat import find_shared_walls, judge_problem
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
PROBLEM = json.loads((ROOT / "data/small/problems/reverse-a-list.json").read_text())
TEXT = build_reverse6()


def _rounds(lists):
    return [
        {
            "in": [str(len(v))] + [str(x) for x in v],
            "out": [str(x) for x in reversed(v)],
        }
        for v in lists
    ]


def _border(room):
    cells = set()
    for column in range(room.left, room.right + 1):
        cells.add((room.top, column))
        cells.add((room.bottom, column))
    for row in range(room.top, room.bottom + 1):
        cells.add((row, room.left))
        cells.add((row, room.right))
    return cells


def test_submitted_file_matches_generator():
    stored = (ROOT / "submissions/reverse-a-list/reverse_06.man").read_text()
    assert stored == TEXT


def test_geometry():
    machine = Machine.parse(TEXT)
    assert len(machine.pipes) == 4, "a spurious pipe means a bend touched a wall"
    assert all(len(pipe.cells) >= 2 for pipe in machine.pipes), "server rejects 1-cell pipes"
    ring_out = next(p for p in machine.pipes if len(p.cells) > 10)
    assert len(ring_out.cells) >= 15, "pass 1 of n=16 parks head + 14 relays"
    assert not find_shared_walls(TEXT)
    lines = TEXT.split("\n")
    assert max(len(line) for line in lines) == 14
    assert len([line for line in lines if line.strip()]) == 14


def test_one_pipe_touches_the_input_room():
    """The server counts a pipe merely passing an input room's wall."""
    machine = Machine.parse(TEXT)
    for room in machine.rooms:
        if getattr(room, "kind", None) != "input":
            continue
        border = _border(room)
        touching = [
            index
            for index, pipe in enumerate(machine.pipes)
            if any(
                {(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)} & border
                for (r, c) in pipe.cells
            )
        ]
        assert len(touching) == 1, touching


def test_pipe_resolution():
    """Every send lands on the pipe the layout intends."""
    machine = Machine.parse(TEXT)

    class Fake:
        pass

    resolved = {}
    for row, line in enumerate(TEXT.split("\n")):
        for column, char in enumerate(line):
            if char not in "srRUq":
                continue
            room = next(
                (rm for rm in machine.rooms if rm.contains_interior(row, column)), None
            )
            if room is None:
                continue
            fake = Fake()
            fake.r, fake.c, fake.room = row, column, room
            pipe = (
                machine._nearest_outgoing(fake)
                if char == "s"
                else machine._nearest_incoming(fake)
            )
            resolved[(row, column)] = pipe.cells[-1]

    ring_in, output = (0, 8), (10, 11)
    ring_out, input_in = (6, 2), (6, 1)  # both land on the relay's floor
    assert resolved[(5, 7)] == ring_out, "the loop's s must feed the ring"
    for cell in [(4, 10), (5, 12), (7, 11)]:
        assert resolved[cell] == output, f"{cell} must print"
    for cell in [(2, 10), (4, 9), (5, 8), (7, 10)]:
        assert resolved[cell] == ring_in, f"{cell} must read the ring"
    # relay: input sorts first, so `R` drains the input frame before relays
    assert resolved[(3, 1)] == input_in


def test_public_cases():
    report = judge_problem(TEXT, PROBLEM)
    assert report.cases_passed == report.cases_total == 8
    assert report.footprint == 196
    assert report.score < 74_390.0, "must beat reverse_05"


def test_every_length_and_extremes():
    for n in range(1, 17):
        assert judge_case(TEXT, _rounds([list(range(1, n + 1))])).passed
        extreme = [(-1000000 if i % 2 else 1000000) for i in range(n)]
        assert judge_case(TEXT, _rounds([extreme])).passed


def test_multi_round_fuzz():
    random.seed(20260726)
    for _ in range(120):
        lists = [
            [random.randint(-1000000, 1000000) for _ in range(random.randint(1, 16))]
            for _ in range(random.randint(1, 3))
        ]
        result = judge_case(TEXT, _rounds(lists))
        assert result.passed, (lists, result.reason)


def test_round_boundaries():
    """Lengths that exercise every branch back to back (k1 spur, k2 fall)."""
    for lists in [
        [[1], [1], [1]],
        [[1, 2], [3], [4, 5, 6]],
        [list(range(16)), [7], list(range(9))],
        [[0] * 15, [0], [0] * 16],
    ]:
        assert judge_case(TEXT, _rounds(lists)).passed, lists
