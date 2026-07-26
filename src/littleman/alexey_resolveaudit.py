"""Static check that a geometry change did not move any pipe resolution.

The expensive part of accepting a squeeze or a re-route on a big program is
the judge run -- subset-sum takes a quarter of an hour.  But the only thing a
row/column deletion can break (given the room and pipe counts are unchanged)
is *which pipe an instruction resolves to*, because resolution is Manhattan
distance with a reading-order tie-break.

So compare the resolution maps directly.  Rooms and pipes come out of the
parser in reading order, which a deletion preserves, so room i in one program
is room i in the other and pipe j is pipe j.  For every `s`/`S`/`r`/`R`/`U`/`q`
cell, in each room's own reading order, record the index of the pipe it
resolves to.  Two programs with identical maps behave identically.

    from littleman.alexey_resolveaudit import resolution_map, compare
    ok, diffs = compare(before_text, after_text)

`compare` returns (True, []) when every instruction still talks to the same
pipe.  A difference is reported as
(room_index, cell_index, glyph, pipe_before, pipe_after).
"""

from __future__ import annotations

from .sim import Machine

OPS = "sSrRUq"


class _Fake:
    __slots__ = ("r", "c", "room")


def resolution_map(text: str):
    """[(room_index, cell_index, glyph, pipe_index)] for every pipe op."""
    machine = Machine.parse(text)
    pipe_index = {id(p): i for i, p in enumerate(machine.pipes)}
    grid = machine.grid
    out = []
    for room_index, room in enumerate(machine.rooms):
        cell_index = 0
        for r in range(room.top + 1, room.bottom):
            row = grid[r]
            for c in range(room.left + 1, room.right):
                if c >= len(row):
                    break
                ch = row[c]
                if ch not in OPS:
                    continue
                fake = _Fake()
                fake.r, fake.c, fake.room = r, c, room
                if ch in "sS":
                    pipe = machine._nearest_outgoing(fake)
                else:
                    pipe = machine._nearest_incoming(fake)
                out.append(
                    (room_index, cell_index, ch,
                     pipe_index.get(id(pipe)) if pipe is not None else None)
                )
                cell_index += 1
    return out


def compare(before: str, after: str, limit: int = 20):
    """(ok, diffs). ok is True when every op resolves to the same pipe."""
    a = resolution_map(before)
    b = resolution_map(after)
    if len(a) != len(b):
        return False, [("count", len(a), len(b))]
    diffs = []
    for x, y in zip(a, b):
        if x[3] != y[3] or x[2] != y[2]:
            diffs.append((x[0], x[1], x[2], x[3], y[3]))
            if len(diffs) >= limit:
                break
    return not diffs, diffs


def structure(text: str):
    machine = Machine.parse(text)
    return {
        "rooms": len(machine.rooms),
        "pipes": len(machine.pipes),
        "men": len(machine.men),
        "pipe_lengths": [len(p.cells) for p in machine.pipes],
    }
