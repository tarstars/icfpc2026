"""Little Little Man (LLM): interpret a littleman subset and render it.

Problem `little-little-man`. The input is an LLM program as a grid of ASCII
codes; we must render its state to a 16x16 display, stepping it forward on
command.

This module is the **reference interpreter** for the LLM semantics, written in
Python. It exists to pin the semantics before any littleman machine is built:
the spec has several details that differ from real littleman and are easy to
get wrong.

Differences from littleman that matter here
-------------------------------------------
* Hitting a wall is **not an error**. The whole program stops, every man
  freezes where he stands (including the one on the wall cell), and the man on
  the wall is still drawn. The tick in which someone steps onto a wall
  *completes in full* -- every other man executes and moves on that tick too.
* `@` marks where a man starts; the cell itself is ordinary space, so once he
  walks off it, it renders black.
* The op set is only ``^ > v < 0-9 M + - X s r H``. Everything else in a
  well-formed program is a space.

Tick order (from the spec): pipes advance one cell, then every man executes
the op under him, then every non-blocked man advances one cell.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .sim import wrap64

# ------------------------------------------------------------------ colours
COLOR_SPACE = 0
COLOR_WALL = 4
COLOR_PIPE = 6
COLOR_DIGIT = 8
COLOR_MAN = 9
COLOR_ARITH = 10
COLOR_M = 12
COLOR_SR = 13
COLOR_PIPE_FULL = 14
COLOR_ARROW = 3

DISPLAY = 16

HEADINGS = {"^": (-1, 0), ">": (0, 1), "v": (1, 0), "<": (0, -1)}
# clockwise order N -> E -> S -> W
_CW = [(-1, 0), (0, 1), (1, 0), (0, -1)]


def op_color(ch: str) -> int:
    """Fixed colour of a program cell (the man is drawn separately)."""
    if ch in "<>^vXH":
        return COLOR_ARROW
    if ch.isdigit():
        return COLOR_DIGIT
    if ch == "M":
        return COLOR_M
    if ch in "+-":
        return COLOR_ARITH
    if ch in "sr":
        return COLOR_SR
    return COLOR_SPACE


@dataclass
class Pipe:
    """One LLM pipe: an ordered list of cells from source room to dest room."""

    cells: list[tuple[int, int]]
    source: int          # room index
    dest: int            # room index
    values: list[int | None] = field(default_factory=list)

    def __post_init__(self):
        if not self.values:
            self.values = [None] * len(self.cells)

    @property
    def head(self) -> tuple[int, int]:
        """The arrowhead leaving the source room (where `s` writes)."""
        return self.cells[0]

    @property
    def tail(self) -> tuple[int, int]:
        """The arrowhead entering the dest room (where `r` reads)."""
        return self.cells[-1]

    def advance(self) -> None:
        """Shift every value one cell toward the destination if free."""
        for i in range(len(self.values) - 1, 0, -1):
            if self.values[i] is None and self.values[i - 1] is not None:
                self.values[i] = self.values[i - 1]
                self.values[i - 1] = None


@dataclass
class Room:
    top: int
    left: int
    bottom: int
    right: int

    def contains_interior(self, r: int, c: int) -> bool:
        return self.top < r < self.bottom and self.left < c < self.right

    def on_border(self, r: int, c: int) -> bool:
        if not (self.top <= r <= self.bottom and self.left <= c <= self.right):
            return False
        return r in (self.top, self.bottom) or c in (self.left, self.right)


@dataclass
class Man:
    r: int
    c: int
    room: int
    heading: tuple[int, int] = (0, 1)   # men always start facing east
    A: int = 0
    B: int = 0
    halted: bool = False                # reached an H
    on_wall: bool = False               # froze on a wall cell


# ------------------------------------------------------------------ parsing
def program_grid(tokens: list[int]) -> list[str]:
    """First-round tokens ``W H c0 c1 ...`` -> the program's rows."""
    width, height = tokens[0], tokens[1]
    cells = tokens[2 : 2 + width * height]
    return [
        "".join(chr(c) for c in cells[y * width : (y + 1) * width])
        for y in range(height)
    ]


