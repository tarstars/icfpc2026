"""Build the solver-derived 20-square single-Y Reverse candidate.

A single Y station spawns one worker every six ticks. The continuation carries
the round count in BP, decrements once per loop, and exits when BP reaches zero.
Every worker receives one value, enters the proven seven-tick countdown chain,
sends in reverse order, and halts. The controller returns to the input U for
the next round, so no fixed-farm reset or sentinel protocol is required.
"""
from pathlib import Path

from littleman.canvas import Canvas

INTERIOR_HEIGHT = 16
INTERIOR_WIDTH = 15
cells: dict[tuple[int, int], str] = {}


def put(row: int, column: int, glyph: str) -> None:
    old = cells.get((row, column))
    if old not in (None, glyph, " "):
        raise AssertionError(((row, column), old, glyph))
    cells[(row, column)] = glyph


# Proven seven-tick countdown chain.
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

# Single-Y worker factory. From one Y execution to the next:
#   m, d, ^, blank, >, Y
# so workers are created every six ticks. Seven ticks per countdown unit makes
# each later value overtake its predecessor by exactly one tick.
for position, glyph in {
    (5, 13): "Y",
    (6, 13): "m",
    (7, 13): "d",
    (7, 12): "^",
    (5, 12): ">",
    # Worker branch: north birth -> input U -> countdown chain.
    (3, 13): "U",
    (3, 12): "a",
    (4, 12): "d",
    (4, 11): "^",
    (0, 11): "<",
    # BP-zero continuation exits south to the shared return column.
    (8, 13): ">",
    (8, 14): "v",
    # Per-round controller receive and BP initialization.
    (14, 14): "U",
    (14, 13): "@",
    (14, 12): "b",
    (14, 11): "v",
    # Bottom detour climbs column 13, then turns west into a clear column.
    (15, 11): ">",
    (15, 13): "^",
    (13, 13): "a",
    (13, 11): "^",
    (5, 11): ">",
}.items():
    put(*position, glyph)

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
canvas.put(0, 17, io_room("I"))
canvas.pipe([(3, 18), (4, 18), (4, 17)])
canvas.put(6, 17, io_room("O"))
canvas.pipe([(9, 17), (9, 18)])
canvas.cells[(9, 18)] = "^"

text = canvas.render()
Path(__file__).with_name("reverse_fresh_20.man").write_text(text)
print(text, end="")
