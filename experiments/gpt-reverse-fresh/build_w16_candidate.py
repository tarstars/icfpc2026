"""Build the solver-derived 21-square multi-round Reverse candidate.

The left 11 columns retain the proven sixteen-stage seven-tick countdown
pipeline. A bounded right-strip routing search then permits the cycle and
controller to occupy only columns 11..15:

* both Y cells move two columns left;
* BP-positive workers and the BP-zero controller share crossings through
  conditional ``a``/``d`` instructions;
* odd and even controller exits share one return column;
* the input FIFO shrinks from 13 cells to the three-cell legal minimum for
  the chosen side-by-side I/O placement.
"""
from pathlib import Path

from littleman.canvas import Canvas

INTERIOR_HEIGHT = 16
INTERIOR_WIDTH = 16
cells: dict[tuple[int, int], str] = {}


def put(row: int, column: int, glyph: str) -> None:
    old = cells.get((row, column))
    if old not in (None, glyph, " "):
        raise AssertionError(((row, column), old, glyph))
    cells[(row, column)] = glyph


# Proven seven-tick countdown chain. A later worker arrives four or six ticks
# after its predecessor, so seven ticks per decremented backpack unit produces
# strict reverse output order.
for row in range(16):
    if row % 2 == 0:
        for column, glyph in ((3, "m"), (2, "a"), (1, "s"), (0, "H")):
            put(row, column, glyph)
        if row:
            put(row, 8, "<")
    else:
        for column, glyph in ((7, "m"), (8, "d"), (9, "s"), (10, "H")):
            put(row, column, glyph)
        put(row, 2, ">")

# Two-Y fresh-worker cycle, translated two columns left from the verified
# 23-square baseline. The continuation alternates four- and six-tick arcs.
for position, glyph in {
    (5, 14): "Y",
    (6, 14): "m",
    (7, 14): "d",
    (7, 13): "<",
    (7, 12): "Y",
    (6, 12): "^",
    (5, 12): "m",
    (4, 12): "d",
    (4, 13): "v",
    (5, 13): ">",
}.items():
    put(*position, glyph)

# Worker branches. The sole input pipe enters on the east, so U turns west.
# At the shared crossings, workers have BP>0 while the finished controller has
# BP=0. This lets one static a/d glyph implement two different routes.
put(4, 14, "^")
put(3, 14, "U")
put(3, 12, "a")       # worker: south; BP-zero controller: straight north
put(4, 11, "^")

put(8, 12, "v")
put(9, 12, "U")
put(9, 11, "^")
put(0, 11, "<")       # common worker route into countdown stage 1

# Odd-round BP-zero return: d at (4,12) does not turn; a at (3,12) does not
# turn; the controller reaches the top and then descends the free east column.
put(0, 12, ">")
put(0, 15, "v")

# Controller setup and per-round input receive. After U turns west, b stores n;
# the bottom bump moves the controller to column 13, which climbs directly into
# the predecessor of the first Y.
for position, glyph in {
    (14, 15): "U",
    (14, 14): "@",
    (14, 13): "b",
    (14, 12): "v",
    (15, 12): ">",
    (15, 13): "^",
}.items():
    put(*position, glyph)

# Even-round BP-zero continuation returns down the same east column.
put(8, 14, ">")
put(8, 15, "v")

room = ["+" + "-" * INTERIOR_WIDTH + "+"]
for row in range(INTERIOR_HEIGHT):
    room.append(
        "|"
        + "".join(cells.get((row, column), " ") for column in range(INTERIOR_WIDTH))
        + "|"
    )
room.append("+" + "-" * INTERIOR_WIDTH + "+")
io_room = lambda glyph: ["+-+", f"|{glyph}|", "+-+"]

canvas = Canvas()
canvas.put(0, 0, room)
canvas.put(0, 18, io_room("I"))
canvas.pipe([(3, 19), (4, 19), (4, 18)])
canvas.put(6, 18, io_room("O"))
canvas.pipe([(9, 18), (9, 19)])
canvas.cells[(9, 19)] = "^"  # final pipe cell points into O's bottom wall

text = canvas.render()
Path(__file__).with_name("reverse_fresh_21.man").write_text(text)
print(text, end="")
