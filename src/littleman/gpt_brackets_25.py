"""Solver-guided 25x25 Brackets candidate.

Starting from ``gpt_brackets_13``:

* CLOSE moves the empty-stack output addition/send vertically at relative
  column 21 and shares the existing terminal halt, reducing outer width 24->23.
* OPEN moves its startup into row 5 and joins the existing row-7 return,
  reducing outer height 10->9.
* The OPEN->CLASSIFY transport corridor moves to global column 24, shortening
  the route 44->42 cells.

The module only reproduces an immutable branch artifact. Submission and live
freshness belong to the integrator/submission controller.
"""

from __future__ import annotations

from .canvas import Canvas

CLASSIFY = [
    "@ssv      <   ",
    "   >rXrsrs^   ",
    "     >MrW+++sv",
    "   ^    s+1Mr<",
]

CLOSE_25 = [
    "         >rM1+ sH    ",
    ">@rXrsrsv   >+MrXrM1v",
    "   >    M4W-XrX  sH +",
    "^ s+1MrsWXW/W3M-<   s",
    "^       <     >rM1+sH",
]

OPEN_25 = [
    "H  s4    s <  ",
    "v  s  0  s<   ",
    ">qd0       ^  ",
    "  >rbM5W} x   ",
    "@rv       ]   ",
    "^  s  0  sxM0v",
    "^ <s    Ws   <",
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
    ([(17, 20), (17, 24), (0, 24), (0, 4)], "v"),
    ([(23, 21), (23, 20)], "<"),
]


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_gpt_brackets_14() -> str:
    """Render the exact 25x25 branch candidate."""

    art = {
        "classify": _box(CLASSIFY),
        "close": _box(CLOSE_25),
        "open": _box(OPEN_25),
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
    print(build_gpt_brackets_14(), end="")
