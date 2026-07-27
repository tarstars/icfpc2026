"""Shave a row or column while PROVING the behaviour is unchanged.

Step 2 of `docs/MANIFEST.md`. Score is ``max(w, h) ** 2 * ticks``, so a
single row or column off the binding dimension is worth more than a large
tick win: reverse went 14x14 -> 13x13 at essentially unchanged ticks
(503.4 -> 502.5) for a 0.862x score, and memory went 30x30 -> 29x29 for
0.934x.

Two things separate this from the blunt squeeze we already had, both
learned by losing candidates to them:

* **It verifies behaviour, not just passing tests.** The old squeeze kept
  anything that passed the public cases. That is not evidence: a shortened
  storage pipe deadlocks only on inputs the public set never reaches --
  alexey's subset-sum squeeze was 0/7 that way, and a snake squeeze of mine
  passed 5/5 public and died at snake-length 68. Here every candidate must
  reproduce each room's **boundary contract** (`room_lab`) exactly, and must
  not shorten any pipe or rebind any I/O cell.

* **It can MAKE a row blank rather than only finding one.** The blunt
  squeeze deletes rows that are already empty, which is why it found
  nothing on memory, brackets or matmul. A human in the visual editor
  compacts content until a row frees up, then deletes it -- that is the
  operation that actually wins, and `compact_candidates` is the mechanical
  version of it.

Nothing here submits or judges; `scripts/preflight.py` remains the final
authority and should run on anything this proposes.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import room_lab, room_reflow, sim


def _grid(text: str) -> list[str]:
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    width = max((len(line) for line in lines), default=0)
    return [line.ljust(width) for line in lines]


def _text(grid: list[str]) -> str:
    return "\n".join(line.rstrip() for line in grid) + "\n"


def pipe_lengths(text: str) -> list[int]:
    machine = sim.Machine.parse(text)
    return sorted(len(pipe.cells) for pipe in machine.pipes)


def box(text: str) -> int:
    grid = _grid(text)
    return max(max((len(line.rstrip()) for line in grid), default=0), len(grid))


def drop_row(text: str, row: int) -> str:
    grid = _grid(text)
    return _text(grid[:row] + grid[row + 1:])


def drop_column(text: str, col: int) -> str:
    grid = _grid(text)
    return _text([line[:col] + line[col + 1:] for line in grid])


@dataclass
class Verdict:
    ok: bool
    reason: str = ""
    box_before: int = 0
    box_after: int = 0


def verify(before: str, after: str, cases, max_ticks: int = 5_000_000
           ) -> Verdict:
    """Is `after` the same machine, only smaller?

    Checks in cost order, cheapest first, so a bad candidate is rejected in
    milliseconds rather than after a full replay.
    """
    b_box, a_box = box(before), box(after)
    if a_box >= b_box:
        return Verdict(False, "box did not shrink", b_box, a_box)

    try:
        b_pipes, a_pipes = pipe_lengths(before), pipe_lengths(after)
    except Exception as exc:                     # parse/load failure
        return Verdict(False, f"does not load: {type(exc).__name__}", b_box, a_box)

    if len(a_pipes) != len(b_pipes):
        return Verdict(False, f"pipe count {len(b_pipes)} -> {len(a_pipes)}",
                       b_box, a_box)
    # A pipe's length is its delay AND its capacity. Longer is usually
    # harmless; SHORTER deadlocks with no other symptom.
    shrunk = [(x, y) for x, y in zip(b_pipes, a_pipes) if y < x]
    if shrunk:
        return Verdict(False, f"pipes shortened {shrunk}", b_box, a_box)

    # `r`/`s` bind to the NEAREST pipe by distance from the cell, so moving
    # cells silently rewires the machine -- the failure that deadlocked the
    # pathfinder fold while every structural check passed.
    before_bind = room_reflow.binding_map(before)
    after_bind = room_reflow.binding_map(after)
    if sorted(before_bind.values()) != sorted(after_bind.values()):
        return Verdict(False, "I/O cells rebound to different pipes",
                       b_box, a_box)

    b_contracts = room_lab.record_all(before, cases, max_ticks)
    a_contracts = room_lab.record_all(after, cases, max_ticks)
    if set(b_contracts) != set(a_contracts):
        return Verdict(False, "room set changed", b_box, a_box)
    for index in b_contracts:
        if not b_contracts[index].events():
            return Verdict(False, f"room {index} contract is empty "
                                  "(would pass vacuously)", b_box, a_box)
        if not room_lab.same_behaviour(b_contracts[index], a_contracts[index]):
            return Verdict(False, f"room {index} behaviour changed",
                           b_box, a_box)
    return Verdict(True, "same behaviour, smaller box", b_box, a_box)


def blank_candidates(text: str) -> list[tuple[str, int]]:
    """Rows/columns that are already empty -- what a blunt squeeze finds."""
    grid = _grid(text)
    height = len(grid)
    width = max((len(line) for line in grid), default=0)
    out: list[tuple[str, int]] = []
    out += [("row", r) for r in range(height) if not grid[r].strip()]
    out += [("col", c) for c in range(width)
            if all(grid[r][c] == " " for r in range(height))]
    return out


def shave(text: str, cases, max_ticks: int = 5_000_000):
    """Try every already-blank row/column; return the surviving candidates."""
    results = []
    for kind, index in blank_candidates(text):
        candidate = (drop_row(text, index) if kind == "row"
                     else drop_column(text, index))
        verdict = verify(text, candidate, cases, max_ticks)
        results.append((kind, index, verdict, candidate if verdict.ok else None))
    return results
