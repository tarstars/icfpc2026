"""Plotter, geometry-pressed: the *same* rooms as ``plotter_04.man``,
re-placed so the bounding box is near-square instead of a tall column.

``plotter_04`` is live at 9,367,793,668.  It is 113 wide x 326 tall, so its
footprint -- ``max(113, 326)**2 = 106,276`` -- is paid for entirely by the
height.  Nothing about the *rooms* is wrong; only the placement is.

WHY IT IS 326 TALL
------------------
Five of its eighteen pipes are so short that they weld their two rooms into
one rigid vertical stack::

    ETEST --3--> EUPD --4--> ADDRESS --7--> ROUTER --4--> PLOT --3--> DISPLAY

87 + 3 + 91 + 4 + 76 + ... rows of rooms, one on top of the other.  Any press
must break exactly one of those welds, and it must break the cheapest one.

WHAT THIS MODULE MOVES
----------------------
Four rigid BLOCKS are lifted verbatim out of ``plotter_04.man`` -- as
character rectangles, so every room interior *and* every pipe inside a block
is byte-identical, glyph for glyph:

===========  =====================================  ==============
block        contents                               size
===========  =====================================  ==============
``etest``    the error-test room                    87 x 36
``eupd``     the error-update room                  91 x 37
``setup``    I + the five setup rooms + 5 pipes     59 x 34
``group``    ADDRESS, RELAY, ROUTER, PLOT, SWAP,
             DISPLAY + the nine pipes among them    141 x 113
===========  =====================================  ==============

``group`` is kept whole on purpose: it carries the entire LM-75 display path
(PLOT --19--> DISPLAY address, PLOT --3--> DISPLAY data, SWAP --56-->
DISPLAY, ROUTER --49--> SWAP), so every driver lap length and every ADDR /
DATA / SWAP timing relationship survives untouched by construction.

Only five pipes are re-drawn, and four of them keep their plotter_04 length
to the cell:

    ETEST -> EUPD   3, 3    (two pipes; ETEST stays directly above EUPD)
    SETUP -> ETEST  111     (re-routed the long way round, same length)
    EUPD  -> ETEST  233     (the ring return, same length)
    EUPD  -> ADDRESS  4 -> 335   <-- the one weld that is broken

Keeping the 233-cell ring return at its exact length is not politeness: a
probe that lengthened it by 20 cells cost 620 extra ticks on the main
diagonal, i.e. the Bresenham ring is traversed once per plotted pixel and
its length is paid 32 times over.  The 233 cells are also the geometric
minimum for this box -- ETEST sends from its bottom wall and receives on its
top wall, so the return must climb the whole 181-row ETEST+EUPD stack -- and
that stack is likewise what fixes the pressed height at 185.

The broken weld is the cheap one by the same measurement: its extra 331
cells are paid once per *segment*, not once per pixel (+341 ticks on the
one-pixel case, the same +341 per extra segment elsewhere).

EUPD -> ADDRESS is the safe weld to break.  ADDRESS never answers EUPD: the
only pipes leaving ADDRESS go to the RELAY (its own ring) and to the ROUTER
(the display path).  The link is therefore a pure feed-forward pipeline, and
lengthening it adds start-up latency per segment, not a cost per Bresenham
step, and it cannot open a race because nothing races with it.

Every port keeps its OFFSET from its room's top-left corner, so every
``s``/``r`` sees exactly the distances it saw in plotter_04 and binds to
exactly the same pipe.  :func:`resolution_by_offset` re-derives the engine's
own binding for all 181 instruction cells and the tests diff it against
plotter_04's: 0 differences, and :func:`port_margins` is unchanged too.

    plotter_04   113 x 326   fp 106,276   avgTicks 60,293.8   6,407,787,431
    plotter_05   175 x 185   fp  34,225   avgTicks 61,452.3   2,103,206,108
"""

from __future__ import annotations

import pathlib

from .canvas import Canvas

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE = REPO / "submissions" / "plotter" / "plotter_04.man"

# (top, left, bottom, right) rectangles in plotter_04.man.  Verified pure:
# every non-space cell inside belongs to the block's own rooms and pipes.
BLOCKS = {
    "etest": (3, 7, 89, 42),
    "eupd": (93, 7, 183, 43),
    "setup": (3, 59, 61, 92),
    "group": (185, 0, 325, 112),
}

