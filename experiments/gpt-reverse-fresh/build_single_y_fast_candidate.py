"""Build the faster 20-square single-Y Reverse candidate.

This preserves the single-Y factory and seven-tick countdown chain from
``reverse_fresh_20``. The only change is controller placement: the next-round
U sits directly below the BP-zero factory exit, and the BP initialization path
uses a small two-row pocket before joining the clear countdown-side column.
This removes three ticks per round without changing worker timing.
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

for position, glyph in {
    # Six-tick single-Y factory.
    (5, 13): "Y",
    (6, 13): "m",
    (7, 13): "d",
    (7, 12): "^",
    (5, 12): ">",
    # Worker receive and countdown entry.
    (3, 13): "U",
    (3, 12): "a",
    (4, 12): "d",
    (4, 11): "^",
    (0, 11): "<",
    # Factory zero exit.
    (8, 13): ">",
    (8, 14): "v",
    # Next-round receive immediately below the exit.
    (9, 14): "U",
    (9, 13): "@",
    (9, 12): "b",
    (9, 11): "v",
    # Two-row setup pocket, then join the clear column at row 8.
    (10, 11): ">",
    (10, 13): "v",
    (11, 13): "<",
    (11, 12): "^",
    (8, 12): "a",
    (8, 11): "^",
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
Path(__file__).with_name("reverse_fresh_20_fast.man").write_text(text)
print(text, end="")
