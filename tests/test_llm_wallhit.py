"""Physical gates for the LLM wall-freeze predicate."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_wallhit import build_wallhit_rig, wallhit_reference
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
        self.expected = wallhit_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_wallhit_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_wallhit_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_wall_hits(text):
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


def test_each_wall_and_interior():
    bounds = (2, 3, 10, 12, 6)
    addrs = [2 * 16 + 7, 10 * 16 + 7, 6 * 16 + 3, 6 * 16 + 12, 6 * 16 + 7]
    tokens = [item for addr in addrs for item in record(*bounds, addr)]
    assert wallhit_reference(tokens) == [1, 1, 1, 1, 0]
