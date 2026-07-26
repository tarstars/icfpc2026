"""Reference model for the proposed three-column packed MatMul kernel.

For three adjacent output columns, pack shifted B values into 20-bit lanes:

    P_t = (b[t,j]   + 100)
        + (b[t,j+1] + 100) * 2**20
        + (b[t,j+2] + 100) * 2**40

For a row factor x_t = a[i,t] + 100, accumulate R += x_t * P_t. Because
M <= 16 and every shifted operand is in 1..199, each lane stays below 2**20,
so ordinary 64-bit multiplication and addition act as three independent
lanes without carries between them.
"""

from __future__ import annotations

from random import Random
from typing import Sequence

LANE_BITS = 20
LANE_BASE = 1 << LANE_BITS
LANE_MASK = LANE_BASE - 1
SHIFT = 100


def pack_b_group(row: Sequence[int], start: int) -> int:
    """Pack up to three B-row values beginning at *start*."""
    packed = 0
    for lane in range(3):
        column = start + lane
        if column < len(row):
            packed |= (row[column] + SHIFT) << (LANE_BITS * lane)
    return packed


def multiply(A: Sequence[Sequence[int]], B: Sequence[Sequence[int]]) -> list[list[int]]:
    """Exact matrix multiplication through three packed output lanes."""
    n = len(A)
    m = len(A[0])
    k = len(B[0])
    assert len(B) == m

    groups = (k + 2) // 3
    packed_b = [
        [pack_b_group(B[t], 3 * group) for group in range(groups)]
        for t in range(m)
    ]

    # Shifted column sums can be accumulated with the same lane packing.
    shifted_b_sums = [0] * groups
    for t in range(m):
        for group in range(groups):
            shifted_b_sums[group] += packed_b[t][group]

    result: list[list[int]] = []
    for row in A:
        shifted_a = [value + SHIFT for value in row]
        shifted_a_sum = sum(shifted_a)
        accumulators = [0] * groups
        for t, x in enumerate(shifted_a):
            for group in range(groups):
                accumulators[group] += x * packed_b[t][group]

        output_row: list[int] = []
        for group, packed_sum in enumerate(accumulators):
            for lane in range(3):
                column = 3 * group + lane
                if column >= k:
                    break
                raw = (packed_sum >> (LANE_BITS * lane)) & LANE_MASK
                shifted_b_sum = (
                    shifted_b_sums[group] >> (LANE_BITS * lane)
                ) & LANE_MASK
                # R = sum((a+100)(b+100)). Using shifted sums avoids carrying
                # signed column sums as a second representation.
                value = (
                    raw
                    - SHIFT * shifted_a_sum
                    - SHIFT * shifted_b_sum
                    + m * SHIFT * SHIFT
                )
                output_row.append(value)
        result.append(output_row)
    return result


def naive(A: Sequence[Sequence[int]], B: Sequence[Sequence[int]]) -> list[list[int]]:
    """Straightforward oracle implementation."""
    return [
        [
            sum(A[i][t] * B[t][j] for t in range(len(B)))
            for j in range(len(B[0]))
        ]
        for i in range(len(A))
    ]


def self_test(seed: int = 20260726, trials: int = 5_000) -> None:
    """Exercise extremes, legal random shapes, and the arithmetic bounds."""
    rng = Random(seed)
    directed = (-99, 99)
    for a in directed:
        for b in directed:
            A = [[a] * 16 for _ in range(16)]
            B = [[b] * 16 for _ in range(16)]
            assert multiply(A, B) == naive(A, B)

    for _ in range(trials):
        n = rng.randint(2, 16)
        m = rng.randint(2, 16)
        k = rng.randint(2, 16)
        A = [[rng.randint(-99, 99) for _ in range(m)] for _ in range(n)]
        B = [[rng.randint(-99, 99) for _ in range(k)] for _ in range(m)]
        assert multiply(A, B) == naive(A, B)

    max_packed_b = 199 * (1 + (1 << 20) + (1 << 40))
    max_term = 199 * max_packed_b
    max_accumulator = 16 * max_term
    assert max_accumulator < 1 << 63
    assert 16 * 199 * 199 < 1 << LANE_BITS


if __name__ == "__main__":
    self_test()
    print("packed three-lane MatMul reference: all tests passed")
