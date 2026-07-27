"""Solver-guided 24x24 Brackets candidates.

The lineage changes two components, not merely their placement:

* CLOSE folds the mismatched-close result tail into the existing unmatched-open
  result send. Both paths finish on the same ``s`` and use the server-confirmed
  final-wall-after-send rule, shrinking the room by one column.
* OPEN removes its dedicated end-of-stream row. End-of-stream is routed through
  two otherwise-unused columns, emits the same ``(0, 4)`` pair through the
  ordinary pair sender, and halts via the backpack branch, shrinking the room by
  one row.

``gpt_brackets_17`` then moves OPEN left and reassigns the safe ports. The
OPEN -> CLOSE state transport falls to five cells and OPEN -> CLASSIFY to 39;
the input transport is three cells. All changes are regenerated exactly here.
"""

from __future__ import annotations

from .canvas import Canvas

CLASSIFY = [
    "@ssv      <   ",
    "   >rXrsrs^   ",
    "     >MrW+++sv",
    "   ^    s+1Mr<",
]

CLOSE_24 = [
    "         >rM1+ sH   ",
    ">@rXrsrsv   >+MrXrMv",
    "   >    M4W-XrX  sH1",
    "^ s+1MrsWXW/W3M-<  +",
    "^       <     >rM1+s",
]

OPEN_24 = [
    "v  s  0  s<>4M0v",
    ">qd0       ^    ",
    "  >rbM5W} x     ",
    "@rv       ]     ",
    "^ <s  0  sxM0v  ",
    "H ds    Ws   < <",
]

ROOMS_16 = [
    (1, 0, "classify"),
    (4, 19, "output"),
    (9, 1, "close"),
    (16, 4, "open"),
    (21, 0, "input"),
]

PIPES_16 = [
    ([(7, 6), (8, 6)], "v"),
    ([(8, 8), (7, 8)], "^"),
    ([(8, 20), (7, 20)], "^"),
    ([(17, 3), (17, 0), (11, 0)], ">"),
    (
        [(17, 22), (17, 23), (0, 23), (0, 19), (2, 19), (2, 17), (0, 17), (0, 4)],
        "v",
    ),
    ([(20, 1), (19, 1), (19, 3)], ">"),
]

ROOMS_17 = [
    (1, 0, "classify"),
    (4, 19, "output"),
    (9, 1, "close"),
    (16, 2, "open"),
    (20, 20, "input"),
]

PIPES_17 = [
    ([(7, 9), (8, 9)], "v"),
    ([(8, 7), (7, 7)], "^"),
    ([(8, 20), (7, 20)], "^"),
    ([(17, 1), (17, 0), (14, 0)], ">"),
    ([(17, 20), (17, 23), (0, 23), (0, 5)], "v"),
    ([(19, 21), (18, 21), (18, 20)], "<"),
]


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def _build(rooms, pipes) -> str:
    art = {
        "classify": _box(CLASSIFY),
        "close": _box(CLOSE_24),
        "open": _box(OPEN_24),
        "input": ["+-+", "|I|", "+-+"],
        "output": ["+-+", "|O|", "+-+"],
    }
    canvas = Canvas()
    for row, column, name in rooms:
        canvas.put(row, column, art[name])
    for waypoints, terminal in pipes:
        canvas.pipe(waypoints)
        canvas.cells[waypoints[-1]] = terminal
    return canvas.render()


def build_gpt_brackets_16() -> str:
    """Render the first exact 24x24 candidate."""

    return _build(ROOMS_16, PIPES_16)


def build_gpt_brackets_17() -> str:
    """Render the port-shortened 24x24 successor."""

    return _build(ROOMS_17, PIPES_17)


if __name__ == "__main__":
    print(build_gpt_brackets_17(), end="")
