"""Solver-guided 24x24 Brackets candidate.

The machine descends from the 25-square GPT lineage but changes two components,
not merely their placement:

* CLOSE folds the mismatched-close result tail into the existing unmatched-open
  result send. Both paths finish on the same ``s`` and use the server-confirmed
  final-wall-after-send rule, shrinking the room by one column.
* OPEN removes its dedicated end-of-stream row. End-of-stream is routed through
  two otherwise-unused columns, emits the same ``(0, 4)`` pair through the
  ordinary pair sender, and halts via the backpack branch, shrinking the room by
  one row.

The input room moves to the lower left. The long OPEN -> CLASSIFY transport
retains exactly 42 pipe cells through a four-cell staple detour, and the
OPEN -> CLOSE state pipe remains at its ten-cell Manhattan minimum.
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
    (16, 4, "open"),
    (21, 0, "input"),
]

PIPES = [
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


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_gpt_brackets_16() -> str:
    """Render the exact 24x24 candidate."""

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
    print(build_gpt_brackets_16(), end="")
