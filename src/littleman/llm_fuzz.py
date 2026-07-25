"""Adversarial case generator for the LLM/LLLM interpreter problems.

Under all-or-nothing pass scoring, one hidden-case bug is worth exactly as
much as no machine, so a candidate must survive far more than the public
fixtures before submission. This module generates random *well-formed* LLLM
programs (the pipe-free subset that is also valid LLM input), runs the
validated reference interpreter (`littleman.llm`, 24/24 public frame
sequences) as the oracle, and emits cases in the same shape as
``publicTestData`` rounds — directly consumable by
``littleman.judge.judge_case``.

The generator respects the stated input contract: 4 <= W,H <= 16, a single
room, a single ``@``, every other character a valid op or space, step
commands 1..64, at most 30 rounds, no step command after the program halts.
Tick budgets differ per problem (LLLM 200, LLM 100), so the cap is a
parameter.
"""

from __future__ import annotations

import random

from .llm import LLM, program_grid
from .sim import Machine

# Weighted op alphabet: movement-heavy so men actually travel, plus enough
# arithmetic to exercise wrapping, X so headings depend on data, and H so a
# fair share of programs halt before the wall does it for them.
ALPHABET = (
    " " * 30
    + "><^v" * 4
    + "0123456789"
    + "M" * 4
    + "+" * 3
    + "-" * 3
    + "X" * 4
    + "H" * 2
)


def random_program(rng: random.Random) -> list[str]:
    """A random well-formed LLLM program as grid rows."""
    width = rng.randint(4, 16)
    height = rng.randint(4, 16)
    interior_w, interior_h = width - 2, height - 2
    cells = [
        [rng.choice(ALPHABET) for _ in range(interior_w)]
        for _ in range(interior_h)
    ]
    at_r = rng.randrange(interior_h)
    at_c = rng.randrange(interior_w)
    cells[at_r][at_c] = "@"
    top = "+" + "-" * interior_w + "+"
    rows = [top]
    rows += ["|" + "".join(line) + "|" for line in cells]
    rows.append(top)
    return rows


def program_tokens(rows: list[str]) -> list[int]:
    """First-round input tokens ``W H c0 c1 ...`` for a program grid."""
    height = len(rows)
    width = len(rows[0])
    return [width, height] + [ord(ch) for row in rows for ch in row]


def random_case(rng: random.Random, *, tick_cap: int = 200) -> dict:
    """One judge-ready case: rounds of {"in": tokens, "frames": [frame]}."""
    rows = random_program(rng)
    machine = LLM.parse(rows)
    rounds = [
        {"in": [str(t) for t in program_tokens(rows)], "frames": [machine.render()]}
    ]
    ticks_used = 0
    while (
        len(rounds) < 30
        and ticks_used < tick_cap
        and not machine.halted()
    ):
        # Small steps dominate: they sample many intermediate frames, and the
        # frames just before/after a halt are exactly where freeze-semantics
        # bugs live. Occasional large jumps keep the k<=64 range exercised.
        roll = rng.random()
        if roll < 0.7:
            step = rng.randint(1, 4)
        elif roll < 0.9:
            step = rng.randint(5, 12)
        else:
            step = rng.randint(13, 64)
        step = min(step, tick_cap - ticks_used)
        machine.run(step)
        ticks_used += step
        rounds.append({"in": [str(step)], "frames": [machine.render()]})
    return {"name": f"fuzz-{rng.random():.0f}", "rounds": rounds}


def corpus(seed: int, count: int, *, tick_cap: int = 200) -> list[dict]:
    """A deterministic list of generated cases."""
    rng = random.Random(seed)
    return [random_case(rng, tick_cap=tick_cap) for _ in range(count)]


# --------------------------------------------------------------- multi-room
# Layout strategy: a vertical chain of 2-3 rooms of a shared width, each
# consecutive pair separated by a straight 2-3 cell pipe ('v' arrowheads,
# '|' body). Room i sends (has "s") if it has a room below; room i receives
# (has "r") if it has a room above. Any room that sends must avoid '+'/'-'
# so `A` can never leave 0..9 (see SAFE_ALPHABET below).
SAFE_ALPHABET = (
    " " * 30
    + "><^v" * 4
    + "0123456789"
    + "M" * 4
    + "X" * 4
    + "H" * 2
)

# A man starting on `@` always faces east. Most rooms are only 1 interior
# row tall, so any vertical turn (or X after a nonzero digit) marches him
# straight into a wall and freezes the whole program (LLM semantics: any
# wall hit stops everything) before he ever reaches a forced `s`/`r`. To
# get real pipe traffic, the cells between `@` and each forced op on its
# carrier row are filled from this turn-free, halt-free alphabet instead.
CORRIDOR_ALPHABET = " " * 10 + "0123456789" + "M" * 3 + ">" * 3

MIN_ROOM = 3       # smallest legal room: 1x1 interior
MAX_CANVAS = 16


def _room_heights_and_gaps(rng: random.Random, n: int) -> tuple[list[int], list[int]]:
    """Room heights and inter-room gaps (each 2 or 3 rows) that fit in 16 rows."""
    for _ in range(20):
        gaps = [rng.choice([2, 3]) for _ in range(n - 1)]
        base = MIN_ROOM * n + sum(gaps)
        if base > MAX_CANVAS:
            continue
        slack = MAX_CANVAS - base
        extra = [0] * n
        for _ in range(rng.randint(0, slack)):
            extra[rng.randrange(n)] += 1
        return [MIN_ROOM + e for e in extra], gaps
    return [MIN_ROOM] * n, [2] * (n - 1)


