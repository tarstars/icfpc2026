"""Machine IR v0: a serialized, execution-ready view of a parsed program.

Tier-1 milestone 1 of `docs/architecture/claude_02_ir_and_engine.md`. The
IR is what search mutates and what a fast executor consumes: rooms, men,
pipes, and — the piece that removes all geometric reasoning from the hot
loop — a precomputed **resolution map** giving, for every pipe instruction
cell, exactly which pipe(s) the engine's own resolver binds it to.

Nearest-pipe selection depends only on geometry, never on run state, so it
is computed once per candidate here (by calling the engine's private
resolvers with a probe, the same technique as
``tests/test_memory_packed.py::test_station_pipe_resolution_is_unambiguous``)
rather than re-derived every tick or — worse — reimplemented from prose.

The IR deliberately stores the original grid rows: v0 has no renderer, so
the grid is both the provenance record and the way back to ``.man`` text.
"""

from __future__ import annotations

import hashlib
import json

from .sim import Machine

IR_VERSION = 1

# instruction cells whose behavior binds to one nearest pipe / a pipe set
NEAREST_OUT = "sq"          # q counts the nearest *incoming* pipe; see below
NEAREST_IN = "rq"
SET_OUT = "S"
SET_IN = "RU"


class _Probe:
    """A stand-in man at a fixed cell, for the engine's resolvers."""

    __slots__ = ("r", "c", "room")

    def __init__(self, r: int, c: int, room):
        self.r, self.c, self.room = r, c, room


def machine_ir(text: str) -> dict:
    """Parse ``text`` and return the serialized machine IR."""
    machine = Machine.parse(text)
    rooms = list(machine.rooms)
    room_index = {id(room): i for i, room in enumerate(rooms)}
    pipes = list(machine.pipes)
    pipe_index = {id(pipe): i for i, pipe in enumerate(pipes)}

    grid_rows = ["".join(row).rstrip() for row in machine.grid]

    resolution: dict[str, dict] = {}
    for room in rooms:
        if room.kind != "room":
            continue
        for r in range(room.top + 1, room.bottom):
            for c in range(room.left + 1, room.right):
                ch = machine.grid[r][c]
                if ch not in "srqRUS":
                    continue
                probe = _Probe(r, c, room)
                entry: dict = {"op": ch}
                if ch in "s":
                    pipe = machine._nearest_outgoing(probe)
                    entry["pipe"] = pipe_index.get(id(pipe))
                elif ch in "rq":
                    pipe = machine._nearest_incoming(probe)
                    entry["pipe"] = pipe_index.get(id(pipe))
                elif ch == "S":
                    entry["pipes"] = sorted(
                        pipe_index[id(p)] for p in machine._outgoing(probe)
                    )
                elif ch in "RU":
                    entry["pipes"] = sorted(
                        pipe_index[id(p)] for p in machine._incoming(probe)
                    )
                resolution[f"{r},{c}"] = entry

    ir = {
        "version": IR_VERSION,
        "grid": grid_rows,
        "rooms": [
            {
                "top": room.top,
                "left": room.left,
                "bottom": room.bottom,
                "right": room.right,
                "kind": room.kind,
            }
            for room in rooms
        ],
        "men": [
            {"r": man.r, "c": man.c, "room": room_index[id(man.room)]}
            for man in machine.men
        ],
        "pipes": [
            {
                "cells": [list(cell) for cell in pipe.cells],
                "source": room_index.get(id(pipe.source)),
                "dest": room_index.get(id(pipe.dest)),
            }
            for pipe in pipes
        ],
        "resolution": resolution,
    }
    ir["sha256"] = ir_hash(ir)
    return ir


def ir_hash(ir: dict) -> str:
    """Content hash of the IR minus its own hash field."""
    body = {k: v for k, v in ir.items() if k != "sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def ir_text(ir: dict) -> str:
    """The ``.man`` text this IR was built from (v0: stored grid)."""
    return "\n".join(ir["grid"]) + "\n"
