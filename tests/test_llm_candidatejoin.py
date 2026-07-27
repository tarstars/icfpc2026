"""Physical gates for the packed-candidate join stage."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_candidatejoin import (
    build_candidatejoin_rig,
    candidatejoin_reference,
)
from littleman.llm_packedcandidate import pack_room_context
from littleman.llm_pipeapply import OP_RECV, OP_SEND
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = candidatejoin_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_candidatejoin_rig()


def context(addr: int, op: int = OP_SEND) -> int:
    return pack_room_context(op, -1, 0, 16, 0, 16, addr)


def test_reference_records_and_truncation():
    assert candidatejoin_reference([context(73), 11, 1, context(73), 22, 0]) == [
        73,
        1,
        0,
        11,
        22,
    ]
    with pytest.raises(ValueError, match="truncated"):
        candidatejoin_reference([context(0)])


def test_generator_is_deterministic_and_server_safe(text):
    assert build_candidatejoin_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_seeded_corpus(text):
    rng = random.Random(20260726)
    tokens = []
    for _ in range(2_000):
        addr = rng.randrange(256)
        room = context(addr, rng.choice((OP_SEND, OP_RECV)))
        tokens.extend(
            (
                room,
                rng.randrange(256),
                rng.randrange(2),
                room,
                rng.randrange(256),
                rng.randrange(2),
            )
        )
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
