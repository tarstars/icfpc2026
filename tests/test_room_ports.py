"""Port placement metadata: perimeter parametrisation, claim regions, margin."""

from __future__ import annotations

import pathlib

import pytest

from littleman.ir_export import machine_ir
from littleman.room_ports import (
    Op, audit, binds_to, feasible, intervals, margin, perimeter, satisfied,
)
from littleman.sim import Machine

ROOT = pathlib.Path(__file__).resolve().parents[1]
MEMORY = (ROOT / "submissions/memory/memory_04.man").read_text()


def station(machine):
    return max(machine.rooms, key=lambda r: r.bottom - r.top)


def declared_ops(text: str) -> tuple[Machine, object, list[Op]]:
    """Read a built machine's real bindings back out as declarations."""
    machine = Machine.parse(text)
    room = station(machine)
    pipes = dict(enumerate(machine.pipes))
    ops = []
    for key, entry in machine_ir(text)["resolution"].items():
        r, c = map(int, key.split(","))
        if not (room.top < r < room.bottom and room.left < c < room.right):
            continue
        pipe = pipes[entry["pipe"]]
        outgoing = entry["op"] == "s"
        if outgoing:
            name = "ring_out" if pipe.dest.kind == "room" else "output"
        else:
            name = "ring_in" if pipe.source.kind == "room" else "cmd"
        ops.append(Op((r, c), name, outgoing))
    return machine, room, ops


def test_perimeter_is_a_cycle_of_adjacent_cells():
    machine = Machine.parse(MEMORY)
    room = station(machine)
    cells = perimeter(room)
    assert len(cells) == 2 * ((room.right - room.left - 1) + (room.bottom - room.top - 1))
    assert len(set(cells)) == len(cells)
    for r, c in cells:                      # every position touches the border
        assert (room.top - 1 <= r <= room.bottom + 1) and (
            room.left - 1 <= c <= room.right + 1
        )


def test_binds_to_matches_the_engine_on_a_live_machine():
    machine, room, ops = declared_ops(MEMORY)
    report = audit(machine, room, ops)
    assert report["satisfied"], report
    for op in ops:
        group = {
            p: c
            for p, c in report["positions"].items()
            if any(o.port == p and o.outgoing == op.outgoing for o in ops)
        }
        assert binds_to(op.cell, group) == op.port


def test_live_station_has_real_margin_and_measurable_freedom():
    machine, room, ops = declared_ops(MEMORY)
    report = audit(machine, room, ops)
    assert report["margin"] >= 2, "shipped machine should not be one cell from broken"
    assert set(report["freedom"]) == set(report["positions"])
    assert all(runs for runs in report["freedom"].values())


def test_margin_detects_a_deliberately_broken_placement():
    ops = [Op((5, 5), "a", True), Op((5, 20), "b", True)]
    good = {"a": (4, 5), "b": (4, 20)}
    bad = {"a": (4, 20), "b": (4, 5)}     # ports swapped: both ops mis-reach
    assert satisfied(ops, good) and margin(ops, good) > 0
    assert not satisfied(ops, bad) and margin(ops, bad) <= 0


def test_directions_do_not_compete():
    """An `s` never loses to an incoming pipe, however close it sits."""
    ops = [Op((5, 5), "out", True), Op((5, 5), "in", False)]
    assert satisfied(ops, {"out": (9, 9), "in": (4, 5)})


def test_intervals_collapse_runs_and_wrap_the_cycle():
    machine = Machine.parse(MEMORY)
    room = station(machine)
    cells = perimeter(room)
    assert intervals(room, cells[3:8]) == [(3, 7)]
    wrapped = intervals(room, cells[-2:] + cells[:2])
    assert len(wrapped) == 1 and wrapped[0][0] < 0


def test_feasible_excludes_occupied_positions():
    machine, room, ops = declared_ops(MEMORY)
    report = audit(machine, room, ops)
    fixed = {p: c for p, c in report["positions"].items() if p != "cmd"}
    for cell in feasible(room, ops, "cmd", fixed):
        assert cell not in fixed.values()
