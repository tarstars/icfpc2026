"""Physical gates for STATEFRAME to DRAW adaptation."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_pairpack import (
    build_pairpack_rig,
    pairpack_reference,
)
from littleman.llm_stateframe import FRAME_END
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = pairpack_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if value == FRAME_END else None


@pytest.fixture(scope="module")
def text():
    return build_pairpack_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pairpack_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_pair_packing(text):
    rng = random.Random(20260726)
    tokens = []
    for _ in range(2_000):
        tokens.extend((rng.randrange(16), rng.randrange(256)))
    tokens.append(FRAME_END)
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=20_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_address_zero_color_zero_and_maximum():
    assert pairpack_reference([0, 0, 15, 255, FRAME_END]) == [
        0,
        4095,
        FRAME_END,
    ]
