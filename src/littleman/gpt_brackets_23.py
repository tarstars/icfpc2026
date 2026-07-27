"""Solver-guided 23x23 Brackets candidate.

The component variants are inherited from :mod:`littleman.gpt_brackets_24`.
A mixed-integer multi-commodity flow search jointly chooses the room ordering,
port cells, and six vertex-disjoint routes while preserving every logical
nearest-pipe binding.
"""

from __future__ import annotations

from .canvas import Canvas
from .gpt_brackets_24 import CLASSIFY, CLOSE_24, OPEN_24

ROOMS = {
    "close": (0, 0),
    "classify": (9, 6),
    "open": (15, 0),
    "output": (17, 20),
    "input": (20, 18),
}

PIPES = [
    ([(8, 6), (7, 6)], "^"),
    ([(7, 13), (8, 13), (8, 14), (8, 15)], "v"),
    (
        [
            (7, 18), (8, 18), (8, 19), (8, 20), (8, 21), (8, 22),
            (9, 22), (10, 22), (11, 22), (12, 22), (13, 22),
            (14, 22), (15, 22), (16, 22),
        ],
        "v",
    ),
    ([(14, 3), (13, 3), (12, 3), (11, 3), (10, 3), (9, 3), (8, 3), (7, 3)], "^"),
    ([(14, 5), (13, 5), (12, 5), (11, 5)], ">"),
    ([(19, 18), (18, 18)], "<"),
]


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_gpt_brackets_18() -> str:
    """Render the immutable solver-guided 23x23 candidate."""

    art = {
        "close": _box(CLOSE_24),
        "classify": _box(CLASSIFY),
        "open": _box(OPEN_24),
        "output": ["+-+", "|O|", "+-+"],
        "input": ["+-+", "|I|", "+-+"],
    }
    canvas = Canvas()
    for name, (row, column) in ROOMS.items():
        canvas.put(row, column, art[name])
    for path, terminal in PIPES:
        canvas.pipe(path)
        canvas.cells[path[-1]] = terminal
    return canvas.render()


if __name__ == "__main__":
    print(build_gpt_brackets_18(), end="")
