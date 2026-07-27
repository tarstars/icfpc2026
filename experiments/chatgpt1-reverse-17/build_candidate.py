#!/usr/bin/env python3
"""Build chatgpt1_reverse_09: a 17x17 multi-round linear-time Reverse farm.

The machine uses a four-tick two-Y worker factory. Every worker receives one
value, decrements its inherited sequence number, splits on parity, and either
waits in one of two shared 14-cell countdown loops or takes a zero-lap bypass.
The k=0 bypass emits first and becomes the controller for the next round.

This module only renders the immutable candidate. It never submits.
"""
from __future__ import annotations

INTERIOR_HEIGHT = 12
INTERIOR_WIDTH = 15
CANVAS_SIDE = 17


def _interior() -> list[list[str]]:
    grid = [[" "] * INTERIOR_WIDTH for _ in range(INTERIOR_HEIGHT)]

    def put(row: int, column: int, glyph: str) -> None:
        old = grid[row][column]
        if old not in (" ", glyph):
            raise AssertionError(((row, column), old, glyph))
        grid[row][column] = glyph

    # Even residue loop: 3x6 perimeter = 14 cells.
    for item in (
        (0, 1, ">"), (0, 6, "v"), (2, 1, "^"), (2, 5, "m"),
        (2, 6, "d"), (3, 6, "s"), (4, 6, "H"),
    ):
        put(*item)

    # Odd residue loop, mirrored. Its root-to-gate path is six ticks longer.
    for item in (
        (0, 8, "v"), (0, 13, "<"), (2, 8, "a"), (2, 9, "m"),
        (2, 13, "^"), (3, 8, "s"), (4, 8, "H"),
    ):
        put(*item)

    # Parity split and positive-lap entry gates.
    for item in (
        (5, 4, "x"), (5, 3, "]"), (5, 2, "d"),
        (5, 5, "]"), (5, 12, "a"),
        (4, 2, "<"), (4, 1, "^"),
        (4, 12, ">"), (4, 13, "^"),
    ):
        put(*item)

    # Odd zero-lap worker (k=1): delayed bypass, then output and halt.
    for item in (
        (5, 14, "v"), (11, 14, "<"), (11, 13, "^"),
        (6, 13, "<"), (6, 12, "s"), (6, 11, "H"),
    ):
        put(*item)

    # Equal-length worker merge, common k := k-1, and parity root.
    for item in (
        (7, 7, "^"), (6, 7, "<"), (6, 6, "m"), (6, 4, "^"),
        (8, 3, "^"), (7, 3, ">"),
        (10, 9, "^"), (7, 9, "<"),
    ):
        put(*item)

    # Rotated two-Y factory. Y1 is bottom-right; workers are born horizontally.
    for item in (
        (8, 5, "Y"), (8, 6, "m"), (8, 7, "d"), (8, 8, "H"),
        (9, 5, "^"), (9, 7, "v"),
        (10, 4, "H"), (10, 5, "d"), (10, 6, "m"),
        (10, 7, "Y"), (8, 4, "r"), (10, 8, "r"),
    ):
        put(*item)

    # Initial / next-round controller: read n, store BP, enter Y1.
    for item in (
        (11, 11, "@"), (11, 12, "U"), (10, 12, "b"),
        (9, 12, "<"), (9, 7, "v"),
    ):
        put(*item)

    # Even zero-lap worker (k=0): output first, then wait at U as controller.
    for item in ((5, 0, "v"), (11, 0, ">"), (11, 6, "s")):
        put(*item)

    return grid


def build() -> str:
    canvas = [[" "] * CANVAS_SIDE for _ in range(CANVAS_SIDE)]

    # Main room: 17x14 outside, 15x12 inside.
    for column in range(CANVAS_SIDE):
        canvas[0][column] = canvas[13][column] = "-"
    for row in range(14):
        canvas[row][0] = canvas[row][16] = "|"
    for row, column in ((0, 0), (0, 16), (13, 0), (13, 16)):
        canvas[row][column] = "+"
    for row, line in enumerate(_interior(), 1):
        for column, glyph in enumerate(line, 1):
            canvas[row][column] = glyph

    def put_room(row: int, column: int, glyph: str) -> None:
        for dr, line in enumerate(("+-+", f"|{glyph}|", "+-+")):
            for dc, char in enumerate(line):
                canvas[row + dr][column + dc] = char

    put_room(14, 0, "O")
    put_room(14, 14, "I")

    # Main -> O: two cells. I -> main: three cells.
    for row, column, glyph in (
        (14, 3, "v"), (15, 3, "<"),
        (15, 13, "<"), (15, 12, "^"), (14, 12, "^"),
    ):
        canvas[row][column] = glyph

    return "\n".join("".join(row).rstrip() for row in canvas) + "\n"


def main() -> int:
    print(build(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
