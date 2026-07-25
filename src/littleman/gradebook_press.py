"""Grade Book, geometry-pressed: the rooms of ``gradebook_02.man`` re-placed.

``gradebook_02`` is live at 81,914,188,255.  It is 386 wide x 423 tall, so
its footprint is ``423**2 = 178,929``.  Measured first, argued afterwards:

* room boxes fill 147,527 of the 163,278 cells of the bounding box (90.4%),
  so the box is *already* nearly solid.  The parser room alone is 385 wide,
  which pins the width; the parser (183) stacked on the workers (199) pins
  382 of the 423 rows.  Rebalancing buys nothing here.
* the only slack is the 35-row band under the workers that holds the eight
  5x5 relay rooms (in two tiers), the 384x5 collector and the 3x3 output.
  Pressed into one relay tier that band becomes 19 rows.

Ticks were the other candidate lever and they turned out to be a small one.
The command/ack loop (parser->worker1 broadcast + the worker ack chain +
worker4->parser return) is 1406 cells here; this module cuts it to 1290 and
shortens the eight relay laps from 48/98 cells to 30/44.  Measured, not
assumed: that is worth 0.5% of ticks (mean 136,739 -> 135,955).  Ticks in
this machine are dominated by walking inside the rooms, and room interiors
are off limits, so the box is the whole of the win.

The earlier-looking correlation across the shipped artifacts is a trap --
gradebook_01 and gradebook_02 differ in room WIDTHS (``fsm_right_padding``),
not only in routing, so their 14k tick gap is intra-room travel.

WHAT MOVES
----------
The sixteen rooms are lifted out of ``gradebook_02.man`` as character
rectangles, so every room interior is byte-identical, glyph for glyph.  Only
placement and routing change:

* rows 0..388 are untouched: input, parser, and the four workers keep their
  exact coordinates.  Their heights are what fix the height.
* the eight relay rooms move into a single tier at rows 390..394, each one
  next to the worker ports it serves.
* the collector moves from row 413 to row 397; the 3x3 output moves out of
  the bottom of the machine into the right margin (cols 386..388), which is
  free because the parser is 385 wide.

Every port keeps its OFFSET from its room's top-left corner, so every
``s``/``r`` sees the same wall cell and binds to the same pipe role.  There
is no ``q``, no ``U`` and only the collector's single ``R`` in this machine,
so no instruction observes pipe occupancy or arrival order; pipe lengths are
pure latency here, which is why they may be shortened at all.

    gradebook_02   386 x 423   fp 178,929   loop 1406
    gradebook_03   390 x 404   fp 163,216   loop 1290
"""

from __future__ import annotations

import pathlib

from .canvas import Canvas

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCE = REPO / "submissions" / "gradebook" / "gradebook_02.man"

# (top, left, bottom, right) rectangles in gradebook_02.man.
ROOMS = {
    "input": (0, 9, 2, 11),
    "parser": (5, 0, 187, 384),
    "w1": (189, 2, 384, 97),
    "w2": (189, 99, 387, 192),
    "w3": (189, 194, 387, 287),
    "w4": (189, 289, 387, 382),
    "relayB1": (390, 36, 394, 40),
    "relayA1": (400, 26, 404, 30),
    "relayB2": (394, 131, 398, 135),
    "relayA2": (404, 121, 408, 125),
    "relayB3": (394, 226, 398, 230),
    "relayA3": (404, 216, 408, 220),
    "relayB4": (394, 321, 398, 325),
    "relayA4": (404, 311, 408, 315),
    "collector": (413, 0, 417, 383),
    "output": (420, 192, 422, 194),
}

# Where each room's top-left corner goes on the pressed canvas.
PLACE = {
    "input": (0, 9),
    "parser": (5, 0),
    "w1": (189, 2),
    "w2": (189, 99),
    "w3": (189, 194),
    "w4": (189, 289),
    "relayA1": (390, 5),
    "relayB1": (390, 34),
    "relayA2": (390, 100),
    "relayB2": (390, 129),
    "relayA3": (390, 195),
    "relayB3": (390, 224),
    "relayA4": (390, 290),
    "relayB4": (390, 319),
    "collector": (397, 0),
    "output": (395, 386),
}

RELAY_TOP = 390          # relay tier rows 390..394
LOW_LANE = 395           # horizontal lane under the relay tier
CHAIN_LANE = 396         # lane carrying worker -> worker ack hops
COLL_TOP = 397           # collector rows 397..401


