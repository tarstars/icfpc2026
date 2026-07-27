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
