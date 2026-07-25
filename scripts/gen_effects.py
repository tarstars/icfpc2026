#!/usr/bin/env python
"""Generate the per-opcode effects table by probing the engine, not prose.

Motivation (docs/architecture/claude_01_measured_ground_truth.md §1): the
cookbook carried a wrong register-destruction list for two days. This script
derives {writes, turns, halts, may_block} per opcode *empirically* -- it
stands a man on each opcode with hundreds of randomized (A, B, BP) states,
executes exactly one instruction via the real engine, and records which
registers ever change. Whatever this prints is what the simulator does;
disagreement with any document is a documentation bug by definition.

Usage:  uv run python scripts/gen_effects.py > docs/architecture/claude_effects.json
"""

from __future__ import annotations

import json
import random
import sys

from littleman.sim import Machine

# Opcodes probed in a plain room context (no pipes needed).
PLAIN_OPS = "0123456789MW+-*/%N&|~{}Xbmdax]H.< >^v"

# Opcodes that require a pipe on the room: probed with both an incoming and
# an outgoing pipe attached so the instruction is legal.
PIPE_OPS = "srqRUS"

SEEDS = 400
RNG = random.Random(20260725)

INTERESTING = [
    0, 1, -1, 9, -9, 63, 64, -64, 2**62, -(2**62), 2**63 - 1, -(2**63),
]


def sample_state():
    def val():
        if RNG.random() < 0.4:
            return RNG.choice(INTERESTING)
        return RNG.randint(-(2**63), 2**63 - 1)

    return val(), val(), val()


DIRECTIONS = [(0, 1), (0, -1), (-1, 0), (1, 0)]


def build_plain(op: str) -> Machine:
    machine = Machine.parse("\n".join(["+-----+", "|  @  |", "+-----+"]))
    man = machine.men[0]
    machine.grid[man.r][man.c] = op   # the opcode under test, under the man
    return machine


def build_piped(op: str):
    # one incoming pipe (fed by the left room) and one outgoing (to the right)
    text = "\n".join([
        "+---+   +-----+   +---+",
        "|@sH|>->|  @  |>->|@rH|",
        "+---+   +-----+   +---+",
    ])
    machine = Machine.parse(text)
    man = machine.men[1]  # middle room's man
    machine.grid[man.r][man.c] = op
    incoming = [p for p in machine.pipes if p.dest is man.room][0]
    outgoing = [p for p in machine.pipes if p.source is man.room][0]
    return machine, man, incoming, outgoing


def probe(op: str, piped: bool) -> dict:
    writes = {"A": False, "B": False, "BP": False}
    turns = False
    halts = False
    blocked_seen = False
    a_depends_on_b = False

    for _ in range(SEEDS):
        if piped:
            machine, man, incoming, outgoing = build_piped(op)
            # half the seeds can proceed, half must block: empty vs full
            # incoming (for r/R/U/q) and free vs occupied outgoing (for s/S)
            if RNG.random() < 0.5:
                incoming.values[-1] = RNG.randint(-9, 9)
            if RNG.random() < 0.5:
                outgoing.values[0] = RNG.randint(-9, 9)
        else:
            machine = build_plain(op)
            man = machine.men[0]
        a, b, bp = sample_state()
        man.A, man.B, man.BP = a, b, bp
        man.direction = RNG.choice(DIRECTIONS)
        d0 = man.direction
        machine._execute(man)
        if man.A != a:
            writes["A"] = True
        if man.B != b:
            writes["B"] = True
        if man.BP != bp:
            writes["BP"] = True
        if man.direction != d0:
            turns = True
        if man.halted:
            halts = True
        if man.blocked or man.wait_kind:
            blocked_seen = True
        # crude read-inference for A: same A, different B
        if not piped and op in "+-*/%&|~{}":
            machine2 = build_plain(op)
            man2 = machine2.men[0]
            man2.A, man2.B, man2.BP = a, b ^ 0x5A5A, bp
            man2.direction = d0
            machine2._execute(man2)
            if man2.A != man.A:
                a_depends_on_b = True

    out = {
        "writes": sorted(k for k, v in writes.items() if v),
        "turns": turns,
        "halts": halts,
        "may_block": blocked_seen,
    }
    if op in "+-*/%&|~{}":
        out["A_depends_on_B"] = a_depends_on_b
    return out


def main() -> int:
    table = {}
    for op in PLAIN_OPS:
        if op == " ":
            continue
        table[op] = probe(op, piped=False)
    for op in PIPE_OPS:
        table[op] = probe(op, piped=True)

    b_writers = sorted(op for op, e in table.items() if "B" in e["writes"])
    result = {
        "generated_by": "scripts/gen_effects.py",
        "seeds_per_op": SEEDS,
        "engine": "littleman.sim.Machine._execute",
        "headline": {
            "B_written_only_by": b_writers,
            "BP_written_by": sorted(
                op for op, e in table.items() if "BP" in e["writes"]
            ),
        },
        "ops": {op: table[op] for op in sorted(table)},
    }
    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