# Where each block's top-left corner goes on the pressed canvas.
PLACE = {
    "group": (2, 21),      # rows 2..142,   cols 21..133
    "setup": (3, 100),     # rows 3..61,    cols 100..133 (group's empty band)
    "etest": (2, 137),     # rows 2..88,    cols 137..172
    "eupd": (92, 137),     # rows 92..182,  cols 137..173
}

# The five re-drawn pipes, as Canvas waypoints, with their required lengths.
# A pipe's first cell must point away from its source wall and its last cell
# into its destination wall, so every route starts and ends perpendicular.
ROUTES = [
    ([(89, 155), (91, 155)], 3),                                # ETEST->EUPD
    ([(89, 160), (91, 160)], 3),                                # ETEST->EUPD
    ([(62, 102), (63, 102), (63, 135), (0, 135), (0, 147),
      (1, 147)], 111),                                          # SETUP->ETEST
    ([(183, 151), (184, 151), (184, 174), (0, 174), (0, 151),
      (1, 151)], 233),                                          # EUPD->ETEST
    ([(183, 147), (184, 147), (184, 20), (0, 20), (0, 38),
      (4, 38)], 335),                                           # EUPD->ADDRESS
]

# The single deliberate length change: EUPD -> ADDRESS.
BROKEN_WELD = (4, 335)


def path_length(waypoints: list[tuple[int, int]]) -> int:
    """Number of cells a Canvas pipe through these waypoints will occupy."""
    total = 1
    for a, b in zip(waypoints, waypoints[1:]):
        total += abs(b[0] - a[0]) + abs(b[1] - a[1])
    return total


def source_cells() -> dict[tuple[int, int], str]:
    """plotter_04.man as a sparse cell map.  Read-only; never rewritten."""
    text = SOURCE.read_text()
    return {
        (r, c): ch
        for r, line in enumerate(text.rstrip("\n").split("\n"))
        for c, ch in enumerate(line)
        if ch != " "
    }


def external_cells() -> set[tuple[int, int]]:
    """Cells of the five pipes that join two different blocks.

    Those pipes are the only ones re-drawn, so their glyphs are stripped out
    of every block rectangle before it is stamped onto the new canvas.
    """
    from .sim import Machine

    machine = Machine.parse(SOURCE.read_text())

    def block_of(room):
        for name, (top, left, bottom, right) in BLOCKS.items():
            if top <= room.top <= bottom and left <= room.left <= right:
                return name
        raise AssertionError(f"room at {(room.top, room.left)} is in no block")

    cells: set[tuple[int, int]] = set()
    for pipe in machine.pipes:
        if block_of(pipe.source) != block_of(pipe.dest):
            cells.update(pipe.cells)
    return cells


def build_pressed_plotter() -> str:
    """The pressed Plotter machine.  Deterministic: no randomness anywhere."""
    src = source_cells()
    stale = external_cells()
    assert len(ROUTES) == 5
    cv = Canvas()

    for name, (top, left, bottom, right) in BLOCKS.items():
        row, col = PLACE[name]
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if (r, c) in stale or (r, c) not in src:
                    continue
                cv.cells[(row + r - top, col + c - left)] = src[(r, c)]

    for waypoints, length in ROUTES:
        assert path_length(waypoints) == length, (waypoints, length)
        for cell in _route_cells(waypoints):
            assert cell not in cv.cells, f"pipe collision at {cell}"
        cv.pipe(waypoints)

    return cv.render()


def _route_cells(waypoints: list[tuple[int, int]]) -> list[tuple[int, int]]:
    cells = [waypoints[0]]
    for a, b in zip(waypoints, waypoints[1:]):
        dr = (b[0] > a[0]) - (b[0] < a[0])
        dc = (b[1] > a[1]) - (b[1] < a[1])
        pos = a
        while pos != b:
            pos = (pos[0] + dr, pos[1] + dc)
            cells.append(pos)
    return cells


