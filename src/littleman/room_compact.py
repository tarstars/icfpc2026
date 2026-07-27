"""Do by machine what a human does in the visual editor: compact, then shave.

`docs/MANIFEST.md` step 3. The measured prize:

    alexey-reverse_06  14x14  fp 196  98,676  ticks 503.4
    alexey-reverse_07  13x13  fp 169  84,922  ticks 502.5   box -1, ticks FLAT

One cell off the binding dimension, ticks unchanged, 0.862x score. Score is
``max(w, h) ** 2 * ticks``, so that single row beat every tick optimisation
we have done. `memory_10 -> _11` is the same move, 30x30 -> 29x29.

Our existing squeeze could never find these: it deletes rows that are
**already blank**, and memory, brackets and matmul have none. The human
operation is strictly larger — *compact the content until a row becomes
blank, and only then delete it.* This module is that operation.

## The safe primitive

Most random edits to a room break it instantly (the man walks into a wall
or onto a bad op), so a blind search wastes all its time on corpses.
Instead every move here is drawn from one family that is behaviour-
preserving by construction:

    on a straight run of the man's path, swap a NON-ARROW glyph with an
    adjacent BLANK cell that lies on the same run

The man still traverses the same cells in the same order and executes the
same instruction sequence — only the position of the instruction inside
the run changes. Tick count is identical. Arrows are never moved, because
they are what *define* the path.

What a slide does change is **where cells sit**, and that is the point:
slide enough content out of a column and the column becomes blank, at
which point `room_shrink` can delete it and the box drops.

It also changes distances, and `r`/`s` bind to the **nearest** pipe by
distance from the cell — so a slide can silently rewire the machine. That
is checked, along with the full behavioural contract, by
`room_shrink.verify`, which is the only thing allowed to approve a
candidate here.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import judge, room_shrink, sim

ARROWS = frozenset("<>^vV")
# `@` is where a man begins and must not move; walls/backticks are structural.
IMMOVABLE = ARROWS | frozenset("@+-|`")


@dataclass
class Slide:
    """Move `glyph` from `src` to `dst`, both on one straight run."""

    src: tuple[int, int]
    dst: tuple[int, int]
    glyph: str


def walked(text: str, cases, max_ticks: int = 2_000_000
           ) -> dict[tuple[int, int], set[tuple[int, int]]]:
    """Cells the men actually traverse, and with which direction(s).

    Derived from real runs rather than a static graph, so a cell only counts
    if the program truly reaches it — a static over-approximation would
    invite slides on dead code that no contract could validate.
    """
    seen: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for case in cases:
        machine = sim.Machine.parse(text)
        rounds = judge.normalize_case(case)
        original = machine._tick

        def traced(res, _m=machine, _o=original, _s=seen):
            err = _o(res)
            for man in _m.men:
                if not man.halted:
                    _s.setdefault((man.r, man.c), set()).add(man.direction)
            return err

        machine._tick = traced
        machine.run(max_ticks=max_ticks,
                    controller=judge.RoundController(rounds))
    return seen


def _grid(text: str) -> list[str]:
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    width = max((len(line) for line in lines), default=0)
    return [line.ljust(width) for line in lines]


def slides_toward(text: str, cases, target_col: int | None = None,
                  target_row: int | None = None) -> list[Slide]:
    """Every legal slide that moves a glyph OFF the target row/column.

    A slide is legal when the glyph is movable, the destination is blank,
    and both cells are traversed in the same direction — i.e. they lie on
    one straight run, so swapping them cannot reorder execution.
    """
    grid = _grid(text)
    paths = walked(text, cases)
    height = len(grid)
    width = len(grid[0]) if height else 0
    out: list[Slide] = []

    for (row, col), directions in paths.items():
        if row >= height or col >= width:
            continue
        glyph = grid[row][col]
        if glyph == " " or glyph in IMMOVABLE:
            continue
        if target_col is not None and col != target_col:
            continue
        if target_row is not None and row != target_row:
            continue
        for d_row, d_col in directions:
            for step in (1, -1):        # forward or backward along the run
                nr, nc = row + d_row * step, col + d_col * step
                if not (0 <= nr < height and 0 <= nc < width):
                    continue
                if grid[nr][nc] != " ":
                    continue
                if (nr, nc) not in paths:
                    continue
                if (d_row, d_col) not in paths[(nr, nc)]:
                    continue        # not the same straight run
                out.append(Slide((row, col), (nr, nc), glyph))
    return out


def apply_slides(text: str, slides: list[Slide]) -> str:
    grid = [list(line) for line in _grid(text)]
    for slide in slides:
        sr, sc = slide.src
        dr, dc = slide.dst
        if grid[sr][sc] != slide.glyph or grid[dr][dc] != " ":
            continue                 # a previous slide invalidated this one
        grid[dr][dc] = slide.glyph
        grid[sr][sc] = " "
    return "\n".join("".join(row).rstrip() for row in grid) + "\n"


def column_occupancy(text: str) -> list[int]:
    grid = _grid(text)
    width = len(grid[0]) if grid else 0
    return [sum(1 for row in grid if row[c] != " ") for c in range(width)]


def row_occupancy(text: str) -> list[int]:
    return [sum(1 for ch in row if ch != " ") for row in _grid(text)]


def compact_and_shave(text: str, cases, max_ticks: int = 5_000_000,
                      report=None):
    """Try to vacate each sparse row/column, then delete it.

    Sparsest first: a column holding two glyphs needs two successful slides,
    one holding twenty is hopeless. Returns the best verified candidate, or
    None. `report` is an optional callable for progress lines.
    """
    def say(message):
        if report:
            report(message)

    best = None
    cols = column_occupancy(text)
    rows = row_occupancy(text)
    order = ([("col", c, n) for c, n in enumerate(cols) if 0 < n <= 6]
             + [("row", r, n) for r, n in enumerate(rows) if 0 < n <= 6])
    order.sort(key=lambda t: t[2])
    say(f"{len(order)} sparse lines worth attempting")

    for kind, index, count in order:
        slides = (slides_toward(text, cases, target_col=index) if kind == "col"
                  else slides_toward(text, cases, target_row=index))
        if len(slides) < count:
            continue                 # cannot empty it; do not waste a replay
        moved = apply_slides(text, slides)
        occupancy = (column_occupancy(moved) if kind == "col"
                     else row_occupancy(moved))
        if index >= len(occupancy) or occupancy[index] != 0:
            continue
        candidate = (room_shrink.drop_column(moved, index) if kind == "col"
                     else room_shrink.drop_row(moved, index))
        verdict = room_shrink.verify(text, candidate, cases, max_ticks)
        say(f"  {kind} {index} (occupancy {count}): "
            f"{'ACCEPTED' if verdict.ok else verdict.reason}")
        if verdict.ok:
            best = (candidate, verdict)
            break
    return best
