"""Physical gates for filtering LLM pipe candidates."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_pipeapply import OP_RECV, OP_SEND
from littleman.llm_pipecandidate import (
    build_pipecandidate_rig,
    pipecandidate_reference,
)
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = pipecandidate_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipecandidate_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipecandidate_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_send_and_receive_candidates(text):
    rng = random.Random(20260726)
    tokens = []
    for _ in range(2_000):
        top = rng.randrange(15)
        bottom = rng.randrange(top + 1, 16)
        left = rng.randrange(15)
        right = rng.randrange(left + 1, 16)
        man_row = rng.randrange(top, bottom + 1)
        room = rng.randrange(3)
        source = rng.randrange(3)
        op = rng.randrange(2)
        tokens.extend(
            (
                op,
                room,
                source,
                man_row * 16 + left,
                man_row * 16 + right,
                top * 16 + left,
                bottom * 16 + left,
                rng.randrange(256),
                rng.randrange(256),
            )
        )
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


@pytest.mark.parametrize(
    ("op", "room", "source", "dest", "expected"),
    [
        (OP_SEND, 1, 1, 0, 1),
        (OP_SEND, 1, 0, 35, 0),
        (OP_RECV, 1, 0, 35, 1),
        (OP_RECV, 1, 1, 2, 0),
    ],
)
def test_directed_eligibility(op, room, source, dest, expected):
    request = [op, room, source, 33, 38, 19, 99, dest, 77]
    assert pipecandidate_reference(request) == [77, expected]
