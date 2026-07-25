"""little-little-little-man (LLLM): reference interpreter + machine generator.

The problem: interpret a tiny subset of littleman ("LLLM") and render its
state onto a 16x16 LM-75 display, one frame per round.

This module holds

* :func:`interpret` / :func:`frames_for_rounds` -- a pure-Python reference
  implementation used to validate our understanding of the semantics against
  the public test data, and
* :func:`build` -- the littleman machine that does the same thing.
"""

from __future__ import annotations

DISPLAY = 16

# colour table for the *characters* of an LLLM program (walls are positional)
CHAR_COLOR = {
    " ": 0,
    "<": 3,
    ">": 3,
    "^": 3,
    "v": 3,
    "V": 3,
    "X": 3,
    "H": 3,
    "M": 12,
    "+": 10,
    "-": 10,
}
for _d in "0123456789":
    CHAR_COLOR[_d] = 8
WALL_COLOR = 4
MAN_COLOR = 9

# headings, indexed 0..3 = N, E, S, W (clockwise order)
DELTAS = [(-1, 0), (0, 1), (1, 0), (0, -1)]


class LLLM:
    """Reference interpreter for one LLLM program."""

    def __init__(self, grid: list[str]):
        self.h = len(grid)
        self.w = len(grid[0])
        self.grid = [list(row) for row in grid]
        pos = [
            (r, c)
            for r in range(self.h)
            for c in range(self.w)
            if self.grid[r][c] == "@"
        ]
        if len(pos) != 1:
            raise ValueError(f"expected exactly one '@', found {len(pos)}")
        self.r, self.c = pos[0]
        self.grid[self.r][self.c] = " "  # the '@' cell is ordinary space
        self.heading = 1  # always begins facing east
        self.a = 0
        self.b = 0
        self.halted = False

    def is_wall(self, r: int, c: int) -> bool:
        return r == 0 or c == 0 or r == self.h - 1 or c == self.w - 1

    def step(self) -> None:
        if self.halted:
            return
        ch = self.grid[self.r][self.c]
        if self.is_wall(self.r, self.c):
            self.halted = True
            return
        if ch == "H":
            self.halted = True
            return
        if ch in "0123456789":
            self.a = int(ch)
        elif ch == "M":
            self.b = self.a
        elif ch == "+":
            self.a += self.b
        elif ch == "-":
            self.a -= self.b
        elif ch == "^":
            self.heading = 0
        elif ch == ">":
            self.heading = 1
        elif ch in "vV":
            self.heading = 2
        elif ch == "<":
            self.heading = 3
        elif ch == "X":
            if self.a > 0:
                self.heading = (self.heading + 1) % 4
            elif self.a < 0:
                self.heading = (self.heading + 3) % 4
        dr, dc = DELTAS[self.heading]
        self.r += dr
        self.c += dc
        if self.is_wall(self.r, self.c):
            self.halted = True

    def run(self, k: int) -> None:
        for _ in range(k):
            if self.halted:
                break
            self.step()

    def frame(self) -> list[str]:
        """Render the current state as 16 rows of 16 hex digits."""
        rows = []
        for r in range(DISPLAY):
            out = []
            for c in range(DISPLAY):
                if r >= self.h or c >= self.w:
                    out.append(0)
                elif (r, c) == (self.r, self.c):
                    out.append(MAN_COLOR)
                elif self.is_wall(r, c):
                    out.append(WALL_COLOR)
                else:
                    out.append(CHAR_COLOR.get(self.grid[r][c], 0))
            rows.append("".join("%x" % v for v in out))
        return rows


def grid_from_round1(values: list[int]) -> list[str]:
    """Decode the first round's input (W H then W*H ASCII codes)."""
    w, h = values[0], values[1]
    body = values[2 : 2 + w * h]
    return ["".join(chr(v) for v in body[r * w : (r + 1) * w]) for r in range(h)]


def frames_for_rounds(rounds: list[dict]) -> list[list[list[str]]]:
    """Reference frames for a public test case (one frame list per round)."""
    values = [int(x) for x in rounds[0]["in"]]
    machine = LLLM(grid_from_round1(values))
    out = [[machine.frame()]]
    for rnd in rounds[1:]:
        k = int(rnd["in"][0])
        machine.run(k)
        out.append([machine.frame()])
    return out
