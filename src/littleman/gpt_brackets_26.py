"""Solver-guided 26x26 successor to accepted ``brackets_11``.

The architecture and pipe roles are unchanged.  Two finite component variants
make the square reduction possible:

* CLOSE folds its final output ``s; H`` arm down through two previously blank
  cells, reducing the outer room width from 25 to 24.
* OPEN folds its one-time startup U-turn into row 7, reducing the outer room
  height from 11 to 10.

The freed right corridor moves the long OPEN -> CLASSIFY transport route from
column 26 to column 25, shortening it from 49 to 47 cells.  This module does
not submit; it only reproduces the immutable candidate artifact.
"""

from __future__ import annotations

from .canvas import Canvas

CLASSIFY = [
    "@ssv      <   ",
    "   >rXrsrs^   ",
    "     >MrW+++sv",
    "   ^    s+1Mr<",
]

CLOSE_26 = [
    "         >rM1+ sH     ",
    ">@rXrsrsv   >+MrXrM1+v",
    "   >    M4W-XrX  sH  s",
    "^ s+1MrsWXW/W3M-<    H",
    "^       <     >rM1+sH ",
]

OPEN_26 = [
    "H  s4    s <  ",
    "v  s  0  s<   ",
    ">qd0       ^  ",
    "  >rbM5W} x   ",
    "          ]   ",
    "^  s  0  sxM0v",
    "^ <s    Ws   <",
    "@r^           ",
]

ROOMS = [
    (1, 0, "classify"),
    (4, 19, "output"),
    (9, 1, "close"),
    (16, 4, "open"),
    (22, 22, "input"),
]

PIPES = [
    ([(7, 6), (8, 6)], "v"),
    ([(8, 8), (7, 8)], "^"),
    ([(8, 20), (7, 20)], "^"),
    ([(20, 3), (20, 2), (16, 2), (16, 0), (11, 0)], ">"),
    ([(20, 20), (20, 21), (16, 21), (16, 25), (0, 25), (0, 4)], "v"),
    ([(23, 21), (23, 20)], "<"),
]


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_gpt_brackets_26() -> str:
    """Render the exact 26x26 candidate preserved as ``gpt_brackets_12.man``."""

    art = {
        "classify": _box(CLASSIFY),
        "close": _box(CLOSE_26),
        "open": _box(OPEN_26),
        "input": ["+-+", "|I|", "+-+"],
        "output": ["+-+", "|O|", "+-+"],
    }
    canvas = Canvas()
    for row, column, name in ROOMS:
        canvas.put(row, column, art[name])
    for waypoints, terminal in PIPES:
        canvas.pipe(waypoints)
        canvas.cells[waypoints[-1]] = terminal
    return canvas.render()


if __name__ == "__main__":
    print(build_gpt_brackets_26(), end="")