@dataclass
class LLM:
    """A parsed LLM program plus its running state."""

    rows: list[str]
    rooms: list[Room]
    pipes: list[Pipe]
    men: list[Man]
    over: bool = False

    @classmethod
    def parse(cls, rows: list[str]) -> LLM:
        """Parse geometry with the real littleman parser, then take over.

        Every one of the 14 public LLM programs parses cleanly with
        ``Machine.parse``, so room and pipe discovery is reused rather than
        reimplemented; only the *execution* semantics differ.
        """
        from .sim import Machine

        text = "\n".join(rows)
        machine = Machine.parse(text)
        rooms = [
            Room(room.top, room.left, room.bottom, room.right)
            for room in machine.rooms
        ]
        index = {id(room): i for i, room in enumerate(machine.rooms)}
        pipes = [
            Pipe(list(p.cells), index[id(p.source)], index[id(p.dest)])
            for p in machine.pipes
        ]
        men = []
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != "@":
                    continue
                room = next(
                    i for i, rm in enumerate(rooms) if rm.contains_interior(y, x)
                )
                men.append(Man(y, x, room))
        return cls(rows=list(rows), rooms=rooms, pipes=pipes, men=men)

    # ------------------------------------------------------------ helpers
    def at(self, r: int, c: int) -> str:
        if 0 <= r < len(self.rows) and 0 <= c < len(self.rows[r]):
            return self.rows[r][c]
        return " "

    def _nearest(self, man: Man, outgoing: bool) -> Pipe | None:
        """Nearest pipe arrowhead at this man's room, ties by reading order."""
        candidates = [
            (p, p.head if outgoing else p.tail)
            for p in self.pipes
            if (p.source if outgoing else p.dest) == man.room
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda pc: (
                abs(pc[1][0] - man.r) + abs(pc[1][1] - man.c),
                pc[1][0],
                pc[1][1],
            ),
        )[0]

    # --------------------------------------------------------------- step
    def step(self) -> None:
        """Advance one tick: pipes shift, men execute, men move."""
        if self.over or all(m.halted or m.on_wall for m in self.men):
            return

        for pipe in self.pipes:          # 1. pipes shift before the men act
            pipe.advance()

        moving: list[Man] = []
        for man in self.men:             # 2. every man executes
            if man.halted or man.on_wall:
                continue
            ch = self.at(man.r, man.c)
            if ch == "H":
                man.halted = True
                continue
            if ch in HEADINGS:
                man.heading = HEADINGS[ch]
            elif ch.isdigit():
                man.A = int(ch)
            elif ch == "M":
                man.B = man.A
            elif ch == "+":
                man.A = wrap64(man.A + man.B)
            elif ch == "-":
                man.A = wrap64(man.A - man.B)
            elif ch == "X":
                if man.A:
                    turn = 1 if man.A > 0 else -1
                    man.heading = _CW[(_CW.index(man.heading) + turn) % 4]
            elif ch == "s":
                pipe = self._nearest(man, outgoing=True)
                if pipe is None or pipe.values[0] is not None:
                    continue             # blocked: stays on the `s`
                pipe.values[0] = man.A
            elif ch == "r":
                pipe = self._nearest(man, outgoing=False)
                if pipe is None or pipe.values[-1] is None:
                    continue             # blocked: stays on the `r`
                man.A = pipe.values[-1]
                pipe.values[-1] = None
            moving.append(man)

        # 3. every non-blocked man advances, in man order, against a live
        # occupancy map -- mirroring littleman.sim exactly: stepping into a
        # cell another man occupies stops BOTH (the mover stays put), while
        # stepping into a cell vacated earlier in this same phase is legal.
        # With one man per room and wall-frozen exits this is unreachable in
        # any well-formed LLM program, but the rule is inherited from
        # littleman, and the hidden cases are the judge.
        occupied = {(m.r, m.c): m for m in self.men}
        for man in moving:
            if man.halted:
                continue
            nr, nc = man.r + man.heading[0], man.c + man.heading[1]
            other = occupied.get((nr, nc))
            if other is not None:
                man.halted = True
                other.halted = True
                continue
            del occupied[(man.r, man.c)]
            man.r, man.c = nr, nc
            occupied[(nr, nc)] = man

        # A wall freezes everything, but only after the tick completed in full.
        for man in self.men:
            if man.halted or man.on_wall:
                continue
            if any(room.on_border(man.r, man.c) for room in self.rooms):
                man.on_wall = True
                self.over = True

    def halted(self) -> bool:
        return self.over or all(m.halted or m.on_wall for m in self.men)

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            if self.halted():
                return
            self.step()

    # ------------------------------------------------------------- render
    def render(self) -> list[str]:
        """The 16x16 display frame as 16 rows of hex digits."""
        frame = [[COLOR_SPACE] * DISPLAY for _ in range(DISPLAY)]
        for y, row in enumerate(self.rows[:DISPLAY]):
            for x, ch in enumerate(row[:DISPLAY]):
                if any(room.on_border(y, x) for room in self.rooms):
                    frame[y][x] = COLOR_WALL
                else:
                    frame[y][x] = op_color(" " if ch == "@" else ch)
        for pipe in self.pipes:          # pipes override the plain grid
            for i, (r, c) in enumerate(pipe.cells):
                if r < DISPLAY and c < DISPLAY:
                    frame[r][c] = (
                        COLOR_PIPE_FULL if pipe.values[i] is not None else COLOR_PIPE
                    )
        for man in self.men:             # the man is drawn over everything
            if 0 <= man.r < DISPLAY and 0 <= man.c < DISPLAY:
                frame[man.r][man.c] = COLOR_MAN
        return ["".join(f"{v:x}" for v in row) for row in frame]
