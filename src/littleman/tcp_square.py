"""Twenty-nine-cell square repack of the Packet Reassembly machine."""

from __future__ import annotations

from .canvas import Canvas
from .tcp_fast import build_e, build_io, build_p, build_r
from .tcp_repack import _build_hot_c


def _rotate_clockwise(room: list[str]) -> list[str]:
    """Rotate a room clockwise while preserving its execution directions."""
    interior = room[1:-1]
    old_height = len(interior)
    old_width = len(interior[0]) - 2
    arrows = {"^": ">", ">": "v", "v": "<", "<": "^"}
    cells: dict[tuple[int, int], str] = {}
    for row, line in enumerate(interior):
        for col, glyph in enumerate(line[1:-1]):
            if glyph != " ":
                cells[(col, old_height - 1 - row)] = arrows.get(glyph, glyph)

    # The VM always starts facing east.  The rotated P entry faces south, so
    # start one blank cell to its west and use the old start as a turn.
    assert cells[(1, 2)] == "@"
    assert (1, 1) not in cells
    cells[(1, 2)] = "v"
    cells[(1, 1)] = "@"

    rows = [[" "] * (old_height + 2) for _ in range(old_width + 2)]
    rows[0] = list("+" + "-" * old_height + "+")
    rows[-1] = rows[0].copy()
    for row in range(1, old_width + 1):
        rows[row][0] = rows[row][-1] = "|"
    for (row, col), glyph in cells.items():
        rows[row + 1][col + 1] = glyph
    return ["".join(row) for row in rows]


def build_tcp_square() -> str:
    """Return a strict 29x29-or-smaller repack of ``tarstars_tcp_10``."""
    canvas = Canvas()
    canvas.put(0, 5, build_e())
    canvas.put(2, 0, build_io("O"))
    canvas.put(6, 20, build_io("I"))
    canvas.put(0, 23, _rotate_clockwise(build_p()))
    canvas.put(14, 4, _build_hot_c())
    canvas.put(17, 24, build_r())

    def pipe(points: list[tuple[int, int]], last: str) -> None:
        canvas.pipe(points)
        canvas.cells[points[-1]] = last

    pipe([(2, 18), (2, 22)], ">")
    pipe([(3, 4), (3, 3)], "<")
    pipe([(7, 19), (7, 18)], "<")
    pipe([(13, 22), (13, 11)], "v")
    pipe([(13, 4), (10, 4), (10, 5)], "^")
    pipe([(20, 22), (20, 23)], ">")
    pipe([(19, 23), (19, 22)], "<")
    return canvas.render()
