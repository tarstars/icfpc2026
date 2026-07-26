"""Physical gates for the composed LLM candidate-selection pipeline."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_candidateselect import (
    build_candidateselect_rig,
    candidateselect_reference,
)
from littleman.llm_packedcandidate import (
    missing_pipe_context,
    pack_pipe_context,
    pack_room_context,
)
from littleman.llm_pipeapply import OP_RECV, OP_SEND
from littleman.sim import Machine


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = candidateselect_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_candidateselect_rig()


def send_request(rng: random.Random, eligibility: tuple[int, int]) -> list[int]:
    addr = rng.randrange(256)
    event_addr = rng.randrange(3)
    event = -event_addr - 1
    context = pack_room_context(OP_SEND, event, 0, 16, 0, 16, addr)
    pipes = [
        pack_pipe_context(
            event if eligibility[slot] else -((event_addr + 1) % 3) - 1,
            rng.randrange(256),
            rng.randrange(256),
            rng.randrange(256),
        )
        for slot in range(2)
    ]
    return [context, pipes[0], context, pipes[1]]


def recv_request(rng: random.Random, eligibility: tuple[int, int]) -> list[int]:
    addr = rng.randrange(256)
    context = pack_room_context(OP_RECV, -1, 4, 12, 3 * 16 + 4, 13 * 16 + 4, addr)
    pipes = []
    for slot in range(2):
        row = rng.randrange(3, 13) if eligibility[slot] else rng.choice((1, 14))
        col = rng.randrange(4, 12) if eligibility[slot] else rng.choice((1, 14))
        pipes.append(
            pack_pipe_context(
                -1,
                rng.randrange(256),
                rng.randrange(256),
                row * 16 + col,
            )
        )
    return [context, pipes[0], context, pipes[1]]


def test_reference_supports_absent_second_slot():
    context = pack_room_context(OP_SEND, -1, 0, 16, 0, 16, 34)
    pipe = pack_pipe_context(-1, 51, 68, 85)
    assert candidateselect_reference(
        [context, pipe, context, missing_pipe_context()]
    ) == [0]


def test_generator_is_deterministic_and_server_safe(text):
    assert build_candidateselect_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_seeded_corpus(text):
    rng = random.Random(20260726)
    tokens = []
    options = ((1, 0), (0, 1), (1, 1))
    for _ in range(500):
        eligibility = rng.choice(options)
        maker = rng.choice((send_request, recv_request))
        tokens.extend(maker(rng, eligibility))
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
