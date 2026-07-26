"""Physical gates for one selected LLM pipe operation."""

from __future__ import annotations

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_pipeaction import parse_fetched_state, serialize_fetched_state
from littleman.llm_pipeapply import (
    OP_RECV,
    OP_SEND,
    build_pipeapply_rig,
    pipeapply_reference,
)
from littleman.llm_pipetrace import PIPE_END
from littleman.llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES
from littleman.sim import Machine


def pipe_record(mask, values):
    return [
        100,
        10,
        8,
        11,
        4,
        12,
        2,
        PIPE_DEST_STATE,
        25,
        PIPE_MASK,
        mask,
        PIPE_VALUES,
        len(values),
        *values,
        PIPE_END,
    ]


CASES = [
    (OP_SEND, 7, pipe_record(1, [])),
    (OP_SEND, 0, pipe_record(1, [])),
    (OP_SEND, -9, pipe_record(9, [41])),
    (OP_RECV, 123, pipe_record(3, [-7])),
    (OP_RECV, 123, pipe_record(1, [])),
    (OP_RECV, 123, pipe_record(5, [88])),
]


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = pipeapply_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipeapply_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipeapply_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize(("op", "value", "record"), CASES)
def test_physical_pipe_operations(text, op, value, record):
    tokens = [op, value, *record]
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=1_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_action_pipe_round_trip_helpers():
    fetched = [
        -18,
        16,
        22,
        0,
        64,
        1,
        17,
        0,
        0,
        17,
        0,
        *pipe_record(3, [99]),
        -2000,
        -17,
        25,
        31,
        9,
        73,
        1,
        26,
        0,
        0,
        26,
        0,
        -2000,
        -1000,
    ]
    rooms, pipes = parse_fetched_state(fetched)
    assert serialize_fetched_state(rooms, pipes) == fetched
