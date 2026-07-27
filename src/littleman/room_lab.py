"""Behavioural contracts for individual rooms — step 1 of docs/MANIFEST.md.

The project's direction is a **library of shape-variant rooms**: optimise a
room's size while preserving its function, emit several versions in
different shapes, and let a program-level packer choose the shapes that
square up the whole machine. Score is ``max(w, h) ** 2 * ticks``, so a
packer holding both a 6x20 and a 10x12 version of one room can square up a
machine even when neither is smaller.

Everything we built before this preserved *structure* — rigid room text,
pipe endpoints, cell positions — and it kept failing, because the language
binds ``r``/``s`` to the **nearest** pipe by distance from the man's own
cell. Connection is positional, so geometry and wiring are entangled and
moving a room's contents silently rewires it. That is exactly how a
geometrically perfect pathfinder fold (box 1873 -> 813, pipe multiset
byte-identical) deadlocked with every man blocked on ``r``.

A **behavioural** contract cuts that knot. This module records, for one
room, every value that crosses its pipe boundary and in what order:

    given this sequence on the incoming pipes, emit that on the outgoing

That trace says nothing about where any cell sits, so below it geometry is
free. A mutation is legal exactly when the replayed trace is identical.

It is recorded from the whole machine running the real public cases rather
than from a synthetic standalone harness, so it is exact by construction —
no need to guess what the surrounding machine would have sent. The obvious
limitation is that a trace is only as complete as the cases that produced
it; a mutation that preserves the trace on the public set can still differ
on a hidden one, which is why `preflight` remains the final authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from . import judge, sim


@dataclass
class RoomContract:
    """What one room does, expressed only at its pipe boundary."""

    room_index: int
    # per case: [(direction, pipe_index, value)] in the order they crossed
    traces: list[list[tuple[str, int, int]]] = field(default_factory=list)

    def digest(self) -> str:
        """Stable identity for this behaviour, for keying a library."""
        payload = repr(self.traces).encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def events(self) -> int:
        return sum(len(t) for t in self.traces)


def record(text: str, cases, room_index: int,
           max_ticks: int = 5_000_000) -> RoomContract:
    """Run `text` on `cases` and record what crosses room `room_index`.

    A value is OUT when it is written into a pipe whose SOURCE is this
    room, and IN when it is taken from a pipe whose DEST is this room.

    Attributing by the pipe's own endpoints rather than by which man acted
    is both simpler and more robust: `Pipe.take` is called from the
    blocking-resolution path (sim.py:571), not from `Machine._execute`, so
    hooking the executor misses every receive. The pipe already knows which
    rooms it joins, and the simulator has already decided which end is
    which.
    """
    contract = RoomContract(room_index=room_index)
    original_put, original_take = sim.Pipe.put, sim.Pipe.take

    for case in cases:
        rounds = judge.normalize_case(case)
        machine = sim.Machine.parse(text)
        index_of = {id(pipe): i for i, pipe in enumerate(machine.pipes)}
        room = machine.rooms[room_index]
        trace: list[tuple[str, int, int]] = []

        def traced_put(self, index, value, _t=trace, _i=index_of, _r=room,
                       _o=original_put):
            if self.source is _r:
                _t.append(("out", _i[id(self)], value))
            return _o(self, index, value)

        def traced_take(self, index, _t=trace, _i=index_of, _r=room,
                        _o=original_take):
            value = _o(self, index)
            if value is not None and self.dest is _r:
                _t.append(("in", _i[id(self)], value))
            return value

        sim.Pipe.put, sim.Pipe.take = traced_put, traced_take
        try:
            machine.run(max_ticks=max_ticks,
                        controller=judge.RoundController(rounds))
        finally:
            sim.Pipe.put, sim.Pipe.take = original_put, original_take
        contract.traces.append(trace)

    return contract


def record_all(text: str, cases, max_ticks: int = 5_000_000
               ) -> dict[int, RoomContract]:
    """One contract per non-I/O room. Input/output/display rooms are the
    machine's boundary with the judge, not components to be reshaped."""
    machine = sim.Machine.parse(text)
    targets = [i for i, room in enumerate(machine.rooms)
               if getattr(room, "kind", "room") == "room"]
    return {i: record(text, cases, i, max_ticks) for i in targets}


def same_behaviour(before: RoomContract, after: RoomContract) -> bool:
    """A mutation is legal exactly when the boundary trace is unchanged."""
    return before.traces == after.traces


def geometry(text: str) -> tuple[int, int]:
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return max((len(line) for line in lines), default=0), len(lines)


def shape_of(text: str, room_index: int) -> tuple[int, int]:
    """Width and height of one room, walls included."""
    machine = sim.Machine.parse(text)
    room = machine.rooms[room_index]
    return room.right - room.left + 1, room.bottom - room.top + 1


