"""Production-simulator regressions for the organizer's ``Y`` instruction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import fastsim
from littleman.judge import judge_problem
from littleman.sim import DOWN, LEFT, RIGHT, UP, Machine, RunResult

ROOT = Path(__file__).resolve().parents[1]


def room(rows: list[str]) -> str:
    width = max(map(len, rows))
    return "\n".join(
        ["+" + "-" * width + "+"]
        + ["|" + row.ljust(width) + "|" for row in rows]
        + ["+" + "-" * width + "+"]
    )


def interior_pos(man) -> tuple[int, int]:
    return man.r - man.room.top - 1, man.c - man.room.left - 1


def live(machine) -> list:
    return [man for man in machine.men if getattr(man, "alive", True)]


def tick(machine, result=None):
    if result is None:
        result = RunResult(status="tick-cap")
    if not hasattr(machine, "_input_queue"):
        machine._input_queue = []
        machine._controller = None
        machine._verdict = None
    result.ticks += 1
    return machine._tick(result), result


def test_split_geometry_registers_next_tick_and_creation_order() -> None:
    machine = Machine.parse(room(["     ", "     ", "@Y   ", "     ", "     "]))
    parent = machine.men[0]
    parent.A, parent.B, parent.BP = 5, 7, 9

    assert tick(machine)[0] is None  # @ moves onto Y
    assert interior_pos(machine.men[0]) == (2, 1)

    assert tick(machine)[0] is None  # Y creates, but children do not move
    assert len(machine.men) == 2
    right, left = machine.men
    assert right.direction == DOWN and left.direction == UP
    assert interior_pos(right) == (3, 1)
    assert interior_pos(left) == (1, 1)
    assert (right.A, right.B, right.BP) == (5, 7, 9)
    assert (left.A, left.B, left.BP) == (5, 7, 9)
    assert machine.graveyard == [parent]
    assert not parent.alive

    assert tick(machine)[0] is None  # children first act on the following tick
    assert interior_pos(right) == (4, 1)
    assert interior_pos(left) == (0, 1)


def test_wall_birth_is_immediate_fatal_without_normal_grace() -> None:
    machine = Machine.parse(room(["@Y "]))

    result = machine.run(max_ticks=3)

    assert result.status == "error"
    assert result.error == "wall"
    assert result.ticks == 2


def test_split_limit_is_fatal_before_birth_conflicts() -> None:
    machine = Machine.parse(room(["   ", "@Y ", "   "]))
    machine.max_live_men = 1

    result = machine.run(max_ticks=3)

    assert result.status == "error"
    assert result.error == "split-limit"
    assert result.ticks == 2


def test_birth_onto_halted_man_kills_both_and_sibling_survives() -> None:
    machine = Machine.parse(
        room(["     ", " @   ", "@Y   ", "     ", "     "])
    )
    standing, parent = machine.men
    standing.halted = True

    assert tick(machine)[0] is None
    assert tick(machine)[0] is None

    survivors = live(machine)
    assert len(survivors) == 1
    assert survivors[0].direction == DOWN
    assert interior_pos(survivors[0]) == (3, 1)
    assert not standing.alive
    assert not machine.men[-1].alive  # the north/left newborn


def test_two_splits_spawning_on_same_cell_annihilate_the_newborns() -> None:
    machine = Machine.parse(room(["  ", "@Y", "  ", "@Y", "  "]))

    assert tick(machine)[0] is None
    assert tick(machine)[0] is None

    assert sorted(interior_pos(man) for man in live(machine)) == [(0, 1), (4, 1)]
    dead_at_middle = [
        man for man in machine.men if not man.alive and interior_pos(man) == (2, 1)
    ]
    assert len(dead_at_middle) == 2


def test_same_cell_same_tick_arrival_removes_both() -> None:
    machine = Machine.parse(room(["@ @"]))
    machine.men[1].direction = LEFT

    assert tick(machine)[0] is None

    assert live(machine) == []
    assert machine._occupied == {}


def test_swap_through_removes_both() -> None:
    machine = Machine.parse(room(["@@"]))
    machine.men[1].direction = LEFT

    assert tick(machine)[0] is None

    assert live(machine) == []
    assert machine._occupied == {}


def test_walking_onto_halted_man_removes_both_and_corpses_do_not_block() -> None:
    machine = Machine.parse(room([" @ @ "]))
    standing, mover = machine.men
    standing.halted = True
    mover.direction = LEFT

    assert tick(machine)[0] is None
    assert tick(machine)[0] is None
    assert live(machine) == []
    assert machine._occupied == {}

    # Reuse the cell immediately: a new live man can occupy a dead man's
    # coordinate because collision deaths are removals, not halted obstacles.
    replacement = type(standing)(standing.r, standing.c, standing.room, direction=RIGHT)
    replacement.alive = True
    machine.men.append(replacement)
    assert (replacement.r, replacement.c) not in machine._occupied


def test_official_split_demo_halts_two_children() -> None:
    demo = """\
+------+
| >  H |
|      |
|@Y    |
|      |
| >  H |
+------+"""
    machine = Machine.parse(demo)

    result = machine.run(max_ticks=20)

    assert result.status == "halted"
    assert result.error is None
    assert sorted((interior_pos(man), man.direction, man.halted) for man in live(machine)) == [
        ((0, 4), RIGHT, True),
        ((4, 4), RIGHT, True),
    ]


def test_default_fastsim_entry_point_falls_back_instead_of_compiling_y_as_bad_op() -> None:
    demo = """\
+------+
| >  H |
|      |
|@Y    |
|      |
| >  H |
+------+"""
    machine = fastsim.Machine.parse(demo)

    assert getattr(type(machine).run, "_y_reference_fallback", False)
    result = machine.run(max_ticks=20)

    assert result.status == "halted"
    assert result.error is None
    assert len(live(machine)) == 2


@pytest.mark.parametrize("fast_enabled", [False, True], ids=["reference", "default"])
def test_reverse_fresh_23_matches_organizer_public_ticks(fast_enabled: bool) -> None:
    source = (
        ROOT / "experiments" / "gpt-reverse-fresh" / "reverse_fresh_23.man"
    ).read_text()
    problem = json.loads(
        (ROOT / "data" / "small" / "problems" / "reverse-a-list.json").read_text()
    )
    saved = fastsim.FASTSIM_ENABLED
    fastsim.FASTSIM_ENABLED = fast_enabled
    try:
        report = judge_problem(source, problem)
    finally:
        fastsim.FASTSIM_ENABLED = saved

    assert report.cases_passed == report.cases_total == 8
    assert report.case_ticks == [175, 94, 152, 238, 138, 154, 280, 420]
    assert sum(report.case_ticks) / len(report.case_ticks) == 206.375
