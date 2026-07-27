"""Solver-guided 24x24 Brackets successor.

The immutable ``gpt_brackets_17`` machine descends from
:mod:`littleman.gpt_brackets_25` but changes two components, not merely their
placement:

* CLOSE folds the mismatched-close result tail into the existing unmatched-open
  result send. Both paths finish on the same ``s`` and use the server-confirmed
  final-wall-after-send rule, shrinking the room by one column.
* OPEN removes its dedicated end-of-stream row. End-of-stream is routed through
  two otherwise-unused columns, emits the same ``(0, 4)`` pair through the
  ordinary pair sender, and halts via the backpack branch, shrinking the room by
  one row.

Port placement and routing are then solved inside a 24-square envelope.
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

ROOMS = [
    (1, 0, "classify"),
    (4, 19, "output"),
    (9, 1, "close"),
    (16, 2, "open"),
    (20, 20, "input"),
]

PIPES = [
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


def build_gpt_brackets_17() -> str:
    """Render the immutable solver-guided 24x24 candidate."""
    art = {
        "classify": _box(CLASSIFY),
        "close": _box(CLOSE_24),
        "open": _box(OPEN_24),
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
    print(build_gpt_brackets_17(), end="")
