"""Solver-guided 26x26 successors to accepted ``brackets_11``.

The architecture and logical pipe roles are unchanged. Two finite component
variants make the square reduction possible:

* CLOSE folds its final output ``s; H`` arm down through two previously blank
  cells, reducing the outer room width from 25 to 24.
* OPEN folds its one-time startup U-turn into its existing return row, reducing
  the outer room height from 11 to 10.

``gpt_brackets_12`` keeps the long OPEN -> CLASSIFY endpoint at its inherited
row and moves the corridor from column 26 to 25. ``gpt_brackets_13`` moves that
endpoint to the highest binding-preserving right-wall cell and shortens the
transport route from 47 to 44 cells.

This module never submits. It reproduces immutable branch candidates for the
integrator's independent gates and platform decision.
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

COMMON_PIPES = [
    ([(7, 6), (8, 6)], "v"),
    ([(8, 8), (7, 8)], "^"),
    ([(8, 20), (7, 20)], "^"),
    ([(20, 3), (20, 2), (16, 2), (16, 0), (11, 0)], ">"),
]

PIPES_12 = [
    *COMMON_PIPES,
    ([(20, 20), (20, 21), (16, 21), (16, 25), (0, 25), (0, 4)], "v"),
    ([(23, 21), (23, 20)], "<"),
]

PIPES_13 = [
    *COMMON_PIPES,
    ([(17, 20), (17, 25), (0, 25), (0, 4)], "v"),
    ([(23, 21), (23, 20)], "<"),
]


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def _build(pipes) -> str:
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
    for waypoints, terminal in pipes:
        canvas.pipe(waypoints)
        canvas.cells[waypoints[-1]] = terminal
    return canvas.render()


def build_gpt_brackets_12() -> str:
    """Render the first exact 26x26 candidate, retained as immutable lineage."""

    return _build(PIPES_12)


def build_gpt_brackets_13() -> str:
    """Render the 26x26 candidate with the shortest proven right-wall route."""

    return _build(PIPES_13)


def build_gpt_brackets_26() -> str:
    """Backward-compatible name for the original ``gpt_brackets_12`` builder."""

    return build_gpt_brackets_12()


if __name__ == "__main__":
    print(build_gpt_brackets_13(), end="")
