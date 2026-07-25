"""Port placement metadata: the perimeter as a 1-D space, with claim regions.

`s`/`r`/`q` bind to the NEAREST pipe segment by Manhattan distance (ties by
reading order), so where a pipe attaches to a room's perimeter is part of the
room's meaning, not of its packaging. This module makes that explicit:

* the perimeter is parametrised as a cycle of attachment cells;
* each instruction cell is declared to want a named port;
* given the other ports' positions, the FEASIBLE INTERVALS for one port are
  the perimeter positions that make every declared binding come true;
* the MARGIN of a placement is how much slack it has before a binding flips.

Competition is per direction: `s`/`S` compete over outgoing pipes, `r`/`R`/`q`
over incoming ones, so the two sets never interfere.
"""

from __future__ import annotations

from dataclasses import dataclass

Cell = tuple[int, int]


@dataclass(frozen=True)
class Op:
    """One pipe instruction and the port it is declared to talk to."""

    cell: Cell
    port: str
    outgoing: bool          # True for s/S, False for r/R/q


def perimeter(room) -> list[Cell]:
    """Attachment cells just outside the room, in cycle order.

    Order is top (left->right), right (top->bottom), bottom (right->left),
    left (bottom->top). Corners are excluded: legal for rooms, but they make
    poor ports and every shipped machine avoids them.
    """
    top, left, bottom, right = room.top, room.left, room.bottom, room.right
    cells = [(top - 1, c) for c in range(left + 1, right)]
    cells += [(r, right + 1) for r in range(top + 1, bottom)]
    cells += [(bottom + 1, c) for c in range(right - 1, left, -1)]
    cells += [(r, left - 1) for r in range(bottom - 1, top, -1)]
    return cells


def distance(cell: Cell, position: Cell) -> int:
    return abs(cell[0] - position[0]) + abs(cell[1] - position[1])


def binds_to(cell: Cell, positions: dict[str, Cell]) -> str:
    """Which port an instruction at `cell` actually reaches (engine's rule)."""
    return min(
        positions,
        key=lambda port: (distance(cell, positions[port]),) + positions[port],
    )


def satisfied(ops: list[Op], positions: dict[str, Cell]) -> bool:
    """True iff every op reaches the port it was declared to want."""
    for outgoing in (True, False):
        group = {o.port for o in ops if o.outgoing == outgoing}
        here = {p: positions[p] for p in group if p in positions}
        if len(here) < 2:
            continue                      # a lone port cannot be mis-reached
        for op in ops:
            if op.outgoing == outgoing and binds_to(op.cell, here) != op.port:
                return False
    return True


def margin(ops: list[Op], positions: dict[str, Cell]) -> int:
    """Slack before the weakest binding flips; <= 0 means already wrong.

    For each op: (distance to the nearest WRONG port) - (distance to its own).
    """
    worst = None
    for outgoing in (True, False):
        group = {o.port for o in ops if o.outgoing == outgoing}
        here = {p: positions[p] for p in group if p in positions}
        if len(here) < 2:
            continue
        for op in ops:
            if op.outgoing != outgoing:
                continue
            mine = distance(op.cell, here[op.port])
            other = min(
                distance(op.cell, cell)
                for port, cell in here.items()
                if port != op.port
            )
            slack = other - mine
            worst = slack if worst is None else min(worst, slack)
    return 10**9 if worst is None else worst


def feasible(room, ops: list[Op], port: str, fixed: dict[str, Cell]) -> list[Cell]:
    """Perimeter positions for `port` that satisfy every binding, others fixed."""
    out = []
    for candidate in perimeter(room):
        if candidate in fixed.values():
            continue
        trial = dict(fixed)
        trial[port] = candidate
        if satisfied(ops, trial):
            out.append(candidate)
    return out


def intervals(room, cells: list[Cell]) -> list[tuple[int, int]]:
    """Collapse positions into (start, end) index runs on the perimeter cycle."""
    order = {cell: i for i, cell in enumerate(perimeter(room))}
    idx = sorted(order[c] for c in cells)
    runs: list[tuple[int, int]] = []
    for i in idx:
        if runs and i == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], i)
        else:
            runs.append((i, i))
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == len(order) - 1:
        runs[0] = (runs[-1][0] - len(order), runs[0][1])   # wrap the cycle
        runs.pop()
    return runs


def audit(machine, room, ops: list[Op]) -> dict:
    """Measure a BUILT room: actual positions, margin, and each port's freedom."""
    positions: dict[str, Cell] = {}
    for pipe in machine.pipes:
        if pipe.source is room:
            positions.setdefault(_port_of(pipe.cells[0], ops, True), pipe.cells[0])
        if pipe.dest is room:
            positions.setdefault(_port_of(pipe.cells[-1], ops, False), pipe.cells[-1])
    report = {"positions": positions, "margin": margin(ops, positions),
              "satisfied": satisfied(ops, positions), "freedom": {}}
    for port in positions:
        others = {p: c for p, c in positions.items() if p != port}
        report["freedom"][port] = intervals(room, feasible(room, ops, port, others))
    return report


def _port_of(position: Cell, ops: list[Op], outgoing: bool) -> str:
    """Name the port at `position` by whichever declared op is nearest it."""
    same = [o for o in ops if o.outgoing == outgoing]
    return min(same, key=lambda o: distance(o.cell, position)).port
