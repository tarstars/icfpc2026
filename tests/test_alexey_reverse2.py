"""Stress tests for the corridor-free shrinking-ring reverse (reverse_01).

Two properties are worth hammering. The ring-in pipe must hold a full
16-value list with no `q` to count it, and the B-carried ring size must
survive every path through the machine — including the j == 1 cycle that
relays nothing and the j == 0 cycle that leaves for the input lane.
Round boundaries are where a stale counter would show up, so list sizes
churn across rounds.
"""

import random

from littleman.alexey_reverse2 import build_reverse2
from littleman.judge import footprint, judge_case
from littleman.sim import Machine

LIMIT = 10**6


def _run(lists):
    rounds = [{"in": [len(xs)] + xs, "out": xs[::-1]} for xs in lists]
    return judge_case(build_reverse2(), rounds, max_ticks=200_000)


def test_footprint_and_ring_capacity():
    text = build_reverse2()
    assert footprint(text) == 256
    ring_in = max(Machine.parse(text).pipes, key=lambda p: len(p.cells))
    assert len(ring_in.cells) >= 16  # one cell per parked value at n = 16


def test_worst_case_shapes():
    full = list(range(-8, 8))
    cases = [
        [[7]],                                   # single value, single round
        [[1], [2], [3]],                         # three 1-element rounds
        [list(range(16))],                       # max ring, one round
        [list(range(16))] * 3,                   # max ring, every round
        [[0] * 16],                              # all equal at max size
        [[LIMIT, -LIMIT] * 8],                   # extremes interleaved
        [[-LIMIT] * 16],
        [full, [3], full],                       # 16 -> 1 -> 16 size churn
        [[1, 2], list(range(16)), [5]],
        [list(range(16, 0, -1)), [0], [9, 9]],
    ]
    for lists in cases:
        res = _run(lists)
        assert res.passed, (lists, res.reason)


def test_randomized_sweep():
    rng = random.Random(20260724)
    for trial in range(250):
        lists = []
        for _ in range(rng.randint(1, 3)):
            n = 16 if trial % 3 == 0 else rng.randint(1, 16)
            base = rng.choice([LIMIT, 1000, 2])
            lists.append([rng.randint(-base, base) for _ in range(n)])
        res = _run(lists)
        assert res.passed, (trial, lists, res.reason)
