"""Physical gates for eligibility-aware LLM pipe selection."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_selecteligible import (
    build_selecteligible_rig,
    selecteligible_reference,
)
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = selecteligible_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_selecteligible_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_selecteligible_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_eligible_selection(text):
    rng = random.Random(20260726)
    tokens = []
    for _ in range(2_000):
        eligibility = rng.choice(((1, 0), (0, 1), (1, 1)))
        tokens.extend(
            (
                rng.randrange(256),
                *eligibility,
                rng.randrange(256),
                rng.randrange(256),
            )
        )
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_tie_and_single_eligible_cases():
    man = 5 * 16 + 5
    assert selecteligible_reference([man, 1, 1, 5 * 16 + 7, 3 * 16 + 5]) == [1]
    assert selecteligible_reference([man, 1, 0, 255, 0]) == [0]
    assert selecteligible_reference([man, 0, 1, 0, 255]) == [1]
