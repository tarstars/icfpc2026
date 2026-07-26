"""Physical gates for normalized-pipe frame updates."""

from __future__ import annotations

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_pipeframe import (
    build_pipeframe_rig,
    pipeframe_reference,
)
from littleman.llm_pipetrace import PIPE_END
from littleman.llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES
from littleman.sim import Machine


def record(cells, bits, mask, values=()):
    body = [item for pair in zip(cells, bits, strict=True) for item in pair]
    return [
        100,
        *body,
        PIPE_DEST_STATE,
        25,
        PIPE_MASK,
        mask,
        PIPE_VALUES,
        len(values),
        *values,
        PIPE_END,
    ]


RECORDS = [
    record([0, 1], [8, 4], 1),
    record([17, 18, 19], [16, 8, 4], 21, [-9, 0]),
    record(list(range(20)), [1 << bit for bit in range(20, 0, -1)], 0xAAAAA),
]


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = pipeframe_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipeframe_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipeframe_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_pipe_frames(text):
    tokens = [item for pipe in RECORDS * 20 for item in pipe]
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=10_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
