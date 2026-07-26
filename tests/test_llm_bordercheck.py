"""Physical gates for destination-room ownership checks."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_bordercheck import (
    bordercheck_reference,
    build_bordercheck_rig,
)
from littleman.sim import Machine


def record(top, left, bottom, right, man_row, addr):
    return [
        man_row * 16 + left,
        man_row * 16 + right,
        top * 16 + left,
        bottom * 16 + left,
        addr,
    ]


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = bordercheck_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_bordercheck_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_bordercheck_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_rectangle_ownership(text):
    rng = random.Random(20260726)
    tokens = []
    for _ in range(2_000):
        top = rng.randrange(15)
        bottom = rng.randrange(top + 1, 16)
        left = rng.randrange(15)
        right = rng.randrange(left + 1, 16)
        man_row = rng.randrange(top, bottom + 1)
        addr = rng.randrange(256)
        tokens.extend(record(top, left, bottom, right, man_row, addr))
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_edges_are_inside_and_adjacent_cells_are_outside():
    bounds = (2, 3, 10, 12, 6)
    tokens = []
    expected = []
    for addr in (2 * 16 + 3, 10 * 16 + 12, 6 * 16 + 7, 1 * 16 + 7):
        tokens.extend(record(*bounds, addr))
        expected.append(int(addr != 1 * 16 + 7))
    assert bordercheck_reference(tokens) == expected
