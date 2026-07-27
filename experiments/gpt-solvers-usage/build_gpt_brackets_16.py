#!/usr/bin/env python3
"""Reproduce the solver-guided 24x25 Brackets candidate.

This is an experiment-only builder. It never submits. The candidate derives
from ``gpt_brackets_15`` by selecting a narrower CLOSE implementation, moving
OPEN and INPUT one column left/right respectively, and rerouting the two OPEN
transport pipes at their exact Manhattan lower bounds.

The CLOSE empty-stack arm deliberately ends with ``s`` next to the east wall.
The contest server's verified final-wall semantics halt that man while the
already-sent output drains; validation must therefore use
``littleman.server_compat``, not only the strict simulator judge.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from littleman.canvas import Canvas
from littleman.sim import Machine

HERE = Path(__file__).resolve().parent
ARTIFACT = HERE / "gpt_brackets_16.man"
SHA256 = "081cd30e57d63e7776280755ea75498870fcfff2575fe3b5ee2b3995ae80c79f"
EXPECTED_PIPE_LENGTHS = [2, 2, 2, 9, 41, 2]

CLASSIFY = [
    "@ssv      <   ",
    "   >rXrsrs^   ",
    "     >MrW+++sv",
    "   ^    s+1Mr<",
]

# Outer width 22, down from gpt_brackets_15's 23. The empty-stack arm uses
# columns 18..20 as ``r M v / 1 / + / s`` and then takes the final wall step.
CLOSE_24 = [
    "         >rM1+ sH   ",
    ">@rXrsrsv   >+MrXrMv",
    "   >    M4W-XrX  sH1",
    "^ s+1MrsWXW/W3M-<  +",
    "^       <     >rM1+s",
]

OPEN_24 = [
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
    (16, 3, "open"),
    (22, 21, "input"),
]

PIPES = [
    ([(7, 6), (8, 6)], "v"),
    ([(8, 8), (7, 8)], "^"),
    ([(8, 20), (7, 20)], "^"),
    ([(17, 2), (17, 0), (11, 0)], ">"),
    ([(17, 19), (17, 23), (0, 23), (0, 4)], "v"),
    ([(23, 20), (23, 19)], "<"),
]


def _box(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_gpt_brackets_16() -> str:
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
    text = canvas.render()

    rows = text.rstrip("\n").split("\n")
    if (max(map(len, rows)), len(rows)) != (24, 25):
        raise AssertionError("candidate box drifted")
    machine = Machine.parse(text)
    if (len(machine.rooms), len(machine.men), len(machine.pipes)) != (5, 3, 6):
        raise AssertionError("candidate structure drifted")
    lengths = [len(pipe.cells) for pipe in machine.pipes]
    if lengths != EXPECTED_PIPE_LENGTHS:
        raise AssertionError(f"pipe lengths drifted: {lengths}")
    digest = hashlib.sha256(text.encode()).hexdigest()
    if digest != SHA256:
        raise AssertionError(f"candidate hash drifted: {digest}")
    return text


def main() -> int:
    text = build_gpt_brackets_16()
    if ARTIFACT.exists() and ARTIFACT.read_text() != text:
        raise AssertionError(f"{ARTIFACT} does not match generator output")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