class Worker:
    """Bottom-wall port columns of one worker, plus its two relay corners.

    Every worker port in this machine sits on the room's BOTTOM wall, so all
    routing happens in the band underneath.  ``pr`` is the row of the pipe
    cells that touch that wall.
    """

    def __init__(self, tag: str, left: int, pr: int, gap: int, ports: tuple):
        self.tag = tag
        self.left = left
        self.pr = pr
        self.gap = gap                     # column the broadcast descends
        (self.rp, self.rA, self.sA,
         self.rB, self.sB, self.rPrev, self.sC, self.sN) = ports
        self.la = PLACE["relayA" + tag][1]  # relay A left column
        self.lb = PLACE["relayB" + tag][1]  # relay B left column


def workers() -> list[Worker]:
    out = [Worker("1", 2, 385, 1, (12, 17, 22, 27, 32, None, 57, 67))]
    for tag, base, gap in (("2", 99, 98), ("3", 194, 193), ("4", 289, 288)):
        ports = tuple(base + d for d in (8, 13, 18, 23, 28, 41, 53, 63))
        out.append(Worker(tag, base, 388, gap, ports))
    return out


def routes() -> list[list[tuple[int, int]]]:
    """Waypoints for all thirty pipes.  First cell points away from the
    source wall, last cell points into the destination wall."""
    ws = workers()
    out: list[list[tuple[int, int]]] = [[(3, 10), (4, 10)]]  # input -> parser
    for w in ws:
        out.append([(188, w.gap), (w.pr + 1, w.gap),
                    (w.pr + 1, w.rp), (w.pr, w.rp)])
        # worker -> relay A: down, left under the relay, in through its wall
        out.append([(w.pr, w.sA), (LOW_LANE, w.sA), (LOW_LANE, w.la - 2),
                    (RELAY_TOP + 3, w.la - 2), (RELAY_TOP + 3, w.la - 1)])
        # relay A -> worker: out of the right wall, over the top, back up
        out.append([(RELAY_TOP + 2, w.la + 5), (RELAY_TOP + 2, w.la + 9),
                    (w.pr + 1, w.la + 9), (w.pr + 1, w.rA), (w.pr, w.rA)])
        # worker -> relay B: straight down into its left wall
        out.append([(w.pr, w.sB), (RELAY_TOP + 3, w.sB),
                    (RELAY_TOP + 3, w.lb - 1)])
        # relay B -> worker: out of the right wall, under the tier, back up
        out.append([(RELAY_TOP + 2, w.lb + 5), (RELAY_TOP + 2, w.lb + 6),
                    (LOW_LANE, w.lb + 6), (LOW_LANE, w.rB), (w.pr, w.rB)])
        out.append([(w.pr, w.sC), (COLL_TOP - 1, w.sC)])
    for src, dst in zip(ws, ws[1:]):
        out.append([(src.pr, src.sN), (CHAIN_LANE, src.sN),
                    (CHAIN_LANE, dst.rPrev), (dst.pr, dst.rPrev)])
    # worker4 ack -> parser top: up the free column right of the parser
    out.append([(388, ws[3].sN), (389, ws[3].sN), (389, 385),
                (3, 385), (3, 20), (4, 20)])
    # collector -> output, parked in the right margin
    out.append([(COLL_TOP + 5, 193), (COLL_TOP + 6, 193), (COLL_TOP + 6, 389),
                (RELAY_TOP + 2, 389), (RELAY_TOP + 2, 387),
                (RELAY_TOP + 4, 387)])
    return out


def source_cells() -> dict[tuple[int, int], str]:
    """gradebook_02.man as a sparse cell map.  Read-only; never rewritten."""
    text = SOURCE.read_text()
    return {
        (r, c): ch
        for r, line in enumerate(text.rstrip("\n").split("\n"))
        for c, ch in enumerate(line)
        if ch != " "
    }


def path_cells(waypoints: list[tuple[int, int]]) -> list[tuple[int, int]]:
    cells = [waypoints[0]]
    for a, b in zip(waypoints, waypoints[1:]):
        dr = (b[0] > a[0]) - (b[0] < a[0])
        dc = (b[1] > a[1]) - (b[1] < a[1])
        pos = a
        while pos != b:
            pos = (pos[0] + dr, pos[1] + dc)
            cells.append(pos)
    return cells


def build_pressed_gradebook() -> str:
    """The pressed Grade Book machine.  Deterministic: no randomness."""
    src = source_cells()
    canvas = Canvas()
    for name, (top, left, bottom, right) in ROOMS.items():
        row, col = PLACE[name]
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                ch = src.get((r, c))
                if ch is not None:
                    canvas.cells[(row + r - top, col + c - left)] = ch
    for waypoints in routes():
        for cell in path_cells(waypoints):
            if cell in canvas.cells:
                raise AssertionError(f"pipe collision at {cell}")
        canvas.pipe(waypoints)
    return canvas.render()
