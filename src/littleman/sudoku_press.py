"""Sudoku Auditor, geometry-pressed: the *same* rooms as ``sudoku_02.man``,
re-placed so the bounding box is near-square instead of a tall column.

``sudoku_02.man`` is live at 25,480,732,026.  It stacks parser, broadcaster,
the row/column worker band and the box worker band in one column, so its box
is 184x248 and its footprint is ``max(184, 248)**2 = 61,504`` -- paid for
entirely by the height, while the width is pinned at 184 by the broadcaster
room (``build_broadcaster(184)``, whose *internals* depend on its width and
therefore may not be re-cut).

This module never re-derives a room.  It PARSES the live artifact and lifts
each room -- and, for the three workers, the whole rigid "worker + four
relays + eight ring pipes" group -- out of the grid as a byte-exact stamp.
The stamps are then re-placed in two columns:

    cols 0..1    command lanes down to the two left-column workers
    cols 2..91   column worker (top) over row worker (bottom)
    cols 92..93  result / command lanes
    cols 94..197 box worker, aggregator, parser, input, output

WHAT MAY MOVE AND WHAT MAY NOT
------------------------------
Every worker ``s``/``r`` binds to the NEAREST pipe end, and each worker has
five of each (four ring ports plus command-in / result-out).  So all ten
endpoints keep their exact offsets relative to the worker's top-left corner:

    row     command-in (bottom+1, left+10)   result-out (bottom+1, left+73)
    column  command-in (bottom+1, left+13)   result-out (bottom+1, left+83)
    box     command-in (bottom+1, left+13)   result-out (bottom+1, left+88)

The eight ring endpoints per worker come along for free: the ring pipes are
copied cell-for-cell with the worker, so both their positions and their
LENGTHS (i.e. their FIFO capacities) are identical to sudoku_02's.

The ring cells of every worker live strictly between the command column and
the result column (``left+14..left+70``, ``left+20..left+81``,
``left+20..left+85``), which is why a command pipe may rise to its port
through the ring band and a result pipe may fall through it.

``q``/``U`` appear nowhere.  ``R`` and ``S`` appear only in the broadcaster
(``R`` over its single inbound pipe, ``S`` over all three command pipes) and
``R`` in the aggregator (over all three result pipes); both are SET
operations, so their bindings do not depend on geometry at all.  ``R`` does
pick the ready pipe with the lowest end cell, which would matter if two
workers' flags could ever be in flight for different rounds -- they cannot:
:class:`littleman.judge.RoundController` releases round *n+1*'s input only
after round *n*'s verdict, so the aggregator's three ``R`` reads always see
exactly one pending flag per worker.  Route lengths are therefore free.
"""

from __future__ import annotations

from pathlib import Path

from .canvas import Canvas
from .sim import Machine

LIVE = (
    Path(__file__).resolve().parents[2]
    / "submissions"
    / "sudoku-validity"
    / "sudoku_02.man"
)

# (height, width) of every room in sudoku_02, used to identify them.
SHAPES = {
    "parser": (14, 19),
    "broadcaster": (5, 184),
    "row": (82, 87),
    "column": (82, 90),
    "box": (96, 104),
    "aggregator": (18, 40),
}

# port offsets from each worker's top-left corner: (row - bottom, col - left)
WORKER_PORTS = {
    "row": {"command": (1, 10), "result": (1, 73)},
    "column": {"command": (1, 13), "result": (1, 83)},
    "box": {"command": (1, 13), "result": (1, 88)},
}

Stamp = dict[tuple[int, int], str]


def _room_shape(room) -> tuple[int, int]:
    return (room.bottom - room.top + 1, room.right - room.left + 1)


def parse_live() -> tuple[Machine, dict]:
    """Parse sudoku_02.man and name every room by its (unique) shape."""
    machine = Machine.parse(LIVE.read_text())
    named: dict[str, object] = {}
    relays = []
    for room in machine.rooms:
        if room.kind in ("input", "output"):
            named[room.kind] = room
            continue
        shape = _room_shape(room)
        for name, want in SHAPES.items():
            if shape == want:
                assert name not in named, f"ambiguous room {name}"
                named[name] = room
                break
        else:
            assert shape == (5, 5), f"unexpected room {shape}"
            relays.append(room)
    assert len(relays) == 12, len(relays)
    assert set(named) == set(SHAPES) | {"input", "output"}, sorted(named)
    return machine, named