def _assemble_llm_rows(
    rng: random.Random, width: int, heights: list[int], gaps: list[int]
) -> list[str]:
    """Draw the vertical room chain: rectangles, straight pipes, then ops."""
    n = len(heights)
    row_ranges = []
    cursor = 0
    for i, h in enumerate(heights):
        top, bottom = cursor, cursor + h - 1
        row_ranges.append((top, bottom))
        cursor = bottom + 1 + (gaps[i] if i < n - 1 else 0)
    grid = [[" "] * width for _ in range(cursor)]

    for top, bottom in row_ranges:
        grid[top][0] = grid[top][width - 1] = "+"
        grid[bottom][0] = grid[bottom][width - 1] = "+"
        for c in range(1, width - 1):
            grid[top][c] = grid[bottom][c] = "-"
        for r in range(top + 1, bottom):
            grid[r][0] = grid[r][width - 1] = "|"

    for i in range(n - 1):
        top_of_gap = row_ranges[i][1] + 1
        gap_rows = list(range(top_of_gap, top_of_gap + gaps[i]))
        col = rng.randint(1, width - 2)
        for j, r in enumerate(gap_rows):
            grid[r][col] = "v" if j in (0, len(gap_rows) - 1) else "|"

    for i, (top, bottom) in enumerate(row_ranges):
        has_out, has_in = i < n - 1, i > 0
        alphabet = SAFE_ALPHABET if has_out else ALPHABET
        interior_rows = range(top + 1, bottom)
        carrier_row = rng.choice(list(interior_rows))
        cols_needed = 1 + has_in + has_out
        chosen_cols = sorted(rng.sample(range(1, width - 1), cols_needed))
        at_col, rest = chosen_cols[0], chosen_cols[1:]
        forced = [("@", (carrier_row, at_col))]
        if has_in:
            forced.append(("r", (carrier_row, rest[0])))
            rest = rest[1:]
        if has_out:
            forced.append(("s", (carrier_row, rest[0])))
        forced_pos = {pos for _, pos in forced}
        last_col = chosen_cols[-1]
        for r in interior_rows:
            for c in range(1, width - 1):
                if (r, c) in forced_pos:
                    continue
                if r == carrier_row and at_col < c < last_col:
                    grid[r][c] = rng.choice(CORRIDOR_ALPHABET)
                else:
                    grid[r][c] = rng.choice(alphabet)
        for ch, (r, c) in forced:
            grid[r][c] = ch

    return ["".join(row) for row in grid]


def _valid_llm_rows(rows: list[str]) -> bool:
    """The legality gate: geometry via Machine.parse, plus the numeric caps."""
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if not (4 <= width <= 16 and 4 <= height <= 16):
        return False
    if any(len(r) != width for r in rows):
        return False
    try:
        machine = Machine.parse("\n".join(rows))
    except Exception:
        return False
    if not (2 <= len(machine.rooms) <= 3):
        return False
    if not (1 <= len(machine.pipes) <= 2):
        return False
    if sum(len(p.cells) for p in machine.pipes) > 20:
        return False
    if len(machine.men) != len(machine.rooms):
        return False
    return True


def random_llm_program(rng: random.Random) -> list[str]:
    """A random well-formed multi-room LLM program (2-3 rooms, 1-2 pipes)."""
    for _ in range(20):
        n = rng.choice([2, 3])
        width = rng.randint(5 if n == 3 else 4, 16)
        heights, gaps = _room_heights_and_gaps(rng, n)
        rows = _assemble_llm_rows(rng, width, heights, gaps)
        if _valid_llm_rows(rows):
            return rows
    # Bounded retries exhausted (should not happen): simplify to the
    # smallest guaranteed-legal 2-room, 1-pipe, 2-cell-pipe layout.
    rows = _assemble_llm_rows(rng, 4, [3, 3], [2])
    assert _valid_llm_rows(rows)
    return rows


def random_llm_case(rng: random.Random, *, tick_cap: int = 100) -> dict:
    """One judge-ready multi-room case, mirroring random_case's round shape."""
    rows = random_llm_program(rng)
    machine = LLM.parse(rows)
    rounds = [
        {"in": [str(t) for t in program_tokens(rows)], "frames": [machine.render()]}
    ]
    ticks_used = 0
    while (
        len(rounds) < 30
        and ticks_used < tick_cap
        and not machine.halted()
    ):
        roll = rng.random()
        if roll < 0.7:
            step = rng.randint(1, 4)
        elif roll < 0.9:
            step = rng.randint(5, 12)
        else:
            step = rng.randint(13, 64)
        step = min(step, tick_cap - ticks_used)
        machine.run(step)
        ticks_used += step
        rounds.append({"in": [str(step)], "frames": [machine.render()]})
    return {"name": f"llm-fuzz-{rng.random():.0f}", "rounds": rounds}


def llm_corpus(seed: int, count: int) -> list[dict]:
    """A deterministic list of generated multi-room cases."""
    rng = random.Random(seed)
    return [random_llm_case(rng) for _ in range(count)]
