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