def _stamp_of(machine: Machine, room) -> Stamp:
    grid = machine.grid
    return {
        (r - room.top, c - room.left): grid[r][c]
        for r in range(room.top, room.bottom + 1)
        for c in range(room.left, room.right + 1)
    }


def worker_stamp(machine: Machine, worker) -> Stamp:
    """Worker + its four relays + its eight ring pipes, as one rigid stamp.

    Keyed by offset from the worker room's top-left corner.  The command-in
    and result-out pipes are deliberately NOT included: they leave the group
    and are re-routed, landing on the same offsets (:data:`WORKER_PORTS`).
    """
    ring = [
        pipe
        for pipe in machine.pipes
        if (pipe.source is worker and _room_shape(pipe.dest) == (5, 5))
        or (pipe.dest is worker and _room_shape(pipe.source) == (5, 5))
    ]
    assert len(ring) == 8, len(ring)
    stamp = _stamp_of(machine, worker)
    for pipe in ring:
        relay = pipe.dest if pipe.source is worker else pipe.source
        stamp.update(
            {(k[0] + relay.top - worker.top, k[1] + relay.left - worker.left): v
             for k, v in _stamp_of(machine, relay).items()}
        )
        for r, c in pipe.cells:
            stamp[(r - worker.top, c - worker.left)] = machine.grid[r][c]
    return stamp


def ring_lengths(machine: Machine, worker) -> list[int]:
    """Lengths of the eight ring pipes, in reading order of their first cell.

    Ring capacity is what keeps the nine-mask FIFO from deadlocking; the
    stamp copies these pipes verbatim, and :func:`build_pressed_sudoku`
    asserts the rebuilt machine reproduces this list exactly.
    """
    out = []
    for pipe in machine.pipes:
        if (pipe.source is worker and _room_shape(pipe.dest) == (5, 5)) or (
            pipe.dest is worker and _room_shape(pipe.source) == (5, 5)
        ):
            out.append((pipe.cells[0], len(pipe.cells)))
    return [n for _, n in sorted(out)]


def _put(canvas: Canvas, top: int, left: int, stamp: Stamp) -> None:
    for (dr, dc), ch in stamp.items():
        assert (top + dr, left + dc) not in canvas.cells, (top + dr, left + dc)
        canvas.cells[(top + dr, left + dc)] = ch


# --- placement -------------------------------------------------------------
# Top-left corner of every room.  Worker entries are the WORKER ROOM's corner;
# its relays and ring pipes ride along in the stamp, which extends 8 rows
# below the room (the ring band).
PLACE = {
    "broadcaster": (0, 0),      # rows 0..4,     cols 0..183
    "input": (8, 170),          # rows 8..10,    cols 170..172
    "parser": (8, 176),         # rows 8..21,    cols 176..194
    "column": (8, 2),           # rows 8..89,    cols 2..91  (band to row 97)
    "box": (25, 94),            # rows 25..120,  cols 94..197 (band to 128)
    "row": (102, 2),            # rows 102..183, cols 2..88  (band to 191)
    "aggregator": (160, 94),    # rows 160..177, cols 94..133
    "output": (182, 140),       # rows 182..184, cols 140..142
}

# Lane assignment, by column:
#   0  broadcaster -> row worker command      (turns right at row 185)
#   1  broadcaster -> column worker command   (turns right at row 91)
#   92 column worker result -> aggregator
#   93 broadcaster -> box worker command
# The command that turns at the LOWER row runs in the OUTER lane, so the two
# never cross.  Both approach their port from directly below, rising through
# the ring band in the clear column left of every ring cell.
ROUTES = [
    ("in->parser", [(9, 173), (9, 175)]),
    ("parser->bcast", [(7, 188), (2, 188), (2, 184)]),
    ("bcast->column", [(5, 4), (7, 4), (7, 1), (91, 1), (91, 15), (90, 15)]),
    ("bcast->row", [(5, 2), (6, 2), (6, 0), (185, 0), (185, 12), (184, 12)]),
    ("bcast->box", [(5, 93), (122, 93), (122, 107), (121, 107)]),
    ("column->agg", [(90, 85), (99, 85), (99, 92), (168, 92), (168, 93)]),
    ("row->agg", [(184, 75), (193, 75), (193, 115), (178, 115)]),
    ("box->agg", [(121, 182), (158, 182), (158, 115), (159, 115)]),
    ("agg->out", [(178, 125), (180, 125), (180, 141), (181, 141)]),
]