# ---------------------------------------------------------------------------
# Room interface metadata
#
# A behavioural trace says what a room DOES. It does not say how a room
# CONNECTS, and without that a room in a component library is unusable --
# you cannot drop a variant in if you do not know which socket must reach
# which pipe.
#
# This matters more here than in an ordinary component system, because the
# language never names a connection. `r`/`R` read from the NEAREST incoming
# pipe and `s`/`S` write to the nearest outgoing one, resolved by Manhattan
# distance from the man's own cell. Connection is POSITIONAL, so every
# reshape re-derives it by accident. Recording it explicitly is what turns
# "hope the geometry still works" into a checkable contract -- and it is the
# failure that deadlocked the pathfinder fold while every structural check
# passed.
# ---------------------------------------------------------------------------

SOCKET_OPS = frozenset("rRsSU")


@dataclass(frozen=True)
class Socket:
    """One I/O instruction and the pipe it must reach.

    `row`/`col` are relative to the room's top-left corner so they stay
    meaningful when the room is moved or reshaped.
    """

    row: int
    col: int
    glyph: str
    direction: str          # 'in' for r/R/U, 'out' for s/S
    pipe: int               # index into Machine.pipes


@dataclass(frozen=True)
class Port:
    """Where a pipe meets this room's wall."""

    side: str               # 'N' | 'S' | 'W' | 'E'
    offset: int             # cells along that side from the room's corner
    direction: str          # 'in' if the pipe ends here, 'out' if it starts
    pipe: int


@dataclass
class RoomInterface:
    """Everything a packer needs to substitute one room variant for another."""

    room_index: int
    width: int              # walls included
    height: int
    ports: list[Port]
    sockets: list[Socket]

    def signature(self) -> tuple:
        """Connection identity, independent of geometry.

        Two variants with the same signature are interchangeable as far as
        wiring is concerned: the same sockets bind to the same pipes, and the
        same pipes attach with the same directions. WHERE they attach is
        deliberately excluded -- that is the freedom a packer needs.
        """
        return (
            tuple(sorted((s.glyph, s.direction, s.pipe) for s in self.sockets)),
            tuple(sorted((p.direction, p.pipe) for p in self.ports)),
        )


def describe(text: str) -> dict[int, RoomInterface]:
    """Interface metadata for every non-I/O room.

    Socket bindings are taken from `sim`'s own `_nearest_incoming` /
    `_nearest_outgoing` via a stand-in man, so this can never drift from the
    rule the simulator actually applies.
    """
    machine = sim.Machine.parse(text)
    index_of = {id(pipe): i for i, pipe in enumerate(machine.pipes)}
    out: dict[int, RoomInterface] = {}

    for room_index, room in enumerate(machine.rooms):
        if getattr(room, "kind", "room") != "room":
            continue

        sockets: list[Socket] = []
        for row in range(room.top + 1, room.bottom):
            for col in range(room.left + 1, room.right):
                glyph = machine.grid[row][col]
                if glyph not in SOCKET_OPS:
                    continue
                probe = sim.Man(r=row, c=col, room=room)
                incoming = glyph in "rRU"
                pipe = (machine._nearest_incoming(probe) if incoming
                        else machine._nearest_outgoing(probe))
                if pipe is None:
                    continue
                sockets.append(Socket(
                    row=row - room.top, col=col - room.left, glyph=glyph,
                    direction="in" if incoming else "out",
                    pipe=index_of[id(pipe)]))

        ports: list[Port] = []
        for pipe in machine.pipes:
            # A pipe's end cell sits OUTSIDE the wall it serves, one cell
            # away -- not on the wall itself. Testing for containment finds
            # nothing, which is how an earlier version reported zero ports
            # for every room while the machine was plainly wired up.
            for cell, direction in ((pipe.cells[0], "out"),
                                    (pipe.cells[-1], "in")):
                r, c = cell
                if room.left <= c <= room.right:
                    if r == room.top - 1:
                        ports.append(Port("N", c - room.left, direction,
                                          index_of[id(pipe)]))
                        continue
                    if r == room.bottom + 1:
                        ports.append(Port("S", c - room.left, direction,
                                          index_of[id(pipe)]))
                        continue
                if room.top <= r <= room.bottom:
                    if c == room.left - 1:
                        ports.append(Port("W", r - room.top, direction,
                                          index_of[id(pipe)]))
                    elif c == room.right + 1:
                        ports.append(Port("E", r - room.top, direction,
                                          index_of[id(pipe)]))

        out[room_index] = RoomInterface(
            room_index=room_index,
            width=room.right - room.left + 1,
            height=room.bottom - room.top + 1,
            ports=ports, sockets=sockets)
    return out


def interface_preserved(before: str, after: str) -> list[str]:
    """Rooms whose CONNECTIONS changed. Empty means safe to substitute.

    Geometry is allowed to change freely; what may not change is which
    socket reaches which pipe. This is the check that would have caught the
    pathfinder fold in milliseconds instead of after a 434 KB artifact and a
    multi-minute judge run.
    """
    old, new = describe(before), describe(after)
    problems: list[str] = []
    if set(old) != set(new):
        problems.append(f"room set changed: {sorted(old)} -> {sorted(new)}")
        return problems
    for index in sorted(old):
        if old[index].signature() != new[index].signature():
            problems.append(f"room {index}: connection signature changed")
    return problems
