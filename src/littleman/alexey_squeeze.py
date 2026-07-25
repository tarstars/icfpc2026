"""Mechanical whole-program squeeze: delete rows and columns that carry nothing.

A row whose every cell is `' '` or `'|'` holds no instruction, no wall corner
and no horizontal run. Deleting it shortens by one cell every room interior
and every vertical pipe it crosses, and changes nothing else -- a little man
walks over blanks, so his path is identical apart from being one tick
shorter. Columns of `' '` and `'-'` are the transpose of the same argument.

This is the cheapest geometry win there is: no room is re-laid, no pipe is
re-routed, nothing is moved. It found slack in five of our nine live
programs, and because the surviving pipes get shorter it usually buys TICKS
as well as footprint -- on sudoku and plotter far more of the score came
from ticks than from area.

Measured on 2026-07-25 (footprint before -> after, live score before -> after):

    sudoku     81,796 -> 61,504   105,335,908,125 -> 25,480,732,026  (4.13x)
    plotter   194,481 -> 148,225   75,794,498,065 -> 16,905,772,730  (4.48x)
    gradebook 206,116 -> 178,929  104,303,579,600 -> 81,914,188,255  (1.27x)
    tcp         1,444 -> 1,369         5,981,626 -> 5,655,750        (1.06x)
    memory      2,209 -> 2,116        91,372,248 -> 87,493,514       (1.04x, rows only)

    reverse / sort / brackets / history: zero deletable rows or columns.
    Those four are already tight; do not spend time looking again.

IT IS NOT UNCONDITIONALLY SAFE, so always re-judge. Two failures observed:

* `memory` survives the row pass (7/7) but breaks on the column pass (2/7).
  Deleting a column moves every cell left of nothing and every cell right of
  it one step closer to the left wall, which changes Manhattan distances and
  therefore which pipe an `r`/`s` resolves to. `memory` has reads whose
  margin between two candidate pipes is a single step.
* `matmul` breaks on both passes (0/7 and 6/7). Its footprint is
  width-bound, so only the column pass would have paid anyway.

Use `squeeze(text, rows=True, cols=True)` and fall back to rows-only or
cols-only when the full pass fails; that is how memory_02 was salvaged.
Re-check pipe lengths afterwards too (`alexey_pipecheck.check`): squeezing
can shorten a two-cell pipe to one cell, which the server rejects at load.
"""


def deletable_rows(grid: list[str]) -> list[int]:
    return [i for i, row in enumerate(grid) if all(ch in " |" for ch in row)]


def deletable_cols(grid: list[str]) -> list[int]:
    width = len(grid[0])
    return [j for j in range(width) if all(row[j] in " -" for row in grid)]


def squeeze(program: str, rows: bool = True, cols: bool = True):
    """Return (squeezed_program, rows_dropped, cols_dropped)."""
    grid = program.rstrip("\n").split("\n")
    width = max(len(line) for line in grid)
    grid = [line.ljust(width) for line in grid]

    dropped_rows = set(deletable_rows(grid)) if rows else set()
    grid = [row for i, row in enumerate(grid) if i not in dropped_rows]

    dropped_cols = set(deletable_cols(grid)) if cols else set()
    grid = ["".join(ch for j, ch in enumerate(row) if j not in dropped_cols) for row in grid]

    return "\n".join(row.rstrip() for row in grid) + "\n", len(dropped_rows), len(dropped_cols)