MIN_COMMAND_CELLS = 8


def _expected_ports() -> dict[str, tuple[int, int]]:
    """Absolute cells the command-in / result-out pipe ends must occupy."""
    want = {}
    for name, ports in WORKER_PORTS.items():
        top, left = PLACE[name]
        height = SHAPES[name][0]
        for port, (dr, dc) in ports.items():
            want[f"{name}.{port}"] = (top + height - 1 + dr, left + dc)
    return want


def build_pressed_sudoku() -> str:
    """The pressed Sudoku machine.  Deterministic: no randomness anywhere."""
    machine, named = parse_live()
    canvas = Canvas()
    for name, (top, left) in PLACE.items():
        room = named[name]
        stamp = (
            worker_stamp(machine, room)
            if name in WORKER_PORTS
            else _stamp_of(machine, room)
        )
        _put(canvas, top, left, stamp)

    for label, waypoints in ROUTES:
        scratch = Canvas()
        scratch.pipe(waypoints)
        clash = set(scratch.cells) & set(canvas.cells)
        assert not clash, f"{label} collides at {sorted(clash)[:4]}"
        canvas.cells.update(scratch.cells)

    text = canvas.render()
    _check(text, machine, named)
    return text


def _check(text: str, live: Machine, live_named: dict) -> None:
    """Structural gates: room census, ring capacity, port offsets, size."""
    built = Machine.parse(text)
    built_named: dict[str, object] = {}
    relays = 0
    for room in built.rooms:
        if room.kind in ("input", "output"):
            built_named[room.kind] = room
            continue
        shape = _room_shape(room)
        if shape == (5, 5):
            relays += 1
            continue
        name = next(n for n, want in SHAPES.items() if want == shape)
        assert name not in built_named, f"duplicate {name}"
        built_named[name] = room
    assert relays == 12, relays
    assert len(built.rooms) == len(live.rooms), (
        len(built.rooms), len(live.rooms))
    assert len(built.pipes) == len(live.pipes), (
        len(built.pipes), len(live.pipes))

    for name, (top, left) in PLACE.items():
        room = built_named[name]
        assert (room.top, room.left) == (top, left), (name, room.top, room.left)

    # Ring FIFO capacity: byte-identical pipes, hence identical cell counts.
    for name in WORKER_PORTS:
        assert ring_lengths(built, built_named[name]) == ring_lengths(
            live, live_named[name]
        ), name

    # Every command-in / result-out pipe end sits on its declared offset, so
    # each worker's five `s` and five `r` bind exactly as in sudoku_02.
    want = _expected_ports()
    seen: dict[str, tuple[int, int]] = {}
    for pipe in built.pipes:
        for room, cell, port in (
            (pipe.dest, pipe.cells[-1], "command"),
            (pipe.source, pipe.cells[0], "result"),
        ):
            for name in WORKER_PORTS:
                if room is built_named[name] and _room_shape(
                    pipe.source if port == "command" else pipe.dest
                ) != (5, 5):
                    seen[f"{name}.{port}"] = cell
    assert seen == want, sorted(set(seen.items()) ^ set(want.items()))

    for label, waypoints in ROUTES:
        if label.startswith("bcast->"):
            scratch = Canvas()
            scratch.pipe(waypoints)
            assert len(scratch.cells) >= MIN_COMMAND_CELLS, (label, scratch)

    lines = text.rstrip("\n").split("\n")
    height, width = len(lines), max(len(line) for line in lines)
    assert max(height, width) < 248, (height, width)