def bindings(text: str) -> list[tuple]:
    """Every pipe as (source shape, dest shape, length, port offsets).

    Two machines with the same binding list expose every ``s``/``r`` to the
    same distances, so each instruction reaches the same pipe in both.
    """
    from .sim import Machine

    machine = Machine.parse(text)

    def shape(room):
        return (room.kind, room.bottom - room.top, room.right - room.left)

    out = []
    for pipe in machine.pipes:
        src, dst = pipe.source, pipe.dest
        head, tail = pipe.cells[0], pipe.cells[-1]
        out.append((
            shape(src), shape(dst), len(pipe.cells),
            (head[0] - src.top, head[1] - src.left),
            (tail[0] - dst.top, tail[1] - dst.left),
        ))
    return sorted(out)


def _room_keys(machine) -> dict:
    """Rooms keyed by (kind, height, width, rank among identical shapes)."""
    out: dict = {}
    seen: dict = {}
    for room in sorted(machine.rooms, key=lambda r: (r.top, r.left)):
        shape = (room.kind, room.bottom - room.top, room.right - room.left)
        rank = seen.get(shape, 0)
        seen[shape] = rank + 1
        out[shape + (rank,)] = room
    return out


def _rooms_by_shape(text: str) -> dict:
    from .sim import Machine

    return _room_keys(Machine.parse(text))


def room_texts(text: str) -> dict:
    """Every room's rectangle, verbatim, keyed by shape.  Placement-free."""
    rows = text.rstrip("\n").split("\n")

    def cut(room):
        return tuple(
            "".join(
                rows[r][c] if c < len(rows[r]) else " "
                for c in range(room.left, room.right + 1)
            )
            for r in range(room.top, room.bottom + 1)
        )

    return {key: cut(room) for key, room in _rooms_by_shape(text).items()}


def resolution_by_offset(text: str) -> dict:
    """Every s/r/q/S/R/U cell as (room shape, cell offset) -> pipe role.

    A pipe's "role" is named by geometry only -- its source and destination
    room shapes and its port offsets -- so the map is comparable between two
    machines built from the same rooms at different coordinates.
    """
    from .ir_export import machine_ir
    from .sim import Machine

    machine = Machine.parse(text)
    ir = machine_ir(text)
    rooms = list(machine.rooms)
    keys = {id(room): key for key, room in _room_keys(machine).items()}

    def role(pipe):
        src, dst = pipe.source, pipe.dest
        return (
            keys[id(src)][:3], keys[id(dst)][:3],
            (pipe.cells[0][0] - src.top, pipe.cells[0][1] - src.left),
            (pipe.cells[-1][0] - dst.top, pipe.cells[-1][1] - dst.left),
        )

    roles = [role(pipe) for pipe in machine.pipes]
    out = {}
    for cell, entry in ir["resolution"].items():
        r, c = (int(x) for x in cell.split(","))
        room = next(
            room for room in rooms
            if room.top <= r <= room.bottom and room.left <= c <= room.right
        )
        key = (keys[id(room)], r - room.top, c - room.left)
        if "pipe" in entry:
            bound = None if entry["pipe"] is None else roles[entry["pipe"]]
        else:
            bound = tuple(sorted(roles[i] for i in entry["pipes"]))
        out[key] = (entry["op"], bound)
    return out


def port_margins(text: str) -> dict:
    """Per room: the smallest slack, in cells, before some s/r re-binds.

    For every instruction, the distance to the nearest *wrong* port of its
    own direction minus the distance to the port it actually reaches.
    """
    from .sim import Machine

    machine = Machine.parse(text)
    out = {}
    for key, room in _room_keys(machine).items():
        if room.kind != "room":
            continue
        outs = [p.cells[0] for p in machine.pipes if p.source is room]
        ins = [p.cells[-1] for p in machine.pipes if p.dest is room]
        worst = None
        for r in range(room.top + 1, room.bottom):
            for c in range(room.left + 1, room.right):
                ch = machine.grid[r][c]
                ends = outs if ch == "s" else ins if ch in "rq" else None
                if ends is None or len(ends) < 2:
                    continue
                dist = sorted(abs(r - a) + abs(c - b) for a, b in ends)
                slack = dist[1] - dist[0]
                worst = slack if worst is None else min(worst, slack)
        out[key] = worst
    return out
