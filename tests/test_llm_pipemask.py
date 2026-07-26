"""Packed occupancy transition tests for interpreted LLM pipes."""

from __future__ import annotations

import random

from littleman import alexey_pipecheck, server_compat
from littleman.llm_pipemask import advance_mask, build_pipemask_rig
from littleman.sim import Machine


def slow(mask: int, width: int) -> int:
    values = [bool(mask & (1 << bit)) for bit in range(width)]
    for index in range(1, width):
        if not values[index - 1] and values[index]:
            values[index - 1] = True
            values[index] = False
    return sum(value << bit for bit, value in enumerate(values))


def test_formula_exhaustive_through_twelve_cells():
    for width in range(1, 13):
        for logical in range(1 << width):
            barrier_width = 20 - width
            barrier = (1 << barrier_width) - 1
            packed = barrier | (logical << barrier_width)
            expected = barrier | (slow(logical, width) << barrier_width)
            assert advance_mask(packed) == expected


class Script:
    def __init__(self, masks):
        self.input = list(masks)
        self.expected = [advance_mask(mask) for mask in masks]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


def test_physical_random_parity_and_layout():
    text = build_pipemask_rig()
    assert build_pipemask_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    rng = random.Random(20260726)
    masks = [rng.randrange(1 << 20) | 1 for _ in range(1_000)]
    script = Script(masks)
    result = Machine.parse(text).run(max_ticks=2_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
