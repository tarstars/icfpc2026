"""Physical parity for the packed indexed-action candidate service."""

from __future__ import annotations

import random

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_packedcandidate import (
    build_packedcandidate_rig,
    pack_pipe_context,
    pack_room_context,
    packedcandidate_reference,
    unpack_pipe_context,
    unpack_room_context,
)
from littleman.llm_pipeapply import OP_RECV, OP_SEND
from littleman.sim import Machine


def request(
    op,
    event_addr,
    bounds,
    addr,
    source_addr,
    head,
    tail,
    dest,
):
    left, right, top, bottom = bounds
    return [
        pack_room_context(op, -(event_addr + 1), left, right, top, bottom, addr),
        pack_pipe_context(-(source_addr + 1), head, tail, dest),
    ]


def corpus(seed=20260726, count=2_000):
    rng = random.Random(seed)
    tokens = []
    for _ in range(count):
        row = rng.randrange(1, 15)
        left_col = rng.randrange(0, 14)
        right_col = rng.randrange(left_col + 1, 16)
        top_row = rng.randrange(0, row)
        bottom_row = rng.randrange(row + 1, 16)
        bounds = (
            row * 16 + left_col,
            row * 16 + right_col,
            top_row * 16 + left_col,
            bottom_row * 16 + left_col,
        )
        tokens.extend(
            request(
                rng.randrange(2),
                rng.randrange(256),
                bounds,
                rng.randrange(256),
                rng.randrange(256),
                rng.randrange(256),
                rng.randrange(256),
                rng.randrange(256),
            )
        )
    return tokens


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = packedcandidate_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_packedcandidate_rig()


def test_pack_roundtrips():
    room = pack_room_context(OP_RECV, -256, 17, 30, 1, 241, 255)
    assert unpack_room_context(room) == (OP_RECV, -256, 17, 30, 1, 241, 255)
    pipe = pack_pipe_context(-256, 0, 255, 128)
    assert unpack_pipe_context(pipe) == (255, 0, 255, 128)


def test_directed_send_and_receive_edges():
    bounds = (5 * 16 + 2, 5 * 16 + 9, 2 * 16 + 2, 8 * 16 + 2)
    tokens = [
        *request(OP_SEND, 17, bounds, 88, 17, 4, 9, 0),
        *request(OP_SEND, 17, bounds, 88, 18, 5, 10, 0),
        *request(OP_RECV, 17, bounds, 88, 1, 4, 9, 2 * 16 + 7),
        *request(OP_RECV, 17, bounds, 88, 1, 4, 10, 9 * 16 + 7),
    ]
    assert packedcandidate_reference(tokens) == [4, 1, 5, 0, 9, 1, 10, 0]


def test_generator_is_deterministic_and_server_safe(text):
    assert build_packedcandidate_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_seeded_corpus(text):
    tokens = corpus()
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
