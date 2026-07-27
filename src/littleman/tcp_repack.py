"""Thirty-cell repack of the tcp_09 Packet Reassembly machine."""

from __future__ import annotations

from .canvas import Canvas
from .tcp_fast import build_c, build_e, build_io, build_p, build_r


def _build_hot_c() -> list[str]:
    """Return room C with the two proven tcp_09 return shortcuts."""
    rows = [list(row) for row in build_c()]
    rows[1 + 4][1 + 2] = ">"
    rows[1 + 10][1 + 2] = "^"
    return ["".join(row) for row in rows]


def build_tcp_repack() -> str:
    """Repack tcp_09 into 30x30 without changing any room semantics."""
    canvas = Canvas()
    canvas.put(0, 5, build_e())
    canvas.put(2, 0, build_io("O"))
    canvas.put(6, 20, build_io("I"))
    canvas.put(10, 11, build_p())
    canvas.put(16, 5, _build_hot_c())
    canvas.put(19, 25, build_r())

    def pipe(points: list[tuple[int, int]], last: str) -> None:
        canvas.pipe(points)
        canvas.cells[points[-1]] = last

    # E -> P goes around their adjacent floors/ceilings.  The other two I/O
    # pipes are direct side connections.
    pipe([(2, 18), (2, 24), (9, 24)], "v")
    pipe([(3, 4), (3, 3)], "<")
    pipe([(7, 19), (7, 18)], "<")

    # P and C are stacked with no spare row.  Offset P six columns right so
    # its left-side pipe can enter C's ceiling without touching either wall.
    pipe([(14, 10), (14, 9), (15, 9), (15, 10)], "v")

    # C feedback climbs through the clear strip left of P, then enters E's
    # west wall.  This endpoint preserves the tcp_09 input/feedback ranking.
    pipe([(15, 7), (10, 7), (10, 4), (4, 4)], ">")

    # The three-word ring retains the two two-cell pipes from tcp_09.
    pipe([(22, 23), (22, 24)], ">")
    pipe([(20, 24), (20, 23)], "<")
    return canvas.render()
