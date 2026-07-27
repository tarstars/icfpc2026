"""Physical gates for the LLM nearest-endpoint score."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_bindscore import bindscore_reference, build_bindscore_rig
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = bindscore_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_bindscore_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_bindscore_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_score_is_exact_for_grid_and_random_pairs(text):
    tokens = []
    for man in range(256):
        for endpoint in (0, 15, 240, 255, man):
            tokens.extend((man, endpoint))
    rng = random.Random(20260726)
    for _ in range(1_000):
        tokens.extend((rng.randrange(256), rng.randrange(256)))
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_score_orders_distance_then_reading_order():
    man = 5 * 16 + 5
    endpoints = [5 * 16 + 7, 3 * 16 + 5, 4 * 16 + 4]
    scores = bindscore_reference(
        [item for endpoint in endpoints for item in (man, endpoint)]
    )
    assert min(zip(scores, endpoints))[1] == 3 * 16 + 5
