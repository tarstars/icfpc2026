"""LayoutIR: a placeable description of an existing machine.

The solver stack (claude_32) never invents a machine; it re-places one we
already trust. So the IR is built BY PARSING an artifact, and it carries
exactly what a placer needs and nothing else:

* rooms as RIGID blocks (their interior text is copied verbatim, so any
  re-placement is behaviour-preserving by construction);
* the connection list, with each pipe's endpoints expressed as
  (room index, wall side, offset along that wall) rather than absolute
  coordinates, so a connection survives moving its rooms;
* each pipe's current length plus whether that length is a CONSTRAINT.

That last field is the one that matters and the one a naive packer gets
wrong. A pipe is a conveyor: values move one cell per tick, so its length
is a delay. For machines that only need capacity the length is a lower
bound; for machines whose logic observes occupancy or arrival order
(`q`, `R`, `U`) the length must be reproduced EXACTLY or the machine
changes meaning. `sim` has no notion of this -- it is our knowledge, so
it lives here.

Round-tripping is the acceptance test: ir = parse(text); render(ir) must
reproduce `text` byte-for-byte before any solver is allowed to touch it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .canvas import Canvas
from .sim import Machine

# Ops whose behaviour depends on pipe timing rather than just capacity.
# `q` counts a pipe's occupancy; `R`/`U` pick among ready pipes by arrival.
TIMING_OPS = frozenset("qRU")


@dataclass(frozen=True)
class Port:
    """Where a pipe meets a room, relative to that room's own box."""

    room: int          # index into Layout.rooms
    side: str          # 'N' | 'S' | 'W' | 'E'
    offset: int        # cells along that side from the room's top/left corner


@dataclass
class Room:
    """A rigid block: its text is copied verbatim wherever it lands."""

    index: int
    kind: str          # 'room' | 'input' | 'output' | 'display'
    lines: list[str]   # includes walls; height = len, width = len(lines[0])
    top: int           # original position (the placer overwrites these)
    left: int

    @property
    def height(self) -> int:
        return len(self.lines)

    @property
    def width(self) -> int:
        return max(len(line) for line in self.lines)


@dataclass
class Conn:
    """One pipe: source port -> destination port, with its length rule."""

    src: Port
    dst: Port
    length: int              # cells in the current artifact
    exact: bool              # True => length must be reproduced exactly
    cells: list[tuple[int, int]] = field(default_factory=list)
    glyphs: list[str] = field(default_factory=list)


@dataclass
class Layout:
    rooms: list[Room]
    conns: list[Conn]
    width: int
    height: int
    timing_sensitive: bool   # any q/R/U inside any room

    @property
    def footprint(self) -> int:
        return max(self.width, self.height) ** 2


def _side_and_offset(room: Room, cell: tuple[int, int]) -> tuple[str, int] | None:
    """Classify a pipe-adjacent cell against a room's border."""
    r, c = cell
    top, left = room.top, room.left
    bottom, right = top + room.height - 1, left + room.width - 1
    if r == top - 1 and left <= c <= right:
        return "N", c - left
    if r == bottom + 1 and left <= c <= right:
        return "S", c - left
    if c == left - 1 and top <= r <= bottom:
        return "W", r - top
    if c == right + 1 and top <= r <= bottom:
        return "E", r - top
    return None


def parse(text: str) -> Layout:
    """Build a Layout from an artifact. Rooms are lifted verbatim."""
    machine = Machine.parse(text)
    lines = [line for line in text.split("\n") if line]
    width = max(len(line) for line in lines)
    height = len(lines)

    rooms: list[Room] = []
    for index, sim_room in enumerate(machine.rooms):
        block = []
        for r in range(sim_room.top, sim_room.bottom + 1):
            row = lines[r] if r < len(lines) else ""
            block.append(row[sim_room.left:sim_room.right + 1].ljust(
                sim_room.right - sim_room.left + 1))
        rooms.append(Room(index=index, kind=sim_room.kind, lines=block,
                          top=sim_room.top, left=sim_room.left))

    def port_for(sim_room, cell) -> Port:
        room = rooms[machine.rooms.index(sim_room)]
        placed = _side_and_offset(room, cell)
        if placed is None:                       # pipe end not flush: use nearest
            r, c = cell
            side = "N" if r < room.top else "S" if r >= room.top + room.height \
                else "W" if c < room.left else "E"
            offset = 0
            return Port(room.index, side, offset)
        return Port(room.index, placed[0], placed[1])

    timing = False
    room_has_timing = [False] * len(machine.rooms)
    for idx, room in enumerate(machine.rooms):
        for r in range(room.top + 1, room.bottom):
            line = lines[r] if r < len(lines) else ""
            for c in range(room.left + 1, min(room.right, len(line))):
                if line[c] in TIMING_OPS:
                    timing = True
                    room_has_timing[idx] = True

    # Conn.exact must be PER-PIPE, not the layout-wide `timing` flag above.
    # `timing`/`timing_sensitive` answers "does q/R/U exist anywhere?"; a
    # pipe only needs its exact length reproduced if ITS OWN endpoint room
    # is one that observes occupancy/order. Using the blanket flag here used
    # to mark every pipe in a machine exact as soon as one distant room had
    # a timing op (measured: 231/231 pipes pinned when only 6 touched a
    # timing room), which froze the placer solid. So: exact only if the
    # source or destination room actually contains a timing op.
    conns: list[Conn] = []
    for pipe in machine.pipes:
        src_port = port_for(pipe.source, pipe.cells[0])
        dst_port = port_for(pipe.dest, pipe.cells[-1])
        conns.append(Conn(
            src=src_port,
            dst=dst_port,
            length=len(pipe.cells),
            exact=room_has_timing[src_port.room] or room_has_timing[dst_port.room],
            cells=list(pipe.cells),
            glyphs=[lines[r][c] for r, c in pipe.cells],
        ))
    return Layout(rooms=rooms, conns=conns, width=width, height=height,
                  timing_sensitive=timing)


def render(layout: Layout) -> str:
    """Re-emit an artifact from the IR, rooms verbatim, pipes as stored."""
    canvas = Canvas()
    for room in layout.rooms:
        canvas.put(room.top, room.left, room.lines)
    for conn in layout.conns:
        for (r, c), glyph in zip(conn.cells, conn.glyphs):
            canvas.cells[(r, c)] = glyph
    return canvas.render()
