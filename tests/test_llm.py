"""The LLM reference interpreter must reproduce every public frame exactly.

`little-little-man` asks for a machine that interprets a littleman subset and
renders it. These tests pin the *semantics* -- the part that is easy to get
subtly wrong and expensive to debug inside a littleman machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm import LLM, op_color, program_grid

PROBLEM = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "data/small/problems/little-little-man.json"
    ).read_text()
)
CASES = PROBLEM["publicTestData"]


def replay(case) -> list[tuple[int, list[str], list[str]]]:
    """Run one case, returning (round index, produced frame, expected frame)."""
    rounds = case["rounds"]
    machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
    out = [(0, machine.render(), rounds[0]["frames"][0])]
    for index, rnd in enumerate(rounds[1:], 1):
        machine.run(int(rnd["in"][0]))
        out.append((index, machine.render(), rnd["frames"][0]))
    return out


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_every_frame_matches(case):
    for index, got, expected in replay(case):
        assert got == expected, f"round {index}"


def test_all_public_programs_parse():
    for case in CASES:
        rows = program_grid([int(v) for v in case["rounds"][0]["in"]])
        machine = LLM.parse(rows)
        assert machine.men, case["name"]
        assert len(machine.rooms) == len(machine.men) <= 3
        assert len(machine.pipes) <= 2
        assert sum(len(p.cells) for p in machine.pipes) <= 20


def test_frames_are_16x16_hex():
    for _, got, _ in replay(CASES[0]):
        assert len(got) == 16
        assert all(len(row) == 16 for row in got)
        assert all(ch in "0123456789abcdef" for row in got for ch in row)


def test_start_cell_of_a_man_renders_as_space_once_he_leaves():
    """`@` is a start marker, not an instruction: it must not stay coloured."""
    case = next(c for c in CASES if c["name"] == "first steps")
    rows = program_grid([int(v) for v in case["rounds"][0]["in"]])
    machine = LLM.parse(rows)
    start = (machine.men[0].r, machine.men[0].c)
    machine.run(1)
    assert (machine.men[0].r, machine.men[0].c) != start
    assert machine.render()[start[0]][start[1]] == "0"


def test_wall_freezes_the_whole_program_with_the_man_drawn_on_the_wall():
    """A wall is not an error here; it stops everything and the man shows."""
    frozen = []
    for case in CASES:
        rows = program_grid([int(v) for v in case["rounds"][0]["in"]])
        machine = LLM.parse(rows)
        machine.run(200)
        if any(man.on_wall for man in machine.men):
            frozen.append(case["name"])
            man = next(m for m in machine.men if m.on_wall)
            assert machine.halted()
            assert machine.render()[man.r][man.c] == "9"
    assert frozen, "expected at least one public case to end on a wall"


def test_op_colours_match_the_specified_palette():
    assert op_color("^") == op_color("H") == op_color("X") == 3
    assert op_color("7") == 8
    assert op_color("M") == 12
    assert op_color("+") == op_color("-") == 10
    assert op_color("s") == op_color("r") == 13
    assert op_color(" ") == 0


def test_pipe_values_are_animated_cell_by_cell():
    """A pipe cell holding a value renders 14, an empty one 6."""
    seen_full = False
    for case in CASES:
        rows = program_grid([int(v) for v in case["rounds"][0]["in"]])
        machine = LLM.parse(rows)
        if not machine.pipes:
            continue
        for _ in range(60):
            machine.step()
            frame = machine.render()
            for pipe in machine.pipes:
                for i, (r, c) in enumerate(pipe.cells):
                    if r < 16 and c < 16 and not any(
                        (m.r, m.c) == (r, c) for m in machine.men
                    ):
                        expected = "e" if pipe.values[i] is not None else "6"
                        assert frame[r][c] == expected
                        seen_full |= expected == "e"
    assert seen_full, "expected to observe at least one value in flight"
