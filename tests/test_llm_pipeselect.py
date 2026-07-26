"""Physical gates for nearest LLM pipe selection."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_pipeselect import (
    build_pipeselect_rig,
    pipeselect_reference,
)
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = pipeselect_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipeselect_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipeselect_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_one_and_two_candidate_requests(text):
    tokens = []
    rng = random.Random(20260726)
    for _ in range(2_000):
        man = rng.randrange(256)
        if rng.randrange(4) == 0:
            tokens.extend((man, 1, rng.randrange(256)))
        else:
            tokens.extend((man, 2, rng.randrange(256), rng.randrange(256)))
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_ties_choose_reading_order_then_first_slot():
    man = 5 * 16 + 5
    assert pipeselect_reference([man, 2, 5 * 16 + 7, 3 * 16 + 5]) == [1]
    assert pipeselect_reference([man, 2, 3 * 16 + 5, 3 * 16 + 5]) == [0]
