"""Stress tests for the compact shrinking-ring sort (sort_03 candidate).

The fragile part of the compact geometry is the delay corridor: `q` must
not run before every circulating value is back inside the ring-return
pipe. These tests hammer the worst timing cases (n = 16, extremes,
duplicates) plus a broad randomized sweep within the problem's stated
constraints (1 <= n <= 16, |x| <= 10000, 2-6 lists per case).
"""

import random

from littleman.alexey_sort_ring2 import build_sort_ring2
from littleman.judge import footprint, judge_case


def _rounds(lists):
    return [{"in": [len(xs)] + xs, "out": sorted(xs)} for xs in lists]


def _run(lists):
    return judge_case(build_sort_ring2(), _rounds(lists))


def test_footprint():
    assert footprint(build_sort_ring2()) == 361


def test_worst_case_shapes():
    full = list(range(-8, 8))
    cases = [
        [[5]],                                   # single value, single round
        [[0] * 16, [0] * 16],                    # all equal at max size
        [list(range(16, 0, -1))] * 3,            # reverse sorted, max size
        [list(range(16))] * 3,                   # already sorted, max size
        [[10000, -10000] * 8],                   # extremes interleaved
        [[-10000] * 8 + [10000] * 8],
        [full, full[::-1], [7], full, [1, 1]],   # size churn across rounds
        [[1], [2], [3], [4], [5], [6]],          # six 1-element rounds
    ]
    for lists in cases:
        res = _run(lists)
        assert res.passed, (lists, res.reason)


def test_randomized_sweep():
    rng = random.Random(20260724)
    for trial in range(300):
        n_lists = rng.randint(2, 6)
        lists = []
        for _ in range(n_lists):
            n = 16 if trial % 3 == 0 else rng.randint(1, 16)
            base = rng.choice([10000, 100, 3])
            lists.append([rng.randint(-base, base) for _ in range(n)])
        res = _run(lists)
        assert res.passed, (trial, lists, res.reason)
