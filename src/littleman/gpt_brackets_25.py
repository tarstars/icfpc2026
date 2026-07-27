"""Solver-guided 25x25 Brackets candidates.

Starting from ``gpt_brackets_13``:

* CLOSE moves the empty-stack output addition/send vertically at relative
  column 21 and shares the existing terminal halt, reducing outer width 24->23.
* OPEN moves startup into row 5 and joins the existing row-7 return, reducing
  outer height 10->9.
* The OPEN->CLASSIFY corridor moves to global column 24, shortening 44->42.

``gpt_brackets_15`` additionally moves the OPEN->CLOSE state source to the
highest legal left-wall cell, shortening that transport route 13->10 cells.
The module only reproduces immutable branch artifacts; it never submits.
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

PREFIX_PIPES = [
    ([(7, 6), (8, 6)], "v"),
    ([(8, 8), (7, 8)], "^"),
    ([(8, 20), (7, 20)], "^"),
]

LONG_PIPE = ([(17, 20), (17, 24), (0, 24), (0, 4)], "v")
INPUT_PIPE = ([(23, 21), (23, 20)], "<")
STATE_PIPE_14 = ([(20, 3), (20, 2), (16, 2), (16, 0), (11, 0)], ">")
STATE_PIPE_15 = ([(17, 3), (17, 0), (11, 0)], ">")


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def _build(state_pipe) -> str:
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
    for waypoints, terminal in [*PREFIX_PIPES, state_pipe, LONG_PIPE, INPUT_PIPE]:
        canvas.pipe(waypoints)
        canvas.cells[waypoints[-1]] = terminal
    return canvas.render()


def build_gpt_brackets_14() -> str:
    """Render the first exact 25x25 branch candidate."""

    return _build(STATE_PIPE_14)


def build_gpt_brackets_15() -> str:
    """Render the 25x25 candidate with the minimal state transport route."""

    return _build(STATE_PIPE_15)


if __name__ == "__main__":
    print(build_gpt_brackets_15(), end="")
